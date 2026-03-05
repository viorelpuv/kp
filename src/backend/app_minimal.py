from fastapi import FastAPI
from typing import Optional
import uvicorn

app = FastAPI()

# Тестовые данные
TRIPS = [
    {
        "id": 1,
        "train_name": "Сапсан",
        "train_number": "001А",
        "departure_station": "Москва",
        "arrival_station": "Санкт-Петербург",
        "departure_datetime": "2026-03-04T10:00:00",
        "arrival_datetime": "2026-03-04T14:30:00",
        "available_seats": 45,
        "min_price": 2500
    },
    {
        "id": 2,
        "train_name": "Невский экспресс",
        "train_number": "002Б",
        "departure_station": "Москва",
        "arrival_station": "Санкт-Петербург",
        "departure_datetime": "2026-03-04T15:30:00",
        "arrival_datetime": "2026-03-04T20:00:00",
        "available_seats": 12,
        "min_price": 1800
    }
]


@app.get("/")
async def root():
    return {"message": "Railway Tickets API", "version": "1.0"}


@app.get("/api/trips")
async def get_trips(
        departure: Optional[str] = None,
        arrival: Optional[str] = None,
        date: Optional[str] = None,
        search: Optional[str] = None
):
    # Простая фильтрация по станциям
    result = TRIPS.copy()

    if departure:
        result = [t for t in result if departure.lower() in t["departure_station"].lower()]
    if arrival:
        result = [t for t in result if arrival.lower() in t["arrival_station"].lower()]

    return {
        "trips": result,
        "count": len(result),
        "filters": {
            "departure": departure,
            "arrival": arrival,
            "date": date,
            "search": search
        }
    }


if __name__ == "__main__":
    print("🚀 Запуск минимального сервера на порту 8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)