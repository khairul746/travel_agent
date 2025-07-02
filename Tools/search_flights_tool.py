import asyncio
from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright, Page, Browser  # type: ignore
from typing import Dict, Any, Optional, Tuple
import json
import os

mcp = FastMCP("Flight Search Tool")

async def wait_for_element_to_appear(
    page: Page, selector: str, timeout_ms: int = 10000, check_interval_ms: int = 500
) -> bool:
    """
    Waits for a specific element to appear on the page within a timeout period.

    Args:
        page (Page): The Playwright page instance.
        selector (str): CSS selector of the target element.
        timeout_ms (int, optional): Maximum wait time in milliseconds. Defaults to 10000.
        check_interval_ms (int, optional): Interval between checks in milliseconds. Defaults to 500.

    Returns:
        bool: True if the element appears before timeout, False otherwise.
    """
    max_checks = timeout_ms // check_interval_ms

    for attempt in range(max_checks):
        if await page.locator(selector).count() > 0:
            return True
        await page.wait_for_timeout(check_interval_ms)

    return False


async def fetch_page(url: str) -> Tuple[async_playwright, Browser, Page]:
    """
    Launches Playwright browser, navigates to the given Kiwi.com search results page,
    handles modal popups, and loads additional flight results if available.

    Args:
        url (str): URL of the Kiwi.com search results page.

    Returns:
        tuple: (playwright, browser, page) if successful.
    """

    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=False)
    page = await browser.new_page()
    await page.goto(url)

    # Handle privacy modal if it appears
    close_button = page.locator('button[data-test="ModalCloseButton"]')
    if await close_button.is_visible():
        await close_button.click()

    # Load more results if the button exists, until "No more results" is visible
    clicks = 0
    MAX_LOAD_MORE_CLICKS = 10  # Limit to prevent infinite loop
    while not await page.locator('div[data-test="NoMoreResults"]').is_visible():
        await wait_for_element_to_appear(page, '[data-test="ResultCardWrapper"]', timeout_ms=30000)

        load_more_button = page.locator('button:has-text("load more")')
        if await load_more_button.is_visible():
            await load_more_button.click()
            await page.wait_for_timeout(5000)
            clicks += 1
            if clicks >= MAX_LOAD_MORE_CLICKS:
                break
        else:
            break
    return p, browser, page


async def scrape_page(page: Page) -> Optional[Dict[str, Any]]:
    """
    Scrapes flight information from the given Playwright page object.

    Args:
        page (Page): A Playwright page object already loaded with flight search results.

    Returns:
        dict | None: A dictionary containing flight details such as departure time, arrival time,
                     airports, price, duration, number of stops, and airlines. Returns None on failure.
    """
    results = {"flight_cards": []}

    try:
        flight_cards = await page.locator('[data-test="ResultCardWrapper"]').all()

        for card in flight_cards:
            dep_time = await card.locator('[data-test="TripTimestamp"]').nth(0).inner_text()
            arr_time = await card.locator('[data-test="TripTimestamp"]').nth(1).inner_text()
            from_airport = await card.locator('[data-test="ResultCardStopPlace"]').nth(0).inner_text()
            to_airport = await card.locator('[data-test="ResultCardStopPlace"]').nth(1).inner_text()
            price = await card.locator('[data-test="ResultCardPrice"] span').inner_text()
            duration = await card.locator('div.py-100.px-0.leading-none time').inner_text()

            # Get stop count (e.g., "Direct", "1 stop")
            try:
                stops_text = await card.locator('[data-test^="StopCountBadge"]').first.inner_text()
            except Exception:
                stops_text = "Unknown"

            # Get airline names from alt attributes
            airline_elements = await card.locator('img[alt]').all()
            airlines = {
                await img.get_attribute("alt")
                for img in airline_elements
                if await img.get_attribute("alt")
            }

            # Append data to results
            card_results = {
                "dep_time": dep_time,
                "arr_time": arr_time,
                "from_airport": from_airport,
                "to_airport": to_airport,
                "price": price,
                "duration": duration,
                "stops_text": stops_text,
                "airlines": ', '.join(airlines) if airlines else "Unknown"
            }
            results["flight_cards"].append(card_results)
        print(f"✅ Found {len(results['flight_cards'])} flight cards.")
        return results

    except Exception as e:
        print(f"Error while scraping flight cards: {e}")
        return None
  
@mcp.tool(name="get flight cards")
async def get_flight_cards(
    origin: str = "padang-indonesia",
    destination: str = "kuala-lumpur-malaysia",
    outbound_date: str = "2025-07-21",
    inbound_date: str = "no-return",
    flight_class: str = "ECONOMY",
    adults: int = 1,
    children: int = 0,
    infants: int = 0,
    cabin_baggage: int = 1,
    checked_baggage: int = 0,
):
    """
    Search for flight options between two cities using specific parameters.

    Args:
        origin (str): Departure city in the format "padang-indonesia".
        destination (str): Destination city in the format "kuala-lumpur-malaysia".
        outbound_date (str): Departure date in the format "YYYY-MM-DD".
        inbound_date (str): Return date in the format "YYYY-MM-DD" or "no-return".
        flight_class (str): Flight class (ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST_CLASS).
        adults (int): Number of adult passengers.
        children (int): Number of child passengers.
        infants (int): Number of infants.
        cabin_baggage (int): Number of cabin baggage pieces.
        checked_baggage (int): Number of checked baggage pieces.
    """
    
    # Construct search URL
    flight_class = flight_class.upper()
    base_url = (
        f"https://www.kiwi.com/en/search/results/"
        f"{origin}/{destination}/"
        f"{outbound_date}/{inbound_date}?"
        f"adults={adults}&children={children}&infants={infants}&"
        f"bags={cabin_baggage}.{checked_baggage}-0.0&"
        f"cabinClass={flight_class}-false"
    )

    # Run scraping
    playwright, browser, page = await fetch_page(base_url)
    
    if page:
        results = await scrape_page(page)
        output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "LLM", "flight_results.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        await browser.close()
        await playwright.stop()

        top_3_flights = results[:3]
        return f"Found {len(results)} flights. Top 3 flights:\n" + json.dumps(top_3_flights, indent=2)
        
    else:
        print("❌ Failed to fetch the page.")


if __name__ == "__main__":
    asyncio.run(get_flight_cards())