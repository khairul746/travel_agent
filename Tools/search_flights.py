import asyncio
from playwright.async_api import async_playwright, Page, Browser  # type: ignore
from typing import Dict, Any, Optional, Tuple
import re


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
    browser = await p.chromium.launch(headless=False, slow_mo=200)  # Set headless to False for debugging
    page = await browser.new_page()
    # headers = {
    #     "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0"
    # }
    # await page.set_extra_http_headers(headers)
    await page.goto(url)

    return p, browser, page


# --- Interaction Functions ---
async def select_flight_type(page: Page, flight_type: str = "Round trip"):
    """ Selects the flight type from the dropdown menu.
    Args:
        page (Page): The Playwright page instance.
        flight_type (str): Type of flight to select ("One way", "Round trip").
    """
    try:
        # Click the dropdown trigger for flight type
        await wait_for_element_to_appear(page, "div.VfPpkd-aPP78e", timeout_ms=10000)
        await page.locator("div.VfPpkd-aPP78e").first.click()

        # Wait for the options to appear and select the desired flight type
        await wait_for_element_to_appear(page, "li[role='option']", timeout_ms=10000)
        await page.wait_for_timeout(500)  # Ensure the options are fully loaded
        await page.locator(f"li[role='option']:has-text('{flight_type}')").first.click()
        
        print(f"✅ Flight type {flight_type} selected successfully.")
    except Exception as e:
        print(f"❌ Error selecting flight type: {e}")
        raise


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
        # await wait_for_element_to_appear(page, "li[role='option']:has-text('origin')", timeout_ms=5000)
        origin_option = page.locator(f"li[role='option']:has-text('{origin}')").first
        await origin_option.click()

        print(f"✅ Origin {origin} filled successfully.")
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
        # await wait_for_element_to_appear(page, "li[role='option']:has-text('destination')", timeout_ms=5000)
        destination_option = page.locator(f"li[role='option']:has-text('{destination}')").first
        await destination_option.click()

        print(f"✅ Destination {destination} filled successfully.")
    except Exception as e:
        print(f"❌ Error filling destination: {e}")
        raise


async def set_dates(page: Page, departure_date: str, flight_type: str, return_date: Optional[str] = None):
    """ Sets the departure and optional return dates in the date picker.
    Args:
        page (Page): The Playwright page instance.
        departure_date (str): The departure date. (e.g., July 15)
        flight_type (str): Type of flight ("One way" or "Round trip").
        return_date (Optional[str]): The return date if flight_type is "Round trip". Defaults to None.
    """
    try:
        departure_selector = "input[aria-label='Departure']"
        # Ensure the initial departure input field is ready
        await wait_for_element_to_appear(page, departure_selector, timeout_ms=10000)
        if flight_type == "One way":
            # Click the departure input to open the date picker
            # Note: .nth(0) usually targets the visible input field to open the calendar.
            await page.locator(departure_selector).nth(0).click()
            
            # Assuming .nth(1) is the actual text input field within the date picker for departure
            await page.locator(departure_selector).nth(1).fill(departure_date)
            await page.keyboard.press("Enter")
            await page.keyboard.press("Enter")
            print(f"✅ Departure date {departure_date} set successfully.")
        elif flight_type == "Round trip":
            await page.locator(departure_selector).nth(0).click()
            await page.locator(departure_selector).nth(1).fill(departure_date)
            if return_date:
                await page.keyboard.press("Tab")
                return_date_selector = "input[aria-label='Return']"
                await page.locator(return_date_selector).nth(1).fill(return_date)
                print(f"✅ Departure date {departure_date} and return date {return_date} set successfully.")
            await page.keyboard.press("Enter")
            await page.keyboard.press("Enter")
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
        await page.get_by_role("button", name="1 passenger, change number of").click()
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
    

