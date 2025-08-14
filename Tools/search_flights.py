import asyncio, sys, os
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError  # type: ignore
from typing import Dict, Any, Optional, Tuple, List, Literal
import re
from datetime import datetime
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Utils.session_manager import create_session, close_session, get_session, SESSIONS
from Utils.schemas import (
    FlightSearchInput, SearchFlightsResult, FlightItem,
    GetFlightURLsInput, GetFlightURLsResult, BookingOption,
    CloseSessionInput
)

# --- Helper Functions ---
async def wait_for_element_to_appear(
    page: Page, selector: str, timeout_ms: int = 10000, check_interval_ms: int = 500
) -> bool:
    """
    Waits for a specific element to appear on the page within a timeout period.

    Args:
        page (Page): The Playwright page instance or locator.
        selector (str): CSS selector of the target element.
        timeout_ms (int, optional): Maximum wait time in milliseconds. Defaults to 10000.
        check_interval_ms (int, optional): Interval between checks in milliseconds. Defaults to 500.

    Returns:
        bool: True if the element appears before timeout, False otherwise.
    """
    max_checks = timeout_ms // check_interval_ms
    
    for attempt in range(max_checks):
        if await page.locator(selector).count() > 0:
            if await page.locator(selector).first.is_visible():
                return True
        await asyncio.sleep(check_interval_ms / 1000)
    return False


def clean_price_string(price_str: str) -> int:
    """
    Cleans a price string (e.g., 'Rp41,724,888') and converts it to an integer.
    Removes 'Rp' prefix and commas.
    """
    # Remove 'Rp' and all commas
    cleaned_price = re.sub(r'[Rp,.]', '', price_str)
    try:
        return int(cleaned_price)
    except ValueError:
        print(f"Warning: Could not convert price '{price_str}' to integer.")
        return float('inf') # Return infinity for prices that cannot be parsed


def convert_duration_to_minutes(duration_str: str) -> int:
    """
    Converts a flight duration string (e.g., '18 hr 5 min') to total minutes.
    """
    hours = 0
    minutes = 0

    # Match hours (e.g., "18 hr" or "1 hr")
    hour_match = re.search(r'(\d+)\s*hr', duration_str)
    if hour_match:
        hours = int(hour_match.group(1))

    # Match minutes (e.g., "5 min" or "55 min")
    min_match = re.search(r'(\d+)\s*min', duration_str)
    if min_match:
        minutes = int(min_match.group(1))
    
    total_minutes = (hours * 60) + minutes
    return total_minutes


def parse_dates(input_dates: str, default_year: int = None):
    """
    Accepts date input in various string formats and converts it to a datetime object.
    If no year is specified, it uses the current year or the given default_year.
    
    Examples of supported formats:
    - "2025-07-13"
    - "13/07/2025"
    - "July 13"
    - "13 July"
    - "13 Jul"
    - "Jul 13, 2025"
    - "13-07"
    """

    if input_dates is None:
        raise ValueError("Date input cannot be None. Please provide a valid date string.")
    input_dates = input_dates.strip()
    year = default_year or datetime.now().year
        
    candidate_format = [
        ("%Y-%m-%d", False),
        ("%d/%m/%Y", False),
        ("%B %d, %Y", False),
        ("%d %B %Y", False),
        ("%d %b %Y", False),
        ("%b %d, %Y", False),
        ("%B %d", True),
        ("%d %B", True),
        ("%d %b", True),
        ("%m-%d", True),
        ("%d/%m", True),
    ]

    for fmt, need_year in candidate_format:
        try:
            if need_year:
                input_dates = f"{input_dates} {year}"
                return datetime.strptime(input_dates, fmt + " %Y")
            else:
                return datetime.strptime(input_dates, fmt)
        except ValueError:
            continue

    raise ValueError(f"Date format not recognized: '{input_dates}'")


