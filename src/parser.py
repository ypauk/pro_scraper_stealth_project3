# src/parser.py
"""
Парсер для rozetka.com.ua
"""

from playwright.async_api import Page
from src.models import RozetkaItem
from loguru import logger
from urllib.parse import urljoin
import re
import asyncio


class RozetkaParser:
    """Парсер для rozetka.com.ua"""

    def __init__(self):
        self.selectors = {
            # Головний контейнер товару
            "product_card": [
                "rz-product-tile",
                "div.item",
                "article.content"
            ],

            # Зображення
            "image": [
                "img.tile-image",
                ".tile-image[src*='rozetka']"
            ],

            # Посилання на товар
            "link": [
                "a.tile-image-host",
                "a.tile-title",
                "a[apprzroute]"
            ],

            # Назва товару
            "title": [
                "a.tile-title",
                ".tile-title",
                "a[title]"
            ],

            # Поточна ціна
            "price": [
                "rz-tile-price .price",
                ".price.color-red",
                ".price-wrap .price"
            ],

            # Стара ціна (якщо є знижка)
            "old_price": [
                "rz-tile-price .old-price",
                ".old-price",
                ".old-price.text-base"
            ],

            # Рейтинг
            "rating": [
                "rz-stars-rating-progress",
                ".stars__rating",
                ".rating-block-rating"
            ],

            # Кількість відгуків
            "reviews": [
                ".rating-block-content",
                ".rating-block-content span",
                "a[href*='comments'] span"
            ],

            # Наявність/доставка
            "availability": [
                ".text-xs.color-green",
                ".d-flex.gap-1.items-center.text-xs",
                ".tile-smart-icon"
            ],

            # ID товару (прихований)
            "product_id": [
                ".g-id",
                "div[hidden].g-id"
            ],

            # Бонуси
            "bonus": [
                "rz-tile-bonus",
                ".bonus span b",
                ".icon__center span b"
            ],

            # Кнопка "Купити"
            "buy_button": [
                "rz-buy-button button",
                ".buy-button",
                "button[aria-label='Купити']"
            ],

            # Пагінація
            "next_button": [
                ".pagination__next",
                "a[rel='next']",
                ".show-more__button"
            ]
        }

        self.stats = {
            'pages_processed': 0,
            'products_found': 0,
            'products_parsed': 0,
            'errors': 0
        }

    async def _find_working_selector(self, page: Page, selector_list: list, timeout: int = 5000) -> str | None:
        """
        Знаходить перший робочий селектор зі списку

        Args:
            page: Сторінка Playwright
            selector_list: Список селекторів для перевірки
            timeout: Час очікування в мс

        Returns:
            str: Робочий селектор або None
        """
        for selector in selector_list:
            try:
                element = await page.wait_for_selector(selector, timeout=timeout, state='attached')
                if element:
                    logger.debug(f"✅ [Rozetka] Знайдено робочий селектор: {selector}")
                    return selector
            except:
                continue
        return None

    def _clean_price(self, price_text: str) -> str:
        """Очищає ціну від HTML символів"""
        if not price_text:
            return ""
        # Видаляємо &nbsp; та зайві пробіли
        return price_text.replace('\xa0', ' ').strip()

    def _extract_rating_from_style(self, style: str) -> float | None:
        """
        Витягує рейтинг з CSS style (width: 96%)
        Наприклад: width: 96% -> 4.8 зірки
        """
        if not style:
            return None
        match = re.search(r'width:\s*(\d+)%', style)
        if match:
            return float(match.group(1)) / 20  # 100% = 5 зірок
        return None

    def _extract_number_from_text(self, text: str) -> int | None:
        """Витягує число з тексту"""
        if not text:
            return None
        match = re.search(r'(\d+)', text)
        if match:
            return int(match.group(1))
        return None

    async def parse_listings(self, page: Page) -> list[RozetkaItem]:
        """
        Парсинг товарів зі сторінки категорії або пошуку Rozetka

        Args:
            page: Сторінка Playwright з результатами

        Returns:
            list[RozetkaItem]: Список знайдених товарів
        """
        items = []
        self.stats['pages_processed'] += 1

        logger.info(f"📄 [Rozetka] Початок парсингу сторінки...")

        try:
            # Чекаємо завантаження карток товарів
            await page.wait_for_selector("rz-product-tile", timeout=10000)
            logger.debug("✅ [Rozetka] Картки товарів завантажено")

            # Прокручуємо для підвантаження лінивих зображень
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)

            # Отримуємо всі картки товарів
            cards = await page.query_selector_all("rz-product-tile")
            self.stats['products_found'] += len(cards)

            logger.info(f"📦 [Rozetka] Знайдено {len(cards)} товарів на сторінці")

            for card_index, card in enumerate(cards, 1):
                try:
                    # ===== НАЗВА ТОВАРУ =====
                    title_el = await card.query_selector("a.tile-title")
                    if not title_el:
                        logger.warning(f"⚠️ [Rozetka] Картка #{card_index}: не знайдено елемент з назвою")
                        continue

                    # Спочатку пробуємо отримати з атрибуту title, потім з тексту
                    title = await title_el.get_attribute("title")
                    if not title:
                        title = await title_el.inner_text()

                    # ===== ПОСИЛАННЯ =====
                    link_el = await card.query_selector("a.tile-image-host, a.tile-title")
                    link = await link_el.get_attribute("href") if link_el else ""

                    # Формуємо повне посилання якщо потрібно
                    if link and not link.startswith('http'):
                        link = urljoin("https://rozetka.com.ua", link)

                    # ===== ЗОБРАЖЕННЯ =====
                    img_el = await card.query_selector("img.tile-image")
                    img_url = await img_el.get_attribute("src") if img_el else None

                    # ===== ЦІНИ =====
                    # Поточна ціна
                    price_el = await card.query_selector(".price.color-red, .price-wrap .price")
                    price = await price_el.inner_text() if price_el else ""

                    # Стара ціна (якщо є знижка)
                    old_price_el = await card.query_selector(".old-price")
                    old_price = await old_price_el.inner_text() if old_price_el else None

                    # ===== РЕЙТИНГ =====
                    rating_el = await card.query_selector("rz-stars-rating-progress")
                    rating = None
                    if rating_el:
                        style = await rating_el.get_attribute("style")
                        rating = self._extract_rating_from_style(style)

                    # ===== ВІДГУКИ =====
                    reviews_el = await card.query_selector(".rating-block-content")
                    reviews_count = None
                    if reviews_el:
                        reviews_text = await reviews_el.inner_text()
                        reviews_count = self._extract_number_from_text(reviews_text)

                    # ===== НАЯВНІСТЬ =====
                    avail_el = await card.query_selector(".text-xs.color-green")
                    if avail_el:
                        availability = await avail_el.inner_text()
                    else:
                        # Якщо немає зеленого тексту, перевіряємо наявність кнопки
                        buy_btn = await card.query_selector("rz-buy-button button")
                        availability = "Є в наявності" if buy_btn else "Немає в наявності"

                    # ===== ID ТОВАРУ =====
                    id_el = await card.query_selector(".g-id")
                    product_id = await id_el.inner_text() if id_el else None

                    # ===== БОНУСИ =====
                    bonus_el = await card.query_selector(".bonus span b")
                    bonus = await bonus_el.inner_text() if bonus_el else None
                    if bonus:
                        bonus = self._extract_number_from_text(bonus)

                    # Створюємо об'єкт товару
                    item = RozetkaItem(
                        title=title.strip(),
                        price=self._clean_price(price),
                        old_price=self._clean_price(old_price) if old_price else None,
                        availability=availability.strip(),
                        rating=rating,
                        reviews_count=reviews_count,
                        image_url=img_url,
                        url=link,
                        seller=None,
                        code=product_id
                    )

                    items.append(item)
                    self.stats['products_parsed'] += 1

                    # Логуємо прогрес кожні 10 товарів
                    if card_index % 10 == 0:
                        logger.debug(f"   [Rozetka] Прогрес: {card_index}/{len(cards)}")

                except Exception as e:
                    self.stats['errors'] += 1
                    logger.warning(f"⚠️ [Rozetka] Помилка парсингу картки #{card_index}: {str(e)[:100]}")
                    continue

            logger.success(f"✅ [Rozetka] Успішно спарсено {len(items)} товарів")

        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"❌ [Rozetka] Критична помилка парсингу сторінки: {e}")

            # Зберігаємо HTML для дебагу (тільки якщо це перша сторінка)
            if self.stats['pages_processed'] == 1:
                html = await page.content()
                with open("debug_rozetka.html", "w", encoding="utf-8") as f:
                    f.write(html)
                logger.info("💾 HTML сторінки Rozetka збережено для аналізу")

        return items

    async def get_next_page(self, page: Page) -> str | None:
        """
        Отримує URL наступної сторінки для пагінації

        Args:
            page: Поточна сторінка

        Returns:
            str: URL наступної сторінки або None
        """
        try:
            # Спосіб 1: Класична пагінація з кнопкою "Далі"
            next_button = await page.query_selector(".pagination__next:not(.disabled)")
            if next_button:
                href = await next_button.get_attribute("href")
                if href:
                    next_url = urljoin(page.url, href)
                    logger.info(f"➡️ [Rozetka] Наступна сторінка: {next_url}")
                    return next_url

            # Спосіб 2: Infinite scroll з кнопкою "Показати ще"
            show_more = await page.query_selector(".show-more__button")
            if show_more and await show_more.is_visible():
                await show_more.click()
                logger.info("🔄 [Rozetka] Натиснуто 'Показати ще'")
                await page.wait_for_timeout(2000)  # Чекаємо завантаження нових товарів
                return page.url  # Повертаємо ту саму URL (сторінка оновилась)

        except Exception as e:
            logger.debug(f"ℹ️ [Rozetka] Пагінація не знайдена: {e}")

        logger.info(f"🏁 [Rozetka] Це остання сторінка")
        return None

    async def parse_product_details(self, page: Page) -> dict:
        """
        Парсинг додаткових деталей зі сторінки товару (опціонально)

        Args:
            page: Сторінка конкретного товару

        Returns:
            dict: Додаткові характеристики товару
        """
        details = {}

        try:
            # Код товару
            code_el = await page.query_selector(".product__code")
            if code_el:
                code_text = await code_el.inner_text()
                code_match = re.search(r'(\d+)', code_text)
                if code_match:
                    details['code'] = code_match.group(1)

            # Продавець
            seller_el = await page.query_selector(".product-seller__title")
            if seller_el:
                details['seller'] = await seller_el.inner_text()

            # Характеристики
            specs = {}
            spec_rows = await page.query_selector_all(".product-attributes__item")
            for row in spec_rows[:10]:  # Обмежуємо кількість
                try:
                    name_el = await row.query_selector(".product-attributes__label")
                    value_el = await row.query_selector(".product-attributes__value")
                    if name_el and value_el:
                        name = await name_el.inner_text()
                        value = await value_el.inner_text()
                        specs[name.strip()] = value.strip()
                except:
                    continue

            if specs:
                details['specifications'] = specs

        except Exception as e:
            logger.warning(f"⚠️ [Rozetka] Помилка парсингу деталей: {e}")

        return details

    def print_stats(self):
        """Виводить статистику роботи парсера"""
        logger.info("=" * 60)
        logger.info("📊 СТАТИСТИКА ПАРСЕРА ROZETKA")
        logger.info("=" * 60)
        logger.info(f"   • Сторінок оброблено: {self.stats['pages_processed']}")
        logger.info(f"   • Товарів знайдено: {self.stats['products_found']}")
        logger.info(f"   • Товарів спарсено: {self.stats['products_parsed']}")
        logger.info(f"   • Помилок: {self.stats['errors']}")

        if self.stats['products_found'] > 0:
            success_rate = (self.stats['products_parsed'] / self.stats['products_found']) * 100
            logger.info(f"   • Успішність: {success_rate:.1f}%")

        logger.info("=" * 60)


# Для зручності - функція створення парсера
def create_rozetka_parser() -> RozetkaParser:
    """
    Створює екземпляр парсера для Rozetka

    Returns:
        RozetkaParser: Налаштований парсер
    """
    logger.info("🎯 Створено парсер для Rozetka")
    return RozetkaParser()