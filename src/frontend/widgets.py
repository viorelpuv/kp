import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Callable, Optional
from datetime import datetime


class TripCard(tk.Frame):
    """Карточка рейса для списка"""

    def __init__(self, parent, trip_data, on_select=None, on_add_to_cart=None):
        super().__init__(parent, bg="white", relief="raised", bd=1)

        # Защита от неправильных данных
        if not isinstance(trip_data, dict):
            print(f"❌ TripCard получил не словарь: {trip_data}")
            trip_data = {}

        self.trip_data = trip_data
        self.on_select = on_select
        self.on_add_to_cart = on_add_to_cart

        # Безопасное получение данных с значениями по умолчанию
        availability = trip_data.get("available_seats", 0)
        if not isinstance(availability, (int, float)):
            availability = 0

        # Определяем цвет в зависимости от доступности
        if availability > 20:
            color = "#d4edda"  # зелёный - много мест
        elif availability > 5:
            color = "#fff3cd"  # жёлтый - мало мест
        else:
            color = "#f8d7da"  # красный - почти нет мест

        self.configure(bg=color)

        # Основная информация
        info_frame = tk.Frame(self, bg=color)
        info_frame.pack(fill="x", padx=5, pady=5)

        # Безопасное получение всех полей
        dep_station = trip_data.get("departure_station", "Неизвестно")
        arr_station = trip_data.get("arrival_station", "Неизвестно")
        train_name = trip_data.get("train_name", "Неизвестный поезд")
        train_number = trip_data.get("train_number", "")
        min_price = trip_data.get("min_price", 0)
        dep_datetime = trip_data.get("departure_datetime", "")

        # Маршрут
        route_text = f"{dep_station} → {arr_station}"
        tk.Label(info_frame, text=route_text, font=("Arial", 12, "bold"), bg=color).pack(anchor="w")

        # Номер поезда
        if train_number:
            tk.Label(info_frame, text=f"Поезд №{train_number} {train_name}",
                     font=("Arial", 10), bg=color).pack(anchor="w")
        else:
            tk.Label(info_frame, text=f"Поезд: {train_name}",
                     font=("Arial", 10), bg=color).pack(anchor="w")

        # Время
        if dep_datetime:
            try:
                if 'T' in dep_datetime:
                    dep_time = dep_datetime.replace('T', ' ')[:16]
                else:
                    dep_time = dep_datetime
            except:
                dep_time = dep_datetime
        else:
            dep_time = "Время неизвестно"

        tk.Label(info_frame, text=f"Отправление: {dep_time}", bg=color).pack(anchor="w")

        # Цена и кнопки
        bottom_frame = tk.Frame(info_frame, bg=color)
        bottom_frame.pack(fill="x", pady=5)

        tk.Label(bottom_frame, text=f"от {min_price} ₽",
                 font=("Arial", 14, "bold"), fg="green", bg=color).pack(side="left")

        # Кнопки
        buttons_frame = tk.Frame(bottom_frame, bg=color)
        buttons_frame.pack(side="right")

        # Кнопка выбора мест
        select_btn = tk.Button(buttons_frame, text="Выбрать места",
                               bg="#007bff", fg="white",
                               font=("Arial", 9),
                               command=self._on_select)
        select_btn.pack(side="left", padx=2)

        # Кнопка добавления в корзину
        if on_add_to_cart:
            cart_btn = tk.Button(buttons_frame, text="🛒 В корзину",
                                 bg="#28a745", fg="white",
                                 font=("Arial", 9),
                                 command=self._add_to_cart)
            cart_btn.pack(side="left", padx=2)

        # Доступность
        availability_text = f"Свободно: {availability} мест"
        tk.Label(info_frame, text=availability_text, bg=color,
                 font=("Arial", 9, "italic")).pack(anchor="w")

        # Привязка событий
        self.bind("<Button-1>", lambda e: self._on_select())
        for child in self.winfo_children():
            child.bind("<Button-1>", lambda e: self._on_select())

    def _on_select(self):
        if self.on_select and isinstance(self.trip_data, dict):
            self.on_select(self.trip_data)

    def _add_to_cart(self):
        if self.on_add_to_cart and isinstance(self.trip_data, dict):
            self.on_add_to_cart(self.trip_data)