async def get_departing_flights(page: Page, flight_class: str = "Economy") -> Tuple[Dict[str, Any], str]:
    """ Retrieves departing flight results from the page.
    Args:
        page (Page): The Playwright page instance.
    Returns:
        Dict[str, Any]: A dictionary containing flight results.
    """
    departing_flight_results = {}

    try:
        # Click the search button to initiate the flight search
        search_results_selector = "button[aria-label='Search']"
        await wait_for_element_to_appear(page, search_results_selector, timeout_ms=15000)
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
        
        limiter = 9  # Limit to the first 10 results for performance
        seen_details = set()
        for i, flight in enumerate(top_flights_locator):
            travel_detail = await flight.locator("div.JMc5Xc").first.get_attribute("aria-label")
            # print(f"✈️ Flight {i+1}: {travel_detail}", end="\n\n")
            if travel_detail not in seen_details:
                departing_flight_results[f"Flight {i+1}"] = travel_detail
                seen_details.add(travel_detail)
            if i > limiter:
                break
            
        print(f"✅ Found {len(departing_flight_results)} departing flight.") if len(departing_flight_results) > 0 else print("❌ No departing flight found")
        return departing_flight_results, flight_class_used
    except Exception as e:
        print(f"❌ Error retrieving departing flight: {e}")
        raise
    

async def get_returning_flights(page: Page, departing_detail: str) -> Dict[str, Any]:
    """Retrieves returning flight results from the page.
    Args:
        page (Page): The Playwright page instance.    
    Returns:
        Dict[str, Any]: A dictionary containing flight results.
    """
    returning_flight_results = {}
    try:
        top_flights_selector = await page.locator("li.pIav2d").all()
        for i, flight in enumerate(top_flights_selector):
            # Select the departing flight based on the provided detail
            selected_departing_flight = flight.locator(f"div.JMc5Xc[aria-label='{departing_detail}']").first

            # Scrape the returning flight based on the selected departing flight
            if await selected_departing_flight.is_visible():
                # print(f"🔍 Processing returning flight {i+1}: {departing_detail}")
                await flight.locator("div.yR1fYc").first.click()
                await wait_for_element_to_appear(page, "li.pIav2d", timeout_ms=10000)
                top_flights_selector = await page.locator("li.pIav2d").all()
                limiter = 9  # Limit to the first 10 results for performance
                seen_details = set()
                for i, flight in enumerate(top_flights_selector):
                    travel_detail = await flight.locator("div.JMc5Xc").first.get_attribute("aria-label")
                    if travel_detail not in seen_details:
                        returning_flight_results[f"Flight {i+1}"] = travel_detail
                        # print(f"✈️ Returning flight {i+1} added: {travel_detail}", end="\n\n")
                        seen_details.add(travel_detail)
                        if i > limiter:
                            break

        print(f"✅ Found {len(returning_flight_results)} returning flight.") if len(returning_flight_results) > 0 else print("❌ No returning flights found.")   
        return returning_flight_results
    
    except Exception as e:
        print(f"❌ Error retrieving returning flight: {e}")
        raise e

        
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
            print(f"✈️ {flight} has been parsed successfully")
            parsed_results[flight] = result

        except Exception as e:
            print(f"❌ Error parsing flight {flight}: {e}")
            print(f"Raw details: {details}", end="\n\n")
            parsed_results[flight] = {"Error": str(e)}

    return parsed_results


