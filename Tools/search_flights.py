import asyncio, sys, os
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError  # type: ignore
from typing import Dict, Any, Optional, Tuple, List, Literal, Union
import re
from datetime import datetime
from uuid import uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Utils.session_manager import create_session, close_session, get_session
from Utils.schemas import FlightSearchInput, GetFlightURLsInput, SelectCurrencyInput, CloseSessionInput
from Utils.logger import setup_logger

logger = setup_logger(name="search_flights", log_level="INFO")
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
    base = input_dates.strip()
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
            probe = f"{base} {year}" if need_year else base
            return datetime.strptime(probe, fmt + (" %Y" if need_year else ""))
        except ValueError:
            continue

    raise ValueError(f"Date format not recognized: '{input_dates}'")


# --- Interaction Functions ---
async def get_currency(page: Page) -> Optional[str]:
    """
    Extracts the currency symbol from the page.
    """
    # Get default price
    try:
        await wait_for_element_to_appear(page, "span.VfPpkd-vQzf8d", timeout_ms=10000)
        currency = await page.locator("span.twocKe").nth(2).inner_text()
        logger.info(f"Currency detected : {currency}.")
        return currency
    except Exception as e:
        logger.warning(f"Warning: Could not find price element on page: {e}")
        return None
    

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
        
        logger.info(f"Flight class {flight_class} selected successfully.")
    except Exception as e:
        logger.exception(f"Error selecting flight class: {e}")
        # raise


async def fill_origin(page: Page, origin: str):
    """ Fills the origin input field with the specified origin.
    Args:
        page (Page): The Playwright page instance.
        origin (str): The origin to fill in the input field.
    """
    try:
        origin_input_selector = "input[aria-label^='Where from?']" 
        await wait_for_element_to_appear(page, origin_input_selector, timeout_ms=10000)
        
        origin_input_locator = page.locator(origin_input_selector)
        await origin_input_locator.fill(origin)
        
        # Wait for the suggestion to appear and click it.
        origin_selector = f"//li[@role='option'][contains(., '{origin}')]"
        if await wait_for_element_to_appear(page, origin_selector, timeout_ms=5000):
            origin_option = page.locator(origin_selector) 
            await origin_option.first.click()
            logger.info(f"Origin {origin} filled successfully.")
        else:
            raise ValueError(f"{origin} is not exist")
    except Exception as e:
        logger.exception(f"Error filling origin: {e}")
        # raise


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
            logger.info(f"Destination {destination} filled successfully.")
        else:
            raise ValueError(f"{destination} is not exist")
    except Exception as e:
        logger.exception(f"Error filling destination: {e}")
        # raise


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
                    logger.warning("Date can not be set")
                    return
                    # await departure_input.click()
                    # ...continue the process...
            else:
                logger.warning("🚨 Date can not be set")
                return
            
            await wait_for_element_to_appear(page, "div.WhDFk Io4vne") # wait for calendar to visible clearly

            # Assuming .nth(1) is the actual text input field within the date picker for departure
            await page.locator(departure_selector).nth(1).fill(departure_date)
            await page.keyboard.press("Enter")
            await page.keyboard.press("Enter")
            logger.info(f"The date has been set successfully to {departure_date}.")

        else:
            logger.warning("Date can not be set")
    except Exception as e:
        logger.exception(f"Error setting departure or return date: {e}")
        # raise


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
        logger.info("Number of passengers set successfully. ")
    except Exception as e:
        logger.exception(f"Error setting number of passengers: {e}")
        # raise
    