class SeatButton(tk.Button):
    """Кнопка места в вагоне"""

    def __init__(self, parent, seat_data: Dict[str, Any], on_click: Callable = None):
        self.seat_data = seat_data
        self.is_selected = False

        # Определяем цвет в зависимости от статуса и характеристик
        if seat_data.get("status") != "Free":
            bg_color = "#6c757d"  # серый - занято
            state = "disabled"
        else:
            state = "normal"
            if seat_data.get("is_window"):
                bg_color = "#17a2b8"  # голубой - у окна
            elif seat_data.get("has_socket"):
                bg_color = "#28a745"  # зелёный - с розеткой
            else:
                bg_color = "#ffc107"  # жёлтый - обычное

        text = f"{seat_data.get('seat_number', '')}\n{seat_data.get('price', 0)}₽"

        super().__init__(
            parent, text=text, bg=bg_color, state=state,
            font=("Arial", 8), width=8, height=2,
            command=self._toggle_selection
        )

        self.on_click = on_click

    def _toggle_selection(self):
        self.is_selected = not self.is_selected
        if self.is_selected:
            self.configure(bg="#dc3545")  # красный - выбрано
        else:
            # Возвращаем исходный цвет
            if self.seat_data.get("is_window"):
                self.configure(bg="#17a2b8")
            elif self.seat_data.get("has_socket"):
                self.configure(bg="#28a745")
            else:
                self.configure(bg="#ffc107")

        if self.on_click:
            self.on_click(self.seat_data, self.is_selected)


class FilterPanel(tk.Frame):
    """Панель фильтрации и поиска"""

    def __init__(self, parent, on_filter_change: Callable):
        super().__init__(parent, bg="#f8f9fa", relief="raised", bd=1)
        self.on_filter_change = on_filter_change

        self.pack(fill="x", padx=5, pady=5)

        # Поиск
        search_frame = tk.Frame(self, bg="#f8f9fa")
        search_frame.pack(fill="x", padx=5, pady=2)

        tk.Label(search_frame, text="🔍 Поиск:", bg="#f8f9fa").pack(side="left")
        self.search_entry = tk.Entry(search_frame, width=30)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", self._on_filter_change)

        # Фильтры
        filter_frame = tk.Frame(self, bg="#f8f9fa")
        filter_frame.pack(fill="x", padx=5, pady=2)

        tk.Label(filter_frame, text="Откуда:", bg="#f8f9fa").pack(side="left")
        self.departure_entry = tk.Entry(filter_frame, width=15)
        self.departure_entry.pack(side="left", padx=5)
        self.departure_entry.bind("<KeyRelease>", self._on_filter_change)

        tk.Label(filter_frame, text="Куда:", bg="#f8f9fa").pack(side="left", padx=(10, 0))
        self.arrival_entry = tk.Entry(filter_frame, width=15)
        self.arrival_entry.pack(side="left", padx=5)
        self.arrival_entry.bind("<KeyRelease>", self._on_filter_change)

        tk.Label(filter_frame, text="Дата:", bg="#f8f9fa").pack(side="left", padx=(10, 0))
        self.date_entry = tk.Entry(filter_frame, width=12)
        self.date_entry.pack(side="left", padx=5)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.bind("<KeyRelease>", self._on_filter_change)

    def _on_filter_change(self, event=None):
        filters = {
            "departure": self.departure_entry.get(),
            "arrival": self.arrival_entry.get(),
            "date": self.date_entry.get(),
            "search": self.search_entry.get()
        }
        self.on_filter_change(filters)

    def get_filters(self) -> Dict[str, str]:
        return {
            "departure": self.departure_entry.get(),
            "arrival": self.arrival_entry.get(),
            "date": self.date_entry.get(),
            "search": self.search_entry.get()
        }