# --- Core Playwright Setup ---
async def fetch_page(url: str) -> Tuple[async_playwright, Browser, Page]:
    """
    Launches Playwright browser and navigates to the page.

    Args:
        url (str): URL of the page to fetch.

    Returns:
        tuple: (playwright, browser, page) if successful.
    """

    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True)  # Set headless to False for debugging
    page = await browser.new_page()
    headers = {
        "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0"
    }
    await page.set_extra_http_headers(headers)
    await page.goto(url)

    # Click the dropdown trigger for flight type
    await wait_for_element_to_appear(page, "div.VfPpkd-aPP78e", timeout_ms=10000)
    await page.locator("div.VfPpkd-aPP78e").first.click()

    # Wait for the options to appear and select the desired flight type
    await wait_for_element_to_appear(page, "li[role='option']", timeout_ms=10000)
    await page.wait_for_timeout(500)  # Ensure the options are fully loaded
    await page.locator(f"li[role='option']:has-text('One way')").first.click()

    return p, browser, page


# --- Interaction Functions ---
async def select_flight_class(page: Page, flight_class: str = "Economy"):
    """ Selects the flight class from the dropdown menu.
    Args:
        page (Page): The Playwright page instance.
        flight_class (str): Class of flight to select ("Economy", "Premium economy", "Business", "First").
    """
    try:
        # Click the dropdown trigger for flight class (assuming it's the second one)
        # It's highly recommended to use a more specific selector if possible,
        # e.g., using aria-label or a parent container.
        await wait_for_element_to_appear(page, "div.VfPpkd-aPP78e", timeout_ms=10000)
        await page.locator("div.VfPpkd-aPP78e").nth(1).click()

        # Wait for the options to appear and select the desired flight class
        await wait_for_element_to_appear(page, "li[role='option']", timeout_ms=5000)
        await page.locator(f"li[role='option']:has-text('{flight_class}')").first.click()
        
        print(f"✅ Flight class {flight_class} selected successfully.")
    except Exception as e:
        print(f"❌ Error selecting flight class: {e}")
        raise


async def fill_origin(page: Page, origin: str):
    """ Fills the origin input field with the specified origin.
    Args:
        page (Page): The Playwright page instance.
        origin (str): The origin to fill in the input field.
    """
    try:
        origin_input_selector = "input[aria-label='Where from?']"
        await wait_for_element_to_appear(page, origin_input_selector, timeout_ms=10000)
        
        origin_input_locator = page.locator(origin_input_selector)
        await origin_input_locator.fill(origin)
        
        # Wait for the suggestion to appear and click it.
        origin_selector = f"//li[@role='option'][contains(., '{origin}')]"
        if await wait_for_element_to_appear(page, origin_selector, timeout_ms=5000):
            origin_option = page.locator(origin_selector) 
            await origin_option.first.click()
            print(f"✅ Origin {origin} filled successfully.")
        else:
            raise ValueError(f"{origin} is not exist")
    except Exception as e:
        print(f"❌ Error filling origin: {e}")
        raise


async def fill_destination(page: Page, destination: str):
    """ Fills the destination input field with the specified destination.
    Args:
        page (Page): The Playwright page instance.
        destination (str): The destination to fill in the input field.
    """
    try:
        # Crucial: The space after 'Where to?' is important for the selector.
        destination_input_selector = "input[aria-label='Where to? ']"
        await wait_for_element_to_appear(page, destination_input_selector, timeout_ms=15000)
        
        destination_input_locator = page.locator(destination_input_selector)
        await destination_input_locator.fill(destination)

        # Wait for the suggestion to appear and click it.
        destination_selector = f"//li[@role='option'][contains(., '{destination}')]"
        if await wait_for_element_to_appear(page, destination_selector, timeout_ms=5000):
            destination_option = page.locator(destination_selector)
            await destination_option.first.click()
            print(f"✅ Destination {destination} filled successfully.")
        else:
            raise ValueError(f"❌ Error filling destination: {destination} is not exist")
    except Exception as e:
        print(f"❌ Error filling destination: {e}")
        raise