# --- Main Execution ---   
async def main(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    flight_type: str = "Round trip",
    flight_class: str = "Economy",
    adults: int = 1,
    children: int = 0,
    infants_on_lap: int = 0,
    infants_in_seat: int = 0,
    search_type: str = "Top flight" # categorize search to : ("Top flight", "Lowest price", "Shortest duration")
) -> Dict[str, Any] | None:
    """
    Orchestrates the flight search process on Google Flights and returns the parsed results.

    Args:
        origin (str): The departure city/airport.
        destination (str): The arrival city/airport.
        departure_date (str): The desired departure date (e.g., "July 15").
        return_date (Optional[str]): The desired return date (e.g., "July 22"). Required for "Round trip".
        flight_type (str): Type of flight ("One way" or "Round trip"). Defaults to "Round trip".
        flight_class (str): Class of flight ("Economy", "Premium economy", etc.). Defaults to "Economy".
        adults (int): Number of adult passengers. Defaults to 1.
        children (int): Number of children passengers. Defaults to 0.
        infants_on_lap (int): Number of infants on lap. Defaults to 0.
        infants_in_seat (int): Number of infants in seat. Defaults to 0.

    Returns:
        Dict[str, Any] | None: A dictionary containing parsed flight results (departing and returning if applicable),
                                or None if an error occurs. The structure will be:
                                {
                                    "departing_flights": List[Dict],
                                    "returning_flights": List[Dict] | None
                                }
    """
    BASE_URL = "https://www.google.com/travel/flights"
    playwright_instance: async_playwright | None = None
    browser: Browser | None = None
    page: Page | None = None
    
    try:
        playwright_instance, browser, page = await fetch_page(BASE_URL)
        print("✅ Page loaded successfully.")

        # Set number of passengers (only if different from default)
        if adults > 1 or children > 0 or infants_on_lap > 0 or infants_in_seat > 0:
            await set_number_of_passengers(page, adults, children, infants_on_lap, infants_in_seat)
        else:
            print("✅ No additional passengers to set.")

        # Select flight class (only if different from default)
        if flight_class != "Economy":
            await select_flight_class(page, flight_class)
        else:
            print("✅ Flight class is Economy, no selection needed.")
        
        # Fill flight origin and destination
        await fill_origin(page, origin)
        await fill_destination(page, destination)
        
        # Select flight type and set dates (default flight type: "Round trip")
        if flight_type == "Round trip":
            print("✅ Flight type is Round trip, no selection needed.")
            assert return_date is not None, "🚨 Return date is required for round trip flights."
            await set_dates(page, departure_date, flight_type, return_date)
            
            # Get departing flights
            departing_res, flight_class_used = await get_departing_flights(page)
            print("🔃 Parsing departing flights")
            parsed_departing = parse_flight_results(departing_res)
            parsed_returning = None

            # Get returning flights based on top flight
            if parsed_departing and search_type == "Top flight":
                print(f"🔝 Get returning flights based on top flight")
                selected_departing_flight = "Flight 1"
                returning_res = await get_returning_flights(page, departing_res[selected_departing_flight])
                print("🔃 Parsing returning flights")
                parsed_returning = parse_flight_results(returning_res)
                print("✅ Flight search completed successfully.")

            # Get returning flights based on lowest price
            elif parsed_departing and search_type == "Lowest price":
                print(f"💸 Get returning flight based on lowest price flight.")
                
                selected_departing_flight_details = min(
                    parsed_departing,
                    key=lambda flight_key: clean_price_string(parsed_departing[flight_key]['price'])
                )
                print(f"Lowest price flight : {selected_departing_flight_details}")
                selected_departing_flight_aria_label = departing_res.get(selected_departing_flight_details)
                
                if selected_departing_flight_aria_label:
                    returning_raw_results = await get_returning_flights(page, selected_departing_flight_aria_label)
                    print("🔃 Parsing returning flights")
                    parsed_returning = parse_flight_results(returning_raw_results)
                    print("✅ Flight search completed successfully.")
                else:
                    print("❌ Failed to find aria-label for the automatically selected departure flight.")

            # Get returning flights based on shortest flight duration
            elif parsed_departing and search_type == "Shortest duration":
                print(f"⚡ Get returning flight based on shortest flight duration.")

                selected_departing_flight_details = min(
                    parsed_departing,
                    key=lambda flight_key: convert_duration_to_minutes(parsed_departing[flight_key]['flight_duration'])
                )
                print(f"Shortest duration flight : {selected_departing_flight_details}")
                selected_departing_flight_aria_label = departing_res.get(selected_departing_flight_details)
                
                if selected_departing_flight_aria_label:
                    returning_raw_results = await get_returning_flights(page, selected_departing_flight_aria_label)
                    print("🔃 Parsing returning flights")
                    parsed_returning = parse_flight_results(returning_raw_results)
                    print("✅ Flight search completed successfully.")
                else:
                    print("❌ Failed to find aria-label for the automatically selected departure flight.")

            return {
                "departing_flights" : parsed_departing, 
                "returning_flights" : parsed_returning
            }
        
        # Set dates for one way flight
        else:
            await select_flight_type(page, flight_type)
            await set_dates(page, departure_date, flight_type)
            
            # Get departing flights
            departing_res, flight_class_used = await get_departing_flights(page)
            parsed_departing = parse_flight_results(departing_res)
            
            print("✅ Flight search completed successfully.")
            return {"departing_flights" : parsed_departing}
        
    except Exception as e:
        print(f"❌ Error during flight search: {e}")
        raise

    finally:
        await browser.close()
        await playwright_instance.stop()


if __name__ == "__main__":
    asyncio.run(main(
        origin="Surabaya",
        destination="Tokyo",
        departure_date="July 12",
        return_date="July 19",
        flight_type="One way", # "One way" or "Round trip"
        flight_class="First", # [Optional] "Economy", "Premium economy", "Business", "First"
        adults=2,
        children=1,
        infants_on_lap=1,
        infants_in_seat=1,
        search_type="Lowest price" # [Optional] "Top flights", "Lowest price", "Shortest duration"
    ))