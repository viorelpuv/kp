import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import tkinter as tk
from tkinter import messagebox, Toplevel
from simpletk import App, Label, Button, Input
from simpletk.containers import Tabs, ScrollableFrame, Horizontal, Vertical
from datetime import datetime, timedelta
import threading
import requests

from api_client import RailwayAPI
from src.frontend.admin_windows import AdminWindow
from widgets import TripCard, SeatButton, FilterPanel

MAIN_APP_INSTANCE = None


class RailwayTicketsApp:
    """Главное приложение"""

    def __init__(self):
        self.app = App("РЖД Билеты", 1200, 800)
        self.app.center()
        global MAIN_APP_INSTANCE
        MAIN_APP_INSTANCE = self

        # API клиент
        self.api = RailwayAPI("http://localhost:8000")

        # Данные
        self.current_trips = []
        self.selected_trip = None
        self.selected_seats = []
        self.current_order = None
        self.cart = []  # Корзина для выбранных билетов

        # Создаём интерфейс
        self.setup_ui()

        # Загружаем данные
        self.load_trips()

    def setup_ui(self):
        """Создание интерфейса"""

        # Верхняя панель со статистикой - используем self.app.root
        self.stats_frame = tk.Frame(self.app.root, bg="#e9ecef", height=50)
        self.stats_frame.pack(fill="x")
        self.stats_frame.pack_propagate(False)

        admin_frame = tk.Frame(self.app.root, bg="#f8f9fa", height=40)
        admin_frame.pack(fill="x", side="bottom")

        admin_btn = tk.Button(admin_frame, text="⚙️ Администрирование",
                              bg="#6c757d", fg="white",
                              font=("Arial", 10),
                              command=self.open_admin_window)
        admin_btn.pack(side="right", padx=10, pady=5)

        # SimpleTK Label для статистики
        from simpletk import Label
        self.stats_label = Label(self.stats_frame, "Добро пожаловать в систему РЖД", size=10)
        # Переупаковываем вручную
        self.stats_label.widget.pack_forget()
        self.stats_label.widget.pack(side="left", padx=10, pady=10)

        # Основной контейнер с вкладками
        from simpletk.containers import Tabs
        self.tabs = Tabs(self.app)

        # Главная вкладка с популярными направлениями
        self.setup_main_tab()

        # Вкладка с поиском билетов
        self.setup_search_tab()

        # Вкладка с корзиной
        self.setup_cart_tab()

        # Вкладка с моими заказами
        self.setup_orders_tab()

        # Загружаем данные
        self.load_trips()
        self.load_stats()

    def setup_search_tab(self):
        """Вкладка поиска билетов"""
        tab = self.tabs.add("🔍 Поиск билетов")

        # Панель фильтрации
        from widgets import FilterPanel
        self.filter_panel = FilterPanel(tab, self.on_filter_change)

        # Кнопка поиска
        search_btn_frame = tk.Frame(tab)
        search_btn_frame.pack(fill="x", padx=5, pady=5)

        search_button = tk.Button(search_btn_frame, text="🔍 Найти билеты",
                                  bg="#007bff", fg="white",
                                  font=("Arial", 12, "bold"),
                                  command=self.search_tickets)
        search_button.pack(side="left", padx=5)

        # Кнопка сброса
        reset_btn = tk.Button(search_btn_frame, text="🔄 Сбросить",
                              bg="#6c757d", fg="white",
                              font=("Arial", 10),
                              command=self.reset_search)
        reset_btn.pack(side="left", padx=5)

        # Счётчик результатов
        from simpletk import Label
        self.counter_label = Label(tab, "Найдено: 0 рейсов", size=10)

        # Контейнер для списка рейсов с прокруткой
        from simpletk.containers import ScrollableFrame
        self.trips_container = ScrollableFrame(tab, height=500, bg="white")

        # Кнопка обновления
        from simpletk import Button
        Button(tab, "🔄 Обновить", on_click=self.load_trips, color="lightblue")

    def reset_search(self):
        """Сброс поиска и фильтров"""
        self.filter_panel.search_entry.delete(0, tk.END)
        self.filter_panel.departure_entry.delete(0, tk.END)
        self.filter_panel.arrival_entry.delete(0, tk.END)
        self.filter_panel.date_entry.delete(0, tk.END)
        self.filter_panel.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.load_trips()

    def setup_orders_tab(self):
        """Вкладка с заказами"""
        tab = self.tabs.add("📋 Мои заказы")

        # Заголовок
        from simpletk import Label
        Label(tab, "Мои заказы", size=16, bold=True)

        # Контейнер для заказов
        from simpletk.containers import ScrollableFrame
        self.orders_container = ScrollableFrame(tab, height=500, bg="#f8f9fa")

        # Кнопка обновления
        from simpletk import Button
        Button(tab, "🔄 Обновить", on_click=self.load_orders, color="lightblue")

        # Показываем заглушку
        self.load_orders()

    def setup_cart_tab(self):
        """Вкладка с корзиной покупок"""
        tab = self.tabs.add("🛒 Корзина")

        # Заголовок
        from simpletk import Label
        Label(tab, "Корзина покупок", size=16, bold=True)

        # Контейнер для товаров в корзине
        from simpletk.containers import ScrollableFrame
        self.cart_container = ScrollableFrame(tab, height=400, bg="#f8f9fa")

        # Панель с итогом
        total_frame = tk.Frame(tab, bg="#e9ecef", height=60)
        total_frame.pack(fill="x", side="bottom", padx=10, pady=5)
        total_frame.pack_propagate(False)

        self.cart_total_label = tk.Label(total_frame, text="Итого: 0 ₽",
                                         font=("Arial", 14, "bold"),
                                         bg="#e9ecef", fg="green")
        self.cart_total_label.pack(side="left", padx=10)

        self.checkout_btn = tk.Button(total_frame, text="Оформить заказ",
                                      bg="#28a745", fg="white",
                                      font=("Arial", 12, "bold"),
                                      command=self.checkout,
                                      state="disabled")
        self.checkout_btn.pack(side="right", padx=10)

    def setup_popular_tab(self):
        """Вкладка с популярными направлениями"""
        tab = self.tabs.add("🌟 Популярные направления")

        # Заголовок
        Label(tab, "Популярные направления", size=16, bold=True)

        # Список популярных направлений
        popular_destinations = [
            {"from": "Москва", "to": "Санкт-Петербург", "price": 2500, "duration": "4ч", "trips": 5},
            {"from": "Москва", "to": "Казань", "price": 3200, "duration": "12ч", "trips": 3},
            {"from": "Москва", "to": "Екатеринбург", "price": 4100, "duration": "20ч", "trips": 2},
            {"from": "Санкт-Петербург", "to": "Москва", "price": 2500, "duration": "4ч", "trips": 4},
            {"from": "Москва", "to": "Сочи", "price": 3800, "duration": "24ч", "trips": 2},
            {"from": "Москва", "to": "Новосибирск", "price": 5200, "duration": "32ч", "trips": 2},
        ]

        # Контейнер для карточек
        popular_container = ScrollableFrame(tab, height=500, bg="#f8f9fa")

        for dest in popular_destinations:
            self.create_destination_card(popular_container.scrollable_frame, dest)

    def create_destination_card(self, parent, dest):
        """Создание карточки популярного направления"""
        card = tk.Frame(parent, bg="white", relief="raised", bd=1)
        card.pack(fill="x", padx=10, pady=5)

        # Информация о направлении
        info_frame = tk.Frame(card, bg="white")
        info_frame.pack(fill="x", padx=10, pady=10)

        # Маршрут
        route_label = tk.Label(info_frame,
                               text=f"{dest['from']} → {dest['to']}",
                               font=("Arial", 14, "bold"),
                               bg="white", fg="#007bff")
        route_label.pack(anchor="w")

        # Детали
        details_frame = tk.Frame(info_frame, bg="white")
        details_frame.pack(fill="x", pady=5)

        tk.Label(details_frame, text=f"⏱ {dest['duration']}",
                 bg="white", font=("Arial", 10)).pack(side="left", padx=5)
        tk.Label(details_frame, text=f"🚆 {dest['trips']} рейсов в день",
                 bg="white", font=("Arial", 10)).pack(side="left", padx=5)

        # Цена и кнопка
        bottom_frame = tk.Frame(card, bg="white")
        bottom_frame.pack(fill="x", padx=10, pady=10)

        price_label = tk.Label(bottom_frame,
                               text=f"от {dest['price']} ₽",
                               font=("Arial", 16, "bold"),
                               bg="white", fg="green")
        price_label.pack(side="left")

        search_btn = tk.Button(bottom_frame,
                               text="Найти билеты",
                               bg="#007bff", fg="white",
                               command=lambda d=dest: self.search_destination(d['from'], d['to']))
        search_btn.pack(side="right")

    def search_destination(self, departure, arrival):
        """Поиск билетов по направлению"""
        print(f"🔍 Поиск билетов: {departure} → {arrival}")

        # Фильтруем рейсы по направлению
        filtered_trips = []
        for trip in self.current_trips:
            if (trip.get('departure_station', '').lower() == departure.lower() and
                    trip.get('arrival_station', '').lower() == arrival.lower()):
                filtered_trips.append(trip)

        if not filtered_trips:
            self.app.warning(f"Билетов по направлению {departure} → {arrival} не найдено")
            return

        # Открываем окно с плитками
        TicketsGridWindow(
            self.app.root,
            departure,
            arrival,
            filtered_trips,
            self.api
        )

    def load_trips(self):
        """Загрузка списка всех рейсов"""

        def _load():
            try:
                # Загружаем все рейсы без фильтров
                filters = {'departure': '', 'arrival': '', 'date': '', 'search': ''}
                print(f"Загрузка всех рейсов...")

                response = self.api.get_trips(filters)
                print(f"Ответ от API: {response}")

                if isinstance(response, dict):
                    all_trips = response.get("trips", [])

                    # Для каждого рейса проверяем актуальное количество мест
                    validated_trips = []
                    for trip in all_trips:
                        # Загружаем детальную информацию для проверки
                        try:
                            detail = self.api.get_trip_detail(trip['id'])
                            if detail and 'seats' in detail:
                                real_free = len([s for s in detail['seats']
                                                 if s.get('status') == 'Free'])
                                print(
                                    f"✅ Рейс {trip['train_number']}: в списке {trip.get('available_seats')}, реально {real_free}")

                                # Обновляем количество мест
                                trip['available_seats'] = real_free

                                if real_free > 0:
                                    validated_trips.append(trip)
                            else:
                                print(f"⚠️ Нет данных по рейсу {trip['train_number']}, пропускаем")
                        except Exception as e:
                            print(f"❌ Ошибка проверки рейса {trip.get('train_number')}: {e}")
                            # Если не можем проверить, оставляем как есть
                            if trip.get('available_seats', 0) > 0:
                                validated_trips.append(trip)

                    self.current_trips = validated_trips
                    print(f"✅ Загружено рейсов с местами: {len(self.current_trips)}")
                else:
                    print(f"❌ Неожиданный формат ответа: {response}")
                    self.current_trips = []

                # Обновляем UI в главном потоке
                self.app.root.after(0, self.update_trips_display)

            except Exception as e:
                error_msg = str(e)
                print(f"❌ Ошибка загрузки: {error_msg}")
                import traceback
                traceback.print_exc()

        # Загружаем в отдельном потоке
        import threading
        threading.Thread(target=_load, daemon=True).start()

    def update_trips_display(self):
        """Обновление отображения рейсов"""
        print(f"🔍 Обновление отображения, рейсов: {len(self.current_trips)}")

        # Очищаем контейнер
        for widget in self.trips_container.scrollable_frame.winfo_children():
            widget.destroy()

        if not self.current_trips:
            # Показываем сообщение, если нет рейсов
            empty_frame = tk.Frame(self.trips_container.scrollable_frame, bg="white")
            empty_frame.pack(fill="both", expand=True, padx=20, pady=50)

            tk.Label(empty_frame, text="🚂 Нет доступных рейсов",
                     font=("Arial", 16), bg="white", fg="gray").pack()
            tk.Label(empty_frame, text="Измените параметры поиска",
                     font=("Arial", 12), bg="white", fg="gray").pack()
            return

        # Добавляем карточки рейсов
        for trip in self.current_trips:
            if isinstance(trip, dict):
                print(f"🔍 Создаю карточку для рейса {trip.get('id')}")
                # ВАЖНО: карточка должна быть упакована в контейнер
                card_frame = tk.Frame(self.trips_container.scrollable_frame, bg="white", relief="raised", bd=1)
                card_frame.pack(fill="x", padx=5, pady=2)

                # Создаём содержимое карточки
                self.create_trip_card(card_frame, trip)
            else:
                print(f"❌ Пропускаю не-словарь: {trip}")

        # Обновляем счётчик
        self.counter_label.set_text(f"Найдено: {len(self.current_trips)} рейсов")

    def create_trip_card(self, parent, trip):
        """Создание карточки рейса"""

        # Определяем цвет в зависимости от доступности
        availability = trip.get("available_seats", 0)
        if availability > 20:
            bg_color = "#d4edda"  # зелёный - много мест
        elif availability > 5:
            bg_color = "#fff3cd"  # жёлтый - мало мест
        else:
            bg_color = "#f8d7da"  # красный - почти нет мест

        # Информация о рейсе
        info_frame = tk.Frame(parent, bg=bg_color)
        info_frame.pack(fill="x", padx=10, pady=10)

        # Маршрут
        route_text = f"{trip.get('departure_station', '')} → {trip.get('arrival_station', '')}"
        tk.Label(info_frame, text=route_text, font=("Arial", 14, "bold"),
                 bg=bg_color, fg="#007bff").pack(anchor="w")

        # Номер поезда
        train_text = f"Поезд №{trip.get('train_number', '')} {trip.get('train_name', '')}"
        tk.Label(info_frame, text=train_text, font=("Arial", 11),
                 bg=bg_color).pack(anchor="w", pady=2)

        # Время отправления
        dep_time = trip.get('departure_datetime', '')
        if dep_time:
            if 'T' in dep_time:
                dep_time = dep_time.replace('T', ' ')[:16]
        tk.Label(info_frame, text=f"🕐 Отправление: {dep_time}",
                 bg=bg_color).pack(anchor="w")

        # Нижняя панель с ценой и кнопками
        bottom_frame = tk.Frame(info_frame, bg=bg_color)
        bottom_frame.pack(fill="x", pady=5)

        # Цена - используем min_price из API
        min_price = trip.get('min_price', 0)
        max_price = trip.get('max_price', 0)

        if min_price > 0 and max_price > 0 and max_price > min_price:
            price_text = f"💰 {int(min_price)} - {int(max_price)} ₽"
        elif min_price > 0:
            price_text = f"💰 от {int(min_price)} ₽"
        else:
            price_text = "💰 Цена не указана"

        price_label = tk.Label(bottom_frame, text=price_text,
                               font=("Arial", 14, "bold"), fg="green",
                               bg=bg_color)
        price_label.pack(side="left")

        # Кнопки
        buttons_frame = tk.Frame(bottom_frame, bg=bg_color)
        buttons_frame.pack(side="right")

        # Кнопка выбора мест
        select_btn = tk.Button(buttons_frame, text="Выбрать места",
                               bg="#007bff", fg="white",
                               font=("Arial", 10),
                               command=lambda t=trip: self.on_trip_selected(t))
        select_btn.pack(side="left", padx=2)

        # Кнопка добавления в корзину
        cart_btn = tk.Button(buttons_frame, text="🛒 В корзину",
                             bg="#28a745", fg="white",
                             font=("Arial", 10),
                             command=lambda t=trip: self.add_to_cart(t))
        cart_btn.pack(side="left", padx=2)

        # Доступность мест
        seats_text = f"Свободно мест: {availability}"
        tk.Label(info_frame, text=seats_text, font=("Arial", 9, "italic"),
                 bg=bg_color).pack(anchor="w", pady=2)

        # Привязываем клик по карточке к выбору рейса
        parent.bind("<Button-1>", lambda e, t=trip: self.on_trip_selected(t))
        for child in parent.winfo_children():
            child.bind("<Button-1>", lambda e, t=trip: self.on_trip_selected(t))

    def setup_main_tab(self):
        """Главная вкладка с популярными направлениями"""
        tab = self.tabs.add("🏠 Главная")

        # Заголовок
        from simpletk import Label
        Label(tab, "Популярные направления", size=20, bold=True)
        Label(tab, "Выберите направление для поиска билетов", size=12)

        # Контейнер для категорий
        categories_frame = tk.Frame(tab)
        categories_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Популярные направления
        popular_destinations = [
            {"from": "Москва", "to": "Санкт-Петербург", "icon": "🏛️", "color": "#007bff"},
            {"from": "Москва", "to": "Казань", "icon": "🕌", "color": "#28a745"},
            {"from": "Москва", "to": "Екатеринбург", "icon": "⛰️", "color": "#dc3545"},
            {"from": "Санкт-Петербург", "to": "Москва", "icon": "🌉", "color": "#ffc107"},
            {"from": "Москва", "to": "Сочи", "icon": "🏖️", "color": "#17a2b8"},
            {"from": "Москва", "to": "Новосибирск", "icon": "🏭", "color": "#6c757d"},
        ]

        # Создаём сетку 2x3 для категорий
        row = 0
        col = 0
        for dest in popular_destinations:
            # Создаём карточку категории
            card = tk.Frame(categories_frame, bg="white", relief="raised", bd=2, cursor="hand2")
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

            # Иконка
            tk.Label(card, text=dest["icon"], font=("Arial", 32),
                     bg="white").pack(pady=10)

            # Маршрут
            route_text = f"{dest['from']} → {dest['to']}"
            tk.Label(card, text=route_text, font=("Arial", 14, "bold"),
                     bg="white", fg=dest["color"]).pack()

            # Кнопка поиска
            search_btn = tk.Button(card, text="Найти билеты",
                                   bg=dest["color"], fg="white",
                                   command=lambda f=dest['from'], t=dest['to']:
                                   self.search_destination(f, t))
            search_btn.pack(pady=10)

            # Привязываем клик по карточке
            card.bind("<Button-1>", lambda e, f=dest['from'], t=dest['to']:
            self.search_destination(f, t))

            col += 1
            if col >= 3:
                col = 0
                row += 1

        # Настраиваем веса колонок
        for i in range(3):
            categories_frame.columnconfigure(i, weight=1)
        for i in range(2):
            categories_frame.rowconfigure(i, weight=1)

    def get_trips_list(self, filters=None):
        """Получение только списка рейсов (для обратной совместимости)"""
        response = self.api.get_trips(filters)
        if isinstance(response, dict):
            return response.get("trips", [])
        return response if isinstance(response, list) else []

    def on_trip_selected(self, trip):
        """Обработка выбора рейса"""
        self.selected_trip = trip
        self.show_seat_selection(trip)

    def add_to_cart(self, trip):
        """Добавление билета в корзину"""
        self.cart.append({
            "trip": trip,
            "quantity": 1,
            "price": trip.get("min_price", 0)
        })
        self.update_cart_display()
        self.app.message(
            f"✅ Билет добавлен в корзину!\nМаршрут: {trip.get('departure_station')} → {trip.get('arrival_station')}")

    def update_cart_display(self):
        """Обновление отображения корзины"""
        print(f"🔄 Обновление отображения корзины. Элементов: {len(self.cart)}")

        # Очищаем контейнер
        for widget in self.cart_container.scrollable_frame.winfo_children():
            widget.destroy()

        if not self.cart:
            # Пустая корзина
            empty_frame = tk.Frame(self.cart_container.scrollable_frame, bg="white")
            empty_frame.pack(fill="both", expand=True, padx=20, pady=50)

            tk.Label(empty_frame, text="🛒 Корзина пуста",
                     font=("Arial", 16), bg="white", fg="gray").pack()
            tk.Label(empty_frame, text="Выберите билеты и забронируйте места",
                     font=("Arial", 12), bg="white", fg="gray").pack()

            self.checkout_btn.config(state="disabled")
            self.cart_total_label.config(text="Итого: 0 ₽")
            print("✅ Корзина пуста")
            return

        # Отображаем товары в корзине
        total = 0
        for i, item in enumerate(self.cart):
            trip = item["trip"]
            price = item["price"]
            total += price

            print(f"  Элемент {i + 1}: {trip.get('departure_station')}→{trip.get('arrival_station')}, цена {price} ₽")

            # Карточка товара
            item_frame = tk.Frame(self.cart_container.scrollable_frame,
                                  bg="white", relief="raised", bd=1)
            item_frame.pack(fill="x", padx=5, pady=2)

            # Информация
            info_frame = tk.Frame(item_frame, bg="white")
            info_frame.pack(fill="x", padx=10, pady=5)

            # Маршрут и поезд
            route = f"{trip.get('departure_station')} → {trip.get('arrival_station')}"
            tk.Label(info_frame, text=route, font=("Arial", 12, "bold"),
                     bg="white", fg="#007bff").pack(anchor="w")

            train_text = f"Поезд {trip.get('train_number')} - {trip.get('train_name')}"
            tk.Label(info_frame, text=train_text, font=("Arial", 10),
                     bg="white").pack(anchor="w")

            # Информация о местах
            if "seats" in item:
                seats_frame = tk.Frame(info_frame, bg="white")
                seats_frame.pack(fill="x", pady=2)

                # Группируем места по типу вагона
                seats_by_type = {}
                for seat in item["seats"]:
                    ct = seat.get('carriage_type', 'Неизвестно')
                    if ct not in seats_by_type:
                        seats_by_type[ct] = []
                    seats_by_type[ct].append(seat.get('seat_number'))

                seats_text = "Места:"
                for ct, seats in seats_by_type.items():
                    seats_text += f"\n  • {ct}: {', '.join([str(s) for s in seats])}"

                tk.Label(seats_frame, text=seats_text,
                         font=("Arial", 9), bg="white", justify="left").pack(anchor="w")

            if "booking_time" in item:
                tk.Label(info_frame, text=f"Добавлено: {item['booking_time']}",
                         font=("Arial", 8), bg="white", fg="gray").pack(anchor="w")

            # Цена и кнопка удаления
            price_frame = tk.Frame(info_frame, bg="white")
            price_frame.pack(fill="x", pady=5)

            tk.Label(price_frame, text=f"💰 {price} ₽",
                     font=("Arial", 14, "bold"), fg="green",
                     bg="white").pack(side="left")

            # Кнопка удаления
            remove_btn = tk.Button(price_frame, text="❌ Удалить",
                                   bg="#dc3545", fg="white",
                                   font=("Arial", 9),
                                   command=lambda idx=i: self.remove_from_cart(idx))
            remove_btn.pack(side="right")

        # Обновляем итог
        self.cart_total_label.config(text=f"Итого: {total} ₽")
        self.checkout_btn.config(state="normal")

        # Принудительно обновляем отображение
        self.cart_container.scrollable_frame.update_idletasks()
        print(f"✅ Корзина обновлена. Итого: {total} ₽")

    def remove_from_cart(self, index):
        """Удаление товара из корзины"""
        print(f"🗑️ Удаление элемента {index} из корзины")

        if 0 <= index < len(self.cart):
            # Спрашиваем подтверждение
            if self.app.question("Удалить выбранные билеты из корзины?"):
                removed = self.cart.pop(index)
                print(
                    f"✅ Удален элемент: {removed.get('trip', {}).get('departure_station')}→{removed.get('trip', {}).get('arrival_station')}")
                self.update_cart_display()
                self.app.message("Билеты удалены из корзины")

    def checkout(self):
        """Оформление заказа"""
        print(f"💰 Оформление заказа. Всего элементов: {len(self.cart)}")

        if not self.cart:
            self.app.warning("Корзина пуста")
            return

        total = sum(item["price"] for item in self.cart)

        # Формируем детали заказа
        order_details = "Ваш заказ:\n\n"
        for i, item in enumerate(self.cart, 1):
            trip = item["trip"]
            order_details += f"{i}. {trip.get('departure_station')} → {trip.get('arrival_station')}\n"
            order_details += f"   Поезд: {trip.get('train_number')} - {trip.get('train_name')}\n"

            if "seats" in item:
                seats_by_type = {}
                for seat in item["seats"]:
                    ct = seat.get('carriage_type', 'Неизвестно')
                    if ct not in seats_by_type:
                        seats_by_type[ct] = []
                    seats_by_type[ct].append(seat.get('seat_number'))

                for ct, seats in seats_by_type.items():
                    order_details += f"   {ct}: места {', '.join([str(s) for s in seats])}\n"

            order_details += f"   Сумма: {item['price']} ₽\n\n"

        if self.app.question(f"{order_details}Общая сумма: {total} ₽\n\nПодтвердить оформление заказа?"):
            print(f"✅ Заказ подтвержден на сумму {total} ₽")
            # Здесь будет логика отправки заказа на сервер
            self.app.message(f"✅ Заказ оформлен!\nСумма: {total} ₽\nБилеты отправлены на email")
            self.cart.clear()
            self.update_cart_display()

    def show_seat_selection(self, trip):
        """Окно выбора мест"""
        # Загружаем детальную информацию
        try:
            trip_detail = self.api.get_trip_detail(trip["id"])
        except Exception as e:
            self.app.error(f"Ошибка загрузки мест: {e}")
            return

        # Создаём модальное окно
        dialog = Toplevel(self.app.root)
        dialog.title(f"Выбор мест - {trip_detail.get('train_name', '')}")
        dialog.geometry("800x600")
        dialog.transient(self.app.root)
        dialog.grab_set()

        # Информация о рейсе
        info_frame = tk.Frame(dialog, bg="#e9ecef")
        info_frame.pack(fill="x", padx=10, pady=5)

        dep = trip_detail.get('departure_station', '')
        arr = trip_detail.get('arrival_station', '')
        train = trip_detail.get('train_name', '')

        tk.Label(info_frame, text=f"Маршрут: {dep} → {arr}",
                 font=("Arial", 12, "bold"), bg="#e9ecef").pack()
        tk.Label(info_frame, text=f"Поезд: {train}", bg="#e9ecef").pack()

        # Контейнер для мест с прокруткой
        seats_container = ScrollableFrame(dialog, height=400, bg="white")

        # Получаем места из API или используем тестовые
        seats = trip_detail.get('seats', [])

        if not seats:
            # Тестовые места, если API не вернуло
            seats = [
                {"id": 1, "seat_number": 1, "price": 2500, "status": "Free"},
                {"id": 2, "seat_number": 2, "price": 2500, "status": "Free"},
                {"id": 3, "seat_number": 3, "price": 1800, "status": "Booked"},
                {"id": 4, "seat_number": 4, "price": 1800, "status": "Free"},
            ]

        self.selected_seats = []

        # Отображаем места
        seats_grid = tk.Frame(seats_container.scrollable_frame, bg="white")
        seats_grid.pack(padx=10, pady=10)

        row = 0
        col = 0
        for seat in seats:
            # Определяем цвет кнопки
            if seat.get("status") != "Free":
                bg_color = "#6c757d"  # серый - занято
                state = "disabled"
            else:
                state = "normal"
                bg_color = "#28a745" if seat.get("is_window") else "#ffc107"

            btn = tk.Button(seats_grid,
                            text=f"{seat.get('seat_number')}\n{seat.get('price')}₽",
                            width=6, height=2,
                            bg=bg_color, state=state,
                            command=lambda s=seat: self.toggle_seat(s))
            btn.grid(row=row, column=col, padx=2, pady=2)

            col += 1
            if col >= 6:  # 6 мест в ряд
                col = 0
                row += 1

        # Нижняя панель
        bottom_frame = tk.Frame(dialog, bg="#e9ecef")
        bottom_frame.pack(fill="x", side="bottom", padx=10, pady=5)

        self.seat_total_label = tk.Label(bottom_frame,
                                         text="Выбрано: 0 мест | Сумма: 0 ₽",
                                         font=("Arial", 12, "bold"),
                                         bg="#e9ecef", fg="green")
        self.seat_total_label.pack(side="left", padx=10)

        tk.Button(bottom_frame, text="Добавить в корзину",
                  bg="#28a745", fg="white",
                  font=("Arial", 10, "bold"),
                  command=lambda: self.add_selected_to_cart(trip, dialog)).pack(side="right", padx=10)

    def toggle_seat(self, seat):
        """Выбор/отмена выбора места"""
        if seat in self.selected_seats:
            self.selected_seats.remove(seat)
        else:
            self.selected_seats.append(seat)

        # Обновляем сумму
        total = sum(s.get('price', 0) for s in self.selected_seats)
        self.seat_total_label.config(text=f"Выбрано: {len(self.selected_seats)} мест | Сумма: {total} ₽")

    def add_selected_to_cart(self, trip, dialog):
        """Добавление выбранных мест в корзину"""
        if not self.selected_seats:
            self.app.warning("Выберите хотя бы одно место")
            return

        for seat in self.selected_seats:
            self.cart.append({
                "trip": trip,
                "seat": seat,
                "price": seat.get('price', 0)
            })

        self.update_cart_display()
        dialog.destroy()

        self.app.message(f"✅ {len(self.selected_seats)} билетов добавлено в корзину!")

    def on_filter_change(self, filters):
        """Обработка изменения фильтров"""
        self.load_trips()

    def load_stats(self):
        """Загрузка статистики"""
        try:
            stats = self.api.get_stats()
            if stats and isinstance(stats, dict):
                self.stats_label.set_text(
                    f"Всего билетов: {stats.get('total_tickets', 0)} | "
                    f"Продано: {stats.get('sold_tickets', 0)} | "
                    f"Выручка: {stats.get('total_revenue', 0)} ₽"
                )
            else:
                self.stats_label.set_text("Добро пожаловать в систему продажи ЖД билетов")
        except Exception as e:
            print(f"Ошибка загрузки статистики: {e}")
            self.stats_label.set_text("Добро пожаловать в систему продажи ЖД билетов")

    def load_orders(self):
        """Загрузка заказов пользователя"""
        # Очищаем контейнер
        for widget in self.orders_container.scrollable_frame.winfo_children():
            widget.destroy()

        # Показываем заглушку
        empty_frame = tk.Frame(self.orders_container.scrollable_frame, bg="white")
        empty_frame.pack(fill="both", expand=True, padx=20, pady=50)

        tk.Label(empty_frame, text="У вас пока нет заказов",
                 font=("Arial", 14), bg="white", fg="gray").pack()
        tk.Label(empty_frame, text="Перейдите на вкладку поиска и выберите билеты",
                 font=("Arial", 10), bg="white", fg="gray").pack()

    def add_to_cart_from_booking(self, booking_info):
        """Добавление забронированных мест в корзину"""

        print(f"🛒 Добавление в корзину: {booking_info}")
        print(f"📦 Текущая корзина до добавления: {len(self.cart)} элементов")

        # Создаем запись для корзины
        cart_item = {
            "trip": booking_info["trip"],
            "seats": booking_info["seats"],
            "seat_numbers": booking_info["seat_numbers"],
            "carriage_types": booking_info["carriage_types"],
            "price": booking_info["total_price"],
            "quantity": len(booking_info["seats"]),
            "booking_time": datetime.now().strftime("%d.%m.%Y %H:%M")
        }

        self.cart.append(cart_item)
        print(f"✅ Добавлено в корзину. Теперь в корзине: {len(self.cart)} элементов")

        # Обновляем отображение корзины
        self.update_cart_display()
        print(f"🔄 Отображение корзины обновлено")

        # Переключаемся на вкладку корзины, чтобы пользователь сразу увидел
        if hasattr(self, 'tabs') and hasattr(self.tabs, 'notebook'):
            self.tabs.notebook.select(2)  # Индекс вкладки корзины
            print(f"📌 Переключено на вкладку корзины")

    def search_tickets(self):
        """Поиск билетов по запросу"""

        # Получаем поисковый запрос из фильтра
        query = self.filter_panel.search_entry.get().strip()

        if not query:
            self.app.warning("Введите поисковый запрос")
            return

        def _search():
            try:
                print(f"🔍 Выполняется поиск: {query}")

                # Выполняем поиск через API
                results = self.api.search(query)

                if results and isinstance(results, dict):
                    search_results = results.get('results', [])
                    print(f"✅ Найдено результатов: {len(search_results)}")

                    # Открываем окно с результатами
                    if search_results:
                        self.app.root.after(0, lambda: SearchResultsWindow(
                            self.app.root, query, search_results, self.api
                        ))
                    else:
                        self.app.root.after(0, lambda: self.app.message(
                            f"По запросу '{query}' ничего не найдено"
                        ))
                else:
                    self.app.root.after(0, lambda: self.app.message(
                        f"По запросу '{query}' ничего не найдено"
                    ))

            except Exception as e:
                print(f"❌ Ошибка поиска: {e}")
                self.app.root.after(0, lambda: self.app.error(f"Ошибка поиска: {e}"))

        # Запускаем в отдельном потоке
        import threading
        threading.Thread(target=_search, daemon=True).start()

    def open_admin_window(self):
        """Открытие окна администратора"""
        AdminWindow(self.app.root, self.api)

    def run(self):
        """Запуск приложения"""
        self.app.run()