async def set_dates(page: Page, departure_date: str):
    """ Sets the departure and optional return dates in the date picker.
    Args:
        page (Page): The Playwright page instance.
        departure_date (str): The departure date. (e.g., July 15)
    """
    
    if parse_dates(departure_date) < datetime.now():
        raise ValueError("❌ Departure date is in the past. Please provide a valid future date.")
    try:
        departure_selector = "input[aria-label='Departure']"
        if await wait_for_element_to_appear(page, departure_selector):
            # Ensure the initial departure input field is ready
            # Click the departure input to open the date picker
            # Note: .nth(0) usually targets the visible input field to open the calendar.
            departure_input = page.locator(departure_selector).nth(0)
            if await departure_input.is_visible() and await departure_input.is_enabled():
                element_handle = await departure_input.element_handle()
                if element_handle:
                    await element_handle.evaluate("element => element.click()")
                else:
                    print("🚨 Date can not be set")
                    return
                    # await departure_input.click()
                    # ...continue the process...
            else:
                print("🚨 Date can not be set")
                return
            
            await wait_for_element_to_appear(page, "div.WhDFk Io4vne") # wait for calendar to visible clearly

            # Assuming .nth(1) is the actual text input field within the date picker for departure
            await page.locator(departure_selector).nth(1).fill(departure_date)
            await page.keyboard.press("Enter")
            await page.keyboard.press("Enter")
            print(f"✅ The date has been set successfully to {departure_date}.")

        else:
            print("🚨 Date can not be set")
    except Exception as e:
        print(f"❌ Error setting departure or return date: {e}")
        raise


async def set_number_of_passengers(
        page: Page, 
        adults: int = 1, 
        children: int = 0, 
        infants_on_lap: int = 0, 
        infants_in_seat: int = 0
    ):
    """ Sets the number of passengers in the flight search.
    Args:
        page (Page): The Playwright page instance.
        adults (int): Number of adults.
        children (int): Number of children.
        infants_on_lap (int): Number of infants on lap.
        infants_in_seat (int): Number of infants in seat.
    """
    passengers = {
        "adult": adults,
        "child": children,
        "infant in seat": infants_in_seat,
        "infant on lap": infants_on_lap
    }
    try:
        passenger_selector = "div.VfPpkd-RLmnJb"
        await wait_for_element_to_appear(page, passenger_selector, timeout_ms=10000)
        await page.get_by_role("button", name="1 passenger").click()
        for passenger_type, count in passengers.items():
            if count > 0:
                # Initialize current_count based on default UI state
                current_count = 1 if passenger_type == "adult" else 0

                # Click 'Add' button until target count is reached
                while current_count < count:
                    add_button_selector = f"button[aria-label='Add {passenger_type}']"
                    await page.locator(add_button_selector).click()
                    current_count += 1
        
        # Close the passenger menu by clicking the "Done" button
        await page.get_by_role("button", name="Done").click() # close the passenger menu
        print("✅ Number of passengers set successfully. ")
    except Exception as e:
        print(f"❌ Error setting number of passengers: {e}")
        raise
    

async def get_flights(page: Page, flight_class: str = "Economy") -> Tuple[Dict[str, Any], str]:
    """ Retrieves flight results from the page.
    Args:
        page (Page): The Playwright page instance.
    Returns:
        Dict[str, Any]: A dictionary containing flight results.
    """
    flight_results = {}

    try:
        # Click the search button to initiate the flight search
        search_results_selector = "button[aria-label='Search']"
        await wait_for_element_to_appear(page, search_results_selector, timeout_ms=15000)
        if not await page.locator(search_results_selector).is_visible():
            print("🚨 No available flight for this search parameter")
            return flight_results, flight_class
        await page.locator(search_results_selector).click()
        await page.wait_for_timeout(5000)  # Wait for the search results to load

        # Handle searching progress if there are no result
        flight_class_used = flight_class
        if await page.locator("div[role='alert']:has-text('No results returned.')").is_visible():
            print(f"😢 There are no flights for this class. Changing flight class to Economy...")
            await select_flight_class(page, flight_class="Economy")
            await page.wait_for_load_state("networkidle", timeout=30000)
            flight_class_used = "Economy"

        # Wait for the flight results to appear
        top_flights_locator = await page.locator("li.pIav2d").all()
        
        limiter = 10  # Limit to the first 10 results for performance
        seen_details = set()
        for i, flight in enumerate(top_flights_locator):
            travel_detail = await flight.locator("div.JMc5Xc").first.get_attribute("aria-label")
            # print(f"✈️ Flight {i+1}: {travel_detail}", end="\n\n")
            if travel_detail not in seen_details:
                flight_results[f"Flight {i+1}"] = travel_detail
                seen_details.add(travel_detail)
            if i+1 >= limiter:
                break
            
        print(f"✅ Found {len(flight_results)} flights.") if len(flight_results) > 0 else print("❌ No departing flight found")
        return flight_results, flight_class_used
    except Exception as e:
        print(f"❌ Error retrieving departing flight: {e}")
        raise
    
        
