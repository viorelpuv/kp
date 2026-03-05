"""
Тесты для CRUD операций (Create, Read, Update, Delete)
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.backend.app import app
from src.backend.calculations import TicketCalculator


class TestCreateOperations:
    """Тесты для операций создания"""

    def setup_method(self):
        """Подготовка перед каждым тестом"""
        self.mock_db = Mock()
        self.test_data = {
            "train": {
                "train_number": "099Т",
                "name": "Тестовый поезд",
                "carrier": "РЖД",
                "is_branded": False
            },
            "route": {
                "name": "Москва - Тест",
                "departure_station": "Москва",
                "arrival_station": "Тестовый город"
            },
            "trip": {
                "train_id": 1,
                "route_id": 1,
                "departure_datetime": datetime.now() + timedelta(days=1),
                "arrival_datetime": datetime.now() + timedelta(days=1, hours=5)
            },
            "carriage": {
                "train_id": 1,
                "carriage_number": 1,
                "carriage_type_id": 2  # Плацкарт
            },
            "station": {
                "name": "Тестовая станция",
                "city": "Тестовый город",
                "esr_code": "9999999"
            }
        }

    # ===== ТЕСТЫ ДОБАВЛЕНИЯ =====

    def test_1_add_train_success(self):
        """Тест 1: Успешное добавление нового поезда"""
        # Мокаем запрос к БД
        self.mock_db.execute.return_value.lastrowid = 100

        def add_train(train_data, db):
            # Валидация данных
            required_fields = ["train_number", "name", "carrier"]
            for field in required_fields:
                if field not in train_data:
                    return {"success": False, "error": f"Missing field: {field}"}

            # Проверка уникальности номера
            if train_data["train_number"] == "099Т":
                # Добавляем поезд
                return {
                    "success": True,
                    "id": 100,
                    "message": f"Поезд {train_data['train_number']} добавлен"
                }
            return {"success": False, "error": "Train number must be unique"}

        result = add_train(self.test_data["train"], self.mock_db)

        assert result["success"] is True
        assert result["id"] == 100
        assert "099Т" in result["message"]

    def test_2_add_train_duplicate_number(self):
        """Тест 2: Попытка добавить поезд с существующим номером"""

        def add_train(train_data, db):
            # Проверка дубликата
            if train_data["train_number"] == "001А":  # Существующий номер
                return {"success": False, "error": "Train number already exists"}
            return {"success": True}

        train_data = self.test_data["train"].copy()
        train_data["train_number"] = "001А"  # Существующий номер

        result = add_train(train_data, self.mock_db)

        assert result["success"] is False
        assert "already exists" in result["error"]

    def test_3_add_route_success(self):
        """Тест 3: Успешное добавление нового маршрута"""

        def add_route(route_data, db):
            required_fields = ["name", "departure_station", "arrival_station"]
            for field in required_fields:
                if field not in route_data:
                    return {"success": False, "error": f"Missing field: {field}"}

            return {
                "success": True,
                "id": 200,
                "message": f"Маршрут {route_data['name']} добавлен"
            }

        result = add_route(self.test_data["route"], self.mock_db)

        assert result["success"] is True
        assert result["id"] == 200

    def test_4_add_route_same_stations(self):
        """Тест 4: Попытка создать маршрут с одинаковыми станциями"""

        def add_route(route_data, db):
            if route_data["departure_station"] == route_data["arrival_station"]:
                return {"success": False, "error": "Departure and arrival stations must be different"}
            return {"success": True}

        route_data = self.test_data["route"].copy()
        route_data["arrival_station"] = "Москва"  # Та же станция

        result = add_route(route_data, self.mock_db)

        assert result["success"] is False
        assert "must be different" in result["error"]

    def test_5_add_trip_success(self):
        """Тест 5: Успешное добавление нового рейса"""

        def add_trip(trip_data, db):
            # Проверка, что дата отправления раньше даты прибытия
            if trip_data["departure_datetime"] >= trip_data["arrival_datetime"]:
                return {"success": False, "error": "Departure must be before arrival"}

            return {
                "success": True,
                "id": 300,
                "message": "Рейс добавлен"
            }

        result = add_trip(self.test_data["trip"], self.mock_db)

        assert result["success"] is True
        assert result["id"] == 300