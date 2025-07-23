import asyncio
import unittest
from playwright.async_api import async_playwright, Page, Browser # type: ignore
import sys
import os

# Add the parent directory of search_flights.py to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Tools.search_flights import search_flights, parse_flight_results # Import parse_flight_results for assertions
# Import other functions if you want to test them individually
# from search_flights import select_flight_type, fill_origin, ...

class TestFlightSearchE2E(unittest.IsolatedAsyncioTestCase):
    # Using IsolatedAsyncioTestCase for async tests with setUp and tearDown

    async def asyncSetUp(self):
        # Initialize Playwright for each test to ensure a clean state
        self.playwright_instance = await async_playwright().start()
        # Use headless=False for visual debugging during development
        self.browser = await self.playwright_instance.chromium.launch(headless=True, slow_mo=100)
        self.page = await self.browser.new_page()
        # Set a reasonable default timeout for page operations
        self.page.set_default_timeout(30000) # 30 seconds

    async def asyncTearDown(self):
        # Close the browser and stop Playwright after each test
        if self.browser:
            await self.browser.close()
        if self.playwright_instance:
            await self.playwright_instance.stop()

    async def test_round_trip_search_lowest_price(self):
        print("\n--- Running E2E Test: Round Trip - Lowest Price ---")
        origin = "Jakarta"
        destination = "Singapore"
        departure_date = "August 17" # Ensure this date is in the future
        return_date = "August 20"   # Ensure this date is in the future

        results = await search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            flight_type="Round trip",
            flight_class="Economy",
            adults=1,
            search_type="Lowest price"
        )
        
        self.assertIsNotNone(results)
        self.assertIn("departing_flights", results)
        self.assertIn("returning_flights", results)
        
        self.assertGreater(len(results["departing_flights"]), 0)
        self.assertGreater(len(results["returning_flights"]), 0)
        
        # Further assertions: check if prices are numbers, dates make sense, etc.
        # Example: Check if all parsed flights have a price
        for flight, details in results["departing_flights"].items():
            self.assertIn("price", details)
            self.assertTrue(details["price"].startswith("Rp")) # Check price format
        for flight, details in results["returning_flights"].items():
            self.assertIn("price", details)
            self.assertTrue(details["price"].startswith("Rp"))

        print("✅ Round Trip - Lowest Price Test Passed.")

    async def test_one_way_search(self):
        print("\n--- Running E2E Test: One Way Search ---")
        origin = "Surabaya"
        destination = "London"
        departure_date = "August 20" # Ensure this date is in the future

        results = await search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            flight_type="One way",
            flight_class="Business", # Test with a different class
            adults=1
        )
        
        self.assertIsNotNone(results)
        self.assertIn("departing_flights", results)
        self.assertNotIn("returning_flights", results) # Should not have returning for one-way
        
        self.assertGreater(len(results["departing_flights"]), 0)

        print("✅ One Way Search Test Passed.")

    async def test_round_trip_with_multiple_passengers_and_shortest_duration(self):
        print("\n--- Running E2E Test: Round Trip - Multiple Passengers - Shortest Duration ---")
        origin = "Jakarta"
        destination = "Tokyo"
        departure_date = "August 16" # Future date
        return_date = "August 20"   # Future date

        results = await search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            flight_type="Round trip",
            adults=2,
            children=1,
            search_type="Shortest duration"
        )

        self.assertIsNotNone(results)
        self.assertIn("departing_flights", results)
        self.assertIn("returning_flights", results)
        self.assertGreater(len(results["departing_flights"]), 0)
        self.assertGreater(len(results["returning_flights"]), 0)
        
        # Additional checks can be added here, e.g., verify passenger count selection
        # (this is harder to assert directly from the returned data, might need
        # to add a screenshot or more assertions in `set_number_of_passengers` itself)

        print("✅ Round Trip - Multiple Passengers - Shortest Duration Test Passed.")

    async def test_no_results_scenario(self):
        print("\n--- Running E2E Test: No Results Scenario ---")
        # Use a highly unlikely combination to get no results
        # Or a future date far in the future/past that won't have flights
        origin = "NonExistentCity" # This should ideally trigger an error earlier or result in no suggestions
        destination = "AnotherNonExistentCity"
        departure_date = "December 25" # A random date
        return_date = "December 30"

        # Expect an exception for invalid origin/destination or no results
        with self.assertRaises(Exception) as cm: # Catch the raised exception from search_flights
            await search_flights(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
                flight_type="Round trip"
            )
        # You can inspect cm.exception to be more specific about the error type
        self.assertIn("is not exist", str(cm.exception) or "") # Check error message from `fill_origin`

        print("✅ No Results Scenario Test Passed (expected error caught).")

if __name__ == '__main__':
    # Set Playwright_DEBUG=1 to see more detailed logs
    os.environ['PLAYWRIGHT_DEBUG'] = '1'
    unittest.main()