# --- Parsing Functions ---
def parse_flight_results(flight_results: Dict[str, Any]) -> Dict[str, Any]:
    """ Parses flight results into a more structured format.
    Args:
        flight_results (Dict[str, Any]): Raw flight results dictionary.
    Returns:
        Dict[str, Any]: Parsed flight results dictionary.
    """
    parsed_results = {}
    if flight_results is None:
        print("❌ There is no flight to parse")
        return parsed_results
    
    for flight, details in flight_results.items():
        try:
            text = details.replace('\u202f', ' ')
            result = {}

            # price extraction
            price_m = re.search(r"From (\d+)", text)
            if price_m:
                price = f"Rp{int(price_m.group(1)):,}"
                result["price"] = price

            # number of stops extraction and airline extraction
            stops = None
            airlines = None
            stops_m = re.search(r"(Nonstop|\d+ stops?|1 stop) flight with ([\w\s,&]+?)\.", text)
            if stops_m:
                stops_str = stops_m.group(1)
                if stops_str == "Nonstop":
                    stops = 0
                elif stops_str == "1 stop":
                    stops = 1
                else:
                    stops = int(re.search(r"\d+", stops_str).group())
                airlines = [a.strip() for a in re.split(r' and |, ', stops_m.group(2))]
            result["stops"] = stops
            result["airlines"] = airlines

            # departure and arrival details extraction
            m = re.search(
                r"Leaves\s+(.*?)\s+at\s+([\d:]{1,2}:\d{2}\s*[AP]M)\s+on\s+(.+?)\s+and arrives at\s+(.*?)\s+at\s+([\d:]{1,2}:\d{2}\s*[AP]M)\s+on\s+(.+?)(?:\.| Total duration| Layover|$)",
                text.replace('\u202f', ' ')
            )
            if m:
                result['departure_airport'] = m.group(1)
                result['departure_time'] = m.group(2)
                result['departure_date'] = m.group(3)
                result['arrival_airport'] = m.group(4)
                result['arrival_time'] = m.group(5)
                result['arrival_date'] = m.group(6)
            else:
                result['departure_airport'] = result['departure_time'] = result['departure_date'] = None
                result['arrival_airport'] = result['arrival_time'] = result['arrival_date'] = None
            
            # total duration extraction
            duration_m = re.search(r"Total duration\s+([\d\s+hr\s+\d\s+min]+)\.", text)
            result['flight_duration'] = duration_m.group(1) if duration_m else None

            # layover extraction
            layover_pattern = re.compile(r"Layover \((\d+) of \d+\) is a ([\d\s+hrmin]+)(\s+overnight)? layover at (.*?)(?:\.|$)")
            layovers = []
            for lay in layover_pattern.finditer(text):
                layovers.append({
                    'layover_number': int(lay.group(1)),
                    'layover_duration': lay.group(2),
                    'overnight': bool(lay.group(3)),
                    'layover_airport': lay.group(4)
                })
            result['layovers'] = layovers if layovers else None
            # print(f"✈️ {flight} has been parsed successfully")
            parsed_results[flight] = result

            keys_allowed_to_be_none = ['layovers']
            if any(
                result.get(key) is None 
                for key in result.keys() 
                if key not in keys_allowed_to_be_none
            ):
                parsed_results[flight] = {"Error": "Flight details are not valid: mandatory field is None."}

        except Exception as e:
            # print(f"❌ Error parsing flight {flight}: {e}")
            # print(f"Raw details: {details}", end="\n\n")
            # parsed_results[flight] = {"Error": str(e)}
            raise

    return parsed_results

