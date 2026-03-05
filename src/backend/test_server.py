from fastapi import FastAPI
import uvicorn

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/api/test")
async def test():
    return {"status": "ok", "message": "API is working"}


@app.get("/api/trips")
async def get_trips():
    try:
        # Просто возвращаем тестовые данные
        return {
            "trips": [
                {
                    "id": 1,
                    "train_name": "Сапсан",
                    "departure_station": "Москва",
                    "arrival_station": "СПб",
                    "departure_datetime": "2026-03-04T10:00:00",
                    "available_seats": 45,
                    "min_price": 2500
                }
            ],
            "count": 1
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)