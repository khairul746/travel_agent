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


# --- Core Playwright Setup ---
async def fetch_page(url: str) -> Tuple[async_playwright, Browser, Page]:
    """
    Launches Playwright browser, navigates to the page,
    handles modal popups, and loads additional flight results if available.

    Args:
        url (str): URL of the page to fetch.

    Returns:
        tuple: (playwright, browser, page) if successful.
    """

    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True, slow_mo=50)  # Set headless to False for debugging
    page = await browser.new_page()
    headers = {
        "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0"
    }
    await page.set_extra_http_headers(headers)
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
        await wait_for_element_to_appear(page, "div.VfPpkd-aPP78e", timeout_ms=10000)
        await page.locator("div.VfPpkd-aPP78e").first.click()
        await wait_for_element_to_appear(page, "li[role='option']", timeout_ms=10000)
        await page.locator(f"li[role='option']:has-text('{flight_type}')").first.click()
        print(f"✅ Flight type {flight_type} selected successfully.")
    except Exception as e:
        print(f"❌ Error selecting flight type: {e}")


async def select_flight_class(page: Page, flight_class: str = "Economy"):
    """ Selects the flight class from the dropdown menu.
    Args:
        page (Page): The Playwright page instance.
        flight_class (str): Class of flight to select ("Economy", "Premium economy", "Business", "First").
    """
    try:
        await wait_for_element_to_appear(page, "div.VfPpkd-aPP78e", timeout_ms=10000)
        await page.locator("div.VfPpkd-aPP78e").nth(1).click()
        await wait_for_element_to_appear(page, "li[role='option']", timeout_ms=10000)
        await page.locator(f"li[role='option']:has-text('{flight_class}')").first.click()
        print(f"✅ Flight class {flight_class} selected successfully.")
    except Exception as e:
        print(f"❌ Error selecting flight class: {e}")


async def fill_origin(page: Page, origin: str):
    """ Fills the origin input field with the specified origin.
    Args:
        page (Page): The Playwright page instance.
        origin (str): The origin to fill in the input field.
    """
    try:
        await wait_for_element_to_appear(page, "input[aria-label='Where from?']", timeout_ms=10000)
        origin_input_locator = page.locator("input[aria-label='Where from?']")
        await origin_input_locator.fill(origin)
        await wait_for_element_to_appear(page, "li[role='option']:has-text('origin')", timeout_ms=5000)
        origin_option = page.locator(f"li[role='option']:has-text('{origin}')").first
        await origin_option.click()
        print("✅ Origin filled successfully.")
    except Exception as e:
        print(f"❌ Error filling origin: {e}")


async def fill_destination(page: Page, destination: str):
    """ Fills the destination input field with the specified destination.
    Args:
        page (Page): The Playwright page instance.
        destination (str): The destination to fill in the input field.
    """
    try:
        await wait_for_element_to_appear(page, "input[aria-label='Where to? ']", timeout_ms=15000)
        destination_input_locator = page.locator("input[aria-label='Where to? ']")
        await destination_input_locator.fill(destination)
        await wait_for_element_to_appear(page, "li[role='option']:has-text('destination')", timeout_ms=5000)
        destination_option = page.locator(f"li[role='option']:has-text('{destination}')").first
        await destination_option.click()
        print("✅ Destination filled successfully.")
    except Exception as e:
        print(f"❌ Error filling destination: {e}")


async def set_dates(page: Page, departure_date: str, flight_type: str, return_date: Optional[str] = None):
    """ Sets the departure date in the date picker.
    Args:
        page (Page): The Playwright page instance.
        departure_date (str): The departure date. (e.g., July 15)
        flight_type (str): Type of flight ("One way" or "Round trip").
        return_date (Optional[str]): The return date if flight_type is "Round trip". Defaults to None.
    """
    try:
        departure_selector = "input[aria-label='Departure']"
        await wait_for_element_to_appear(page, departure_selector, timeout_ms=10000)
        if flight_type == "One way":
            await page.locator(departure_selector).nth(0).click()
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


