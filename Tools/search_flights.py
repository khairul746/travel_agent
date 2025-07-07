import asyncio
from playwright.async_api import async_playwright, Page, Browser, Locator  # type: ignore
from typing import Dict, Any, Optional, Tuple
import json
import os

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
    browser = await p.chromium.launch(headless=False, slow_mo=5000)
    page = await browser.new_page()
    await page.goto(url)

    return p, browser, page


async def select_flight_type(page: Page, flight_type: str="One way"):
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
        print("✅ Flight type selected successfully.")
    except Exception as e:
        print(f"❌ Error selecting flight type: {e}")


async def select_flight_class(page: Page, flight_class: str="Premium Economy"):
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
        print("✅ Flight class selected successfully.")
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
            print("✅ Departure date set successfully.")
        elif flight_type == "Round trip":
            await page.locator(departure_selector).nth(0).click()
            await page.locator(departure_selector).nth(1).fill(departure_date)
            if return_date:
                await page.keyboard.press("Tab")
                return_date_selector = "input[aria-label='Return']"
                await page.locator(return_date_selector).nth(1).fill(return_date)
                print("✅ Departure and return dates set successfully.")
            else:
                print("⚠️ No return date provided, using default.")
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
        passenger_selector = "div.VfPpkd-RLmnJb" #ow14 > div.cQnuXe.k0gFV > div > button > 
        await wait_for_element_to_appear(page, passenger_selector, timeout_ms=10000)
        await page.get_by_role("button", name="1 passenger, change number of").click()
        for passenger_type, count in passengers.items():
            if count > 0:
                num = 1 if passenger_type == "adult" else 0
                while num < count:
                    await page.locator(f"button[aria-label='Add {passenger_type}']").click()
                    num += 1
        await page.get_by_role("button", name="Done").click() # close the passenger menu
        print("✅ Number of passengers set successfully.")
    except Exception as e:
        print(f"❌ Error setting number of passengers: {e}")
    

async def get_flight_results(page: Page) -> Dict[str, Any]:
    """ Retrieves flight results from the page.
    Args:
        page (Page): The Playwright page instance.
    Returns:
        Dict[str, Any]: A dictionary containing flight results.
    """
    await wait_for_element_to_appear(page, "button[aria-label='Search']", timeout_ms=15000)
    await page.locator("button[aria-label='Search']").click()
    await page.wait_for_timeout(5000)  # Wait for results to load
    await page.screenshot(path="flight_results.png")

       
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
        if flight_type == "One way":
            await select_flight_type(page, flight_type)
        elif flight_type == "Round trip":
            print("✅ Flight type is Round trip, no selection needed.")

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
            assert return_date is not None, "🚨 Return date is required for round trip flights."
        await set_dates(page, departure_date, flight_type, return_date)
        await get_flight_results(page)
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
        departure_date="July 15",
        # return_date="July 22",
        flight_type="One way",
        flight_class="Economy",
        adults=1,
        children=0,
        infants_on_lap=0,
        infants_in_seat=0
    ))