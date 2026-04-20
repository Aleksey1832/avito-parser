import pandas as pd
import os
import datetime  # Нужно для уникальных имен файлов, если старый открыт
from utils.logger import logger


def save_to_excel(data, query):
    """
    Превращает список словарей в таблицу Excel.
    Если файл с таким именем уже открыт в Excel, создает новый с меткой времени.
    """
    if not data:
        logger.warning("Экспорт отменен: список данных пуст.")
        return None

    try:
        # 1. Очищаем запрос от запрещенных символов Windows (/\:*?"<>|)
        # Чтобы программа не упала, если пользователь введет "iphone 15/128"
        forbidden_chars = '/\\:*?"<>|'
        clean_query = query
        for char in forbidden_chars:
            clean_query = clean_query.replace(char, '')

        clean_query = clean_query.replace(' ', '_')
        filename = f"results_{clean_query}.xlsx"

        # 2. Создаем DataFrame (умную таблицу)
        df = pd.DataFrame(data)
        # Укорачивание ссылки.
        if 'Ссылка' in df.columns:
            # Превращаем длинную ссылку в красивую кнопку "Открыть".
            # Формула Excel: =HYPERLINK("адрес", "текст")
            df['Ссылка'] = df['Ссылка'].apply(lambda x: f'=HYPERLINK("{x}", "Открыть")' if x else "")

        # 3. Пытаемся сохранить файл
        try:
            # df.to_excel(filename, index=False)
            # Используем движок xlsxwriter для правильной записи формул
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Sheet1')

                # Получаем доступ к инструментам xlsxwriter
                workbook = writer.book
                worksheet = writer.sheets['Sheet1']

                # Настраиваем формат: синий цвет и подчеркивание (как у ссылок)
                link_format = workbook.add_format({
                    'font_color': 'blue',
                    'underline': 1
                })

                # 2. ПРИМЕНЯЕМ СТИЛЬ К КОЛОНКЕ С ГИПЕРССЫЛКАМИ
                # Предположим, ссылки у нас в колонке C (индекс 2)
                # Мы перезаписываем данные в колонке, добавляя им созданный формат
                for row_num, link_value in enumerate(df['Ссылка']):
                    # row_num + 1, потому что первая строка занята заголовком
                    if link_value:
                        worksheet.write_formula(row_num + 1, 5, link_value, link_format)

                # Устанавливаем ширину колонки C, чтобы кнопка "Открыть" не жалась
                worksheet.set_column('A:A', 40)
                worksheet.set_column('C:C', 20)
                worksheet.set_column('D:D', 20)
                worksheet.set_column('E:E', 20)
                worksheet.set_column('F:F', 25)

        except PermissionError:
            # Если файл открыт в Excel, Windows выдаст PermissionError.
            # Чтобы не терять данные, добавим время к названию:
            timestamp = datetime.datetime.now().strftime("%H-%M-%S")
            filename = f"results_{clean_query}_{timestamp}.xlsx"
            df.to_excel(filename, index=False)
            logger.warning(f"Файл был занят другой программой. Создан дубликат: {filename}")

        # 4. Получаем полный путь для логов
        full_path = os.path.abspath(filename)
        logger.info(f"Данные успешно выгружены в Excel: {full_path}")

        return full_path

    except Exception as e:
        logger.error(f"Критическая ошибка при работе с Excel: {e}")
        return None
