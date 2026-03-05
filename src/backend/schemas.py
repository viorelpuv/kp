from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class TicketBase(BaseModel):
    price: float
    status: str

class TicketCreate(TicketBase):
    order_id: int
    user_id: int
    seat_availability_id: int

class Ticket(TicketBase):
    id: int
    order_id: int
    user_id: int
    seat_availability_id: int
    
    class Config:
        from_attributes = True

class TripBase(BaseModel):
    departure_datetime: datetime
    arrival_datetime: datetime

class Trip(TripBase):
    id: int
    train_id: int
    route_id: int
    available_seats: int
    min_price: float
    
    class Config:
        from_attributes = True

class TripDetail(Trip):
    train_name: str
    route_name: str
    departure_station: str
    arrival_station: str
    seats: List[dict]

class OrderBase(BaseModel):
    total_amount: float

class OrderCreate(OrderBase):
    user_id: int

class Order(OrderBase):
    id: int
    user_id: int
    created_at: datetime
    status: str
    tickets: List[Ticket] = []
    
    class Config:
        from_attributes = True

class SeatAvailabilityBase(BaseModel):
    status: str
    price: float

class SeatAvailability(SeatAvailabilityBase):
    id: int
    trip_id: int
    seat_id: int
    seat_number: int
    carriage_type: str
    is_window: bool
    has_socket: bool