"""
Модульные тесты для библиотеки расчётов с использованием pytest
"""

import pytest
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.backend.calculations import TicketCalculator


class TestTicketCalculator:
    """Тесты для класса TicketCalculator"""

    def setup_method(self):
        """Подготовка перед каждым тестом"""
        self.calculator = TicketCalculator()
        self.base_price = 1000.0

    # ===== Тесты расчёта цены билета =====

    def test_calculate_base_price(self):
        """Тест 1: Базовая цена без скидок и надбавок"""
        price = self.calculator.calculate_ticket_price(
            base_price=1000,
            carriage_type="Плацкарт",
            age=30
        )
        assert price == 1000.0

    def test_child_discount(self):
        """Тест 2: Детская скидка 50%"""
        price = self.calculator.calculate_ticket_price(
            base_price=1000,
            carriage_type="Плацкарт",
            age=10
        )
        assert price == 500.0

    def test_pensioner_discount(self):
        """Тест 3: Пенсионная скидка 30%"""
        price = self.calculator.calculate_ticket_price(
            base_price=1000,
            carriage_type="Плацкарт",
            age=70
        )
        assert price == 700.0

    def test_return_ticket_extra_discount(self):
        """Тест 4: Дополнительная скидка за обратный билет"""
        price = self.calculator.calculate_ticket_price(
            base_price=1000,
            carriage_type="Плацкарт",
            age=30,
            is_return=True
        )
        assert price == 900.0

    def test_carriage_type_multiplier(self):
        """Тест 5: Коэффициент типа вагона"""
        prices = {
            "Сидячий": self.calculator.calculate_ticket_price(1000, "Сидячий", 30),
            "Плацкарт": self.calculator.calculate_ticket_price(1000, "Плацкарт", 30),
            "Купе": self.calculator.calculate_ticket_price(1000, "Купе", 30),
            "СВ": self.calculator.calculate_ticket_price(1000, "СВ", 30),
            "Люкс": self.calculator.calculate_ticket_price(1000, "Люкс", 30)
        }

        assert prices["Сидячий"] == 700.0
        assert prices["Плацкарт"] == 1000.0
        assert prices["Купе"] == 1500.0
        assert prices["СВ"] == 1800.0
        assert prices["Люкс"] == 2500.0

    def test_window_seat_extra(self):
        """Тест 6: Надбавка за место у окна"""
        price = self.calculator.calculate_ticket_price(
            base_price=1000,
            carriage_type="Плацкарт",
            age=30,
            is_window=True
        )
        assert price == 1100.0

    def test_socket_extra(self):
        """Тест 7: Надбавка за розетку"""
        price = self.calculator.calculate_ticket_price(
            base_price=1000,
            carriage_type="Плацкарт",
            age=30,
            has_socket=True
        )
        assert price == 1200.0

    def test_side_seat_discount(self):
        """Тест 8: Скидка за боковое место"""
        price = self.calculator.calculate_ticket_price(
            base_price=1000,
            carriage_type="Плацкарт",
            age=30,
            is_side=True
        )
        assert price == 800.0

    def test_all_factors_combined(self):
        """Тест 9: Все факторы вместе"""
        price = self.calculator.calculate_ticket_price(
            base_price=1000,
            carriage_type="Купе",
            age=10,  # ребёнок
            is_window=True,
            has_socket=True,
            is_return=True
        )
        # Ожидаемый расчёт:
        # 1000 * 1.5 (купе) = 1500
        # +10% за окно = 1650
        # +200 за розетку = 1850
        # -50% детская = 925
        # -10% обратный, но не больше 50% общей скидки = 925 (остаётся 925)
        assert price == 925.0

    def test_max_discount_limit(self):
        """Тест 10: Максимальная скидка не более 50%"""
        price = self.calculator.calculate_ticket_price(
            base_price=1000,
            carriage_type="Плацкарт",
            age=10,  # 50% детская
            is_return=True  # +10% за обратный, но не больше 50%
        )
        assert price == 500.0  # Должно быть 500, а не 450

    # ===== Тесты расчёта длительности =====

    def test_trip_duration_same_day(self):
        """Тест 11: Длительность поездки в тот же день"""
        dep = datetime(2024, 1, 1, 10, 0)
        arr = datetime(2024, 1, 1, 14, 30)

        duration = self.calculator.calculate_trip_duration(dep, arr)
        assert duration["days"] == 0
        assert duration["hours"] == 4
        assert duration["minutes"] == 30
        assert duration["total_minutes"] == 270

    def test_trip_duration_multiple_days(self):
        """Тест 12: Многодневная поездка"""
        dep = datetime(2024, 1, 1, 10, 0)
        arr = datetime(2024, 1, 3, 15, 45)

        duration = self.calculator.calculate_trip_duration(dep, arr)
        assert duration["days"] == 2
        assert duration["hours"] == 5
        assert duration["minutes"] == 45
        assert duration["total_minutes"] == 3225

    def test_format_duration(self):
        """Тест 13: Форматирование длительности"""
        duration1 = {"days": 0, "hours": 4, "minutes": 30, "total_minutes": 270}
        duration2 = {"days": 2, "hours": 5, "minutes": 45, "total_minutes": 3225}
        duration3 = {"days": 0, "hours": 0, "minutes": 0, "total_minutes": 0}

        assert self.calculator.format_duration(duration1) == "4ч 30мин"
        assert self.calculator.format_duration(duration2) == "2д 5ч 45мин"
        assert self.calculator.format_duration(duration3) == "0мин"

    # ===== Тесты расчёта доступности =====

    def test_available_seats_color_green(self):
        """Тест 14: Зелёный цвет при многих местах"""
        color = self.calculator.calculate_available_seats_color(50, 100)
        assert color == "#d4edda"

    def test_available_seats_color_yellow(self):
        """Тест 15: Жёлтый цвет при среднем количестве"""
        color = self.calculator.calculate_available_seats_color(30, 100)
        assert color == "#fff3cd"

    def test_available_seats_color_red(self):
        """Тест 16: Красный цвет при малом количестве"""
        color = self.calculator.calculate_available_seats_color(10, 100)
        assert color == "#f8d7da"

    # ===== Тесты расчёта цен и статистики =====

    def test_calculate_total_price(self):
        """Тест 17: Расчёт общей стоимости"""
        seats = [
            {"price": 1000},
            {"price": 1500},
            {"price": 2000}
        ]
        total = self.calculator.calculate_total_price(seats)
        assert total == 4500.0

    def test_calculate_average_price(self):
        """Тест 18: Расчёт средней цены"""
        prices = [1000, 1500, 2000, 2500]
        avg = self.calculator.calculate_average_price(prices)
        assert avg == 1750.0

    def test_calculate_price_range(self):
        """Тест 19: Расчёт диапазона цен"""
        prices = [1000, 1500, 2000, 2500]
        min_price, max_price = self.calculator.calculate_price_range(prices)
        assert min_price == 1000.0
        assert max_price == 2500.0

    def test_calculate_occupancy_rate(self):
        """Тест 20: Расчёт процента занятости"""
        rate = self.calculator.calculate_occupancy_rate(30, 100)
        assert rate == 70.0

    def test_calculate_revenue(self):
        """Тест 21: Расчёт выручки"""
        tickets = [
            {"price": 1000, "status": "Issued"},
            {"price": 1500, "status": "Issued"},
            {"price": 2000, "status": "Returned"},
            {"price": 2500, "status": "Issued"}
        ]
        revenue = self.calculator.calculate_revenue(tickets)
        assert revenue == 5000.0

    def test_calculate_popularity(self):
        """Тест 22: Расчёт популярности"""
        popularity = self.calculator.calculate_popularity(75, 100)
        assert popularity == 0.75

    def test_calculate_discount_eligible(self):
        """Тест 23: Проверка права на скидку"""
        assert self.calculator.calculate_discount_eligible(10) is True
        assert self.calculator.calculate_discount_eligible(70) is True
        assert self.calculator.calculate_discount_eligible(30, 10) is True
        assert self.calculator.calculate_discount_eligible(30, 1) is False