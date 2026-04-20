import sys
import os

# Добавляем родительскую папку (src) в пути поиска.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time
import re
# import playwright_stealth
from playwright.sync_api import sync_playwright
from utils.logger import logger


def clean_price(price_str):
    """Превращает '15 000 руб.' в целое число 15000"""
    if not price_str:
        return 0
    # Оставляем только цифры
    digits = re.sub(r'\D', '', price_str)
    return int(digits) if digits else 0


def parse_avito(search_query, region="sankt_peterburg_i_lo"):
    results = []
    logger.info(f">>> Запуск парсинга Авито по запросу: '{search_query}'")

    with sync_playwright() as p:
        try:
            # 1. Используем запуск с замедлением (slow_mo), чтобы Авито не паниковало
            browser = p.chromium.launch(headless=False)

            # 2. Создаем контекст БЕЗ viewport внутри скобок (чтобы не злить IDE)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )

            page = context.new_page()

            # 3. Устанавливаем размер окна отдельно — так PyCharm не придерется
            page.set_viewport_size({"width": 1920, "height": 1080})

            # url = f"https://www.avito.ru/rossiya?q={search_query.replace(' ', '%20')}"
            url = f"https://www.avito.ru/{region}?q={search_query.replace(' ', '%20')}"

            # 4. Заходим сначала на главную, а потом на поиск (как человек)
            page.goto("https://www.avito.ru", wait_until="domcontentloaded", timeout=60000)
            time.sleep(2)

            page.goto(url, wait_until="domcontentloaded", timeout=60000)  # Ждем полной загрузки
            logger.info(f"HTML страницы получен, ждем отрисовки карточек...: {url}")

            # 3. Вместо ожидания всей сети, ждем появления хотя бы ОДНОЙ карточки товара
            try:
                page.wait_for_selector('div[data-marker="item"]', timeout=15000)
                page.mouse.wheel(0, 800)
                time.sleep(3)
            except Exception as e:
                logger.warning(f"Карточки не появились вовремя {e}")

            # Скроллим чуть-чуть вниз, чтобы подгрузились ленивые элементы
            logger.info("Прокручиваю страницу для подгрузки адресов и дат...")
            # Делаем 3 резких прыжка вниз, чтобы сработали триггеры загрузки
            for _ in range(5):
                page.mouse.wheel(0, 1000)
                time.sleep(1.5)

            # Возвращаемся в начало, чтобы начать сбор
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(3)

            # Теперь ищем элементы
            # items = page.locator('div[data-marker="item"]').all()
            items = page.locator('div[data-marker="item"], div[class*="iva-item-root"]').all()
            logger.info(f"Найдено объявлений на странице: {len(items)}")

            for i, item in enumerate(items, 1):
                try:
                    # 1. Название: ищем любой заголовок или ссылку с текстом
                    # Мы пробуем найти текст в h3, но если там плашка - берем следующий текст
                    titles = item.locator('h3').all_text_contents()
                    name = ""
                    for t in titles:
                        if not any(x in t.lower() for x in ["проверен", "продавец", "реквизиты"]):
                            name = t.strip()
                            break

                    if not name:
                        # Запасной вариант - текст из ссылки
                        name = item.locator('a[data-marker="item-title"]').inner_text(timeout=500).strip()

                    # 2. Цена: ищем элемент с атрибутом price
                    price = 0
                    price_node = item.locator('[itemprop="price"]').first
                    if price_node.count() > 0:
                        p_raw = price_node.get_attribute('content', timeout=500)
                        price = int(p_raw) if p_raw and p_raw.isdigit() else 0
                    else:
                        # Если мета-тега нет, ищем текст со значком рубля
                        price_text = item.locator('[data-marker="item-price"]').inner_text(timeout=500)
                        price = clean_price(price_text)

                    # === 3. ССЫЛКА (Чисто ищем URL) ===
                    link = ""
                    # Ищем строго тег <a> (анкор), у которого есть атрибут href
                    l_node = item.locator('a[data-marker="item-title"], a[itemprop="url"]').first

                    if l_node.count() > 0:
                        link_raw = l_node.get_attribute('href')
                        if link_raw:
                            # Склеиваем домен и отрезаем весь мусор после знака ?
                            link = "https://www.avito.ru" + link_raw.split('?')[0]

                    # === 4. ГЕОЛОКАЦИЯ (Город и Адрес отдельно) ===
                    full_geo = ""
                    # Пробуем найти любой текстовый блок, который Авито метит как адрес.
                    # Добавили проверку на iva-item-address — это очень частый класс
                    geo_selectors = [
                        '[data-marker="item-address"]',
                        'span[class*="address-address"]',
                        'div[class*="location-"]',
                        'p[class*="geo-address"]'
                    ]

                    for sel in geo_selectors:
                        node = item.locator(sel).first
                        if node.count() > 0:
                            full_geo = node.inner_text(timeout=500).strip()
                            if full_geo: break

                    # Если всё еще пусто, берем ВЕСЬ текст из нижней части карточки (там обычно адрес)
                    if not full_geo:
                        try:
                            # Ищем блок iva-item-description-step (там адрес и дата рядом)
                            full_geo = item.locator('div[class*="geo-root"]').inner_text(timeout=500).strip()
                        except:
                            full_geo = "Санкт-Петербург"  # Наш крайний случай

                    # --- Разделение ---
                    # Очищаем от лишних переносов строк, которые Авито обожает пихать в адрес
                    full_geo = full_geo.replace('\n', ' ').strip()

                    if "," in full_geo:
                        # Если запятая есть — используем твой проверенный метод
                        parts = full_geo.split(',')
                        display_city = parts[0].strip()
                        display_address = ", ".join([p.strip() for p in parts[1:]])
                    elif " р-н " in full_geo:
                        # Если запятой нет, но есть " р-н ", делим по нему
                        parts = full_geo.split(' р-н ')
                        display_city = parts[0].strip()
                        display_address = "р-н " + parts[1].strip()
                    else:
                        # Если ничего не помогло, берем первое слово как город, остальное в адрес
                        words = full_geo.split(' ')
                        if len(words) > 1:
                            display_city = words[0].strip()
                            display_address = " ".join(words[1:]).strip()
                        else:
                            display_city = full_geo
                            display_address = "Санкт-Петербург"


                    # 5. Имя продавца
                    seller_name = ""
                    try:
                        # Мы просим браузер найти текст внутри блока продавца через JavaScript
                        # Это обходит многие защиты интерфейса
                        seller_name = item.evaluate("""(node) => {
                            const sellerBlock = node.querySelector('[data-marker="seller-name"]') ||
                                node.querySelector('[class*="seller-name"]') ||
                                node.querySelector('[class*="style-seller-info"]');
                            return sellerBlock ? sellerBlock.innerText.trim() : "";
                        }""")
                    except:
                        pass

                    if not seller_name or len(seller_name) > 60:
                        seller_name = "Частное лицо"

                    # === 6. ДОБАВЛЕНИЕ В СПИСОК ===
                    if name:
                        logger.info(f"[{i}/{len(items)}] Добавлено: {name[:30]}...")
                        results.append({
                            'Название': name,
                            'Цена, руб': price,
                            'Город': display_city,
                            'Адрес': display_address,
                            'Продавец': seller_name,
                            'Ссылка': link
                        })
                except Exception as e:
                    logger.debug(f"Ошибка на элементе {i}: {e}")
                    continue

            logger.info(f"Сбор данных окончен. Всего собрано: {len(results)}")
            browser.close()  # <--- ОБЯЗАТЕЛЬНО ЗАКРЫВАЕМ ТУТ

        except Exception as e:
            logger.error(f"Ошибка во время работы браузера: {e}")
            if 'browser' in locals():
                browser.close()

    return results


if __name__ == "__main__":
    # Тестовый прогон
    test_results = parse_avito("iphone 15")
    for idx, val in enumerate(test_results[:3], 1):
        print(f"{idx}. {val['Название']} - {val['Цена, руб']} руб.")
