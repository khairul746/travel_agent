from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field

class FlightSearchInput(BaseModel):
    origin: str = Field(
        description="The origin city or airport code for the flight search."
    )
    destination: str = Field(
        description="The destination city or airport code for the flight search."
    )
    departure_date: str = Field(
        description="The departure date in MMMM DD or MMMM DD YYYY format."
    )
    flight_class: Literal["Economy", "Business", "First", "Premium economy"] = "Economy"
    adults: int = Field(1, ge=1)
    children: int = Field(0, ge=0)
    infants_on_lap: int = Field(0, ge=0)
    infants_in_seat: int = Field(0, ge=0)
    headless: bool = True

class FlightItem(BaseModel):
    index: int
    summary: Dict[str, Any]

class SearchFlightsResult(BaseModel):
    session_id: Optional[str]
    flights: List[FlightItem] = []
    flight_class_used: Optional[str] = None
    message: str

class GetFlightURLsInput(BaseModel):
    session_id: str
    flight_no: int = 1
    max_providers: Optional[int] = 5
    popup_wait_timeout: int = 10000

class BookingOption(BaseModel):
    provider: Optional[str] = None
    price: Optional[str] = None
    logo_url: Optional[str] = None
    call_number: Optional[str] = None
    booking_url: Optional[str] = None

class GetFlightURLsResult(BaseModel):
    flight_no: int
    options: List[BookingOption]

class CloseSessionInput(BaseModel):
    session_id: str
