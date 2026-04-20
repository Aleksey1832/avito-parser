import logging
import os
from logging.handlers import RotatingFileHandler


def setup_app_logger():
    # Создаем папку для логов, если её нет
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "app.log")

    # Настройка:
    # maxBytes=1024*1024 (1 МБ) — как только файл станет больше 1МБ, он перезапишется
    # backupCount=1 — храним только 1 предыдущую версию файла
    handler = RotatingFileHandler(
        log_file,
        maxBytes=1024 * 1024,
        backupCount=1,
        encoding='utf-8'
    )

    # Красивый формат: Время [Уровень] Сообщение
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)

    # Внутреннюю переменную назовем lgr, чтобы не путать с глобальной
    lgr = logging.getLogger("AvitoParser")
    lgr.setLevel(logging.INFO)
    lgr.addHandler(handler)

    # Также дублируем логи в консоль, чтобы мы их видели при разработке
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    lgr.addHandler(console_handler)

    return lgr


# Вот здесь мы создаем единственный экземпляр, который будут импортировать другие файлы
logger = setup_app_logger()
