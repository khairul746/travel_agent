import os, sys
from langchain_core.tools import StructuredTool
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Tools.search_flights import (
    search_flights_tool_fn, get_flight_urls_tool_fn, select_currency_tool_fn, close_session_tool_fn
)
from Utils.schemas import FlightSearchInput, GetFlightURLsInput, SelectCurrencyInput, CloseSessionInput

search_flights_tool = StructuredTool.from_function(
    coroutine=search_flights_tool_fn,
    name="search_flights",
    description="Search one-way flights. Use tool twice for round-trip flights.",
    args_schema=FlightSearchInput,
)

get_flight_urls_tool = StructuredTool.from_function(
    coroutine=get_flight_urls_tool_fn,
    name="get_flight_urls",
    description="Using an existing session_id and a chosen flight number, return provider booking URLs.",
    args_schema=GetFlightURLsInput,
)

select_currency_tool = StructuredTool.from_function(
    coroutine=select_currency_tool_fn,
    name="select_currency",
    description="Select the currency for flight prices in an existing session, return updated flight results if there any.",
    args_schema=SelectCurrencyInput,
)

close_session_tool = StructuredTool.from_function(
    coroutine=close_session_tool_fn,
    name="close_session",
    description="Close the Playwright session/browser when done.",
    args_schema=CloseSessionInput,
)
