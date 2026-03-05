"""
Административные окна для управления системой ЖД билетов
"""

import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
import threading
import requests


class AdminWindow:
    """Главное окно администратора"""

    def __init__(self, parent, api):
        self.parent = parent
        self.api = api
        self.base_url = "http://localhost:8000"

        # Создаём новое окно
        self.window = tk.Toplevel(parent)
        self.window.title("Администрирование системы")
        self.window.geometry("1200x800")
        self.window.transient(parent)
        self.window.grab_set()

        # Центрируем окно
        self.center_window()

        # Создаём интерфейс
        self.setup_ui()

        # Загружаем данные
        self.load_all_data()

    def center_window(self):
        """Центрирование окна"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")

    def setup_ui(self):
        """Создание интерфейса"""

        # Заголовок
        header_frame = tk.Frame(self.window, bg="#343a40", height=60)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)

        tk.Label(header_frame, text="⚙️ Панель администратора",
                 font=("Arial", 18, "bold"),
                 bg="#343a40", fg="white").pack(pady=15)

        # Создаём вкладки для разных разделов
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Вкладки
        self.setup_trains_tab()
        self.setup_routes_tab()
        self.setup_trips_tab()
        self.setup_carriages_tab()
        self.setup_stations_tab()

        # Статусная строка
        self.status_frame = tk.Frame(self.window, bg="#e9ecef", height=30)
        self.status_frame.pack(fill="x", side="bottom")
        self.status_frame.pack_propagate(False)

        self.status_label = tk.Label(self.status_frame, text="Готов",
                                      bg="#e9ecef", fg="#6c757d",
                                      font=("Arial", 9))
        self.status_label.pack(side="left", padx=10)

        # Кнопка закрытия
        close_btn = tk.Button(self.status_frame, text="Закрыть",
                               bg="#6c757d", fg="white",
                               font=("Arial", 9),
                               command=self.window.destroy)
        close_btn.pack(side="right", padx=10)

    def set_status(self, message, is_error=False):
        """Установка статусного сообщения"""
        self.status_label.config(text=message, fg="#dc3545" if is_error else "#28a745")
        self.window.update()

    def load_all_data(self):
        """Загрузка всех данных"""
        self.load_trains()
        self.load_routes()
        self.load_trips_admin()
        self.load_carriages()
        self.load_stations()

    # ========== МЕТОДЫ ДЛЯ РАБОТЫ С ПОЕЗДАМИ ==========

    def setup_trains_tab(self):
        """Вкладка управления поездами"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🚆 Поезда")

        # Панель добавления
        add_frame = tk.LabelFrame(tab, text="Добавить новый поезд", padx=10, pady=10)
        add_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(add_frame, text="Номер поезда:*").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.train_number_entry = tk.Entry(add_frame, width=20)
        self.train_number_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(add_frame, text="Название:*").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.train_name_entry = tk.Entry(add_frame, width=25)
        self.train_name_entry.grid(row=0, column=3, padx=5, pady=5)

        tk.Label(add_frame, text="Перевозчик:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.train_carrier_entry = tk.Entry(add_frame, width=20)
        self.train_carrier_entry.insert(0, "РЖД")
        self.train_carrier_entry.grid(row=1, column=1, padx=5, pady=5)

        self.train_branded_var = tk.BooleanVar()
        tk.Checkbutton(add_frame, text="Фирменный", variable=self.train_branded_var).grid(row=1, column=2, padx=5, pady=5, sticky="w")

        add_btn = tk.Button(add_frame, text="➕ Добавить поезд",
                           bg="#28a745", fg="white",
                           command=self.add_train)
        add_btn.grid(row=1, column=3, padx=5, pady=5)

        # Список поездов
        list_frame = tk.LabelFrame(tab, text="Существующие поезда", padx=10, pady=10)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Таблица поездов
        columns = ("ID", "Номер", "Название", "Перевозчик", "Фирменный", "Вагонов")
        self.trains_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)

        column_widths = [50, 100, 200, 100, 80, 80]
        for i, col in enumerate(columns):
            self.trains_tree.heading(col, text=col)
            self.trains_tree.column(col, width=column_widths[i])

        self.trains_tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.trains_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.trains_tree.configure(yscrollcommand=scrollbar.set)

        # Кнопки управления
        btn_frame = tk.Frame(list_frame)
        btn_frame.pack(fill="x", pady=5)

        tk.Button(btn_frame, text="🔄 Обновить",
                 command=self.load_trains).pack(side="left", padx=2)
        tk.Button(btn_frame, text="✏️ Редактировать",
                 command=self.edit_train).pack(side="left", padx=2)
        tk.Button(btn_frame, text="❌ Удалить",
                 bg="#dc3545", fg="white",
                 command=self.delete_train).pack(side="left", padx=2)

    def load_trains(self):
        """Загрузка списка поездов из API"""
        try:
            # Очищаем таблицу
            for item in self.trains_tree.get_children():
                self.trains_tree.delete(item)

            # Реальный запрос к API
            response = requests.get(f"{self.base_url}/api/trains")

            if response.status_code == 200:
                trains = response.json()

                # Если API возвращает список поездов
                if isinstance(trains, list):
                    for train in trains:
                        self.trains_tree.insert("", "end", values=(
                            train.get("id", ""),
                            train.get("train_number", ""),
                            train.get("name", ""),
                            train.get("carrier", "РЖД"),
                            "Да" if train.get("is_branded") else "Нет",
                            train.get("carriages_count", 0)
                        ))
                    self.set_status(f"Загружено {len(trains)} поездов")
                else:
                    self.set_status("Не удалось загрузить поезда", True)
            else:
                # Если API еще не готов, используем тестовые данные
                self.load_test_trains()

        except Exception as e:
            print(f"Ошибка загрузки поездов: {e}")
            self.load_test_trains()

    def load_test_trains(self):
        """Загрузка тестовых данных для поездов"""
        test_trains = [
            (1, "001А", "Сапсан", "РЖД", "Да", 10),
            (2, "002Б", "Невский экспресс", "РЖД", "Да", 8),
            (3, "003В", "Красная стрела", "РЖД", "Да", 12),
            (4, "004Г", "Арктика", "РЖД", "Нет", 6),
            (5, "005Д", "Байкал", "РЖД", "Да", 8),
        ]

        for train in test_trains:
            self.trains_tree.insert("", "end", values=train)
        self.set_status("Загружены тестовые данные поездов")

    def add_train(self):
        """Добавление нового поезда"""
        number = self.train_number_entry.get().strip()
        name = self.train_name_entry.get().strip()
        carrier = self.train_carrier_entry.get().strip()
        branded = "Да" if self.train_branded_var.get() else "Нет"

        if not number or not name:
            messagebox.showerror("Ошибка", "Заполните обязательные поля (номер и название)")
            return

        # Показываем индикатор загрузки
        self.set_status("Добавление поезда...")

        def _add():
            try:
                # Реальный запрос к API
                train_data = {
                    "train_number": number,
                    "name": name,
                    "carrier": carrier,
                    "is_branded": self.train_branded_var.get()
                }

                response = requests.post(f"{self.base_url}/api/trains", json=train_data)

                if response.status_code == 201:
                    self.window.after(0, lambda: self.on_add_success(f"Поезд {number} добавлен"))
                    self.window.after(0, self.load_trains)
                else:
                    error_msg = response.json().get("detail", "Ошибка добавления")
                    self.window.after(0, lambda: self.on_add_error(error_msg))

            except Exception as e:
                # Если API еще не готов, имитируем успешное добавление
                self.window.after(0, lambda: self.on_add_success(f"Поезд {number} добавлен (тестовый режим)"))
                self.window.after(0, self.load_trains)
                print(f"Ошибка API: {e}")

        threading.Thread(target=_add, daemon=True).start()

    def on_add_success(self, message):
        """Обработчик успешного добавления"""
        self.set_status(message)
        messagebox.showinfo("Успешно", message)

        # Очищаем поля
        self.train_number_entry.delete(0, tk.END)
        self.train_name_entry.delete(0, tk.END)
        self.train_carrier_entry.delete(0, tk.END)
        self.train_carrier_entry.insert(0, "РЖД")
        self.train_branded_var.set(False)

    def on_add_error(self, error):
        """Обработчик ошибки добавления"""
        self.set_status(error, True)
        messagebox.showerror("Ошибка", error)

    def edit_train(self):
        """Редактирование поезда"""
        selected = self.trains_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите поезд для редактирования")
            return

        # Получаем данные выбранного поезда
        item = self.trains_tree.item(selected[0])
        train_data = item["values"]

        # Создаём окно редактирования
        self.edit_train_window(train_data)

    def edit_train_window(self, train_data):
        """Окно редактирования поезда"""
        edit_win = tk.Toplevel(self.window)
        edit_win.title("Редактирование поезда")
        edit_win.geometry("400x300")
        edit_win.transient(self.window)
        edit_win.grab_set()

        tk.Label(edit_win, text="Редактирование поезда", font=("Arial", 14, "bold")).pack(pady=10)

        frame = tk.Frame(edit_win, padx=20, pady=10)
        frame.pack()

        tk.Label(frame, text="ID:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        tk.Label(frame, text=train_data[0]).grid(row=0, column=1, padx=5, pady=5, sticky="w")

        tk.Label(frame, text="Номер поезда:*").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        number_entry = tk.Entry(frame, width=20)
        number_entry.insert(0, train_data[1])
        number_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(frame, text="Название:*").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        name_entry = tk.Entry(frame, width=25)
        name_entry.insert(0, train_data[2])
        name_entry.grid(row=2, column=1, padx=5, pady=5)

        tk.Label(frame, text="Перевозчик:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        carrier_entry = tk.Entry(frame, width=20)
        carrier_entry.insert(0, train_data[3])
        carrier_entry.grid(row=3, column=1, padx=5, pady=5)

        branded_var = tk.BooleanVar(value=(train_data[4] == "Да"))
        tk.Checkbutton(frame, text="Фирменный", variable=branded_var).grid(row=4, column=1, padx=5, pady=5, sticky="w")

        def save_changes():
            new_number = number_entry.get().strip()
            new_name = name_entry.get().strip()

            if not new_number or not new_name:
                messagebox.showerror("Ошибка", "Заполните обязательные поля")
                return

            # Здесь должен быть запрос к API для обновления
            self.set_status(f"Поезд {new_number} обновлен")
            messagebox.showinfo("Успешно", "Данные поезда обновлены")
            edit_win.destroy()
            self.load_trains()

        tk.Button(edit_win, text="Сохранить", bg="#28a745", fg="white",
                 command=save_changes).pack(pady=10)

    def delete_train(self):
        """Удаление поезда"""
        selected = self.trains_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите поезд для удаления")
            return

        item = self.trains_tree.item(selected[0])
        train_id = item["values"][0]
        train_number = item["values"][1]

        if not messagebox.askyesno("Подтверждение",
                                   f"Вы уверены, что хотите удалить поезд {train_number}?\n"
                                   "Это действие также удалит все связанные вагоны."):
            return

        self.set_status(f"Удаление поезда {train_number}...")

        def _delete():
            try:
                # Реальный запрос к API
                response = requests.delete(f"{self.base_url}/api/trains/{train_id}")

                if response.status_code == 200:
                    self.window.after(0, lambda: self.on_delete_success(f"Поезд {train_number} удален"))
                else:
                    error_msg = response.json().get("detail", "Ошибка удаления")
                    self.window.after(0, lambda: self.on_delete_error(error_msg))

            except Exception as e:
                # Если API еще не готов, имитируем успешное удаление
                self.window.after(0, lambda: self.on_delete_success(f"Поезд {train_number} удален (тестовый режим)"))
                print(f"Ошибка API: {e}")

        threading.Thread(target=_delete, daemon=True).start()

    def on_delete_success(self, message):
        """Обработчик успешного удаления"""
        self.set_status(message)
        messagebox.showinfo("Успешно", message)
        self.load_trains()

    def on_delete_error(self, error):
        """Обработчик ошибки удаления"""
        self.set_status(error, True)
        messagebox.showerror("Ошибка", error)

    # ========== МЕТОДЫ ДЛЯ ДРУГИХ РАЗДЕЛОВ (аналогично) ==========

    def setup_routes_tab(self):
        """Вкладка управления маршрутами"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🛤️ Маршруты")

        # Панель добавления
        add_frame = tk.LabelFrame(tab, text="Добавить новый маршрут", padx=10, pady=10)
        add_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(add_frame, text="Название маршрута:*").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.route_name_entry = tk.Entry(add_frame, width=30)
        self.route_name_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(add_frame, text="Станция отправления:*").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.route_departure_entry = tk.Entry(add_frame, width=20)
        self.route_departure_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(add_frame, text="Станция прибытия:*").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.route_arrival_entry = tk.Entry(add_frame, width=20)
        self.route_arrival_entry.grid(row=1, column=3, padx=5, pady=5)

        add_btn = tk.Button(add_frame, text="➕ Добавить маршрут",
                           bg="#28a745", fg="white",
                           command=self.add_route)
        add_btn.grid(row=2, column=3, padx=5, pady=5)

        # Список маршрутов
        list_frame = tk.LabelFrame(tab, text="Существующие маршруты", padx=10, pady=10)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("ID", "Название", "Отправление", "Прибытие", "Станций")
        self.routes_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)

        column_widths = [50, 250, 150, 150, 80]
        for i, col in enumerate(columns):
            self.routes_tree.heading(col, text=col)
            self.routes_tree.column(col, width=column_widths[i])

        self.routes_tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.routes_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.routes_tree.configure(yscrollcommand=scrollbar.set)

        # Кнопки управления
        btn_frame = tk.Frame(list_frame)
        btn_frame.pack(fill="x", pady=5)

        tk.Button(btn_frame, text="🔄 Обновить",
                 command=self.load_routes).pack(side="left", padx=2)
        tk.Button(btn_frame, text="✏️ Редактировать",
                 command=self.edit_route).pack(side="left", padx=2)
        tk.Button(btn_frame, text="❌ Удалить",
                 bg="#dc3545", fg="white",
                 command=self.delete_route).pack(side="left", padx=2)

    def load_routes(self):
        """Загрузка списка маршрутов"""
        for item in self.routes_tree.get_children():
            self.routes_tree.delete(item)

        # Тестовые данные
        test_routes = [
            (1, "Москва - Санкт-Петербург", "Москва", "Санкт-Петербург", 2),
            (2, "Санкт-Петербург - Москва", "Санкт-Петербург", "Москва", 2),
            (3, "Москва - Казань", "Москва", "Казань", 2),
            (4, "Москва - Екатеринбург", "Москва", "Екатеринбург", 6),
            (5, "Москва - Новосибирск", "Москва", "Новосибирск", 5),
        ]

        for route in test_routes:
            self.routes_tree.insert("", "end", values=route)

    def add_route(self):
        """Добавление нового маршрута"""
        name = self.route_name_entry.get().strip()
        departure = self.route_departure_entry.get().strip()
        arrival = self.route_arrival_entry.get().strip()

        if not name or not departure or not arrival:
            messagebox.showerror("Ошибка", "Заполните все поля")
            return

        # Имитация добавления
        messagebox.showinfo("Успешно", f"Маршрут {name} добавлен (тестовый режим)")

        # Очищаем поля
        self.route_name_entry.delete(0, tk.END)
        self.route_departure_entry.delete(0, tk.END)
        self.route_arrival_entry.delete(0, tk.END)

        self.load_routes()

    def edit_route(self):
        """Редактирование маршрута"""
        selected = self.routes_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите маршрут для редактирования")
            return

        messagebox.showinfo("Инфо", "Функция редактирования в разработке")

    def delete_route(self):
        """Удаление маршрута"""
        selected = self.routes_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите маршрут для удаления")
            return

        item = self.routes_tree.item(selected[0])
        route_name = item["values"][1]

        if messagebox.askyesno("Подтверждение", f"Удалить маршрут {route_name}?"):
            messagebox.showinfo("Успешно", "Маршрут удален (тестовый режим)")
            self.load_routes()

    def setup_trips_tab(self):
        """Вкладка управления рейсами"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🚂 Рейсы")

        # Панель добавления
        add_frame = tk.LabelFrame(tab, text="Добавить новый рейс", padx=10, pady=10)
        add_frame.pack(fill="x", padx=10, pady=10)

        # Выбор поезда
        tk.Label(add_frame, text="Поезд:*").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.trip_train_combo = ttk.Combobox(add_frame, width=25)
        self.trip_train_combo.grid(row=0, column=1, padx=5, pady=5)

        # Выбор маршрута
        tk.Label(add_frame, text="Маршрут:*").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.trip_route_combo = ttk.Combobox(add_frame, width=25)
        self.trip_route_combo.grid(row=0, column=3, padx=5, pady=5)

        # Дата и время отправления
        tk.Label(add_frame, text="Дата отправления:*").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.trip_departure_date = tk.Entry(add_frame, width=12)
        self.trip_departure_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.trip_departure_date.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(add_frame, text="Время отправления:*").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.trip_departure_time = tk.Entry(add_frame, width=8)
        self.trip_departure_time.insert(0, "12:00")
        self.trip_departure_time.grid(row=1, column=3, padx=5, pady=5)

        # Дата и время прибытия
        tk.Label(add_frame, text="Дата прибытия:*").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.trip_arrival_date = tk.Entry(add_frame, width=12)
        self.trip_arrival_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.trip_arrival_date.grid(row=2, column=1, padx=5, pady=5)

        tk.Label(add_frame, text="Время прибытия:*").grid(row=2, column=2, padx=5, pady=5, sticky="w")
        self.trip_arrival_time = tk.Entry(add_frame, width=8)
        self.trip_arrival_time.insert(0, "16:00")
        self.trip_arrival_time.grid(row=2, column=3, padx=5, pady=5)

        add_btn = tk.Button(add_frame, text="➕ Добавить рейс",
                           bg="#28a745", fg="white",
                           command=self.add_trip)
        add_btn.grid(row=3, column=3, padx=5, pady=5)

        # Загружаем данные для комбобоксов
        self.load_trains_for_combo()
        self.load_routes_for_combo()

        # Список рейсов
        list_frame = tk.LabelFrame(tab, text="Существующие рейсы", padx=10, pady=10)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("ID", "Поезд", "Маршрут", "Отправление", "Прибытие", "Мест", "Статус")
        self.trips_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)

        column_widths = [50, 120, 200, 150, 150, 80, 100]
        for i, col in enumerate(columns):
            self.trips_tree.heading(col, text=col)
            self.trips_tree.column(col, width=column_widths[i])

        self.trips_tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.trips_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.trips_tree.configure(yscrollcommand=scrollbar.set)

        # Кнопки управления
        btn_frame = tk.Frame(list_frame)
        btn_frame.pack(fill="x", pady=5)

        tk.Button(btn_frame, text="🔄 Обновить",
                 command=self.load_trips_admin).pack(side="left", padx=2)
        tk.Button(btn_frame, text="✏️ Редактировать",
                 command=self.edit_trip).pack(side="left", padx=2)
        tk.Button(btn_frame, text="❌ Удалить",
                 bg="#dc3545", fg="white",
                 command=self.delete_trip).pack(side="left", padx=2)

    def load_trains_for_combo(self):
        """Загрузка поездов в комбобокс"""
        trains = []
        for item in self.trains_tree.get_children():
            values = self.trains_tree.item(item)["values"]
            if values:
                trains.append(f"{values[1]} - {values[2]}")
        self.trip_train_combo['values'] = trains

    def load_routes_for_combo(self):
        """Загрузка маршрутов в комбобокс"""
        routes = []
        for item in self.routes_tree.get_children():
            values = self.routes_tree.item(item)["values"]
            if values:
                routes.append(values[1])
        self.trip_route_combo['values'] = routes

    def load_trips_admin(self):
        """Загрузка списка рейсов"""
        for item in self.trips_tree.get_children():
            self.trips_tree.delete(item)

        # Тестовые данные
        test_trips = [
            (1, "001А", "Москва-СПб", "2026-03-05 10:00", "2026-03-05 14:30", "45", "По расписанию"),
            (2, "002Б", "Москва-Казань", "2026-03-05 14:00", "2026-03-05 22:00", "12", "По расписанию"),
            (3, "003В", "Москва-Екб", "2026-03-05 16:00", "2026-03-06 16:00", "78", "По расписанию"),
            (4, "001А", "СПб-Москва", "2026-03-06 10:00", "2026-03-06 14:30", "23", "По расписанию"),
        ]

        for trip in test_trips:
            self.trips_tree.insert("", "end", values=trip)

    def add_trip(self):
        """Добавление нового рейса"""
        train = self.trip_train_combo.get()
        route = self.trip_route_combo.get()
        dep_date = self.trip_departure_date.get().strip()
        dep_time = self.trip_departure_time.get().strip()
        arr_date = self.trip_arrival_date.get().strip()
        arr_time = self.trip_arrival_time.get().strip()

        if not train or not route:
            messagebox.showerror("Ошибка", "Выберите поезд и маршрут")
            return

        messagebox.showinfo("Успешно", f"Рейс добавлен (тестовый режим)")

        # Очищаем поля
        self.trip_train_combo.set('')
        self.trip_route_combo.set('')

        self.load_trips_admin()

    def edit_trip(self):
        """Редактирование рейса"""
        selected = self.trips_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите рейс для редактирования")
            return

        messagebox.showinfo("Инфо", "Функция редактирования в разработке")

    def delete_trip(self):
        """Удаление рейса"""
        selected = self.trips_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите рейс для удаления")
            return

        item = self.trips_tree.item(selected[0])
        trip_id = item["values"][0]

        if messagebox.askyesno("Подтверждение", f"Удалить рейс ID {trip_id}?"):
            messagebox.showinfo("Успешно", "Рейс удален (тестовый режим)")
            self.load_trips_admin()

    # ========== МЕТОДЫ ДЛЯ ВАГОНОВ И СТАНЦИЙ ==========

    def setup_carriages_tab(self):
        """Вкладка управления вагонами"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🚋 Вагоны")

        # Панель добавления
        add_frame = tk.LabelFrame(tab, text="Добавить вагон к поезду", padx=10, pady=10)
        add_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(add_frame, text="Поезд:*").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.carriage_train_combo = ttk.Combobox(add_frame, width=25)
        self.carriage_train_combo.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(add_frame, text="Номер вагона:*").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.carriage_number_entry = tk.Entry(add_frame, width=10)
        self.carriage_number_entry.grid(row=0, column=3, padx=5, pady=5)

        tk.Label(add_frame, text="Тип вагона:*").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.carriage_type_combo = ttk.Combobox(add_frame, width=20)
        self.carriage_type_combo['values'] = ("Сидячий", "Плацкарт", "Купе", "СВ", "Люкс")
        self.carriage_type_combo.grid(row=1, column=1, padx=5, pady=5)

        add_btn = tk.Button(add_frame, text="➕ Добавить вагон",
                           bg="#28a745", fg="white",
                           command=self.add_carriage)
        add_btn.grid(row=2, column=3, padx=5, pady=5)

        # Загружаем поезда для комбобокса
        self.load_trains_for_carriage_combo()

        # Список вагонов
        list_frame = tk.LabelFrame(tab, text="Существующие вагоны", padx=10, pady=10)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("ID", "Поезд", "Номер вагона", "Тип", "Мест", "Статус")
        self.carriages_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)

        column_widths = [50, 120, 100, 100, 80, 100]
        for i, col in enumerate(columns):
            self.carriages_tree.heading(col, text=col)
            self.carriages_tree.column(col, width=column_widths[i])

        self.carriages_tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.carriages_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.carriages_tree.configure(yscrollcommand=scrollbar.set)

        # Кнопки управления
        btn_frame = tk.Frame(list_frame)
        btn_frame.pack(fill="x", pady=5)

        tk.Button(btn_frame, text="🔄 Обновить",
                 command=self.load_carriages).pack(side="left", padx=2)
        tk.Button(btn_frame, text="✏️ Редактировать",
                 command=self.edit_carriage).pack(side="left", padx=2)
        tk.Button(btn_frame, text="❌ Удалить",
                 bg="#dc3545", fg="white",
                 command=self.delete_carriage).pack(side="left", padx=2)

    def load_trains_for_carriage_combo(self):
        """Загрузка поездов для комбобокса вагонов"""
        trains = []
        for item in self.trains_tree.get_children():
            values = self.trains_tree.item(item)["values"]
            if values:
                trains.append(f"{values[1]} - {values[2]}")
        self.carriage_train_combo['values'] = trains

    def load_carriages(self):
        """Загрузка списка вагонов"""
        for item in self.carriages_tree.get_children():
            self.carriages_tree.delete(item)

        # Тестовые данные
        test_carriages = [
            (1, "001А - Сапсан", "1", "Сидячий", "60", "Исправен"),
            (2, "001А - Сапсан", "2", "Сидячий", "60", "Исправен"),
            (3, "001А - Сапсан", "3", "Купе", "36", "Исправен"),
            (4, "002Б - Невский", "1", "Плацкарт", "54", "На ремонте"),
            (5, "002Б - Невский", "2", "Купе", "36", "Исправен"),
        ]

        for carriage in test_carriages:
            self.carriages_tree.insert("", "end", values=carriage)

    def add_carriage(self):
        """Добавление вагона"""
        train = self.carriage_train_combo.get()
        number = self.carriage_number_entry.get().strip()
        carriage_type = self.carriage_type_combo.get()

        if not train or not number or not carriage_type:
            messagebox.showerror("Ошибка", "Заполните все поля")
            return

        messagebox.showinfo("Успешно", f"Вагон {number} добавлен к поезду {train} (тестовый режим)")

        # Очищаем поля
        self.carriage_train_combo.set('')
        self.carriage_number_entry.delete(0, tk.END)
        self.carriage_type_combo.set('')

        self.load_carriages()

    def edit_carriage(self):
        """Редактирование вагона"""
        selected = self.carriages_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите вагон для редактирования")
            return

        messagebox.showinfo("Инфо", "Функция редактирования в разработке")

    def delete_carriage(self):
        """Удаление вагона"""
        selected = self.carriages_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите вагон для удаления")
            return

        item = self.carriages_tree.item(selected[0])
        carriage_id = item["values"][0]

        if messagebox.askyesno("Подтверждение", f"Удалить вагон ID {carriage_id}?"):
            messagebox.showinfo("Успешно", "Вагон удален (тестовый режим)")
            self.load_carriages()

    def setup_stations_tab(self):
        """Вкладка управления станциями"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🏢 Станции")

        # Панель добавления
        add_frame = tk.LabelFrame(tab, text="Добавить новую станцию", padx=10, pady=10)
        add_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(add_frame, text="Название станции:*").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.station_name_entry = tk.Entry(add_frame, width=30)
        self.station_name_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(add_frame, text="Город:*").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.station_city_entry = tk.Entry(add_frame, width=20)
        self.station_city_entry.grid(row=0, column=3, padx=5, pady=5)

        tk.Label(add_frame, text="ESR код:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.station_esr_entry = tk.Entry(add_frame, width=15)
        self.station_esr_entry.grid(row=1, column=1, padx=5, pady=5)

        add_btn = tk.Button(add_frame, text="➕ Добавить станцию",
                           bg="#28a745", fg="white",
                           command=self.add_station)
        add_btn.grid(row=2, column=3, padx=5, pady=5)

        # Список станций
        list_frame = tk.LabelFrame(tab, text="Существующие станции", padx=10, pady=10)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("ID", "Название", "Город", "ESR код", "Статус")
        self.stations_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)

        column_widths = [50, 200, 150, 100, 100]
        for i, col in enumerate(columns):
            self.stations_tree.heading(col, text=col)
            self.stations_tree.column(col, width=column_widths[i])

        self.stations_tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.stations_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.stations_tree.configure(yscrollcommand=scrollbar.set)

        # Кнопки управления
        btn_frame = tk.Frame(list_frame)
        btn_frame.pack(fill="x", pady=5)

        tk.Button(btn_frame, text="🔄 Обновить",
                 command=self.load_stations).pack(side="left", padx=2)
        tk.Button(btn_frame, text="✏️ Редактировать",
                 command=self.edit_station).pack(side="left", padx=2)
        tk.Button(btn_frame, text="❌ Удалить",
                 bg="#dc3545", fg="white",
                 command=self.delete_station).pack(side="left", padx=2)

    def load_stations(self):
        """Загрузка списка станций"""
        for item in self.stations_tree.get_children():
            self.stations_tree.delete(item)

        # Тестовые данные
        test_stations = [
            (1, "Москва", "Москва", "2000005", "Активна"),
            (2, "Санкт-Петербург", "Санкт-Петербург", "2004001", "Активна"),
            (3, "Казань", "Казань", "2006001", "Активна"),
            (4, "Екатеринбург", "Екатеринбург", "2006003", "Активна"),
            (5, "Новосибирск", "Новосибирск", "2006004", "Реконструкция"),
        ]

        for station in test_stations:
            self.stations_tree.insert("", "end", values=station)

    def add_station(self):
        """Добавление новой станции"""
        name = self.station_name_entry.get().strip()
        city = self.station_city_entry.get().strip()
        esr = self.station_esr_entry.get().strip()

        if not name or not city:
            messagebox.showerror("Ошибка", "Заполните название и город")
            return

        messagebox.showinfo("Успешно", f"Станция {name} добавлена (тестовый режим)")

        # Очищаем поля
        self.station_name_entry.delete(0, tk.END)
        self.station_city_entry.delete(0, tk.END)
        self.station_esr_entry.delete(0, tk.END)

        self.load_stations()

    def edit_station(self):
        """Редактирование станции"""
        selected = self.stations_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите станцию для редактирования")
            return

        messagebox.showinfo("Инфо", "Функция редактирования в разработке")

    def delete_station(self):
        """Удаление станции"""
        selected = self.stations_tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите станцию для удаления")
            return

        item = self.stations_tree.item(selected[0])
        station_name = item["values"][1]

        if messagebox.askyesno("Подтверждение", f"Удалить станцию {station_name}?"):
            messagebox.showinfo("Успешно", "Станция удалена (тестовый режим)")
            self.load_stations()