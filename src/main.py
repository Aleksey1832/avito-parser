import sys
import os
import time

# Добавляем папку src в пути поиска, чтобы Python видел utils и engines
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def start_app():
    from engines.avito_engine import parse_avito
    from utils.excel_exporter import save_to_excel
    from utils.logger import logger

    logger.info("--- Запуск Smart Parser Pro (Консольный режим) ---")

    # Даем логам 0.1 секунды, чтобы они "проплевались" в консоль до вопроса
    time.sleep(0.2)

    # 1. Запрос данных
    query = input("\nВведите запрос для Авито (например, велосипед): ")
    if not query:
        query = "iphone"

        # 2. Запускаем "мотор"
    results = parse_avito(query)

    # 3. Если что-то нашли — сохраняем
    if results:
        file_path = save_to_excel(results, query)
        if file_path:
            logger.info(f"Финиш! Результаты лежат здесь: {file_path}")
        else:
            logger.error("Ошибка при создании Excel файла.")
    else:
        logger.warning("Поиск не дал результатов. Возможно, стоит сменить прокси или запрос.")


if __name__ == "__main__":
    try:
        start_app()
    except KeyboardInterrupt:
        # Это сработает, если нажать Ctrl+C
        print("\n\n[!] Работа прервана пользователем.")
        sys.exit(0)
    except Exception as e:
        # Это поймает любую другую критическую ошибку, чтобы окно не схлопнулось мгновенно
        import logging
        logging.error(f"Произошел критический сбой: {e}")
        input("\nНажмите Enter, чтобы закрыть программу...")
