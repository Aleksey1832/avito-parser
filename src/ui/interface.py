import sys
import os
import threading # Чтобы окно не зависало во время парсинга!

# Добавляем путь к папке src, чтобы интерфейс видел соседей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk
from engines.avito_engine import parse_avito
from utils.excel_exporter import save_to_excel

# Настраиваем внешний вид
ctk.set_appearance_mode("dark")  # Темная тема для настоящих хакеров
ctk.set_default_color_theme("blue")


class AvitoApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Smart Parser Pro v1.0")
        self.geometry("600x500")

        # --- Центрируем всё ---
        self.grid_columnconfigure(0, weight=1)

        # Заголовок
        self.label = ctk.CTkLabel(self, text="AVITO PARSER", font=("Roboto", 28, "bold"))
        self.label.grid(row=0, column=0, pady=(30, 20))

        # Поле ввода
        self.entry = ctk.CTkEntry(self, placeholder_text="Что ищем? (например: Велосипед)", width=400, height=40)
        self.entry.grid(row=1, column=0, pady=10)

        # --- Выбор региона (пока текстом, потом сделаем списком) ---
        self.region_entry = ctk.CTkEntry(self, placeholder_text="Регион", width=400)
        self.region_entry.insert(0, "sankt_peterburg_i_lo")  # Ставим Питер по умолчанию
        self.region_entry.grid(row=2, column=0, pady=10)

        # Кнопка СТАРТ
        self.btn_start = ctk.CTkButton(self, text="НАЧАТЬ СБОР ДАННЫХ", font=("Roboto", 16, "bold"),
                                       height=45, command=self.run_thread)
        self.btn_start.grid(row=3, column=0, pady=20)

        # Окно логов (заменяет консоль)
        self.log_view = ctk.CTkTextbox(self, width=550, height=200, font=("Consolas", 12))
        self.log_view.grid(row=4, column=0, pady=10)
        self.log_view.insert("0.0", ">>> Программа готова к работе.\n")

    def log(self, message):
        """Выводит текст в окно логов"""
        self.log_view.insert("end", f">{message}\n")
        self.log_view.see("end")

    def run_thread(self):
        """Запускает парсинг в отдельном потоке, чтобы UI не вис"""
        query = self.entry.get()
        region = self.region_entry.get()  # <--- Достаем регион
        if not query:
            self.log("!!! Ошибка: Введите поисковый запрос!")
            return

        self.btn_start.configure(state="disabled")  # Выключаем кнопку на время работы

        # Запускаем функцию в фоновом потоке
        thread = threading.Thread(target=self.start_parsing, args=(query, region))
        thread.daemon = True  # <--- Чтобы не плодить зомби-процессы
        thread.start()

    def start_parsing(self, query, region):
        """Сама работа движка"""
        try:
            self.log(f">>> Запуск поиска: {query} ({region})")

            # Вызываем наш мотор
            results = parse_avito(query, region)

            if results:
                self.log(f"--- Найдено объектов: {len(results)} шт.")
                path = save_to_excel(results, query)
                if path:
                    self.log(f"--- Успех! Файл создан:\n{path}")
            else:
                self.log("!!! Ничего не найдено или возникла ошибка.")

        except Exception as e:
            self.log(f"КРИТИЧЕСКАЯ ОШИБКА: {e}")

        finally:
            self.btn_start.configure(state="normal")  # Возвращаем кнопку в строй
            # Убираем фокус с кнопки, чтобы она не выглядела "нажатой"
            self.focus()
            self.log("--- Программа готова к новому поиску ---")


if __name__ == "__main__":
    app = AvitoApp()
    app.mainloop()
