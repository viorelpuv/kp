from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from datetime import datetime
import uvicorn
import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# =====================================================
# ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ
# =====================================================

# Параметры подключения к MySQL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "UM8$7I9o")
DB_NAME = os.getenv("DB_NAME", "RailwayTickets")

# Строка подключения
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Создаём движок SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)

# Создаём фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# =====================================================
# СОЗДАНИЕ FASTAPI ПРИЛОЖЕНИЯ
# =====================================================

app = FastAPI(
    title="Railway Tickets API",
    description="API для системы продажи ЖД билетов",
    version="1.0.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =====================================================

def get_db():
    """Получение сессии базы данных"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_carriage_type_name(carriage_type_id):
    """Получение названия типа вагона по ID"""
    carriage_types = {
        1: "Сидячий",
        2: "Плацкарт",
        3: "Купе",
        4: "СВ",
        5: "Люкс"
    }
    return carriage_types.get(carriage_type_id, "Неизвестно")

# =====================================================
# БАЗОВЫЕ ЭНДПОИНТЫ
# =====================================================

@app.get("/")
async def root():
    """Корневой эндпоинт - информация об API"""
    return {
        "message": "Railway Tickets API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "database": DB_NAME,
        "endpoints": {
            "trips": "/api/trips",
            "trip_detail": "/api/trips/{id}",
            "search": "/api/search",
            "stats": "/api/stats",
            "docs": "/docs"
        }
    }

@app.get("/api/health")
async def health_check(db: Session = Depends(get_db)):
    """Проверка здоровья сервиса и подключения к БД"""
    try:
        # Проверяем подключение к БД
        result = db.execute(text("SELECT 1")).scalar()
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "degraded",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# =====================================================
# ЭНДПОИНТЫ ДЛЯ РЕЙСОВ
# =====================================================

@app.get("/api/trips")
async def get_trips(
        departure: Optional[str] = Query(None, description="Станция отправления"),
        arrival: Optional[str] = Query(None, description="Станция прибытия"),
        date: Optional[str] = Query(None, description="Дата (ГГГГ-ММ-ДД)"),
        search: Optional[str] = Query(None, description="Поиск по тексту"),
        db: Session = Depends(get_db)
):
    """
    Получение списка рейсов с фильтрацией
    """
    try:
        print(f"🔍 Запрос списка рейсов с параметрами: {departure}, {arrival}, {date}, {search}")

        # SQL запрос с реальными ценами из CarriagePrices
        sql = """
        SELECT 
            t.id,
            tr.train_number,
            tr.name as train_name,
            r.departure_station,
            r.arrival_station,
            t.departure_datetime,
            t.arrival_datetime,
            COALESCE(t.available_seats_total, 0) as available_seats,
            COALESCE(MIN(cp.price), 1500) as min_price,
            COALESCE(MAX(cp.price), 1500) as max_price
        FROM Trips t
        JOIN Trains tr ON t.train_id = tr.id
        JOIN Routes r ON t.route_id = r.id
        LEFT JOIN CarriagePrices cp ON cp.trip_id = t.id
        WHERE 1=1
        """

        params = {}

        # Добавляем фильтры
        if departure:
            sql += " AND r.departure_station LIKE :departure"
            params["departure"] = f"%{departure}%"

        if arrival:
            sql += " AND r.arrival_station LIKE :arrival"
            params["arrival"] = f"%{arrival}%"

        if date:
            sql += " AND DATE(t.departure_datetime) = :date"
            params["date"] = date

        if search:
            sql += """ AND (
                tr.name LIKE :search 
                OR tr.train_number LIKE :search
                OR r.departure_station LIKE :search
                OR r.arrival_station LIKE :search
            )"""
            params["search"] = f"%{search}%"

        sql += " GROUP BY t.id ORDER BY t.departure_datetime LIMIT 50"

        print(f"📝 SQL запрос: {sql}")

        # Выполняем запрос
        result = db.execute(text(sql), params)
        trips = result.fetchall()

        print(f"✅ Найдено рейсов: {len(trips)}")

        # Форматируем результат
        trips_list = []
        for trip in trips:
            min_price = float(trip[8]) if trip[8] else 1500
            max_price = float(trip[9]) if trip[9] else 1500

            trips_list.append({
                "id": trip[0],
                "train_number": trip[1],
                "train_name": trip[2],
                "departure_station": trip[3],
                "arrival_station": trip[4],
                "departure_datetime": trip[5].isoformat() if trip[5] else None,
                "arrival_datetime": trip[6].isoformat() if trip[6] else None,
                "available_seats": trip[7],
                "min_price": min_price,
                "max_price": max_price
            })

        response = {
            "trips": trips_list,
            "count": len(trips_list)
        }

        print(f"✅ Успешно сформирован ответ с {len(trips_list)} рейсами")

        # Выводим первые несколько цен для проверки
        for i, trip in enumerate(trips_list[:3]):
            print(
                f"  Рейс {i + 1}: {trip['train_number']} - {trip['departure_station']}→{trip['arrival_station']}, цена от {trip['min_price']} ₽")

        return response

    except Exception as e:
        print(f"❌ Ошибка в get_trips: {e}")
        import traceback
        traceback.print_exc()
        # Возвращаем пустой список вместо ошибки 500
        return {
            "trips": [],
            "count": 0,
            "error": str(e)
        }

@app.get("/api/trips/{trip_id}")
async def get_trip_detail(
        trip_id: int,
        db: Session = Depends(get_db)
):
    """
    Детальная информация о рейсе с местами
    """
    try:
        print(f"🔍 Запрос деталей рейса {trip_id}")

        # Получаем информацию о рейсе
        trip_sql = """
        SELECT 
            t.id,
            tr.train_number,
            tr.name as train_name,
            r.departure_station,
            r.arrival_station,
            t.departure_datetime,
            t.arrival_datetime
        FROM Trips t
        JOIN Trains tr ON t.train_id = tr.id
        JOIN Routes r ON t.route_id = r.id
        WHERE t.id = :trip_id
        """

        trip_result = db.execute(text(trip_sql), {"trip_id": trip_id}).first()

        if not trip_result:
            raise HTTPException(status_code=404, detail="Trip not found")

        print(f"✅ Рейс найден: {trip_result[1]} - {trip_result[2]}")

        # Пробуем получить реальные места из БД
        seats_sql = """
        SELECT 
            sa.id,
            s.seat_number,
            ct.name as carriage_type,
            cp.price as price,
            sa.status,
            s.is_window,
            s.has_socket
        FROM SeatAvailability sa
        JOIN Seats s ON sa.seat_id = s.id
        JOIN Carriages c ON s.carriage_id = c.id
        JOIN CarriageTypes ct ON c.carriage_type_id = ct.id
        LEFT JOIN CarriagePrices cp ON cp.trip_id = sa.trip_id 
            AND cp.carriage_type_id = c.carriage_type_id
        WHERE sa.trip_id = :trip_id
        ORDER BY ct.name, s.seat_number
        """

        seats_result = db.execute(text(seats_sql), {"trip_id": trip_id})
        seats = seats_result.fetchall()

        print(f"✅ Найдено мест в SeatAvailability: {len(seats)}")

        # Если есть реальные места, используем их
        if len(seats) > 0:
            seats_list = []
            for seat in seats:
                seats_list.append({
                    "id": seat[0],
                    "seat_number": seat[1],
                    "carriage_type": seat[2],
                    "price": float(seat[3]) if seat[3] else 1500,
                    "status": seat[4],
                    "is_window": bool(seat[5]),
                    "has_socket": bool(seat[6])
                })
        else:
            # Если нет реальных мест, генерируем тестовые, но с привязкой к рейсу
            print(f"⚠️ Нет реальных мест для рейса {trip_id}, генерируем тестовые")
            seats_list = generate_test_seats(trip_id)

        # Подсчитываем статистику
        free_seats = [s for s in seats_list if s["status"] == "Free"]
        booked_seats = [s for s in seats_list if s["status"] == "Booked"]
        sold_seats = [s for s in seats_list if s["status"] == "Sold"]

        # Находим минимальную цену среди свободных мест
        min_price = min([s["price"] for s in free_seats]) if free_seats else 0

        response = {
            "id": trip_result[0],
            "train_number": trip_result[1],
            "train_name": trip_result[2],
            "departure_station": trip_result[3],
            "arrival_station": trip_result[4],
            "departure_datetime": trip_result[5].isoformat() if trip_result[5] else None,
            "arrival_datetime": trip_result[6].isoformat() if trip_result[6] else None,
            "available_seats": len(free_seats),
            "total_seats": len(seats_list),
            "min_price": float(min_price),
            "seats": seats_list,
            "seats_stats": {
                "free": len(free_seats),
                "booked": len(booked_seats),
                "sold": len(sold_seats)
            }
        }

        print(f"✅ Успешно сформирован ответ для рейса {trip_id}")
        print(f"📊 Свободных мест: {len(free_seats)} из {len(seats_list)}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка в get_trip_detail: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def generate_test_seats(self, trip_id):
    """Генерация тестовых мест с привязкой к рейсу"""
    test_seats = []

    # Используем trip_id как seed для генерации разных данных
    seed = trip_id * 100

    # Плацкарт (54 места)
    for i in range(1, 55):
        price = 1500 + (i % 10) * 100 + (trip_id * 50)
        status = "Free" if (i + seed) % 5 != 0 else "Sold"
        test_seats.append({
            "id": seed + i,
            "seat_number": i,
            "carriage_type": "Плацкарт",
            "price": price,
            "status": status,
            "is_window": i % 2 == 0,
            "has_socket": i % 4 == 0
        })

    # Купе (36 мест)
    for i in range(55, 91):
        idx = i - 54
        price = 2500 + (idx % 10) * 100 + (trip_id * 70)
        status = "Free" if (idx + seed) % 3 != 0 else "Sold"
        test_seats.append({
            "id": seed + i,
            "seat_number": idx,
            "carriage_type": "Купе",
            "price": price,
            "status": status,
            "is_window": idx % 2 == 0,
            "has_socket": idx % 3 == 0
        })

    # СВ (18 мест)
    for i in range(91, 109):
        idx = i - 90
        price = 4000 + (idx % 5) * 200 + (trip_id * 100)
        status = "Free" if (idx + seed) % 4 != 0 else "Sold"
        test_seats.append({
            "id": seed + i,
            "seat_number": idx,
            "carriage_type": "СВ",
            "price": price,
            "status": status,
            "is_window": True,
            "has_socket": idx % 2 == 0
        })

    return test_seats

# =====================================================
# ЭНДПОИНТЫ ДЛЯ ПОИСКА
# =====================================================

@app.get("/api/search")
async def search_trips(
    query: str = Query(..., description="Поисковый запрос"),
    limit: int = Query(10, description="Максимальное количество результатов"),
    db: Session = Depends(get_db)
):
    """
    Поиск по рейсам
    """
    try:
        sql = """
        SELECT 
            t.id,
            tr.train_number,
            tr.name as train_name,
            r.departure_station,
            r.arrival_station,
            t.departure_datetime,
            t.available_seats_total,
            MIN(cp.price) as min_price
        FROM Trips t
        JOIN Trains tr ON t.train_id = tr.id
        JOIN Routes r ON t.route_id = r.id
        JOIN CarriagePrices cp ON cp.trip_id = t.id
        WHERE 
            tr.name LIKE :query
            OR tr.train_number LIKE :query
            OR r.departure_station LIKE :query
            OR r.arrival_station LIKE :query
        GROUP BY t.id
        ORDER BY t.departure_datetime
        LIMIT :limit
        """

        params = {
            "query": f"%{query}%",
            "limit": limit
        }

        result = db.execute(text(sql), params)
        trips = result.fetchall()

        results_list = []
        for trip in trips:
            results_list.append({
                "id": trip[0],
                "train_number": trip[1],
                "train_name": trip[2],
                "departure_station": trip[3],
                "arrival_station": trip[4],
                "departure_datetime": trip[5].isoformat() if trip[5] else None,
                "available_seats": trip[6] or 0,
                "price_from": float(trip[7]) if trip[7] else 0
            })

        return {
            "results": results_list,
            "count": len(results_list),
            "query": query
        }

    except Exception as e:
        print(f"❌ Ошибка в search_trips: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# ЭНДПОИНТЫ ДЛЯ СТАТИСТИКИ
# =====================================================

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Получение статистики по системе"""
    try:
        # Общее количество билетов
        tickets_count = db.execute(text("SELECT COUNT(*) FROM Tickets")).scalar() or 0

        # Количество проданных билетов
        sold_tickets = db.execute(
            text("SELECT COUNT(*) FROM Tickets WHERE status = 'Issued'")
        ).scalar() or 0

        # Общая выручка
        total_revenue = db.execute(
            text("SELECT SUM(price) FROM Tickets WHERE status = 'Issued'")
        ).scalar() or 0

        # Количество рейсов
        trips_count = db.execute(text("SELECT COUNT(*) FROM Trips")).scalar() or 0

        # Количество свободных мест
        free_seats = db.execute(
            text("SELECT COUNT(*) FROM SeatAvailability WHERE status = 'Free'")
        ).scalar() or 0

        return {
            "total_tickets": tickets_count,
            "sold_tickets": sold_tickets,
            "total_revenue": float(total_revenue),
            "total_trips": trips_count,
            "free_seats": free_seats
        }

    except Exception as e:
        print(f"❌ Ошибка в get_stats: {e}")
        return {
            "total_tickets": 0,
            "sold_tickets": 0,
            "total_revenue": 0,
            "total_trips": 0,
            "free_seats": 0
        }

# =====================================================
# ЭНДПОИНТЫ ДЛЯ БРОНИРОВАНИЯ
# =====================================================

@app.post("/api/bookings")
async def create_booking(
    user_id: int,
    seat_ids: List[int],
    db: Session = Depends(get_db)
):
    """
    Создание бронирования
    """
    try:
        # Проверяем, что все места свободны
        check_sql = """
        SELECT id, status FROM SeatAvailability 
        WHERE id IN :seat_ids
        """

        result = db.execute(text(check_sql), {"seat_ids": tuple(seat_ids)})
        seats = result.fetchall()

        for seat in seats:
            if seat[1] != 'Free':
                raise HTTPException(
                    status_code=400,
                    detail=f"Место {seat[0]} уже занято"
                )

        # Получаем цены мест
        price_sql = """
        SELECT SUM(price) as total FROM SeatAvailability 
        WHERE id IN :seat_ids
        """
        total = db.execute(text(price_sql), {"seat_ids": tuple(seat_ids)}).scalar() or 0

        # Создаём заказ
        order_sql = """
        INSERT INTO Orders (user_id, created_at, total_amount, status)
        VALUES (:user_id, NOW(), :total, 'Created')
        """
        db.execute(text(order_sql), {"user_id": user_id, "total": total})
        db.commit()

        # Получаем ID созданного заказа
        order_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()

        # Бронируем места
        update_sql = """
        UPDATE SeatAvailability 
        SET status = 'Booked', 
            booked_until = DATE_ADD(NOW(), INTERVAL 15 MINUTE),
            order_id = :order_id
        WHERE id IN :seat_ids
        """
        db.execute(text(update_sql), {
            "order_id": order_id,
            "seat_ids": tuple(seat_ids)
        })

        # Создаём билеты
        for seat_id in seat_ids:
            ticket_sql = """
            INSERT INTO Tickets (order_id, user_id, seat_availability_id, 
                                document_type, document_number, price, status)
            SELECT :order_id, :user_id, :seat_id, 'RussianPassport', 
                   CONCAT('4512 ', LPAD(FLOOR(RAND() * 1000000), 6, '0')), 
                   price, 'Issued'
            FROM SeatAvailability WHERE id = :seat_id
            """
            db.execute(text(ticket_sql), {
                "order_id": order_id,
                "user_id": user_id,
                "seat_id": seat_id
            })

        db.commit()

        return {
            "order_id": order_id,
            "total": float(total),
            "status": "created",
            "message": "Бронирование создано"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка в create_booking: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/bookings/{booking_id}")
async def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db)
):
    """
    Отмена бронирования
    """
    try:
        # Проверяем статус заказа
        check_sql = """
        SELECT status FROM Orders WHERE id = :booking_id
        """
        result = db.execute(text(check_sql), {"booking_id": booking_id}).first()

        if not result:
            raise HTTPException(status_code=404, detail="Booking not found")

        if result[0] == 'Paid':
            raise HTTPException(status_code=400, detail="Cannot cancel paid booking")

        # Обновляем статус заказа
        db.execute(
            text("UPDATE Orders SET status = 'Cancelled' WHERE id = :booking_id"),
            {"booking_id": booking_id}
        )

        # Освобождаем места
        db.execute(
            text("""
                UPDATE SeatAvailability 
                SET status = 'Free', booked_until = NULL, order_id = NULL 
                WHERE order_id = :booking_id
            """),
            {"booking_id": booking_id}
        )

        db.commit()

        return {
            "status": "cancelled",
            "message": "Бронирование отменено"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка в cancel_booking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/debug/trip/{trip_id}")
async def debug_trip(trip_id: int, db: Session = Depends(get_db)):
    """Отладочный эндпоинт для проверки данных рейса"""
    try:
        # Проверяем наличие рейса
        trip_check = db.execute(
            text("SELECT id FROM Trips WHERE id = :trip_id"),
            {"trip_id": trip_id}
        ).first()

        if not trip_check:
            return {"error": f"Trip {trip_id} not found"}

        # Проверяем наличие мест
        seats_count = db.execute(
            text("SELECT COUNT(*) FROM SeatAvailability WHERE trip_id = :trip_id"),
            {"trip_id": trip_id}
        ).scalar()

        # Проверяем статусы
        status_counts = db.execute(
            text("""
                SELECT status, COUNT(*) 
                FROM SeatAvailability 
                WHERE trip_id = :trip_id 
                GROUP BY status
            """),
            {"trip_id": trip_id}
        ).fetchall()

        return {
            "trip_id": trip_id,
            "exists": True,
            "seats_in_seatavailability": seats_count,
            "status_distribution": [{"status": s[0], "count": s[1]} for s in status_counts]
        }
    except Exception as e:
        return {"error": str(e)}


# =====================================================
# ЭНДПОИНТЫ ДЛЯ УПРАВЛЕНИЯ ПОЕЗДАМИ (CRUD)
# =====================================================

@app.get("/api/trains")
async def get_trains(db: Session = Depends(get_db)):
    """Получение списка всех поездов"""
    try:
        sql = """
        SELECT 
            t.id,
            t.train_number,
            t.name,
            t.carrier,
            t.is_branded,
            COUNT(c.id) as carriages_count
        FROM Trains t
        LEFT JOIN Carriages c ON c.train_id = t.id
        GROUP BY t.id
        ORDER BY t.id
        """
        result = db.execute(text(sql))
        trains = result.fetchall()

        trains_list = []
        for train in trains:
            trains_list.append({
                "id": train[0],
                "train_number": train[1],
                "name": train[2],
                "carrier": train[3],
                "is_branded": bool(train[4]),
                "carriages_count": train[5] or 0
            })

        return trains_list
    except Exception as e:
        print(f"❌ Ошибка получения поездов: {e}")
        return []


@app.get("/api/trains/{train_id}")
async def get_train(train_id: int, db: Session = Depends(get_db)):
    """Получение информации о конкретном поезде"""
    try:
        sql = """
        SELECT 
            t.id,
            t.train_number,
            t.name,
            t.carrier,
            t.is_branded
        FROM Trains t
        WHERE t.id = :train_id
        """
        result = db.execute(text(sql), {"train_id": train_id})
        train = result.first()

        if not train:
            raise HTTPException(status_code=404, detail="Train not found")

        # Получаем вагоны поезда
        carriages_sql = """
        SELECT 
            c.id,
            c.carriage_number,
            ct.name as carriage_type,
            COUNT(s.id) as seats_count
        FROM Carriages c
        JOIN CarriageTypes ct ON c.carriage_type_id = ct.id
        LEFT JOIN Seats s ON s.carriage_id = c.id
        WHERE c.train_id = :train_id
        GROUP BY c.id, c.carriage_number, ct.name
        ORDER BY c.carriage_number
        """
        carriages_result = db.execute(text(carriages_sql), {"train_id": train_id})
        carriages = carriages_result.fetchall()

        carriages_list = []
        for carriage in carriages:
            carriages_list.append({
                "id": carriage[0],
                "carriage_number": carriage[1],
                "carriage_type": carriage[2],
                "seats_count": carriage[3] or 0
            })

        return {
            "id": train[0],
            "train_number": train[1],
            "name": train[2],
            "carrier": train[3],
            "is_branded": bool(train[4]),
            "carriages": carriages_list
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Ошибка получения поезда: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/trains", status_code=201)
async def create_train(
        train_data: dict,
        db: Session = Depends(get_db)
):
    """Создание нового поезда"""
    try:
        # Проверка обязательных полей
        required_fields = ["train_number", "name"]
        for field in required_fields:
            if field not in train_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

        # Проверка уникальности номера поезда
        check_sql = "SELECT id FROM Trains WHERE train_number = :train_number"
        existing = db.execute(text(check_sql), {"train_number": train_data["train_number"]}).first()
        if existing:
            raise HTTPException(status_code=400, detail="Train number already exists")

        # Вставка нового поезда
        insert_sql = """
        INSERT INTO Trains (train_number, name, carrier, is_branded)
        VALUES (:train_number, :name, :carrier, :is_branded)
        """
        db.execute(text(insert_sql), {
            "train_number": train_data["train_number"],
            "name": train_data["name"],
            "carrier": train_data.get("carrier", "РЖД"),
            "is_branded": train_data.get("is_branded", False)
        })
        db.commit()

        # Получаем ID созданного поезда
        train_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()

        return {
            "id": train_id,
            "train_number": train_data["train_number"],
            "name": train_data["name"],
            "carrier": train_data.get("carrier", "РЖД"),
            "is_branded": train_data.get("is_branded", False),
            "message": "Train created successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка создания поезда: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/trains/{train_id}")
async def update_train(
        train_id: int,
        train_data: dict,
        db: Session = Depends(get_db)
):
    """Обновление информации о поезде"""
    try:
        # Проверка существования поезда
        check_sql = "SELECT id FROM Trains WHERE id = :train_id"
        existing = db.execute(text(check_sql), {"train_id": train_id}).first()
        if not existing:
            raise HTTPException(status_code=404, detail="Train not found")

        # Обновление данных
        update_sql = """
        UPDATE Trains 
        SET train_number = :train_number,
            name = :name,
            carrier = :carrier,
            is_branded = :is_branded
        WHERE id = :train_id
        """
        db.execute(text(update_sql), {
            "train_id": train_id,
            "train_number": train_data["train_number"],
            "name": train_data["name"],
            "carrier": train_data.get("carrier", "РЖД"),
            "is_branded": train_data.get("is_branded", False)
        })
        db.commit()

        return {"message": "Train updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка обновления поезда: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/trains/{train_id}")
async def delete_train(train_id: int, db: Session = Depends(get_db)):
    """Удаление поезда"""
    try:
        # Проверка существования поезда
        check_sql = "SELECT id FROM Trains WHERE id = :train_id"
        existing = db.execute(text(check_sql), {"train_id": train_id}).first()
        if not existing:
            raise HTTPException(status_code=404, detail="Train not found")

        # Проверка, есть ли связанные рейсы
        trips_sql = "SELECT id FROM Trips WHERE train_id = :train_id LIMIT 1"
        has_trips = db.execute(text(trips_sql), {"train_id": train_id}).first()
        if has_trips:
            raise HTTPException(status_code=400, detail="Cannot delete train with existing trips")

        # Удаление поезда (вагоны удалятся каскадно)
        delete_sql = "DELETE FROM Trains WHERE id = :train_id"
        db.execute(text(delete_sql), {"train_id": train_id})
        db.commit()

        return {"message": "Train deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка удаления поезда: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# ЭНДПОИНТЫ ДЛЯ УПРАВЛЕНИЯ МАРШРУТАМИ
# =====================================================

@app.get("/api/routes")
async def get_routes(db: Session = Depends(get_db)):
    """Получение списка всех маршрутов"""
    try:
        sql = """
        SELECT 
            r.id,
            r.name,
            r.departure_station,
            r.arrival_station,
            COUNT(rs.id) as stations_count
        FROM Routes r
        LEFT JOIN RouteStations rs ON rs.route_id = r.id
        GROUP BY r.id
        ORDER BY r.id
        """
        result = db.execute(text(sql))
        routes = result.fetchall()

        routes_list = []
        for route in routes:
            routes_list.append({
                "id": route[0],
                "name": route[1],
                "departure_station": route[2],
                "arrival_station": route[3],
                "stations_count": route[4] or 0
            })

        return routes_list
    except Exception as e:
        print(f"❌ Ошибка получения маршрутов: {e}")
        return []


@app.post("/api/routes")
async def create_route(route_data: dict, db: Session = Depends(get_db)):
    """Создание нового маршрута"""
    try:
        required_fields = ["name", "departure_station", "arrival_station"]
        for field in required_fields:
            if field not in route_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

        insert_sql = """
        INSERT INTO Routes (name, departure_station, arrival_station)
        VALUES (:name, :departure_station, :arrival_station)
        """
        db.execute(text(insert_sql), {
            "name": route_data["name"],
            "departure_station": route_data["departure_station"],
            "arrival_station": route_data["arrival_station"]
        })
        db.commit()

        route_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()

        return {
            "id": route_id,
            "name": route_data["name"],
            "departure_station": route_data["departure_station"],
            "arrival_station": route_data["arrival_station"],
            "message": "Route created successfully"
        }
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка создания маршрута: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/routes/{route_id}")
async def delete_route(route_id: int, db: Session = Depends(get_db)):
    """Удаление маршрута"""
    try:
        # Проверка, есть ли связанные рейсы
        trips_sql = "SELECT id FROM Trips WHERE route_id = :route_id LIMIT 1"
        has_trips = db.execute(text(trips_sql), {"route_id": route_id}).first()
        if has_trips:
            raise HTTPException(status_code=400, detail="Cannot delete route with existing trips")

        delete_sql = "DELETE FROM Routes WHERE id = :route_id"
        db.execute(text(delete_sql), {"route_id": route_id})
        db.commit()

        return {"message": "Route deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка удаления маршрута: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# ЭНДПОИНТЫ ДЛЯ УПРАВЛЕНИЯ ВАГОНАМИ
# =====================================================

@app.get("/api/carriages")
async def get_carriages(db: Session = Depends(get_db)):
    """Получение списка всех вагонов"""
    try:
        sql = """
        SELECT 
            c.id,
            t.train_number,
            c.carriage_number,
            ct.name as carriage_type,
            COUNT(s.id) as seats_count
        FROM Carriages c
        JOIN Trains t ON c.train_id = t.id
        JOIN CarriageTypes ct ON c.carriage_type_id = ct.id
        LEFT JOIN Seats s ON s.carriage_id = c.id
        GROUP BY c.id, t.train_number, c.carriage_number, ct.name
        ORDER BY t.train_number, c.carriage_number
        """
        result = db.execute(text(sql))
        carriages = result.fetchall()

        carriages_list = []
        for carriage in carriages:
            carriages_list.append({
                "id": carriage[0],
                "train_number": carriage[1],
                "carriage_number": carriage[2],
                "carriage_type": carriage[3],
                "seats_count": carriage[4] or 0
            })

        return carriages_list
    except Exception as e:
        print(f"❌ Ошибка получения вагонов: {e}")
        return []


@app.post("/api/carriages")
async def create_carriage(carriage_data: dict, db: Session = Depends(get_db)):
    """Создание нового вагона"""
    try:
        required_fields = ["train_id", "carriage_number", "carriage_type_id"]
        for field in required_fields:
            if field not in carriage_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

        insert_sql = """
        INSERT INTO Carriages (train_id, carriage_number, carriage_type_id)
        VALUES (:train_id, :carriage_number, :carriage_type_id)
        """
        db.execute(text(insert_sql), {
            "train_id": carriage_data["train_id"],
            "carriage_number": carriage_data["carriage_number"],
            "carriage_type_id": carriage_data["carriage_type_id"]
        })
        db.commit()

        carriage_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()

        return {
            "id": carriage_id,
            "train_id": carriage_data["train_id"],
            "carriage_number": carriage_data["carriage_number"],
            "carriage_type_id": carriage_data["carriage_type_id"],
            "message": "Carriage created successfully"
        }
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка создания вагона: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/carriages/{carriage_id}")
async def delete_carriage(carriage_id: int, db: Session = Depends(get_db)):
    """Удаление вагона"""
    try:
        # Проверка, есть ли связанные места
        seats_sql = "SELECT id FROM Seats WHERE carriage_id = :carriage_id LIMIT 1"
        has_seats = db.execute(text(seats_sql), {"carriage_id": carriage_id}).first()
        if has_seats:
            raise HTTPException(status_code=400, detail="Cannot delete carriage with existing seats")

        delete_sql = "DELETE FROM Carriages WHERE id = :carriage_id"
        db.execute(text(delete_sql), {"carriage_id": carriage_id})
        db.commit()

        return {"message": "Carriage deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка удаления вагона: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# ЭНДПОИНТЫ ДЛЯ УПРАВЛЕНИЯ СТАНЦИЯМИ
# =====================================================

@app.get("/api/stations")
async def get_stations(db: Session = Depends(get_db)):
    """Получение списка всех станций"""
    try:
        sql = "SELECT id, name, city, esr_code FROM Stations ORDER BY name"
        result = db.execute(text(sql))
        stations = result.fetchall()

        stations_list = []
        for station in stations:
            stations_list.append({
                "id": station[0],
                "name": station[1],
                "city": station[2],
                "esr_code": station[3]
            })

        return stations_list
    except Exception as e:
        print(f"❌ Ошибка получения станций: {e}")
        return []


@app.post("/api/stations")
async def create_station(station_data: dict, db: Session = Depends(get_db)):
    """Создание новой станции"""
    try:
        required_fields = ["name", "city"]
        for field in required_fields:
            if field not in station_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

        insert_sql = """
        INSERT INTO Stations (name, city, esr_code)
        VALUES (:name, :city, :esr_code)
        """
        db.execute(text(insert_sql), {
            "name": station_data["name"],
            "city": station_data["city"],
            "esr_code": station_data.get("esr_code")
        })
        db.commit()

        station_id = db.execute(text("SELECT LAST_INSERT_ID()")).scalar()

        return {
            "id": station_id,
            "name": station_data["name"],
            "city": station_data["city"],
            "esr_code": station_data.get("esr_code"),
            "message": "Station created successfully"
        }
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка создания станции: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/stations/{station_id}")
async def delete_station(station_id: int, db: Session = Depends(get_db)):
    """Удаление станции"""
    try:
        # Проверка, используется ли станция в маршрутах
        routes_sql = "SELECT id FROM RouteStations WHERE station_id = :station_id LIMIT 1"
        has_routes = db.execute(text(routes_sql), {"station_id": station_id}).first()
        if has_routes:
            raise HTTPException(status_code=400, detail="Cannot delete station used in routes")

        delete_sql = "DELETE FROM Stations WHERE id = :station_id"
        db.execute(text(delete_sql), {"station_id": station_id})
        db.commit()

        return {"message": "Station deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка удаления станции: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# ТОЧКА ВХОДА
# =====================================================

if __name__ == "__main__":
    print("=" * 50)
    print("🚂 Railway Tickets API")
    print("=" * 50)
    print(f"📡 Подключение к БД: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(f"📡 Сервер запускается на http://127.0.0.1:8000")
    print(f"📡 Документация: http://127.0.0.1:8000/docs")
    print("=" * 50)

    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )