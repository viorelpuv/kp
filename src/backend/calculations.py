from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import math


class TicketCalculator:
    """Класс для расчётов, связанных с билетами"""

    # Константы для расчётов
    CHILD_AGE_LIMIT = 18
    PENSION_AGE_LIMIT = 65
    CHILD_DISCOUNT = 0.5
    PENSION_DISCOUNT = 0.3
    RETURN_TICKET_DISCOUNT = 0.1
    MAX_DISCOUNT = 0.5

    # Коэффициенты для разных типов вагонов
    CARRIAGE_MULTIPLIERS = {
        "Сидячий": 0.7,
        "Плацкарт": 1.0,
        "Купе": 1.5,
        "СВ": 1.8,
        "Люкс": 2.5
    }

    # Надбавки
    WINDOW_SEAT_EXTRA = 0.1  # +10% за место у окна
    SOCKET_EXTRA = 200  # +200₽ за розетку
    SIDE_SEAT_DISCOUNT = 0.2  # -20% за боковое место

    @staticmethod
    def calculate_ticket_price(
            base_price: float,
            carriage_type: str,
            age: int,
            is_window: bool = False,
            has_socket: bool = False,
            is_side: bool = False,
            is_return: bool = False
    ) -> float:
        """
        Расчёт итоговой цены билета с учётом всех факторов

        Args:
            base_price: Базовая цена
            carriage_type: Тип вагона
            age: Возраст пассажира
            is_window: Место у окна
            has_socket: Наличие розетки
            is_side: Боковое место
            is_return: Обратный билет

        Returns:
            float: Итоговая цена
        """
        # Применяем коэффициент типа вагона
        multiplier = TicketCalculator.CARRIAGE_MULTIPLIERS.get(carriage_type, 1.0)
        price = base_price * multiplier

        # Надбавки за характеристики места
        if is_window:
            price *= (1 + TicketCalculator.WINDOW_SEAT_EXTRA)
        if has_socket:
            price += TicketCalculator.SOCKET_EXTRA
        if is_side:
            price *= (1 - TicketCalculator.SIDE_SEAT_DISCOUNT)

        # Скидки
        discount = TicketCalculator._calculate_discount(age, is_return)
        price *= (1 - discount)

        return round(price, 2)

    @staticmethod
    def _calculate_discount(age: int, is_return: bool = False) -> float:
        """
        Расчёт скидки в зависимости от возраста и типа билета

        Args:
            age: Возраст пассажира
            is_return: Обратный билет

        Returns:
            float: Процент скидки
        """
        discount = 0.0

        if age < TicketCalculator.CHILD_AGE_LIMIT:
            discount = TicketCalculator.CHILD_DISCOUNT
        elif age >= TicketCalculator.PENSION_AGE_LIMIT:
            discount = TicketCalculator.PENSION_DISCOUNT

        if is_return:
            discount = min(discount + TicketCalculator.RETURN_TICKET_DISCOUNT,
                           TicketCalculator.MAX_DISCOUNT)

        return discount

    @staticmethod
    def calculate_trip_duration(
            departure: datetime,
            arrival: datetime
    ) -> Dict[str, int]:
        """
        Расчёт длительности поездки

        Args:
            departure: Время отправления
            arrival: Время прибытия

        Returns:
            Dict: Словарь с днями, часами и минутами
        """
        duration = arrival - departure

        return {
            "days": duration.days,
            "hours": duration.seconds // 3600,
            "minutes": (duration.seconds % 3600) // 60,
            "total_minutes": int(duration.total_seconds() // 60)
        }

    @staticmethod
    def format_duration(duration: Dict[str, int]) -> str:
        """
        Форматирование длительности поездки

        Args:
            duration: Словарь с длительностью

        Returns:
            str: Отформатированная строка
        """
        parts = []
        if duration["days"] > 0:
            parts.append(f"{duration['days']}д")
        if duration["hours"] > 0:
            parts.append(f"{duration['hours']}ч")
        if duration["minutes"] > 0:
            parts.append(f"{duration['minutes']}мин")

        return " ".join(parts) if parts else "0мин"

    @staticmethod
    def calculate_available_seats_color(available: int, total: int) -> str:
        """
        Определение цвета для отображения доступности

        Args:
            available: Количество свободных мест
            total: Общее количество мест

        Returns:
            str: Цвет в HEX формате
        """
        if total == 0:
            return "#d4edda"  # зелёный по умолчанию

        percentage = available / total

        if percentage >= 0.5:
            return "#d4edda"  # зелёный - много мест
        elif percentage >= 0.2:
            return "#fff3cd"  # жёлтый - средне
        else:
            return "#f8d7da"  # красный - мало

    @staticmethod
    def calculate_total_price(seats: List[Dict]) -> float:
        """
        Расчёт общей стоимости выбранных мест

        Args:
            seats: Список мест с ценами

        Returns:
            float: Общая стоимость
        """
        return sum(seat.get("price", 0) for seat in seats)

    @staticmethod
    def calculate_average_price(prices: List[float]) -> float:
        """
        Расчёт средней цены

        Args:
            prices: Список цен

        Returns:
            float: Средняя цена
        """
        if not prices:
            return 0.0
        return sum(prices) / len(prices)

    @staticmethod
    def calculate_price_range(prices: List[float]) -> Tuple[float, float]:
        """
        Расчёт диапазона цен

        Args:
            prices: Список цен

        Returns:
            Tuple[float, float]: Минимальная и максимальная цена
        """
        if not prices:
            return (0.0, 0.0)
        return (min(prices), max(prices))

    @staticmethod
    def calculate_occupancy_rate(available: int, total: int) -> float:
        """
        Расчёт процента занятости

        Args:
            available: Свободные места
            total: Всего мест

        Returns:
            float: Процент занятости (0-100)
        """
        if total == 0:
            return 0.0
        return ((total - available) / total) * 100

    @staticmethod
    def calculate_revenue(tickets: List[Dict]) -> float:
        """
        Расчёт выручки от проданных билетов

        Args:
            tickets: Список билетов

        Returns:
            float: Общая выручка
        """
        return sum(ticket.get("price", 0) for ticket in tickets
                   if ticket.get("status") == "Issued")

    @staticmethod
    def calculate_popularity(tickets_sold: int, total_tickets: int) -> float:
        """
        Расчёт популярности направления

        Args:
            tickets_sold: Продано билетов
            total_tickets: Всего билетов

        Returns:
            float: Коэффициент популярности (0-1)
        """
        if total_tickets == 0:
            return 0.0
        return tickets_sold / total_tickets

    @staticmethod
    def calculate_discount_eligible(age: int, trip_count: int = 1) -> bool:
        """
        Проверка eligibility для скидки

        Args:
            age: Возраст пассажира
            trip_count: Количество поездок

        Returns:
            bool: True если положена скидка
        """
        return (age < TicketCalculator.CHILD_AGE_LIMIT or
                age >= TicketCalculator.PENSION_AGE_LIMIT or
                trip_count >= 10)  # Скидка за лояльность