# --- URL Extraction Functions ---
async def extract_logo_url(page: Page) -> str:
    """Extract booking agent logo URL from style attribute."""
    logo_locator = page.locator("div[class='MnHIn P2UJoe']").first
    style_attr = await logo_locator.get_attribute("style") or ""
    match = re.findall(r"url\((.*?)\)", style_attr)
    return match[0] if match else ""

async def extract_price(page: Page) -> str:
    """Extract booking price, replacing non-breaking spaces."""
    price_locator = page.locator("div.ScwYP")
    if await wait_for_element_to_appear(page, "div.ScwYP"):
        price = await price_locator.inner_text()
        return price.replace("\u00A0", " ")
    return "Visit site for price"

async def extract_booking_name(page: Page, xpath: str, pattern: str) -> str:
    """Extract booking agent/provider name using an XPath and regex pattern."""
    name_locator = page.locator(xpath)
    booking_name = await name_locator.inner_text()
    match = re.findall(pattern, booking_name)
    return match[0].strip() if match else None

async def get_flight_urls(
    page: Page, 
    flight_results: Dict[str, Any], 
    flight_no: int = 1,
    popup_wait_ms: int = 3000, #wait time after popup appears (ms)
    max_providers: Optional[int] = 5
) -> List[Dict[str, str]]:
    """
    Collect all booking (merchant) URLs for one selected flight on Google Flights.
    """
    booking_options = []

    # Get selected flight detail
    detail = flight_results.get(f"Flight {flight_no}")
    if not detail:
        raise ValueError(f"There is no Flight {flight_no} in flight_results.")

    # Locate and click flight card
    flight_summary = page.locator(f'li.pIav2d div.JMc5Xc[aria-label="{detail}"]').first
    await flight_summary.scroll_into_view_if_needed()
    flight_card = flight_summary.locator("xpath=ancestor::li[contains(@class,'pIav2d')]").first
    await flight_card.click()

    # Case 1: No booking options
    if await page.locator(
        "div:has-text('We can’t find booking options for this itinerary. Try changing your flights to see booking options.')"
    ).is_visible():
        booking_options.append({
            "message": "We can’t find booking options for this itinerary. Try changing your flights to see booking options."
        })
        return booking_options

    # Case 2: Page error
    if await page.locator("h1.YAGsO:has-text('Oops, something went wrong.')").is_visible():
        await page.locator("span.VfPpkd-vQzf8d:has-text('Reload')").click()

    # Case 3: Booking options available
    await wait_for_element_to_appear(page, "div.gN1nAc")
    booking_cards = page.locator("div.gN1nAc")
    total_cards = await booking_cards.count()

    for idx in range(total_cards):
        if max_providers is not None and idx >= max_providers:
            break

        book = booking_cards.nth(idx)

        # Try continue/go to site/book buttons
        ctn_selector = "button:has-text('Continue'), button:has-text('Go to site'), button:has-text('Book')" 
        has_ctn = await wait_for_element_to_appear(page, ctn_selector)

        booking_option = {}

        if has_ctn:
            booking_option["logo_url"] = await extract_logo_url(page)
            booking_option["provider"] = await extract_booking_name(
                page,
                "//div[@class='ogfYpf AdWm1c' and contains(normalize-space(.), 'Book ') and contains(normalize-space(.), ' with')]",
                r"Book\s+with\s+(.+)"
            )
            booking_option["price"] = await extract_price(page)

            # Click and capture booking URL
            btn = book.locator(ctn_selector).first
            new_page = None
            try:
                async with page.context.expect_page(timeout=3000) as w:
                    await btn.click()
                new_page = await w.value
            except PlaywrightTimeoutError:
                try:
                    await asyncio.wait_for(page.wait_for_load_state("domcontentloaded"), timeout=8000)
                except asyncio.TimeoutError:
                    pass

            if new_page:
                await new_page.wait_for_load_state("load")
                await asyncio.sleep(popup_wait_ms / 1000)
                booking_option["booking_url"] = new_page.url
                await new_page.close()
            else:
                await asyncio.sleep(popup_wait_ms / 1000)
                booking_option["booking_url"] = page.url
                await page.go_back()
                await wait_for_element_to_appear(page, "div.gN1nAc")

        else:
            booking_option["logo_url"] = await extract_logo_url(page)
            booking_option["provider"] = await extract_booking_name(
                page,
                "//div[@class='ogfYpf AdWm1c' and contains(normalize-space(.), 'Call ') and contains(normalize-space(.), ' to book')]",
                r"Call\s+(.+)\s+to\s+book"
            )
            booking_option["price"] = await extract_price(page)
            booking_option["call_number"] = await page.locator("div.bcmwcd").inner_text()

        booking_options.append(booking_option)

    return booking_options