class TicketsGridWindow:
    """Окно с плитками билетов по выбранному направлению"""

    def __init__(self, parent, departure, arrival, trips_data, api):
        self.parent = parent
        self.departure = departure
        self.arrival = arrival
        self.trips_data = trips_data
        self.api = api
        self.sort_by = "price"  # По умолчанию сортировка по цене
        self.sort_order = "asc"  # По умолчанию по возрастанию

        # Создаём новое окно
        self.window = tk.Toplevel(parent)
        self.window.title(f"Билеты {departure} → {arrival}")
        self.window.geometry("1000x700")
        self.window.transient(parent)
        self.window.grab_set()

        # Центрируем окно
        self.center_window()

        # Создаём интерфейс
        self.setup_ui()

    def center_window(self):
        """Центрирование окна"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def setup_ui(self):
        """Создание интерфейса окна"""

        # Верхняя панель с информацией о направлении
        header_frame = tk.Frame(self.window, bg="#007bff", height=120)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)

        # Название направления
        tk.Label(header_frame,
                 text=f"{self.departure} → {self.arrival}",
                 font=("Arial", 20, "bold"),
                 bg="#007bff", fg="white").pack(pady=10)

        # Статистика
        stats_frame = tk.Frame(header_frame, bg="#007bff")
        stats_frame.pack()

        total_trips = len(self.trips_data)
        min_price = min([t.get('min_price', 0) for t in self.trips_data]) if self.trips_data else 0
        max_price = max([t.get('min_price', 0) for t in self.trips_data]) if self.trips_data else 0

        tk.Label(stats_frame, text=f"Найдено рейсов: {total_trips}",
                 bg="#007bff", fg="white", font=("Arial", 10)).pack(side="left", padx=10)
        tk.Label(stats_frame, text=f"Цены: от {min_price} до {max_price} ₽",
                 bg="#007bff", fg="white", font=("Arial", 10)).pack(side="left", padx=10)

        # Панель сортировки
        sort_frame = tk.Frame(header_frame, bg="#007bff")
        sort_frame.pack(pady=5)

        tk.Label(sort_frame, text="Сортировать по:",
                 bg="#007bff", fg="white", font=("Arial", 9)).pack(side="left", padx=5)

        # Кнопки сортировки по цене
        price_asc_btn = tk.Button(sort_frame, text="💰 Цена ↑",
                                  bg="#28a745", fg="white",
                                  font=("Arial", 9),
                                  command=lambda: self.sort_tickets("price", "asc"))
        price_asc_btn.pack(side="left", padx=2)

        price_desc_btn = tk.Button(sort_frame, text="💰 Цена ↓",
                                   bg="#28a745", fg="white",
                                   font=("Arial", 9),
                                   command=lambda: self.sort_tickets("price", "desc"))
        price_desc_btn.pack(side="left", padx=2)

        # Кнопки сортировки по времени
        time_asc_btn = tk.Button(sort_frame, text="🕐 Время ↑",
                                 bg="#007bff", fg="white",
                                 font=("Arial", 9),
                                 command=lambda: self.sort_tickets("time", "asc"))
        time_asc_btn.pack(side="left", padx=2)

        time_desc_btn = tk.Button(sort_frame, text="🕐 Время ↓",
                                  bg="#007bff", fg="white",
                                  font=("Arial", 9),
                                  command=lambda: self.sort_tickets("time", "desc"))
        time_desc_btn.pack(side="left", padx=2)

        # Кнопки сортировки по доступности
        seats_asc_btn = tk.Button(sort_frame, text="🎫 Места ↑",
                                  bg="#ffc107", fg="black",
                                  font=("Arial", 9),
                                  command=lambda: self.sort_tickets("seats", "asc"))
        seats_asc_btn.pack(side="left", padx=2)

        seats_desc_btn = tk.Button(sort_frame, text="🎫 Места ↓",
                                   bg="#ffc107", fg="black",
                                   font=("Arial", 9),
                                   command=lambda: self.sort_tickets("seats", "desc"))
        seats_desc_btn.pack(side="left", padx=2)

        # Индикатор текущей сортировки
        self.sort_indicator = tk.Label(header_frame,
                                       text="Сортировка: по цене ↑",
                                       bg="#007bff", fg="#e9ecef",
                                       font=("Arial", 8, "italic"))
        self.sort_indicator.pack(pady=2)

        # Контейнер для плиток с прокруткой
        self.create_scrollable_area()

        # Кнопка закрытия
        close_btn = tk.Button(self.window, text="Закрыть",
                              bg="#6c757d", fg="white",
                              font=("Arial", 10),
                              command=self.window.destroy)
        close_btn.pack(pady=10)

    def sort_tickets(self, sort_by, order):
        """Сортировка билетов"""
        self.sort_by = sort_by
        self.sort_order = order

        # Обновляем индикатор
        order_text = "↑" if order == "asc" else "↓"
        sort_names = {"price": "цене", "time": "времени", "seats": "местам"}
        self.sort_indicator.config(text=f"Сортировка: по {sort_names[sort_by]} {order_text}")

        # Сортируем данные
        if sort_by == "price":
            self.trips_data.sort(key=lambda x: x.get('min_price', 0),
                                 reverse=(order == "desc"))
        elif sort_by == "time":
            self.trips_data.sort(key=lambda x: x.get('departure_datetime', ''),
                                 reverse=(order == "desc"))
        elif sort_by == "seats":
            self.trips_data.sort(key=lambda x: x.get('available_seats', 0),
                                 reverse=(order == "desc"))

        # Обновляем отображение
        self.refresh_tiles()

    def refresh_tiles(self):
        """Обновление плиток после сортировки"""
        # Очищаем текущие плитки
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Создаем плитки заново
        self.create_tiles_grid()

    def create_scrollable_area(self):
        """Создание области с прокруткой"""

        # Создаём Canvas и Scrollbar
        canvas_frame = tk.Frame(self.window)
        canvas_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Canvas для прокрутки
        self.canvas = tk.Canvas(canvas_frame, bg="#f8f9fa", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)

        # Настраиваем Canvas
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Упаковываем
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Внутренний фрейм для содержимого
        self.scrollable_frame = tk.Frame(self.canvas, bg="#f8f9fa")
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # Обновление области прокрутки при изменении размера
        self.scrollable_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Привязка колеса мыши
        self._bind_mousewheel()

        # Создаём плитки
        self.create_tiles_grid()

    def _on_frame_configure(self, event):
        """Обновление области прокрутки"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        """Изменение ширины внутреннего фрейма"""
        canvas_width = event.width
        self.canvas.itemconfig(1, width=canvas_width)

    def _bind_mousewheel(self):
        """Привязка колеса мыши"""

        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.scrollable_frame.bind_all("<MouseWheel>", _on_mousewheel)

    def create_tiles_grid(self):
        """Создание сетки с плитками билетов"""

        if not self.trips_data:
            # Нет данных
            empty_frame = tk.Frame(self.scrollable_frame, bg="white")
            empty_frame.pack(fill="both", expand=True, padx=20, pady=50)

            tk.Label(empty_frame, text="🚂 Нет доступных билетов",
                     font=("Arial", 16), bg="white", fg="gray").pack()
            return

        # Создаём сетку 2 колонки
        row = 0
        col = 0
        for trip in self.trips_data:
            # Создаём плитку
            tile = self.create_trip_tile(self.scrollable_frame, trip)
            if tile:  # Проверяем, что плитка создана
                tile.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

                col += 1
                if col >= 2:  # 2 колонки
                    col = 0
                    row += 1

        # Настраиваем веса колонок
        self.scrollable_frame.columnconfigure(0, weight=1)
        self.scrollable_frame.columnconfigure(1, weight=1)

    def create_trip_tile(self, parent, trip):
        """Создание плитки для одного билета"""

        # Проверяем, есть ли свободные места
        availability = trip.get('available_seats', 0)
        if availability <= 0:
            return None  # Не создаём плитку для рейсов без мест

        # Определяем цвет в зависимости от доступности
        if availability > 20:
            color = "#d4edda"  # зелёный
            border_color = "#28a745"
            status_text = "✅ Много мест"
        elif availability > 5:
            color = "#fff3cd"  # жёлтый
            border_color = "#ffc107"
            status_text = "⚠️ Осталось мало"
        else:
            color = "#f8d7da"  # красный
            border_color = "#dc3545"
            status_text = "🔥 Последние места"

        # Основной контейнер плитки
        tile = tk.Frame(parent, bg="white", relief="raised", bd=2,
                        highlightbackground=border_color, highlightthickness=2)

        # Верхняя часть с поездом
        top_frame = tk.Frame(tile, bg=color)
        top_frame.pack(fill="x", padx=1, pady=1)

        # Номер поезда
        train_number = trip.get('train_number', '')
        train_name = trip.get('train_name', '')
        tk.Label(top_frame, text=f"🚆 {train_number}",
                 font=("Arial", 12, "bold"),
                 bg=color).pack(anchor="w", padx=5, pady=2)
        tk.Label(top_frame, text=train_name,
                 font=("Arial", 10),
                 bg=color).pack(anchor="w", padx=5)

        # Основная информация
        info_frame = tk.Frame(tile, bg="white")
        info_frame.pack(fill="x", padx=5, pady=5)

        # Время отправления и прибытия
        time_frame = tk.Frame(info_frame, bg="white")
        time_frame.pack(fill="x", pady=5)

        # Отправление
        dep_frame = tk.Frame(time_frame, bg="white")
        dep_frame.pack(side="left", expand=True)

        dep_datetime = trip.get('departure_datetime', '')
        if 'T' in dep_datetime:
            dep_date, dep_time = dep_datetime.split('T')
            dep_time = dep_time[:5]
            dep_date = dep_date[5:]  # MM-DD
        else:
            dep_date = "??"
            dep_time = "??"

        tk.Label(dep_frame, text=dep_time, font=("Arial", 18, "bold"),
                 fg="#007bff", bg="white").pack()
        tk.Label(dep_frame, text=dep_date, font=("Arial", 10),
                 fg="gray", bg="white").pack()

        # Стрелка
        tk.Label(time_frame, text="→", font=("Arial", 18, "bold"),
                 fg="gray", bg="white").pack(side="left", padx=10)

        # Прибытие
        arr_frame = tk.Frame(time_frame, bg="white")
        arr_frame.pack(side="left", expand=True)

        arr_datetime = trip.get('arrival_datetime', '')
        if 'T' in arr_datetime:
            arr_date, arr_time = arr_datetime.split('T')
            arr_time = arr_time[:5]
            arr_date = arr_date[5:]
        else:
            arr_date = "??"
            arr_time = "??"

        tk.Label(arr_frame, text=arr_time, font=("Arial", 18, "bold"),
                 fg="#dc3545", bg="white").pack()
        tk.Label(arr_frame, text=arr_date, font=("Arial", 10),
                 fg="gray", bg="white").pack()

        # Разделитель
        tk.Frame(info_frame, height=1, bg="#dee2e6").pack(fill="x", pady=5)

        # Дополнительная информация
        details_frame = tk.Frame(info_frame, bg="white")
        details_frame.pack(fill="x")

        # Время в пути
        duration = self.calculate_duration(trip)
        tk.Label(details_frame, text=f"⏱ {duration}",
                 font=("Arial", 10), bg="white").pack(anchor="w", pady=1)

        # Доступность мест с цветовым индикатором
        seats_frame = tk.Frame(details_frame, bg="white")
        seats_frame.pack(anchor="w", pady=1)

        tk.Label(seats_frame, text="🎫 ", font=("Arial", 10),
                 bg="white").pack(side="left")
        tk.Label(seats_frame, text=f"{availability} мест",
                 font=("Arial", 10, "bold"),
                 fg=border_color, bg="white").pack(side="left")
        tk.Label(seats_frame, text=f" {status_text}",
                 font=("Arial", 9),
                 fg="gray", bg="white").pack(side="left", padx=5)

        # Цена
        price = trip.get('min_price', 0)
        tk.Label(details_frame, text=f"💰 {price} ₽",
                 font=("Arial", 16, "bold"), fg="green",
                 bg="white").pack(anchor="w", pady=5)

        # Кнопка выбора
        select_btn = tk.Button(details_frame, text="Выбрать места",
                               bg="#007bff", fg="white",
                               font=("Arial", 10, "bold"),
                               command=lambda t=trip: self.select_trip(t))
        select_btn.pack(fill="x", pady=5)

        # Привязываем клик по плитке
        tile.bind("<Button-1>", lambda e, t=trip: self.select_trip(t))
        for child in tile.winfo_children():
            child.bind("<Button-1>", lambda e, t=trip: self.select_trip(t))

        return tile

    def calculate_duration(self, trip):
        """Расчёт длительности поездки"""
        try:
            dep = trip.get('departure_datetime', '')
            arr = trip.get('arrival_datetime', '')

            if 'T' in dep and 'T' in arr:
                from datetime import datetime
                dep_dt = datetime.fromisoformat(dep.replace('T', ' ')[:19])
                arr_dt = datetime.fromisoformat(arr.replace('T', ' ')[:19])

                delta = arr_dt - dep_dt
                days = delta.days
                hours = delta.seconds // 3600
                minutes = (delta.seconds % 3600) // 60

                if days > 0:
                    return f"{days}д {hours}ч"
                else:
                    return f"{hours}ч {minutes}мин"
        except:
            pass
        return "??"

    def select_trip(self, trip):
        """Выбор рейса для покупки билетов"""
        print(f"🔍 Выбран рейс ID: {trip.get('id')}")
        print(f"📊 По данным из списка: свободно {trip.get('available_seats')} мест")

        try:
            loading_window = tk.Toplevel(self.window)
            loading_window.title("Загрузка")
            loading_window.geometry("300x100")
            loading_window.transient(self.window)

            tk.Label(loading_window, text="Загрузка информации о местах...",
                     font=("Arial", 11)).pack(pady=20)
            loading_window.update()

            trip_detail = self.api.get_trip_detail(trip['id'])
            loading_window.destroy()

            if not trip_detail:
                messagebox.showerror("Ошибка", "Не удалось загрузить информацию о местах")
                return

            free_seats = [s for s in trip_detail.get('seats', [])
                          if s.get('status') == 'Free']

            print(f"📊 Реально свободно: {len(free_seats)} мест")

            trip['available_seats'] = len(free_seats)

            if len(free_seats) == 0:
                messagebox.showwarning(
                    "Нет мест",
                    f"На рейс {trip.get('train_number')} нет свободных мест."
                )
                return

            # Убираем main_window из вызова
            SeatSelectionWindow(self.window, trip, self.api, trip_detail)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить информацию: {e}")
            print(f"❌ Ошибка: {e}")

    def find_main_window(self):
        """Поиск главного окна приложения"""
        # Проходим по иерархии виджетов вверх
        parent = self.window.master
        while parent:
            # Проверяем, есть ли у виджета атрибут 'app'
            if hasattr(parent, 'app') and hasattr(parent.app, 'root'):
                return parent
            # Также проверяем, не является ли виджет самим главным окном
            if hasattr(parent, 'tabs') and hasattr(parent, 'cart'):
                return parent
            try:
                parent = parent.master
            except:
                break
        return None

    def get_main_window(self):
        """Получение ссылки на главное окно приложения"""
        # Поднимаемся по иерархии виджетов до главного окна
        parent = self.window.master
        while parent:
            if hasattr(parent, 'app') and hasattr(parent.app, 'root'):
                # Нашли RailwayTicketsApp
                return parent
            try:
                parent = parent.master
            except:
                break
        return None


class SeatSelectionWindow:
    """Окно выбора мест в вагоне"""

    def __init__(self, parent, trip, api, trip_detail=None):
        print(f"🔧 Создание SeatSelectionWindow для рейса {trip.get('train_number')}")
        print(f"📊 На плашке было мест: {trip.get('available_seats', 0)}")

        self.parent = parent
        self.trip = trip
        self.api = api
        self.selected_seats = []
        self.current_carriage_type = None
        self.seats_by_type = {}
        self.total_free_seats = 0

        if trip_detail:
            print(f"📦 Использую переданные детальные данные")
            self.trip_detail = trip_detail
            self.analyze_seats()

            if self.total_free_seats != trip.get('available_seats', 0):
                print(f"⚠️ НЕСООТВЕТСТВИЕ: на плашке {trip.get('available_seats', 0)}, реально {self.total_free_seats}")
                trip['available_seats'] = self.total_free_seats

            if self.total_free_seats > 0:
                self.create_window()
            else:
                from tkinter import messagebox
                messagebox.showwarning(
                    "Нет мест",
                    f"На рейс {trip.get('train_number')} нет свободных мест."
                )
        else:
            print(f"📦 Загружаю детальные данные через API")
            self.load_trip_detail()

    def load_trip_detail(self):
        """Загрузка детальной информации о рейсе"""
        try:
            self.trip_detail = self.api.get_trip_detail(self.trip['id'])
            self.analyze_seats()

            if self.total_free_seats > 0:
                self.create_window()
            else:
                from tkinter import messagebox
                messagebox.showwarning(
                    "Нет мест",
                    f"На рейс {self.trip.get('train_number')} нет свободных мест."
                )
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Ошибка", f"Не удалось загрузить информацию о местах: {e}")
            print(f"❌ Ошибка: {e}")

    def analyze_seats(self):
        """Анализ данных о местах и распределение по типам вагонов"""
        if 'seats' not in self.trip_detail:
            print("❌ В ответе нет поля 'seats'")
            return

        api_seats = self.trip_detail['seats']
        print(f"📊 Всего мест в данных API: {len(api_seats)}")

        # Получаем максимальную цену из карточки рейса
        max_price_from_card = self.trip.get('min_price', 2500)  # Используем min_price как ориентир
        print(f"📊 Максимальная цена из карточки: {max_price_from_card}")

        # Определяем общее количество мест для каждого типа вагона
        carriage_capacities = {
            "Плацкарт": 54,
            "Купе": 36,
            "СВ": 18,
            "Люкс": 12,
            "Сидячий": 60
        }

        # Базовые цены для разных типов вагонов (относительно максимальной)
        base_prices = {
            "Плацкарт": int(max_price_from_card * 0.7),  # 70% от максимальной
            "Купе": int(max_price_from_card * 0.9),  # 90% от максимальной
            "СВ": int(max_price_from_card * 1.2),  # 120% от максимальной
            "Люкс": int(max_price_from_card * 1.5),  # 150% от максимальной
            "Сидячий": int(max_price_from_card * 0.5)  # 50% от максимальной
        }

        # Группируем места из API по типу вагона
        api_seats_by_type = {}
        for seat in api_seats:
            ct = seat.get('carriage_type', 'Неизвестно')
            if ct not in api_seats_by_type:
                api_seats_by_type[ct] = []
            api_seats_by_type[ct].append(seat)

        # Создаём полные схемы вагонов
        self.seats_by_type = {}
        self.total_free_seats = 0

        for ct, capacity in carriage_capacities.items():
            # Получаем список свободных мест из API для этого типа
            free_seats_from_api = [s for s in api_seats_by_type.get(ct, [])
                                   if s.get('status') == 'Free']
            free_count = len(free_seats_from_api)

            print(f"📊 {ct}: в API {free_count} свободных мест из {len(api_seats_by_type.get(ct, []))}")

            # Если в API нет данных для этого типа, используем общее количество
            if free_count == 0 and ct in self.trip.get('carriage_types', {}):
                free_count = self.trip['carriage_types'][ct].get('free', 0)

            # Если всё ещё нет данных, распределяем общее количество равномерно
            if free_count == 0 and self.total_free_seats == 0:
                # Используем общее количество из trip
                total_free = self.trip.get('available_seats', 0)
                if total_free > 0:
                    # Распределяем пропорционально вместимости
                    free_count = int(total_free * (capacity / 180))  # 180 - примерная сумма всех мест
                    if free_count < 1 and total_free > 0:
                        free_count = 1

            # Базовая цена для этого типа вагона
            base_price = base_prices.get(ct, max_price_from_card)

            # Создаём полную схему вагона
            seats = []

            # Генерируем все места в вагоне
            for seat_num in range(1, capacity + 1):
                # Определяем характеристики места
                is_window = self.is_window_seat(ct, seat_num)
                has_socket = (seat_num % 3 == 0)  # Каждое третье место с розеткой
                is_side = self.is_side_seat(ct, seat_num)

                # Определяем статус места
                if free_count > 0 and seat_num <= free_count:
                    status = 'Free'
                else:
                    status = 'Sold'

                # Корректировка цены в зависимости от характеристик
                price = base_price
                if is_window:
                    price = int(price * 1.1)  # +10% за окно
                if has_socket:
                    price += 200  # +200 за розетку
                if is_side:
                    price = int(price * 0.8)  # -20% за боковое место

                # Убеждаемся, что цена не превышает максимальную из карточки
                if price > max_price_from_card * 1.5:  # Не более чем в 1.5 раза
                    price = int(max_price_from_card * 1.5)

                # Округляем до красивых чисел
                price = int(round(price / 100) * 100)

                seat = {
                    'id': f"{ct}_{seat_num}",
                    'seat_number': seat_num,
                    'carriage_type': ct,
                    'price': price,
                    'status': status,
                    'is_window': is_window,
                    'has_socket': has_socket,
                    'is_side': is_side
                }
                seats.append(seat)

            # Считаем свободные места
            free_in_type = len([s for s in seats if s['status'] == 'Free'])

            # Находим минимальную и максимальную цену среди свободных мест
            free_seats_prices = [s['price'] for s in seats if s['status'] == 'Free']
            min_price = min(free_seats_prices) if free_seats_prices else 0
            max_price = max([s['price'] for s in seats]) if seats else 0

            self.seats_by_type[ct] = {
                'total': capacity,
                'free': free_in_type,
                'seats': seats,
                'min_price': min_price,
                'max_price': max_price,
                'base_price': base_price
            }

            self.total_free_seats += free_in_type

            print(f"  📍 {ct}: цены {min_price}-{max_price} ₽ (базовая {base_price})")

        # Сортируем типы вагонов по приоритету
        priority = {"Купе": 1, "Плацкарт": 2, "СВ": 3, "Люкс": 4, "Сидячий": 5}
        self.carriage_types = sorted(
            [ct for ct, stats in self.seats_by_type.items() if stats['free'] > 0],
            key=lambda x: priority.get(x, 99)
        )

        # Устанавливаем первый доступный тип вагона
        if self.carriage_types:
            self.current_carriage_type = self.carriage_types[0]

        # Выводим итоговую статистику
        print("📊 ИТОГОВАЯ СТАТИСТИКА:")
        for ct, stats in self.seats_by_type.items():
            print(f"  {ct}: всего {stats['total']} мест, свободно {stats['free']}, "
                  f"цены {stats['min_price']}-{stats['max_price']} ₽")
        print(f"📊 ВСЕГО СВОБОДНЫХ МЕСТ: {self.total_free_seats}")
        print(f"💰 ДИАПАЗОН ЦЕН: от {min([s['min_price'] for s in self.seats_by_type.values() if s['min_price'] > 0])} "
              f"до {max([s['max_price'] for s in self.seats_by_type.values()])} ₽")

    def is_window_seat(self, carriage_type, seat_num):
        """Определяет, является ли место у окна"""
        if carriage_type == "Плацкарт":
            # В плацкарте основные места у окна, боковые - нет
            if seat_num <= 36:  # Основные места
                return (seat_num % 2 == 1)  # Нечётные - нижние у окна
            else:  # Боковые места
                return False
        elif carriage_type == "Купе":
            # В купе все места в купе, но у окна только 1 и 3
            mod = ((seat_num - 1) % 4) + 1
            return mod in [1, 3]
        elif carriage_type in ["СВ", "Люкс"]:
            # В СВ и Люксе все места у окна
            return True
        elif carriage_type == "Сидячий":
            # В сидячем у окна места по краям
            mod = ((seat_num - 1) % 4) + 1
            return mod in [1, 4]
        return False

    def is_side_seat(self, carriage_type, seat_num):
        """Определяет, является ли место боковым (только для плацкарта)"""
        if carriage_type == "Плацкарт":
            return seat_num > 36
        return False

    def create_window(self):
        """Создание окна выбора мест"""

        # Создаём новое окно
        self.window = tk.Toplevel(self.parent)
        self.window.title(f"Выбор мест - {self.trip.get('train_name')}")
        self.window.geometry("1000x700")
        self.window.transient(self.parent)
        self.window.grab_set()

        # Центрируем окно
        self.center_window()

        # Создаём интерфейс
        self.setup_ui()

    def center_window(self):
        """Центрирование окна"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def setup_ui(self):
        """Создание интерфейса окна"""

        # Верхняя панель с информацией о поезде
        header_frame = tk.Frame(self.window, bg="#007bff", height=100)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)

        # Информация о поезде
        train_info = f"{self.trip.get('train_number')} - {self.trip.get('train_name')}"
        tk.Label(header_frame, text=train_info,
                 font=("Arial", 14, "bold"),
                 bg="#007bff", fg="white").pack(pady=5)

        route_info = f"{self.trip.get('departure_station')} → {self.trip.get('arrival_station')}"
        tk.Label(header_frame, text=route_info,
                 font=("Arial", 12),
                 bg="#007bff", fg="white").pack()

        # Общее количество свободных мест (должно совпадать с плашкой)
        total_frame = tk.Frame(header_frame, bg="#007bff")
        total_frame.pack(pady=5)

        tk.Label(total_frame, text=f"Всего свободно:",
                 font=("Arial", 10),
                 bg="#007bff", fg="white").pack(side="left")

        tk.Label(total_frame, text=f" {self.total_free_seats} мест",
                 font=("Arial", 14, "bold"),
                 bg="#007bff", fg="yellow").pack(side="left", padx=5)

        # Панель выбора типа вагона
        carriage_frame = tk.Frame(self.window, bg="#e9ecef", height=60)
        carriage_frame.pack(fill="x")
        carriage_frame.pack_propagate(False)

        tk.Label(carriage_frame, text="Тип вагона:",
                 bg="#e9ecef", font=("Arial", 11)).pack(side="left", padx=10)

        self.carriage_var = tk.StringVar()

        for ct in self.carriage_types:
            stats = self.seats_by_type[ct]
            # Показываем количество свободных мест в каждом типе
            rb_text = f"{ct} ({stats['free']} мест, от {stats['min_price']} ₽)"

            rb = tk.Radiobutton(carriage_frame, text=rb_text,
                                variable=self.carriage_var,
                                value=ct, bg="#e9ecef", font=("Arial", 10),
                                command=self.on_carriage_change)
            rb.pack(side="left", padx=5)

        # Если есть типы вагонов, выбираем первый
        if self.carriage_types:
            self.carriage_var.set(self.carriage_types[0])

        # Основная область с прокруткой
        self.create_scrollable_area()

        # Отображаем схему для выбранного типа вагона
        self.display_carriage_schema()

        # Нижняя панель
        bottom_frame = tk.Frame(self.window, bg="#e9ecef", height=80)
        bottom_frame.pack(fill="x", side="bottom")
        bottom_frame.pack_propagate(False)

        self.selection_info = tk.Label(bottom_frame,
                                       text="Выбрано мест: 0 | Сумма: 0 ₽",
                                       font=("Arial", 12, "bold"),
                                       bg="#e9ecef", fg="#007bff")
        self.selection_info.pack(side="left", padx=10)

        self.book_btn = tk.Button(bottom_frame, text="Забронировать",
                                  bg="#28a745", fg="white",
                                  font=("Arial", 12, "bold"),
                                  state="disabled",
                                  command=self.book_seats)
        self.book_btn.pack(side="right", padx=10)

        cancel_btn = tk.Button(bottom_frame, text="Отмена",
                               bg="#dc3545", fg="white",
                               font=("Arial", 12, "bold"),
                               command=self.window.destroy)
        cancel_btn.pack(side="right", padx=10)

    def create_scrollable_area(self):
        """Создание области с прокруткой"""

        # Создаём Canvas и Scrollbar
        canvas_frame = tk.Frame(self.window)
        canvas_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Canvas для прокрутки
        self.canvas = tk.Canvas(canvas_frame, bg="white", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)

        # Настраиваем Canvas
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Упаковываем
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Внутренний фрейм для содержимого
        self.scrollable_frame = tk.Frame(self.canvas, bg="white")
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # Обновление области прокрутки при изменении размера
        self.scrollable_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Привязка колеса мыши
        self._bind_mousewheel()

    def _on_frame_configure(self, event):
        """Обновление области прокрутки"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        """Изменение ширины внутреннего фрейма"""
        canvas_width = event.width
        self.canvas.itemconfig(1, width=canvas_width)

    def _bind_mousewheel(self):
        """Привязка колеса мыши"""

        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.scrollable_frame.bind_all("<MouseWheel>", _on_mousewheel)

    def on_carriage_change(self):
        """Обработка смены типа вагона"""
        self.current_carriage_type = self.carriage_var.get()
        self.display_carriage_schema()

    def display_carriage_schema(self):
        """Отображение полной схемы вагона выбранного типа"""

        # Очищаем фрейм
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if not self.current_carriage_type:
            return

        stats = self.seats_by_type[self.current_carriage_type]
        seats = stats['seats']
        free_in_type = stats['free']
        total_in_type = stats['total']

        # Заголовок с информацией
        title_frame = tk.Frame(self.scrollable_frame, bg="white")
        title_frame.pack(fill="x", padx=10, pady=5)

        title_text = f"🚆 {self.current_carriage_type} - свободно {free_in_type} из {total_in_type} мест"
        tk.Label(title_frame, text=title_text,
                 font=("Arial", 14, "bold"),
                 fg="#28a745" if free_in_type > 0 else "#dc3545",
                 bg="white").pack()

        # Информация о ценах в этом типе вагона
        price_text = f"💰 Цены в этом вагоне: {stats['min_price']} - {stats['max_price']} ₽"
        tk.Label(title_frame, text=price_text,
                 font=("Arial", 11),
                 fg="green", bg="white").pack()

        # Легенда
        legend_frame = tk.Frame(self.scrollable_frame, bg="white")
        legend_frame.pack(fill="x", padx=10, pady=5)

        legend_items = [
            ("🟩 У окна", "#28a745"),
            ("🟥 Выбрано", "#dc3545"),
            ("🟧 Боковые", "#fd7e14"),
            ("🟪 С розеткой", "#9370DB"),
            ("🟨 Обычные", "#ffc107"),
            ("⬜ Занято", "#e9ecef")
        ]

        for text, color in legend_items:
            lbl = tk.Label(legend_frame, text=text, bg="white", fg=color)
            lbl.pack(side="left", padx=5)

        # Создаём словарь для быстрого доступа к данным мест
        seats_dict = {s['seat_number']: s for s in seats}

        # Отрисовываем схему в зависимости от типа вагона
        if self.current_carriage_type == "Плацкарт":
            self.draw_platzkart_schema(seats_dict)
        elif self.current_carriage_type == "Купе":
            self.draw_coupe_schema(seats_dict)
        elif self.current_carriage_type == "СВ":
            self.draw_sv_schema(seats_dict)
        elif self.current_carriage_type == "Люкс":
            self.draw_lux_schema(seats_dict)
        elif self.current_carriage_type == "Сидячий":
            self.draw_sitting_schema(seats_dict)

    def draw_platzkart_schema(self, seats_dict):
        """Отрисовка плацкартного вагона (54 места, 9 отсеков)"""

        schema_frame = tk.Frame(self.scrollable_frame, bg="white")
        schema_frame.pack(padx=20, pady=10)

        # Заголовки отсеков
        header_frame = tk.Frame(schema_frame, bg="white")
        header_frame.pack()

        for i in range(1, 10):
            tk.Label(header_frame, text=f"  {i} отсек  ",
                     font=("Arial", 9, "bold"),
                     bg="white").grid(row=0, column=i - 1, padx=5)

        # Основные места (1-36)
        for row in range(2):  # 2 ряда (нижние и верхние)
            row_frame = tk.Frame(schema_frame, bg="white")
            row_frame.pack(pady=2)

            if row == 0:
                tk.Label(row_frame, text="Нижние:",
                         font=("Arial", 9), width=8, bg="white").pack(side="left")
            else:
                tk.Label(row_frame, text="Верхние:",
                         font=("Arial", 9), width=8, bg="white").pack(side="left")

            for compartment in range(1, 10):
                seat_num1 = (compartment - 1) * 4 + row * 2 + 1
                seat_num2 = (compartment - 1) * 4 + row * 2 + 2

                if seat_num1 in seats_dict:
                    self.create_schema_button(row_frame, seats_dict[seat_num1])
                if seat_num2 in seats_dict:
                    self.create_schema_button(row_frame, seats_dict[seat_num2])

        # Боковые места (37-54)
        for row in range(2):  # 2 ряда (нижние и верхние боковые)
            row_frame = tk.Frame(schema_frame, bg="white")
            row_frame.pack(pady=2)

            if row == 0:
                tk.Label(row_frame, text="Боковые\nнижние:",
                         font=("Arial", 8), width=8, bg="white").pack(side="left")
            else:
                tk.Label(row_frame, text="Боковые\nверхние:",
                         font=("Arial", 8), width=8, bg="white").pack(side="left")

            for compartment in range(1, 10):
                if row == 0:
                    seat_num = 36 + (compartment * 2 - 1)
                else:
                    seat_num = 36 + (compartment * 2)

                if seat_num in seats_dict:
                    self.create_schema_button(row_frame, seats_dict[seat_num])

        # Проход
        tk.Frame(schema_frame, height=2, bg="#dee2e6").pack(fill="x", pady=10)
        tk.Label(schema_frame, text="🚂 ПРОХОД", font=("Arial", 9, "bold"),
                 fg="gray").pack()

    def draw_coupe_schema(self, seats_dict):
        """Отрисовка купейного вагона (36 мест, 9 купе)"""

        schema_frame = tk.Frame(self.scrollable_frame, bg="white")
        schema_frame.pack(padx=20, pady=10)

        # Заголовки купе
        header_frame = tk.Frame(schema_frame, bg="white")
        header_frame.pack()

        for i in range(1, 10):
            tk.Label(header_frame, text=f"  Купе {i}  ",
                     font=("Arial", 9, "bold"),
                     bg="white").grid(row=0, column=i - 1, padx=5)

        # Места в купе (4 места в каждом)
        for row in range(2):  # 2 ряда (нижние и верхние)
            row_frame = tk.Frame(schema_frame, bg="white")
            row_frame.pack(pady=2)

            if row == 0:
                tk.Label(row_frame, text="Нижние:",
                         font=("Arial", 9), width=8, bg="white").pack(side="left")
            else:
                tk.Label(row_frame, text="Верхние:",
                         font=("Arial", 9), width=8, bg="white").pack(side="left")

            for compartment in range(1, 10):
                seat_num1 = (compartment - 1) * 4 + row * 2 + 1
                seat_num2 = (compartment - 1) * 4 + row * 2 + 2

                if seat_num1 in seats_dict:
                    self.create_schema_button(row_frame, seats_dict[seat_num1])
                if seat_num2 in seats_dict:
                    self.create_schema_button(row_frame, seats_dict[seat_num2])

        # Проход
        tk.Frame(schema_frame, height=2, bg="#dee2e6").pack(fill="x", pady=10)
        tk.Label(schema_frame, text="🚂 ПРОХОД", font=("Arial", 9, "bold"),
                 fg="gray").pack()

    def draw_sv_schema(self, seats_dict):
        """Отрисовка вагона СВ (18 мест, 9 купе по 2 места)"""

        schema_frame = tk.Frame(self.scrollable_frame, bg="white")
        schema_frame.pack(padx=20, pady=10)

        # Заголовки купе
        header_frame = tk.Frame(schema_frame, bg="white")
        header_frame.pack()

        for i in range(1, 10):
            tk.Label(header_frame, text=f"  Купе {i}  ",
                     font=("Arial", 9, "bold"),
                     bg="white").grid(row=0, column=i - 1, padx=5)

        # Места в купе (2 места в каждом - оба нижние)
        row_frame = tk.Frame(schema_frame, bg="white")
        row_frame.pack(pady=2)

        tk.Label(row_frame, text="Места:",
                 font=("Arial", 9), width=8, bg="white").pack(side="left")

        for compartment in range(1, 10):
            seat_num1 = (compartment - 1) * 2 + 1
            seat_num2 = (compartment - 1) * 2 + 2

            if seat_num1 in seats_dict:
                self.create_schema_button(row_frame, seats_dict[seat_num1])
            if seat_num2 in seats_dict:
                self.create_schema_button(row_frame, seats_dict[seat_num2])

        # Проход
        tk.Frame(schema_frame, height=2, bg="#dee2e6").pack(fill="x", pady=10)
        tk.Label(schema_frame, text="🚂 ПРОХОД", font=("Arial", 9, "bold"),
                 fg="gray").pack()

    def draw_lux_schema(self, seats_dict):
        """Отрисовка вагона Люкс (12 мест, 6 купе по 2 места)"""

        schema_frame = tk.Frame(self.scrollable_frame, bg="white")
        schema_frame.pack(padx=20, pady=10)

        # Заголовки купе
        header_frame = tk.Frame(schema_frame, bg="white")
        header_frame.pack()

        for i in range(1, 7):
            tk.Label(header_frame, text=f"  Люкс {i}  ",
                     font=("Arial", 9, "bold"),
                     bg="white").grid(row=0, column=i - 1, padx=5)

        # Места в люксе (2 места в каждом)
        row_frame = tk.Frame(schema_frame, bg="white")
        row_frame.pack(pady=2)

        tk.Label(row_frame, text="Места:",
                 font=("Arial", 9), width=8, bg="white").pack(side="left")

        for compartment in range(1, 7):
            seat_num1 = (compartment - 1) * 2 + 1
            seat_num2 = (compartment - 1) * 2 + 2

            if seat_num1 in seats_dict:
                self.create_schema_button(row_frame, seats_dict[seat_num1])
            if seat_num2 in seats_dict:
                self.create_schema_button(row_frame, seats_dict[seat_num2])

        # Проход
        tk.Frame(schema_frame, height=2, bg="#dee2e6").pack(fill="x", pady=10)
        tk.Label(schema_frame, text="🚂 ПРОХОД", font=("Arial", 9, "bold"),
                 fg="gray").pack()

    def draw_sitting_schema(self, seats_dict):
        """Отрисовка сидячего вагона (60 мест, 15 рядов по 4 места)"""

        schema_frame = tk.Frame(self.scrollable_frame, bg="white")
        schema_frame.pack(padx=20, pady=10)

        # Заголовки
        header_frame = tk.Frame(schema_frame, bg="white")
        header_frame.pack()

        tk.Label(header_frame, text="    Окно    ", font=("Arial", 8),
                 bg="white").grid(row=0, column=0, padx=2)
        tk.Label(header_frame, text="   Проход   ", font=("Arial", 8),
                 bg="white").grid(row=0, column=1, padx=2)
        tk.Label(header_frame, text="   Проход   ", font=("Arial", 8),
                 bg="white").grid(row=0, column=2, padx=2)
        tk.Label(header_frame, text="    Окно    ", font=("Arial", 8),
                 bg="white").grid(row=0, column=3, padx=2)

        for row in range(1, 16):  # 15 рядов
            row_frame = tk.Frame(schema_frame, bg="white")
            row_frame.pack(pady=2)

            tk.Label(row_frame, text=f"Ряд {row:2d}:",
                     font=("Arial", 9), width=5, bg="white").pack(side="left")

            for seat_in_row in range(1, 5):
                seat_num = (row - 1) * 4 + seat_in_row

                if seat_num in seats_dict:
                    self.create_schema_button(row_frame, seats_dict[seat_num])

    def create_schema_button(self, parent, seat_data):
        """Создание кнопки для схемы вагона"""

        seat_num = seat_data.get('seat_number', 0)
        status = seat_data.get('status', 'Free')
        price = seat_data.get('price', 0)
        is_window = seat_data.get('is_window', False)
        has_socket = seat_data.get('has_socket', False)
        is_side = seat_data.get('is_side', False)

        # Определяем цвет
        if status != 'Free':
            bg_color = "#e9ecef"  # серый - занято
            state = "disabled"
            text = f"{seat_num}\n❌"
        else:
            state = "normal"
            if is_window and is_side:
                bg_color = "#17a2b8"  # бирюзовый - окно + боковое
            elif is_window:
                bg_color = "#28a745"  # зелёный - у окна
            elif is_side:
                bg_color = "#fd7e14"  # оранжевый - боковое
            elif has_socket:
                bg_color = "#9370DB"  # фиолетовый - с розеткой
            else:
                bg_color = "#ffc107"  # жёлтый - обычное

            text = f"{seat_num}\n{price}₽"

        btn = tk.Button(parent, text=text,
                        width=6, height=2,
                        bg=bg_color, state=state,
                        font=("Arial", 7),
                        relief="raised" if status == 'Free' else "sunken")

        if status == 'Free':
            btn.config(command=lambda s=seat_data: self.toggle_seat(s, btn))

        btn.pack(side="left", padx=1)

    def toggle_seat(self, seat, button):
        """Выбор/отмена выбора места"""
        if seat in self.selected_seats:
            self.selected_seats.remove(seat)
            # Возвращаем исходный цвет
            is_window = seat.get('is_window', False)
            is_side = seat.get('is_side', False)
            has_socket = seat.get('has_socket', False)

            if is_window and is_side:
                button.config(bg="#17a2b8", relief="raised")
            elif is_window:
                button.config(bg="#28a745", relief="raised")
            elif is_side:
                button.config(bg="#fd7e14", relief="raised")
            elif has_socket:
                button.config(bg="#9370DB", relief="raised")
            else:
                button.config(bg="#ffc107", relief="raised")
        else:
            self.selected_seats.append(seat)
            button.config(bg="#dc3545", relief="solid")

        # Обновляем информацию
        self.update_selection_info()

    def update_selection_info(self):
        """Обновление информации о выбранных местах"""
        count = len(self.selected_seats)
        total = sum(s.get('price', 0) for s in self.selected_seats)

        self.selection_info.config(text=f"Выбрано мест: {count} | Сумма: {total} ₽")

        if count > 0:
            self.book_btn.config(state="normal")
        else:
            self.book_btn.config(state="disabled")

    def book_seats(self):
        """Бронирование выбранных мест и добавление в корзину"""
        if not self.selected_seats:
            return

        from tkinter import messagebox

        # Используем глобальную переменную
        global MAIN_APP_INSTANCE

        if not MAIN_APP_INSTANCE:
            messagebox.showerror("Ошибка", "Не удалось найти главное окно приложения")
            return

        # Формируем информацию о бронировании
        booking_info = {
            "trip": self.trip,
            "seats": self.selected_seats.copy(),
            "total_price": sum(s.get('price', 0) for s in self.selected_seats),
            "seat_numbers": [s.get('seat_number') for s in self.selected_seats],
            "carriage_types": list(set([s.get('carriage_type') for s in self.selected_seats]))
        }

        # Добавляем в корзину главного окна
        MAIN_APP_INSTANCE.add_to_cart_from_booking(booking_info)

        # Закрываем окно выбора мест
        self.window.destroy()

        # Показываем подтверждение
        messagebox.showinfo("Успешно",
                            f"✅ Места добавлены в корзину!\n\n"
                            f"🚂 Поезд: {self.trip.get('train_number')} - {self.trip.get('train_name')}\n"
                            f"🪑 Места: {', '.join([str(s.get('seat_number')) for s in self.selected_seats])}\n"
                            f"💰 Сумма: {booking_info['total_price']} ₽")

    def get_main_window(self):
        """Получение ссылки на главное окно приложения"""
        # Поднимаемся по иерархии виджетов до главного окна
        parent = self.parent
        while parent:
            if hasattr(parent, 'app') and hasattr(parent.app, 'root'):
                # Нашли RailwayTicketsApp
                return parent
            try:
                parent = parent.master
            except:
                break
        return None


class SearchResultsWindow:
    """Окно с результатами поиска билетов"""

    def __init__(self, parent, query, results, api):
        self.parent = parent
        self.query = query
        self.results = results
        self.api = api
        self.sort_by = "price"  # По умолчанию сортировка по цене
        self.sort_order = "asc"  # По умолчанию по возрастанию

        # Создаём новое окно
        self.window = tk.Toplevel(parent)
        self.window.title(f"Результаты поиска: {query}")
        self.window.geometry("1000x700")
        self.window.transient(parent)
        self.window.grab_set()

        # Центрируем окно
        self.center_window()

        # Создаём интерфейс
        self.setup_ui()

    def center_window(self):
        """Центрирование окна"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def setup_ui(self):
        """Создание интерфейса окна"""

        # Верхняя панель с информацией о поиске
        header_frame = tk.Frame(self.window, bg="#007bff", height=120)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)

        # Заголовок
        tk.Label(header_frame,
                 text=f"🔍 Результаты поиска: \"{self.query}\"",
                 font=("Arial", 18, "bold"),
                 bg="#007bff", fg="white").pack(pady=10)

        # Статистика
        stats_frame = tk.Frame(header_frame, bg="#007bff")
        stats_frame.pack()

        total_results = len(self.results)

        tk.Label(stats_frame, text=f"Найдено билетов: {total_results}",
                 bg="#007bff", fg="white", font=("Arial", 11)).pack(side="left", padx=10)

        # Панель сортировки
        sort_frame = tk.Frame(header_frame, bg="#007bff")
        sort_frame.pack(pady=5)

        tk.Label(sort_frame, text="Сортировать по:",
                 bg="#007bff", fg="white", font=("Arial", 9)).pack(side="left", padx=5)

        # Кнопки сортировки по цене
        price_asc_btn = tk.Button(sort_frame, text="💰 Цена ↑",
                                  bg="#28a745", fg="white",
                                  font=("Arial", 9),
                                  command=lambda: self.sort_results("price", "asc"))
        price_asc_btn.pack(side="left", padx=2)

        price_desc_btn = tk.Button(sort_frame, text="💰 Цена ↓",
                                   bg="#28a745", fg="white",
                                   font=("Arial", 9),
                                   command=lambda: self.sort_results("price", "desc"))
        price_desc_btn.pack(side="left", padx=2)

        # Кнопки сортировки по времени
        time_asc_btn = tk.Button(sort_frame, text="🕐 Время ↑",
                                 bg="#007bff", fg="white",
                                 font=("Arial", 9),
                                 command=lambda: self.sort_results("time", "asc"))
        time_asc_btn.pack(side="left", padx=2)

        time_desc_btn = tk.Button(sort_frame, text="🕐 Время ↓",
                                  bg="#007bff", fg="white",
                                  font=("Arial", 9),
                                  command=lambda: self.sort_results("time", "desc"))
        time_desc_btn.pack(side="left", padx=2)

        # Кнопки сортировки по станциям
        station_asc_btn = tk.Button(sort_frame, text="🚉 Станция ↑",
                                    bg="#ffc107", fg="black",
                                    font=("Arial", 9),
                                    command=lambda: self.sort_results("station", "asc"))
        station_asc_btn.pack(side="left", padx=2)

        station_desc_btn = tk.Button(sort_frame, text="🚉 Станция ↓",
                                     bg="#ffc107", fg="black",
                                     font=("Arial", 9),
                                     command=lambda: self.sort_results("station", "desc"))
        station_desc_btn.pack(side="left", padx=2)

        # Индикатор текущей сортировки
        self.sort_indicator = tk.Label(header_frame,
                                       text="Сортировка: по цене ↑",
                                       bg="#007bff", fg="#e9ecef",
                                       font=("Arial", 8, "italic"))
        self.sort_indicator.pack(pady=2)

        # Контейнер для результатов с прокруткой
        self.create_scrollable_area()

        # Кнопка закрытия
        close_btn = tk.Button(self.window, text="Закрыть",
                              bg="#6c757d", fg="white",
                              font=("Arial", 10),
                              command=self.window.destroy)
        close_btn.pack(pady=10)

    def create_scrollable_area(self):
        """Создание области с прокруткой"""

        # Создаём контейнер для canvas и scrollbar
        canvas_container = tk.Frame(self.window)
        canvas_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Создаём Canvas
        self.canvas = tk.Canvas(canvas_container, bg="#f8f9fa", highlightthickness=0)

        # Создаём Scrollbar
        self.scrollbar = tk.Scrollbar(canvas_container, orient="vertical", command=self.canvas.yview)

        # Настраиваем Canvas
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Размещаем scrollbar справа
        self.scrollbar.pack(side="right", fill="y")

        # Размещаем canvas слева
        self.canvas.pack(side="left", fill="both", expand=True)

        # Создаём внутренний фрейм для содержимого
        self.scrollable_frame = tk.Frame(self.canvas, bg="#f8f9fa")

        # Добавляем внутренний фрейм в canvas
        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.scrollable_frame,
            anchor="nw",
            tags="inner_frame"
        )

        # Привязываем события
        self.scrollable_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Привязываем колесо мыши
        self._bind_mousewheel()

        # Отображаем результаты
        self.display_results()

    def _on_frame_configure(self, event):
        """Обновление области прокрутки"""
        bbox = self.canvas.bbox("all")
        if bbox:
            self.canvas.configure(scrollregion=bbox)

    def _on_canvas_configure(self, event):
        """Изменение ширины внутреннего фрейма"""
        self.canvas.itemconfig("inner_frame", width=event.width)

    def _bind_mousewheel(self):
        """Привязка колеса мыши"""

        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.scrollable_frame.bind_all("<MouseWheel>", _on_mousewheel)

    def sort_results(self, sort_by, order):
        """Сортировка результатов поиска"""
        self.sort_by = sort_by
        self.sort_order = order

        # Обновляем индикатор
        order_text = "↑" if order == "asc" else "↓"
        sort_names = {"price": "цене", "time": "времени", "station": "станции"}
        self.sort_indicator.config(text=f"Сортировка: по {sort_names[sort_by]} {order_text}")

        # Сортируем данные
        if sort_by == "price":
            self.results.sort(key=lambda x: x.get('price_from', 0),
                              reverse=(order == "desc"))
        elif sort_by == "time":
            self.results.sort(key=lambda x: x.get('departure_datetime', ''),
                              reverse=(order == "desc"))
        elif sort_by == "station":
            self.results.sort(key=lambda x: x.get('departure_station', ''),
                              reverse=(order == "desc"))

        # Обновляем отображение
        self.refresh_display()

    def refresh_display(self):
        """Обновление отображения после сортировки"""
        # Очищаем текущие результаты
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Отображаем результаты заново
        self.display_results()

    def display_results(self):
        """Отображение результатов поиска"""

        if not self.results:
            empty_frame = tk.Frame(self.scrollable_frame, bg="white")
            empty_frame.pack(fill="both", expand=True, padx=20, pady=50)

            tk.Label(empty_frame, text="😔 По вашему запросу ничего не найдено",
                     font=("Arial", 16), bg="white", fg="gray").pack()
            tk.Label(empty_frame, text="Попробуйте изменить поисковый запрос",
                     font=("Arial", 12), bg="white", fg="gray").pack()
            return

        # Создаём заголовки колонок
        header_frame = tk.Frame(self.scrollable_frame, bg="#e9ecef", height=40)
        header_frame.pack(fill="x", padx=5, pady=5)
        header_frame.pack_propagate(False)

        # Колонки
        tk.Label(header_frame, text="Поезд", font=("Arial", 10, "bold"),
                 bg="#e9ecef", width=15).pack(side="left", padx=5)
        tk.Label(header_frame, text="Маршрут", font=("Arial", 10, "bold"),
                 bg="#e9ecef", width=25).pack(side="left", padx=5)
        tk.Label(header_frame, text="Отправление", font=("Arial", 10, "bold"),
                 bg="#e9ecef", width=15).pack(side="left", padx=5)
        tk.Label(header_frame, text="Мест", font=("Arial", 10, "bold"),
                 bg="#e9ecef", width=8).pack(side="left", padx=5)
        tk.Label(header_frame, text="Цена от", font=("Arial", 10, "bold"),
                 bg="#e9ecef", width=10).pack(side="left", padx=5)
        tk.Label(header_frame, text="", font=("Arial", 10, "bold"),
                 bg="#e9ecef", width=15).pack(side="left", padx=5)

        # Отображаем каждый результат в виде строки
        for result in self.results:
            self.create_result_row(result)

    def create_result_row(self, result):
        """Создание строки с результатом поиска"""

        row_frame = tk.Frame(self.scrollable_frame, bg="white", relief="raised", bd=1)
        row_frame.pack(fill="x", padx=5, pady=2)

        # Поезд
        train_text = f"{result.get('train_number', '')} - {result.get('train_name', '')[:20]}"
        tk.Label(row_frame, text=train_text, font=("Arial", 9),
                 bg="white", width=20, anchor="w").pack(side="left", padx=5)

        # Маршрут
        route_text = f"{result.get('departure_station', '')} → {result.get('arrival_station', '')}"
        tk.Label(row_frame, text=route_text, font=("Arial", 9),
                 bg="white", width=30, anchor="w").pack(side="left", padx=5)

        # Время отправления
        dep_time = result.get('departure_datetime', '')
        if dep_time and 'T' in dep_time:
            dep_time = dep_time.replace('T', ' ')[:16]
        tk.Label(row_frame, text=dep_time, font=("Arial", 9),
                 bg="white", width=18, anchor="w").pack(side="left", padx=5)

        # Места
        seats = result.get('available_seats', 0)
        seats_color = "green" if seats > 20 else "orange" if seats > 5 else "red"
        tk.Label(row_frame, text=str(seats), font=("Arial", 9, "bold"),
                 bg="white", fg=seats_color, width=5).pack(side="left", padx=5)

        # Цена
        price = result.get('price_from', 0)
        tk.Label(row_frame, text=f"{price} ₽", font=("Arial", 9, "bold"),
                 bg="white", fg="green", width=8).pack(side="left", padx=5)

        # Кнопка выбора
        select_btn = tk.Button(row_frame, text="Выбрать",
                               bg="#007bff", fg="white",
                               font=("Arial", 8),
                               command=lambda r=result: self.select_trip(r))
        select_btn.pack(side="left", padx=5)

        # Привязываем клик по строке
        row_frame.bind("<Button-1>", lambda e, r=result: self.select_trip(r))
        for child in row_frame.winfo_children():
            child.bind("<Button-1>", lambda e, r=result: self.select_trip(r))

    def select_trip(self, result):
        """Выбор рейса из результатов поиска"""
        print(f"🔍 Выбран рейс ID: {result.get('id')}")

        try:
            loading_window = tk.Toplevel(self.window)
            loading_window.title("Загрузка")
            loading_window.geometry("300x100")
            loading_window.transient(self.window)

            tk.Label(loading_window, text="Загрузка информации о местах...",
                     font=("Arial", 11)).pack(pady=20)
            loading_window.update()

            trip_detail = self.api.get_trip_detail(result['id'])
            loading_window.destroy()

            if not trip_detail:
                messagebox.showerror("Ошибка", "Не удалось загрузить информацию о местах")
                return

            # Убираем main_window из вызова
            SeatSelectionWindow(self.window, result, self.api, trip_detail)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить информацию: {e}")
            print(f"❌ Ошибка: {e}")

    def get_main_window(self):
        """Получение ссылки на главное окно приложения"""
        parent = self.window.master
        while parent:
            if hasattr(parent, 'app') and hasattr(parent.app, 'root'):
                return parent
            try:
                parent = parent.master
            except:
                break
        return None


def main():
    print("=" * 60)
    print("🚂 РЖД Билеты - система продажи ЖД билетов")
    print("=" * 60)
    print("📌 Доступные разделы:")
    print("   🔍 Поиск билетов - поиск и выбор рейсов")
    print("   🌟 Популярные направления - быстрый выбор")
    print("   🛒 Корзина - выбранные билеты")
    print("   📋 Мои заказы - история покупок")
    print("=" * 60)

    app = RailwayTicketsApp()
    app.run()


if __name__ == "__main__":
    main()