import sys
import os
import asyncio

from pydantic import BaseModel, Field
from typing import Optional, Literal
from langchain_core.tools import StructuredTool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Tools.search_flights import search_flights

# Input Schema
class FlightSearchInput(BaseModel):
    """
    Schema for searching flight information.
    """
    origin: str = Field(
        description="The origin city or airport code for the flight search."
    )
    destination: str = Field(
        description="The destination city or airport code for the flight search."
    )
    departure_date: str = Field(
        description="The departure date in MMMM DD or MMMM DD YYYY format."
    )
    # return_date is Optional, and can be None
    return_date: Optional[str] = Field(
        None, # Default value is None
        description="The return date in MMMM DD or MMMM DD YYYY format. Required for round trips."
    )
    # Use Literal for enum types
    flight_type: Literal["Round trip", "One way"] = Field(
        "Round trip", # Default value
        description="The type of flight (e.g., 'Round trip', 'One way')."
    )
    flight_class: Literal["Economy", "Business", "First", "Premium economy"] = Field(
        "Economy", # Default value
        description="The class of flight (e.g., 'Economy', 'Business', 'First', 'Premium economy')."
    )
    adults: int = Field(
        1, # Default value
        description="The number of adult passengers.",
        ge=1 # 'minimum' becomes 'ge' (greater than or equal)
    )
    children: int = Field(
        0, # Default value
        description="The number of child passengers.",
        ge=0
    )
    infants_on_lap: int = Field(
        0, # Default value
        description="The number of infants traveling on lap.",
        ge=0
    )
    infants_in_seat: int = Field(
        0, # Default value
        description="The number of infants requiring a seat.",
        ge=0
    )
    search_type: Literal["Top flight", "Lowest price", "Shortest duration"] = Field(
        "Top flight", # Default value
        description="The preferred search categorization (for return type only)."
    )

search_flights_tool = StructuredTool.from_function(coroutine=search_flights, args_schema=FlightSearchInput)


if __name__ == "__main__":

    async def run_tools():
        result = await search_flights_tool.ainvoke({
            "origin": "Bali",
            "destination": "Bangkok",
            "departure_date": "July 28",
            "flight_type": "One way"
        })
        print(search_flights_tool.name)
        return result
    
    asyncio.run(run_tools())