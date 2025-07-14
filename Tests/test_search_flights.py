import unittest
import sys
import os

# Add the parent directory of search_flights.py to the Python path
# so we can import it. Adjust this path if your file structure is different.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Tools.search_flights import clean_price_string, convert_duration_to_minutes, parse_flight_results

class TestUtils(unittest.TestCase):

    def test_clean_price_string(self):
        self.assertEqual(clean_price_string('Rp41,724,888'), 41724888)
        self.assertEqual(clean_price_string('Rp1,000,000'), 1000000)
        self.assertEqual(clean_price_string('Rp100'), 100)
        self.assertEqual(clean_price_string('41,724,888'), 41724888) # Should handle without 'Rp' too
        self.assertEqual(clean_price_string('Rp500.000'), 500000)
        self.assertEqual(clean_price_string('Invalid Price'), float('inf')) # Should return inf for invalid string

    def test_convert_duration_to_minutes(self):
        self.assertEqual(convert_duration_to_minutes('18 hr 5 min'), (18 * 60) + 5)
        self.assertEqual(convert_duration_to_minutes('1 hr 30 min'), 90)
        self.assertEqual(convert_duration_to_minutes('45 min'), 45)
        self.assertEqual(convert_duration_to_minutes('2 hr'), 120)
        self.assertEqual(convert_duration_to_minutes('0 hr 0 min'), 0)
        self.assertEqual(convert_duration_to_minutes('unknown'), 0) # Should return 0 if no match

    def test_parse_flight_results(self):
        raw_data_single_flight = {
            'Flight 1': "From 41724888 Indonesian rupiahs. 1 stop flight with Scoot. Leaves Juanda International Airport at 10:35 AM on Saturday, July 12 and arrives at Narita International Airport at 6:40 AM on Sunday, July 13. Total duration 18 hr 5 min. Layover (1 of 1) is a 8 hr 45 min layover at Singapore Changi Airport in Singapore."
        }
        parsed_single_flight = parse_flight_results(raw_data_single_flight)
        self.assertIn('Flight 1', parsed_single_flight)
        self.assertEqual(parsed_single_flight['Flight 1']['price'], 'Rp41,724,888')
        self.assertEqual(parsed_single_flight['Flight 1']['stops'], 1)
        self.assertEqual(parsed_single_flight['Flight 1']['airlines'], ['Scoot'])
        self.assertEqual(parsed_single_flight['Flight 1']['departure_airport'], 'Juanda International Airport')
        self.assertEqual(parsed_single_flight['Flight 1']['flight_duration'], '18 hr 5 min')
        self.assertIsNotNone(parsed_single_flight['Flight 1']['layovers'])
        self.assertEqual(parsed_single_flight['Flight 1']['layovers'][0]['layover_duration'], '8 hr 45 min')
        
        raw_data_multiple_flights = {
            'Flight A': "From 1000000 rupiahs. Nonstop flight with Garuda. Leaves Jakarta at 1:00 PM on Mon, Aug 1 and arrives at Bali at 3:00 PM on Mon, Aug 1. Total duration 2 hr 0 min.",
            'Flight B': "From 2000000 rupiahs. 1 stop flight with Lion Air. Leaves Jakarta at 4:00 PM on Mon, Aug 1 and arrives at Bali at 8:00 PM on Mon, Aug 1. Total duration 4 hr 0 min. Layover (1 of 1) is a 1 hr 0 min layover at Surabaya Airport."
        }
        parsed_multiple_flights = parse_flight_results(raw_data_multiple_flights)
        self.assertEqual(len(parsed_multiple_flights), 2)
        self.assertEqual(parsed_multiple_flights['Flight A']['stops'], 0)
        self.assertEqual(parsed_multiple_flights['Flight B']['stops'], 1)
        self.assertIsNotNone(parsed_multiple_flights['Flight B']['layovers'])
        
        raw_data_no_flights = {}
        parsed_no_flights = parse_flight_results(raw_data_no_flights)
        self.assertEqual(len(parsed_no_flights), 0)

        raw_data_none_input = None
        parsed_none_input = parse_flight_results(raw_data_none_input)
        self.assertEqual(len(parsed_none_input), 0)

        raw_data_error_flight = {
            'Flight X': "This is a malformed string without expected patterns."
        }
        parsed_error_flight = parse_flight_results(raw_data_error_flight)
        self.assertIn('Error', parsed_error_flight['Flight X'])


if __name__ == '__main__':
    unittest.main()