# ---------- Tool-ready functions (tinggal di-import di tools.py) ----------
BASE_URL = "https://www.google.com/travel/flights"

async def search_flights_tool_fn(
    origin: str,
    destination: str,
    departure_date: str,
    flight_class: Literal["Economy", "Business", "First", "Premium economy"] = "Economy",
    adults: int = 1,
    children: int = 0,
    infants_on_lap: int = 0,
    infants_in_seat: int = 0,
    headless: bool = True,
) -> SearchFlightsResult:
    """
    1) Create a new Playwright session (unclosed)
    2) Run a ONE-WAY search flow
    3) Save the raw_flights in the session so that subsequent tools can use them
    4) Return the session_id + a summary list of flights (for the user to select)
    Args:
        origin (str): The departure city/airport.
        destination (str): The arrival city/airport.
        departure_date (str): The desired departure date (e.g., "July 15").
        flight_class (str): Class of flight ("Economy", "Premium economy", etc.). Defaults to "Economy".
        adults (int): Number of adult passengers. Defaults to 1.
        children (int): Number of children passengers. Defaults to 0.
        infants_on_lap (int): Number of infants on lap. Defaults to 0.
        infants_in_seat (int): Number of infants in seat. Defaults to 0.
        headless (bool): Whether to run the browser in headless mode. Defaults to True.
    Returns:
        SearchFlightsResult: Result of the search.
            session_id (str | None): Reusable session id when flights are found; None if nothing found.
            flights (List[FlightItem]): Human-readable summaries with 1-based indices.
            flight_class_used (str | None): Cabin actually used by Google Flights for these results.
            message (str): Status text (e.g., "Found N flights. Pick one by index (1..N).").
    """
    params = FlightSearchInput(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        flight_class=flight_class,
        adults=adults,
        children=children,
        infants_on_lap=infants_on_lap,
        infants_in_seat=infants_in_seat,
        headless=headless,
    )
    sid = await create_session(headless=params.headless)
    try:
        sess = get_session(sid)
        page = sess.page

        # Buka halaman awal (pakai halaman session; kita TIDAK pakai fetch_page agar tidak double-launch)
        await page.goto(BASE_URL)

        # Click the dropdown trigger for flight type
        await wait_for_element_to_appear(page, "div.VfPpkd-aPP78e", timeout_ms=10000)
        await page.locator("div.VfPpkd-aPP78e").first.click()

        # Wait for the options to appear and select the desired flight type
        await wait_for_element_to_appear(page, "li[role='option']", timeout_ms=10000)
        await page.wait_for_timeout(500)  # Ensure the options are fully loaded
        await page.locator(f"li[role='option']:has-text('One way')").first.click()

        # Set number of passengers (only if different from default)
        if params.adults > 1 or params.children > 0 or params.infants_on_lap > 0 or params.infants_in_seat > 0:
            await set_number_of_passengers(page, params.adults, params.children, params.infants_on_lap, params.infants_in_seat)
        else:
            print("✅ No additional passengers to set.")

        # Select flight class (only if different from default)
        if params.flight_class != "Economy":
            await select_flight_class(page, params.flight_class)
        else:
            print("✅ Flight class is Economy, no selection needed.")
        
        await fill_origin(page, params.origin)
        await fill_destination(page, params.destination)
        
        await set_dates(page, params.departure_date)

        # Get departing flights
        departing_res, flight_class_used = await get_flights(page)
        parsed = parse_flight_results(departing_res)

        if not parsed:
            await close_session(sid)
            return SearchFlightsResult(session_id=None, flights=[], flight_class_used=None,
                                       message="No flights found for the given criteria.")

        # store RAW in session so get_flight_urls_tool can be used without large payload
        sess.data["raw_flights"] = departing_res

        items = [FlightItem(index=i + 1, summary=summary)
         for i, summary in enumerate(departing_res.values())]
        list_text = "\n".join(f"{it.index}. {it.summary}" for it in items)
        return SearchFlightsResult(
            session_id=sid,
            flights=items,
            flight_class_used=flight_class_used,
            message=
            f"Found {len(items)} flights:\n{list_text}\n\n"
            f"Pick one by index (1..{len(items)}) and I'll fetch booking URLs."

        )
    except Exception:
        # if error, clean the newly created session
        try: await close_session(sid)
        except: pass
        raise

