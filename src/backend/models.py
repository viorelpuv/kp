from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base
import enum
from datetime import datetime


# Enums
class OrderStatus(str, enum.Enum):
    CREATED = "Created"
    PAID = "Paid"
    CANCELLED = "Cancelled"
    EXPIRED = "Expired"


class TicketStatus(str, enum.Enum):
    ISSUED = "Issued"
    RETURNED = "Returned"
    USED = "Used"


class SeatStatus(str, enum.Enum):
    FREE = "Free"
    BOOKED = "Booked"
    SOLD = "Sold"


class PaymentMethod(str, enum.Enum):
    CARD = "Card"
    SBERPAY = "SberPay"
    YOOMONEY = "YooMoney"


class CarriageType(str, enum.Enum):
    SITTING = "Сидячий"
    RESERVED_SEAT = "Плацкарт"
    COUPE = "Купе"
    SV = "СВ"
    LUX = "Люкс"


# Модели, которые не имеют внешних зависимостей (должны быть первыми)
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True)
    last_name = Column(String(50))
    first_name = Column(String(50))
    middle_name = Column(String(50), nullable=True)
    phone = Column(String(20))

    orders = relationship("Order", back_populates="user")
    tickets = relationship("Ticket", back_populates="user")


class Station(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    city = Column(String(100))
    esr_code = Column(String(20), unique=True)


class Train(Base):
    __tablename__ = "trains"

    id = Column(Integer, primary_key=True, index=True)
    train_number = Column(String(10), unique=True)
    name = Column(String(100))
    carrier = Column(String(100), default="RZD")

    trips = relationship("Trip", back_populates="train")
    carriages = relationship("Carriage", back_populates="train")


class CarriageType(Base):
    __tablename__ = "carriage_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    description = Column(Text, nullable=True)


# Модели, которые ссылаются на другие (должны быть после)
class Carriage(Base):
    __tablename__ = "carriages"

    id = Column(Integer, primary_key=True, index=True)
    train_id = Column(Integer, ForeignKey("trains.id"))
    carriage_number = Column(Integer)
    carriage_type_id = Column(Integer, ForeignKey("carriage_types.id"))

    train = relationship("Train", back_populates="carriages")
    carriage_type = relationship("CarriageType")
    seats = relationship("Seat", back_populates="carriage")


class Seat(Base):
    __tablename__ = "seats"

    id = Column(Integer, primary_key=True, index=True)
    carriage_id = Column(Integer, ForeignKey("carriages.id"))
    seat_number = Column(Integer)
    is_window = Column(Boolean, default=False)
    has_socket = Column(Boolean, default=False)

    carriage = relationship("Carriage", back_populates="seats")
    availability = relationship("SeatAvailability", back_populates="seat")


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200))
    departure_station = Column(String(100))
    arrival_station = Column(String(100))

    trips = relationship("Trip", back_populates="route")
    stations = relationship("RouteStation", back_populates="route")


# ВАЖНО: RouteStation должна быть определена ПОСЛЕ Station и Route, но ДО Trip
class RouteStation(Base):
    __tablename__ = "route_stations"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"))
    station_id = Column(Integer, ForeignKey("stations.id"))
    stop_order = Column(Integer)
    arrival_time = Column(String(10), nullable=True)
    departure_time = Column(String(10), nullable=True)
    time_from_start_minutes = Column(Integer, nullable=True)

    route = relationship("Route", back_populates="stations")
    station = relationship("Station")


class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    train_id = Column(Integer, ForeignKey("trains.id"))
    route_id = Column(Integer, ForeignKey("routes.id"))
    departure_datetime = Column(DateTime)
    arrival_datetime = Column(DateTime)

    train = relationship("Train", back_populates="trips")
    route = relationship("Route", back_populates="trips")
    prices = relationship("CarriagePrice", back_populates="trip")
    seat_availability = relationship("SeatAvailability", back_populates="trip")


class CarriagePrice(Base):
    __tablename__ = "carriage_prices"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"))
    carriage_type_id = Column(Integer, ForeignKey("carriage_types.id"))
    price = Column(Float)

    trip = relationship("Trip", back_populates="prices")
    carriage_type = relationship("CarriageType")


class SeatAvailability(Base):
    __tablename__ = "seat_availability"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"))
    seat_id = Column(Integer, ForeignKey("seats.id"))
    status = Column(String(20), default=SeatStatus.FREE)
    price = Column(Float)
    booked_until = Column(DateTime, nullable=True)

    trip = relationship("Trip", back_populates="seat_availability")
    seat = relationship("Seat", back_populates="availability")
    ticket = relationship("Ticket", back_populates="seat_availability", uselist=False)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    total_amount = Column(Float)
    status = Column(String(20), default=OrderStatus.CREATED)

    user = relationship("User", back_populates="orders")
    tickets = relationship("Ticket", back_populates="order")
    payments = relationship("Payment", back_populates="order")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    seat_availability_id = Column(Integer, ForeignKey("seat_availability.id"), unique=True)
    price = Column(Float)
    status = Column(String(20), default=TicketStatus.ISSUED)

    order = relationship("Order", back_populates="tickets")
    user = relationship("User", back_populates="tickets")
    seat_availability = relationship("SeatAvailability", back_populates="ticket")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    amount = Column(Float)
    payment_method = Column(String(20))
    status = Column(String(20))

    order = relationship("Order", back_populates="payments")