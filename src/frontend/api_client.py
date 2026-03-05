import requests
import json
from typing import List, Dict, Any, Optional


class RailwayAPI:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()

    def get_trips(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Получение списка рейсов с полной информацией"""
        params = filters or {}
        print(f"🔍 Запрос к API: {self.base_url}/api/trips с параметрами {params}")

        try:
            response = self.session.get(f"{self.base_url}/api/trips", params=params, timeout=5)
            print(f"📡 Статус ответа: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"📦 Данные от API: {data}")
                return data
            else:
                print(f"❌ Ошибка API: {response.status_code}")
                return {"trips": [], "count": 0, "filters": filters}

        except Exception as e:
            print(f"❌ Ошибка запроса: {e}")
            return {"trips": [], "count": 0, "filters": filters}

    def get_trip_detail(self, trip_id):
        """Получение детальной информации о рейсе"""
        try:
            print(f"🔍 Запрос деталей рейса {trip_id}")
            response = self.session.get(
                f"{self.base_url}/api/trips/{trip_id}",
                timeout=10
            )
            print(f"📡 Статус ответа: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"📦 Получены данные по рейсу {trip_id}")

                # Проверяем наличие мест
                if 'seats' in data:
                    print(f"   Мест в ответе: {len(data['seats'])}")
                    # Покажем пример первого места
                    if data['seats']:
                        print(f"   Пример места: {data['seats'][0]}")
                else:
                    print(f"⚠️ В ответе нет поля 'seats'")
                    # Создаём тестовые места для отладки
                    data['seats'] = self.generate_test_seats()

                return data
            else:
                print(f"❌ Ошибка API: {response.status_code}")
                print(f"Ответ: {response.text[:200]}")
                return {"seats": self.generate_test_seats()}

        except Exception as e:
            print(f"❌ Ошибка запроса: {e}")
            return {"seats": self.generate_test_seats()}

    def generate_test_seats(self):
        """Генерация тестовых мест для отладки"""
        seats = []
        carriage_types = ["Купе", "Плацкарт", "СВ", "Люкс", "Сидячий"]

        for ct in carriage_types:
            # Генерируем разное количество мест для разных типов
            if ct == "Купе":
                total = 36
                free = 12
            elif ct == "Плацкарт":
                total = 54
                free = 8
            elif ct == "СВ":
                total = 18
                free = 4
            elif ct == "Люкс":
                total = 12
                free = 2
            else:  # Сидячий
                total = 60
                free = 20

            for i in range(1, total + 1):
                seat = {
                    'id': i * 100 + len(seats),
                    'seat_number': i,
                    'carriage_type': ct,
                    'price': 1000 + (i * 50),
                    'status': 'Free' if i <= free else 'Sold',
                    'is_window': (i % 4 in [1, 2]),
                    'has_socket': (i % 3 == 0)
                }
                seats.append(seat)

        print(f"🔧 Сгенерировано {len(seats)} тестовых мест")
        return seats
    
    def create_booking(self, user_id: int, seat_ids: List[int]) -> Dict:
        """Создание бронирования"""
        response = self.session.post(
            f"{self.base_url}/api/bookings",
            params={"user_id": user_id},
            json=seat_ids
        )
        response.raise_for_status()
        return response.json()
    
    def pay_booking(self, booking_id: int, payment_method: str) -> Dict:
        """Оплата бронирования"""
        response = self.session.post(
            f"{self.base_url}/api/bookings/{booking_id}/pay",
            params={"payment_method": payment_method}
        )
        response.raise_for_status()
        return response.json()
    
    def cancel_booking(self, booking_id: int) -> Dict:
        """Отмена бронирования"""
        response = self.session.delete(f"{self.base_url}/api/bookings/{booking_id}")
        response.raise_for_status()
        return response.json()
    
    def search(self, query: str) -> List[Dict]:
        """Поиск рейсов"""
        response = self.session.get(
            f"{self.base_url}/api/search",
            params={"query": query}
        )
        response.raise_for_status()
        return response.json()
    
    def get_stats(self) -> Dict:
        """Получение статистики"""
        response = self.session.get(f"{self.base_url}/api/stats")
        response.raise_for_status()
        return response.json()

    def get_trip_detail(self, trip_id):
        """Получение детальной информации о рейсе"""
        try:
            response = self.session.get(f"{self.base_url}/api/trips/{trip_id}", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Ошибка API: {response.status_code}")
                return {"seats": []}
        except Exception as e:
            print(f"❌ Ошибка запроса: {e}")
            return {"seats": []}