async def get_flights(page: Page, flight_class: str = "Economy", limiter: int = 10) -> Tuple[Dict[str, Any], str, Optional[str]]:
    """ Retrieves flight results from the page.
    Args:
        page (Page): The Playwright page instance.
        flight_class (str): The flight class used in the search.
        limiter (int): Maximum number of flight results to retrieve.
    Returns:
        Tuple[Dict[str, Any], str, str]: A tuple containing flight results, flight class and currency.
    """
    global  global_limiter
    global_limiter = limiter
    flight_results = {}

    try:
        # Ensure currency is set
        currency = await get_currency(page)

        # Click the search button to initiate the flight search
        search_results_selector = "button[aria-label='Search']"
        await wait_for_element_to_appear(page, search_results_selector, timeout_ms=15000)
        if not await page.locator(search_results_selector).is_visible():
            logger.warning("No available flight for this search parameter")
            return flight_results, flight_class
        await page.locator(search_results_selector).click()
        await page.wait_for_timeout(5000)  # Wait for the search results to load

        # Handle searching progress if there are no result
        flight_class_used = flight_class
        if await page.locator("div[role='alert']:has-text('No results returned.')").is_visible():
            logger.warning(f"There are no flights for this class. Changing flight class to Economy...")
            await select_flight_class(page, flight_class="Economy")
            await page.wait_for_load_state("networkidle", timeout=30000)
            flight_class_used = "Economy"

        # Wait for the flight results to appear
        top_flights_locator = await page.locator("li.pIav2d").all()
        
        seen_details = set()
        for i, flight in enumerate(top_flights_locator):
            travel_detail = await flight.locator("div.JMc5Xc").first.get_attribute("aria-label")
            # logger.(f"✈️ Flight {i+1}: {travel_detail}", end="\n\n")
            if travel_detail not in seen_details:
                flight_results[f"Flight {i+1}"] = travel_detail
                seen_details.add(travel_detail)
            if i+1 >= limiter:
                break
            
        logger.info(f"Found {len(flight_results)} flights.") if len(flight_results) > 0 else logger.error("No departing flight found")
        return (flight_results, flight_class_used, currency)
    except Exception as e:
        logger.error(f"Error retrieving departing flight: {e}")
        raise
    
        
# --- Parsing Functions ---
def parse_flight_results(flight_results: Dict[str, Any], currency: Optional[str] = None) -> Dict[str, Any]:
    """ Parses flight results into a more structured format.
    Args:
        flight_results (Dict[str, Any]): Raw flight results dictionary.
        currency (Optional[str]): The currency symbol used in the prices (optional).
    Returns:
        Dict[str, Any]: Parsed flight results dictionary.
    """
    parsed_results = {}
    if flight_results is None:
        logger.warning("There is no flight to parse")
        return parsed_results
    
    for flight, details in flight_results.items():
        try:
            text = details.replace('\u202f', ' ')
            result = {}

            # price extraction
            price_m = re.search(r"From (\d+)", text)
            if price_m:
                prefix = f"{currency} " if currency else ""
                price = f"{prefix}{int(price_m.group(1)):,}"
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
            # logger.(f"✈️ {flight} has been parsed successfully")
            parsed_results[flight] = result

            keys_allowed_to_be_none = ['layovers', 'airlines', 'flight_duration']
            if any(
                result.get(key) is None 
                for key in result.keys() 
                if key not in keys_allowed_to_be_none
            ):
                parsed_results[flight] = {"Error": "Flight details are not valid: mandatory field is None."}

        except Exception as e:
            logger.error(f"Error parsing flight {flight}: {e}")
            # logger.(f"Raw details: {details}", end="\n\n")
            # parsed_results[flight] = {"Error": str(e)}
            # raise

    return parsed_results

# --- URL Extraction Functions ---
async def extract_logo_url(root) -> str:
    """Extract booking agent logo URL from style attribute."""
    logo_locator = root.locator("div[class='MnHIn P2UJoe']").first
    style_attr = await logo_locator.get_attribute("style") or ""
    match = re.findall(r"url\((.*?)\)", style_attr)
    return match[0] if match else ""

async def extract_price(root) -> str:
    """Extract booking price, replacing non-breaking spaces."""
    price_locator = root.locator("div.ScwYP")
    if await wait_for_element_to_appear(root, "div.ScwYP"):
        price = await price_locator.inner_text()
        return price.replace("\u00A0", " ")
    return "Visit site for price"

async def extract_booking_name(root, xpath: str, pattern: str) -> str:
    """Extract booking agent/provider name using an XPath and regex pattern."""
    name_locator = root.locator(xpath)
    booking_name = await name_locator.inner_text()
    match = re.findall(pattern, booking_name)
    return match[0].strip() if match else None

flight_url_logger = setup_logger(name="get_flight_urls", log_level="INFO")
async def get_flight_urls(
    page: Page, 
    flight_results: Dict[str, Any], 
    flight_no: Union[int,str] = 1,
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
        raise ValueError(f"❌ There is no Flight {flight_no} in flight_results.")

    try:
        # Locate and click flight card
        flight_summary = page.locator(f'li.pIav2d div.JMc5Xc[aria-label="{detail}"]').first
        await flight_summary.scroll_into_view_if_needed()
        flight_card = flight_summary.locator("xpath=ancestor::li[contains(@class,'pIav2d')]").first
        await flight_card.click()
        flight_url_logger.info("Flight card clicked successfully.")

        # Case 1: No booking options
        if await page.locator(
            "div:has-text('We can’t find booking options for this itinerary. Try changing your flights to see booking options.')"
        ).is_visible():
            booking_options.append({
                "message": "We can’t find booking options for this itinerary. Try changing your flights to see booking options."
            })
            flight_url_logger.warning("No booking options found for this flight.")
            await page.go_back()
            return booking_options

        # Case 2: Page error
        if await page.locator("h1.YAGsO:has-text('Oops, something went wrong.')").is_visible():
            await page.locator("span.VfPpkd-vQzf8d:has-text('Reload')").click()
            flight_url_logger.info("Page reloaded due to error.")

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
            has_ctn = await wait_for_element_to_appear(book, ctn_selector)

            booking_option = {}

            if has_ctn:
                booking_option["logo_url"] = await extract_logo_url(book)
                flight_url_logger.info("Logo URL extracted successfully.")
                booking_option["provider"] = await extract_booking_name(
                    book,
                    "//div[@class='ogfYpf AdWm1c' and contains(normalize-space(.), 'Book ') and contains(normalize-space(.), ' with')]",
                    r"Book\s+with\s+(.+)"
                )
                flight_url_logger.info("Provider name extracted successfully.")
                booking_option["price"] = await extract_price(book)
                flight_url_logger.info("Price extracted successfully.")
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
                    flight_url_logger.info(f"Booking URL extracted successfully")
                    await new_page.close()
                else:
                    await asyncio.sleep(popup_wait_ms / 1000)
                    booking_option["booking_url"] = page.url
                    await page.go_back()
                    flight_url_logger.info("Returned to the main page after no popup appeared.")
                    await wait_for_element_to_appear(page, "div.gN1nAc")

            else:
                booking_option["logo_url"] = await extract_logo_url(book)
                flight_url_logger.info("Logo URL extracted successfully.") 
                booking_option["provider"] = await extract_booking_name(
                    book,
                    "//div[@class='ogfYpf AdWm1c' and contains(normalize-space(.), 'Call ') and contains(normalize-space(.), ' to book')]",
                    r"Call\s+(.+)\s+to\s+book"
                )
                flight_url_logger.info("Provider name extracted successfully.")
                booking_option["price"] = await extract_price(book)
                flight_url_logger.info("Price extracted successfully.")
                booking_option["call_number"] = await book.locator("div.bcmwcd").inner_text()
                flight_url_logger.info("Call number extracted successfully.")

            booking_options.append(booking_option)
        await page.go_back()
        flight_url_logger.info(f"Extracted {len(booking_options)} booking options successfully.")
    
    except Exception as e:
        booking_options = "Failed to fetch links."
        flight_url_logger.error(e)
        return booking_options
    
    return booking_options

# ---------- Tool-ready functions ----------
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
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    1) Create a new Playwright session (unclosed) or reuse an existing one
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
        Dict[str, Any]: A dictionary containing:
            session_id (str | None): Reusable session id when flights are found; None if nothing found.
            flights (Dict[str, Any] | None): Flights search results containing price, airline, number of stops, etc.
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
        session_id=session_id,
    )
    
    sid = await create_session(headless=params.headless) if params.session_id is None else params.session_id

    try:
        sess = get_session(sid)
        page = sess.page

        # Open Google Flights
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
            logger.info("No additional passengers to set.")

        # Select flight class (only if different from default)
        if params.flight_class != "Economy":
            await select_flight_class(page, params.flight_class)
        else:
            logger.info("Flight class is Economy, no selection needed.")
        
        await fill_origin(page, params.origin)
        await fill_destination(page, params.destination)
        
        await set_dates(page, params.departure_date)

        # Get departing flights
        departing_res, flight_class_used, currency = await get_flights(page)
        parsed_flights = parse_flight_results(departing_res, currency)

        if not parsed_flights:
            await close_session(sid)
            return {
                "session_id": None, 
                "flights": None, 
                "flight_class_used": None,
                "currency": None,
                "message": "No flights found for the given criteria."
            }

        sess.data["currency"] = currency
        # store RAW in session so get_flight_urls_tool can be used without large payload
        sess.data["raw_flights"] = departing_res
        # store parsed flights too for reference and select_currency_tool
        sess.data["parsed_flights"] = parsed_flights
        sess.data["flight_class_used"] = flight_class_used

        return {
            "session_id": sid,
            "flights": parsed_flights,
            "flight_class_used": flight_class_used,
            "currency": currency,
        }
        
    except Exception:
        # if error, clean the newly created session
        try: await close_session(sid)
        except: pass
        raise

