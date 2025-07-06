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


async def set_departure_date(page: Page, date: str= "July 15"):
    """ Sets the departure date in the date picker.
    Args:
        page (Page): The Playwright page instance.
        date (str): The departure date. (e.g., July 15)
    """
    try:
        await wait_for_element_to_appear(page, "input[aria-label='Departure']", timeout_ms=10000)
        await page.locator("input[aria-label='Departure']").nth(0).click()
        await page.locator("input[aria-label='Departure']").nth(1).fill(date)
        await page.keyboard.press("Enter")
        await page.keyboard.press("Enter")
        print("✅ Departure date set successfully.")
    except Exception as e:
        print(f"❌ Error setting departure date: {e}")
    

async def get_flight_cards():
    BASE_URL = "https://www.google.com/travel/flights"
    playwright, browser, page = await fetch_page(BASE_URL)
    print("✅ Page loaded successfully.")
    await select_flight_type(page, "One way")
    await select_flight_class(page, "First")
    await fill_origin(page, "New York")
    await fill_destination(page, "Los Angeles")
    await set_departure_date(page, "July 15")
    await browser.close()
    await playwright.stop()

if __name__ == "__main__":
    asyncio.run(get_flight_cards())