async def set_number_of_passengers(
        page: Page, adults: int = 1, 
        children: int = 0, infants_on_lap: int = 0, 
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
                num = 1 if passenger_type == "adult" else 0
                while num < count:
                    await page.locator(f"button[aria-label='Add {passenger_type}']").click()
                    num += 1
        await page.get_by_role("button", name="Done").click() # close the passenger menu
        print("✅ Number of passengers set successfully. ")
    except Exception as e:
        print(f"❌ Error setting number of passengers: {e}")
    

async def get_departing_flights(page: Page) -> Dict[str, Any]:
    """ Retrieves departing flight results from the page.
    Args:
        page (Page): The Playwright page instance.
    Returns:
        Dict[str, Any]: A dictionary containing flight results.
    """
    departing_flight_results = {}
    
    search_results_selector = "button[aria-label='Search']"
    await wait_for_element_to_appear(page, search_results_selector, timeout_ms=15000)
    await page.locator(search_results_selector).click()
    await page.wait_for_timeout(5000)

    try:
        top_flights_selector = await page.locator("li.pIav2d").all()
        print(f"✅ Found {len(top_flights_selector)} departing flight.")
        limiter = 9  # Limit to the first 10 results for performance
        seen_details = set()
        for i, flight in enumerate(top_flights_selector):
            travel_detail = await flight.locator("div.JMc5Xc").first.get_attribute("aria-label")
            print(f"✈️ Flight {i+1}: {travel_detail}", end="\n\n")
            if travel_detail not in seen_details:
                departing_flight_results[f"Flight {i+1}"] = travel_detail
                seen_details.add(travel_detail)
            if i > limiter:
                break
        return departing_flight_results
    except Exception as e:
        print(f"❌ Error retrieving departing flight: {e}")
        raise e
    

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
            selected_departing_flight = flight.locator(f"div.JMc5Xc[aria-label='{departing_detail}']").first

            if await selected_departing_flight.is_visible():
                print(f"🔍 Processing returning flight {i+1}: {departing_detail}")
                await flight.locator("div.yR1fYc").first.click()
                await wait_for_element_to_appear(page, "li.pIav2d", timeout_ms=10000)
                top_flights_selector = await page.locator("li.pIav2d").all()
                print(f"✅ Found {len(top_flights_selector)} returning flight.")
                limiter = 9  # Limit to the first 10 results for performance
                seen_details = set()
                for i, flight in enumerate(top_flights_selector):
                    travel_detail = await flight.locator("div.JMc5Xc").first.get_attribute("aria-label")
                    if travel_detail not in seen_details:
                        returning_flight_results[f"Flight {i+1}"] = travel_detail
                        print(f"✈️ Returning flight {i+1} added: {travel_detail}", end="\n\n")
                        seen_details.add(travel_detail)
                        if i > limiter:
                            break
                break
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
    for flight, details in flight_results.items():
        try:
            details = details.replace('\u202f', ' ')
            segments = details.split(". ")
            price = segments[0].split(" ")[1]
            num_stops = segments[1].split(" ")[0]

            flight_pattern = re.compile(
                r"Leaves (.*?) at ([\d:]{1,2}:\d{2}\s*[AP]M) on (.+?) "
                r"and arrives at (.*?) at ([\d:]{1,2}:\d{2}\s*[AP]M) on (.+)"
            )
            match = flight_pattern.search(segments[2])
            if match:
                departure_airport = match.group(1).strip()
                departure_time = match.group(2).strip()
                departure_date = match.group(3).strip()
                arrival_airport = match.group(4).strip()
                arrival_time = match.group(5).strip()
                arrival_date = match.group(6).strip()
            else:
                raise ValueError("Flight details format is incorrect.")
            
            flight_duration_pattern  = re.compile(r"Total duration ([\d\s\w]+)") 
            duration_match = flight_duration_pattern.search(segments[3])
            if duration_match:
                flight_duration = duration_match.group(1).strip()
            else:
                raise ValueError("Flight duration format is incorrect.")
            
            parsed_results[flight] = {
                "Price": price,
                "Number of Stops": num_stops,
                "Departure Airport": departure_airport,
                "Departure Time": departure_time,
                "Departure Date": departure_date,
                "Arrival Airport": arrival_airport,
                "Arrival Time": arrival_time,
                "Arrival Date": arrival_date,
                "Flight Duration": flight_duration,
            }
            print(f"✅ Successfully parsed flight {flight}.")
            print(f"Details: {parsed_results[flight]}", end="\n\n")
        
        except Exception as e:
            print(f"❌ Error parsing flight {flight}: {e}")
            print(f"Raw details: {details}", end="\n\n")
            parsed_results[flight] = {"Error": str(e)}
    print("✅ All flight results has been parsed.")
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
    infants_in_seat: int = 0
):
    BASE_URL = "https://www.google.com/travel/flights"
    playwright, browser, page = await fetch_page(BASE_URL)
    print("✅ Page loaded successfully.")
    try:
        if adults > 1 or children > 0 or infants_on_lap > 0 or infants_in_seat > 0:
            await set_number_of_passengers(page, adults, children, infants_on_lap, infants_in_seat)
        else:
            print("✅ No additional passengers to set.")

        if flight_class != "Economy":
            await select_flight_class(page, flight_class)
        else:
            print("✅ Flight class is Economy, no selection needed.")
        
        await fill_origin(page, origin)
        await fill_destination(page, destination)
        
        if flight_type == "Round trip":
            print("✅ Flight type is Round trip, no selection needed.")
            assert return_date is not None, "🚨 Return date is required for round trip flights."
            await set_dates(page, departure_date, flight_type, return_date)
            departing_res = await get_departing_flights(page)
            select_departing_flight = input("Select departing flight (e.g., Flight 1): ")
            returning_res = await get_returning_flights(page, departing_res[select_departing_flight])
            parse_flight_results(departing_res)
            parse_flight_results(returning_res)
        else:
            await select_flight_type(page, flight_type)
            await set_dates(page, departure_date, flight_type)
            departing_res = await get_departing_flights(page)
            parse_flight_results(departing_res)
        print("✅ Flight search completed successfully.")
    except Exception as e:
        print(f"❌ Error during flight search: {e}")
    finally:
        await browser.close()
        await playwright.stop()


if __name__ == "__main__":
    asyncio.run(main(
        origin="New York",
        destination="Los Angeles",
        departure_date="July 19",
        return_date="July 27",
        flight_type="Round trip", # "One way" or "Round trip"
        flight_class="First", # [Optional] "Economy", "Premium economy", "Business", "First"
        adults=2,
        children=1,
        infants_on_lap=1,
        infants_in_seat=1
    ))