async def get_flight_urls_tool_fn(session_id: str,
    flight_no: Union[int,str] = 1,
    max_providers: Optional[int] = 5,
    popup_wait_timeout: int = 10000,
)-> List[Dict[str, Any]]:
    """
    Using an existing session created by `search_flights_tool_fn`, open the selected
    flight's offers panel and collect booking (merchant) options and their URLs.

    Args:
        session_id (str): Session id returned by `search_flights_tool_fn`.
        flight_no (str): 1-based index of the flight to open. Default 1.
        max_providers (int | None): Maximum number of booking providers to return. Default 5.
        popup_wait_timeout (int): Milliseconds to wait after a new tab/pop-up appears
                                    before reading its URL. Default 10000.

    Returns:
        booking_options (List[Dict[str,str]]): List of providers with metadata:
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

    return await get_flight_urls(
        page,
        raw,
        flight_no=params.flight_no,
        max_providers=params.max_providers,
        popup_wait_ms=params.popup_wait_timeout,
    )
    
currency_logger = setup_logger(name="select_currency", log_level="INFO")
async def select_currency_tool_fn(currency: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """ Selects the desired currency from the currency dropdown menu.
    Args:
        currency (str): The currency code to select (e.g., "USD", "EUR").
        session_id (str | None): The id of the session to use.
    Returns:
        Optional[Dict[str, Any]]: A dictionary containing:
            flight results (Dict[str, Any]): Flights search results containing price, airline, number of stops, etc.
    """
    params = SelectCurrencyInput(
        session_id=session_id,
        currency=currency,
    )

    if params.session_id is None:
        sid = await create_session(headless=True)
        await get_session(sid).page.goto(BASE_URL)
    else: 
        sid = params.session_id
    sess = get_session(sid)
    page = sess.page

    old_currency = sess.data.get("currency", "unknown")
    if old_currency == currency:
        currency_logger.info(f"Currency is already set to {currency}, no change needed.")
        return {
                "session_id": sid,
                "flights": sess.data.get("parsed_flights", None),
                "flight_class_used": sess.data.get("flight_class_used", None),
                "currency": currency,
            }
    try:
        # Click the currency dropdown trigger
        # currency_locator = "button:has-text('Currency')"
        currency_locator = "button[jsname='z2Jm1b']"
        await wait_for_element_to_appear(page, currency_locator, timeout_ms=3000)
        await page.locator(currency_locator).click()

        # Wait for the options to appear and select the desired currency
        await wait_for_element_to_appear(page, "h1:has-text('Select your currency')", timeout_ms=5000)
        await page.locator(f"label:has-text('{currency}')").first.click()
        await page.locator("button:has-text('OK')").first.click()
        
        currency_logger.info(f"Currency {currency} selected successfully.")

        # Wait for the page to update prices
        flight_results = {}
        top_flights_locator = page.locator("li.pIav2d")
        currency_logger.info("Waiting for flight results to refresh with new currency...")
        if await wait_for_element_to_appear(page, "li.pIav2d", timeout_ms=3000):
            seen_details = set()
            for i, flight in enumerate(await top_flights_locator.all()):
                travel_detail = await flight.locator("div.JMc5Xc").first.get_attribute("aria-label")
                if travel_detail not in seen_details:
                    flight_results[f"Flight {i+1}"] = travel_detail
                    seen_details.add(travel_detail)
                if i+1 >= global_limiter:
                    break
            
            sess.data["raw_flights"] = flight_results
            sess.data["currency"] = currency
            flight_class_used = sess.data.get("flight_class_used", "Economy")
            parsed_flights = parse_flight_results(flight_results, currency)
            currency_logger.info("Flight results has been recovered to fit preferred currency")

            return {
                "session_id": sid,
                "flights": parsed_flights,
                "flight_class_used": flight_class_used,
                "currency": currency,
            }
        else:
            currency_logger.warning("There are no flights available after converting currencies.")
            currency_logger.info("Reverting to previous flight results.")
            return {
                "session_id": sid,
                "flights": sess.data.get("parsed_flights", None),   
                "flight_class_used": sess.data.get("flight_class_used", None),
                "currency": currency,
            }

    except Exception as e:
        currency_logger.exception(f"Error selecting currency: {e}")
        # raise


async def close_session_tool_fn(session_id: str) -> Dict[str, Any]:
    """
    Close and dispose a previously created Playwright session.

    Args:
        session_id (str): The id of the session to close.

    Returns:
        Dict[str, Any]: A dictionary with a single key:
            messages (str): A message indicating the session has been closed.
    """
    params = CloseSessionInput(session_id=session_id)
    await close_session(params.session_id)
    return {"messages": "Session closed."}


if __name__ == "__main__":
    async def _demo():
        sid = None
        try:
            res = await select_currency_tool_fn(currency="USD")

            sid = res["session_id"]
            print(f"Session ID used by select_currency_tool: {sid}")
            res = await search_flights_tool_fn(
                origin="Seoul",
                destination="Bangkok",
                departure_date="December 11",
                flight_class="Economy",
                adults=2,
                children=1,
                infants_on_lap=1,
                infants_in_seat=1,
                headless=True,
                session_id=sid,
            )
            
            print(f"Session ID used by search_flights_tool: {res['session_id']}")
            print(res["flights"])

            currency = input("Enter currency code to change (e.g., USD, EUR): ")
            print(await select_currency_tool_fn(
                session_id=sid,
                currency=currency,
            ))

            flight_no = input("Enter flight number to get booking URLs (1-based index): ")
            print(await get_flight_urls_tool_fn(
                session_id=sid,
                flight_no=flight_no,
                max_providers=3,
                popup_wait_timeout=5000,
            ))
        finally:
            if sid:
                await close_session_tool_fn(session_id=sid)

    asyncio.run(_demo())