async def get_flight_urls_tool_fn(session_id: str,
    flight_no: int = 1,
    max_providers: Optional[int] = 5,
    popup_wait_timeout: int = 10000,
) -> GetFlightURLsResult:
    """
    Using an existing session created by `search_flights_tool_fn`, open the selected
    flight's offers panel and collect booking (merchant) options and their URLs.

    Args:
        session_id (str): Session id returned by `search_flights_tool_fn`.
        flight_no (int): 1-based index of the flight to open. Default 1.
        max_providers (int | None): Maximum number of booking providers to return. Default 5.
        popup_wait_timeout (int): Milliseconds to wait after a new tab/pop-up appears
                                    before reading its URL. Default 10000.

    Returns:
        GetFlightURLsResult: The selected flight number and its available booking options.
            flight_no (int): Echo of the requested flight number.
            options (List[BookingOption]): List of providers with metadata:
                provider (str | None): Booking agent/merchant name.
                price (str | None): Price text as displayed (may include currency).
                logo_url (str | None): Logo image URL if available.
                call_number (str | None): Phone number when booking is by call.
                booking_url (str | None): Direct URL captured from the provider button/tab.

    Raises:
        RuntimeError: If the session has no `raw_flights` (you must run search first).
        ValueError: If `flight_no` does not correspond to any parsed flight.
    """
    params = GetFlightURLsInput(
        session_id=session_id,
        flight_no=flight_no,
        max_providers=max_providers,
        popup_wait_timeout=popup_wait_timeout,
    )
    sess = get_session(params.session_id)
    page = sess.page
    raw = sess.data.get("raw_flights")
    if not raw:
        raise RuntimeError("Missing raw_flights in session. Run search_flights first.")

    options = await get_flight_urls(
        page,
        raw,
        flight_no=params.flight_no,
        max_providers=params.max_providers,
        popup_wait_ms=params.popup_wait_timeout,
    )
    return GetFlightURLsResult(
        flight_no=params.flight_no,
        options=[BookingOption(**o) for o in options]
    )

async def close_session_tool_fn(session_id: str) -> str:
    """
    Close and dispose a previously created Playwright session.

    Args:
        session_id (str): The id of the session to close.

    Returns:
        str: The message "Session closed." (returned even if the session id
             was not found or had already been closed).
    """
    params = CloseSessionInput(session_id=session_id)
    await close_session(params.session_id)
    return "Session closed."


if __name__ == "__main__":
    async def _demo():
        sid = None
        try:
            res = await search_flights_tool_fn(
                FlightSearchInput(
                    origin="Seoul",
                    destination="Bangkok",
                    departure_date="August 31",
                    flight_class="Economy",
                    adults=2,
                    children=1,
                    infants_on_lap=1,
                    infants_in_seat=1,
                    headless=True,
                )
            )
            sid = res.session_id
        finally:
            if sid:
                await close_session_tool_fn(CloseSessionInput(session_id=sid))

    asyncio.run(_demo())
