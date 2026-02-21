# src/scraper.py
"""
Основний скрапер для Rozetka
"""

import asyncio
import random
import time
from src.client import BrowserClient
from src.parser import RozetkaParser
from src.models import RozetkaItem
from loguru import logger
from src.utils import human_delay, smooth_scroll, human_mouse_move
from src.settings import BASE_DELAY, VALID_PROXY_LIST
from src.state_manager import StateManager
from src.exporter import Exporter
from src.stealth import ManualStealth, get_stealth_for_site
from src.proxy_monitor import ProxyMonitor
from src.semaphore_manager import get_semaphore


class Scraper:
    def __init__(self,
                 max_items: int = 50,
                 proxy: dict = None,
                 stealth: ManualStealth = None,
                 site_name: str = "Rozetka",
                 max_concurrent: int = 2,
                 discount_only: bool = False,
                 min_price: int = None,
                 max_price: int = None,
                 min_rating: float = None):

        # Перевірка проксі
        if proxy is None and not VALID_PROXY_LIST:
            logger.critical("=" * 60)
            logger.critical("🔴 КРИТИЧНА ПОМИЛКА: СКРАПЕР НЕ МОЖЕ ПРАЦЮВАТИ БЕЗ ПРОКСІ!")
            logger.critical("=" * 60)
            logger.critical("🛡️ ЗАХИСТ: Програма буде зупинена")
            logger.critical("💡 Рішення: Додайте проксі в config.yaml")
            logger.critical("=" * 60)
            raise Exception("Scraper вимагає проксі для роботи")

        self.client = BrowserClient(proxy=proxy)
        self.parser = RozetkaParser()
        self.max_items = max_items
        self.results: list[RozetkaItem] = []
        self._lock = asyncio.Lock()
        self.state_manager = StateManager()
        self.stealth = stealth or get_stealth_for_site('ukraine')

        # Фільтри
        self.discount_only = discount_only
        self.min_price = min_price
        self.max_price = max_price
        self.min_rating = min_rating

        # Контроль навантаження
        self.site_name = site_name
        self.max_concurrent = max_concurrent
        self.semaphore = get_semaphore(site_name, max_concurrent)
        self.page_semaphore = asyncio.Semaphore(max_concurrent)

        # Моніторинг
        self.proxy_monitor = ProxyMonitor()

        # Статистика
        self.stealth_used = 0
        self.behavior_imitated = 0
        self.pages_processed = 0
        self.start_time = None
        self.total_pages = 0
        self.failed_pages = 0
        self.filtered_items = 0

    def _apply_filters(self, item: RozetkaItem) -> bool:
        """
        Застосовує фільтри до товару

        Returns:
            bool: True якщо товар проходить всі фільтри
        """
        # Фільтр по знижці
        if self.discount_only and not item.has_discount:
            self.filtered_items += 1
            return False

        # Фільтр по мінімальній ціні
        if self.min_price and item.price_value < self.min_price:
            self.filtered_items += 1
            return False

        # Фільтр по максимальній ціні
        if self.max_price and item.price_value > self.max_price:
            self.filtered_items += 1
            return False

        # Фільтр по рейтингу
        if self.min_rating and (item.rating is None or item.rating < self.min_rating):
            self.filtered_items += 1
            return False

        return True

    async def _simulate_human_behavior(self, page):
        """Імітація поведінки людини"""
        try:
            # Випадкова прокрутка
            scroll_amount = random.randint(200, 500)
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(random.uniform(0.5, 1.5))

            # Випадковий рух миші
            viewport = page.viewport_size
            if viewport:
                x = random.randint(100, viewport['width'] - 100)
                y = random.randint(100, viewport['height'] - 100)
                await page.mouse.move(x, y, steps=random.randint(10, 20))

                # Іноді додаткові рухи
                if random.random() < 0.3:
                    for _ in range(random.randint(2, 4)):
                        new_x = x + random.randint(-50, 50)
                        new_y = y + random.randint(-50, 50)
                        await page.mouse.move(new_x, new_y, steps=5)
                        await asyncio.sleep(random.uniform(0.1, 0.2))

            logger.debug(f"[{self.site_name}] 🖱️ Імітація поведінки людини")
            return True
        except Exception as e:
            logger.debug(f"[{self.site_name}] Не вдалося імітувати поведінку: {e}")
            return False

    async def scrape_page(self, url: str, index: int, proxy_override: dict = None) -> str | None:
        """
        Завантажує одну сторінку з контролем навантаження через Semaphore
        """
        if len(self.results) >= self.max_items:
            logger.info(f"[{self.site_name}] 🎯 Досягнуто ліміту в {self.max_items} товарів")
            return None

        async with self.page_semaphore:
            logger.debug(
                f"[{self.site_name}] 🔑 Отримано доступ до сторінки #{index} "
                f"(активних: {self.max_concurrent - self.page_semaphore._value}/{self.max_concurrent})"
            )
            return await self._scrape_page_internal(url, index, proxy_override)

    async def _scrape_page_internal(self, url: str, index: int, proxy_override: dict = None) -> str | None:
        """Внутрішній метод для скрапінгу сторінки"""

        # Перевірка проксі
        if not VALID_PROXY_LIST:
            logger.critical(f"[{self.site_name}] 🔴 [Сторінка #{index}] НЕМАЄ ПРОКСІ!")
            return "ERROR_SIGNAL"

        # Вибір проксі
        safe_index = (index - 1) % len(VALID_PROXY_LIST)
        current_proxy = proxy_override or VALID_PROXY_LIST[safe_index]
        logger.info(f"[{self.site_name}] 🔌 [Сторінка #{index}] Проксі: {current_proxy['server']}")

        # Випадковий User-Agent
        current_ua = self.client.get_random_ua()

        # Створення контексту
        try:
            if self.stealth:
                context = await self.stealth.create_context(self.client.browser)
                logger.debug(f"[{self.site_name}] 🕵️ Контекст створено через стелс")
            else:
                context = await self.client.browser.new_context(
                    user_agent=current_ua,
                    proxy=current_proxy,
                    viewport={
                        "width": random.choice([1366, 1440, 1536, 1920]),
                        "height": random.choice([768, 900, 864, 1080])
                    }
                )
        except Exception as e:
            logger.error(f"[{self.site_name}] ❌ Помилка створення контексту: {e}")
            return "ERROR_SIGNAL"

        page = await context.new_page()

        # Застосування стелсу
        if self.stealth:
            try:
                await self.stealth.apply_to_page(page)
                self.stealth_used += 1
                logger.debug(f"[{self.site_name}] 🕵️ Додаткові маскування застосовано")
            except Exception as e:
                logger.warning(f"[{self.site_name}] ⚠️ Помилка стелсу: {e}")

        try:
            logger.info(f"[{self.site_name}] 🚀 [Сторінка #{index}] Завантаження: {url}")

            # Імітація поведінки людини
            if random.random() < 0.7:
                if await self._simulate_human_behavior(page):
                    self.behavior_imitated += 1

            # Завантажуємо сторінку
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # Парсимо товари
            new_items = await self.parser.parse_listings(page)
            next_page_url = await self.parser.get_next_page(page)

            # Фільтруємо та оновлюємо результати
            added_count = 0
            for item in new_items:
                if self._apply_filters(item):
                    async with self._lock:
                        if len(self.results) < self.max_items:
                            self.results.append(item)
                            added_count += 1

                            # Зберігаємо в реальному часі
                            Exporter.append_to_csv(item, filename=f"{self.site_name.lower()}_live.csv")
                # else: вже пораховано в _apply_filters

            # Оновлюємо статистику
            count = len(self.results)

            if added_count > 0:
                logger.success(
                    f"[{self.site_name}] ✅ [Сторінка #{index}] +{added_count} товарів "
                    f"(Всього: {count}/{self.max_items})"
                )
                self.total_pages += 1
            else:
                logger.info(
                    f"[{self.site_name}] ℹ️ [Сторінка #{index}] Нових товарів не знайдено "
                    f"(Всього: {count}/{self.max_items})"
                )

            # Зберігаємо прогрес
            if next_page_url and next_page_url != url:  # Не зберігаємо для infinite scroll
                self.state_manager.save_checkpoint(next_page_url, count)

            # Випадкова затримка
            delay = random.uniform(BASE_DELAY[0], BASE_DELAY[1])
            logger.debug(f"[{self.site_name}] 💤 Затримка {delay:.1f}с перед наступною сторінкою")
            await asyncio.sleep(delay)

            return next_page_url

        except Exception as e:
            logger.error(f"[{self.site_name}] ❌ Помилка на сторінці #{index}: {e}")
            self.failed_pages += 1
            return "ERROR_SIGNAL"
        finally:
            await context.close()
            self.pages_processed += 1

    async def scrape_page_with_retry(self, url: str, index: int, max_retries: int = 3):
        """Спроба завантажити сторінку з ротацією проксі"""

        if not self.proxy_monitor or not self.proxy_monitor.check_proxy_health():
            logger.critical(f"[{self.site_name}] 🔴 ВСІ ПРОКСІ МЕРТВІ!")
            return "ERROR_SIGNAL"

        for attempt in range(max_retries):
            start_time = time.time()
            current_proxy = None

            try:
                if not VALID_PROXY_LIST:
                    logger.critical(f"[{self.site_name}] 🔴 ПРОКСІ ЗАКІНЧИЛИСЬ!")
                    if self.proxy_monitor:
                        self.proxy_monitor.print_stats()
                    return "ERROR_SIGNAL"

                proxy_index = (index + attempt) % len(VALID_PROXY_LIST)
                current_proxy = VALID_PROXY_LIST[proxy_index]

                logger.info(f"[{self.site_name}] 🔄 Спроба {attempt + 1}/{max_retries} для сторінки #{index}")
                logger.info(f"[{self.site_name}] 🔌 Проксі: {current_proxy['server']}")

                result = await asyncio.wait_for(
                    self.scrape_page(url, index, current_proxy),
                    timeout=60
                )

                response_time = time.time() - start_time
                if self.proxy_monitor and current_proxy:
                    self.proxy_monitor.log_proxy_usage(
                        current_proxy['server'],
                        success=True,
                        response_time=response_time
                    )

                if result != "ERROR_SIGNAL":
                    if attempt > 0:
                        logger.success(
                            f"[{self.site_name}] ✅ Сторінка #{index} завантажена з {attempt + 1} спроби"
                        )
                    return result

            except asyncio.TimeoutError:
                logger.warning(f"[{self.site_name}] ⏰ Таймаут на сторінці #{index}")
                if self.proxy_monitor and current_proxy:
                    self.proxy_monitor.log_proxy_usage(current_proxy['server'], success=False)

            except Exception as e:
                if self.proxy_monitor and current_proxy:
                    self.proxy_monitor.log_proxy_usage(current_proxy['server'], success=False)

                if "ERR_PROXY_CONNECTION_FAILED" in str(e) and current_proxy:
                    logger.warning(f"[{self.site_name}] 🔴 Проксі не відповідає: {current_proxy['server']}")
                    if VALID_PROXY_LIST and current_proxy in VALID_PROXY_LIST:
                        VALID_PROXY_LIST.remove(current_proxy)
                        logger.warning(
                            f"[{self.site_name}] 🗑️ Видалено мертве проксі. "
                            f"Залишилось: {len(VALID_PROXY_LIST)}"
                        )

                        if not VALID_PROXY_LIST and self.proxy_monitor:
                            logger.critical(f"[{self.site_name}] 🔴 ВСІ ПРОКСІ ВИДАЛЕНО!")
                            self.proxy_monitor.print_stats()
                            return "ERROR_SIGNAL"
                else:
                    logger.warning(f"[{self.site_name}] ⚠️ Помилка: {str(e)[:100]}")

            wait_time = 2 ** attempt
            logger.info(f"[{self.site_name}] 💤 Очікування {wait_time}с")
            await asyncio.sleep(wait_time)

        logger.error(f"[{self.site_name}] ❌ Всі {max_retries} спроб для сторінки #{index} не вдалися")
        return "ERROR_SIGNAL"

    async def run(self, start_url: str):
        """Основний метод запуску"""
        self.start_time = time.time()
        await self.client.start()

        checkpoint_data = self.state_manager.load_checkpoint()
        current_url = start_url

        if isinstance(checkpoint_data, dict):
            current_url = checkpoint_data.get("last_url", start_url)
        elif isinstance(checkpoint_data, str):
            current_url = checkpoint_data

        if current_url != start_url:
            logger.info(f"[{self.site_name}] ♻️ Відновлення з чекпоїнта: {current_url}")

        page_index = 1
        start_time = time.time()
        last_url = None

        try:
            while current_url and len(self.results) < self.max_items:
                # Запобігаємо зацикленню
                if current_url == last_url:
                    logger.warning(f"[{self.site_name}] ⚠️ Виявлено зациклення, перериваю")
                    break

                last_url = current_url
                result = await self.scrape_page_with_retry(current_url, page_index)

                if result == "ERROR_SIGNAL":
                    logger.warning(f"[{self.site_name}] ⚠️ Переривання. Чекпоїнт: {current_url}")
                    break

                current_url = result
                page_index += 1

            # Фінальна статистика
            elapsed_time = time.time() - start_time
            logger.info("=" * 70)
            logger.info(f"📊 СТАТИСТИКА ДЛЯ {self.site_name}")
            logger.info("=" * 70)
            logger.info(f"📄 Сторінок успішно: {self.total_pages}")
            logger.info(f"❌ Сторінок з помилками: {self.failed_pages}")
            logger.info(f"📦 Товарів зібрано: {len(self.results)}")
            logger.info(f"🔍 Відфільтровано: {self.filtered_items}")
            logger.info(f"⏱️ Час: {elapsed_time:.1f} сек")

            if elapsed_time > 0:
                speed = len(self.results) / elapsed_time
                logger.info(f"⚡ Швидкість: {speed:.2f} товарів/сек")

            logger.info(f"🕵️ Стелс: {self.stealth_used} разів")
            logger.info(f"🖱️ Імітацій: {self.behavior_imitated} разів")
            logger.info("=" * 70)

            if self.proxy_monitor:
                self.proxy_monitor.print_stats()

            # Очищаємо чекпоїнт при успішному завершенні
            if len(self.results) >= self.max_items or current_url is None:
                self.state_manager.clear_checkpoint()

            return self.results

        except Exception as e:
            logger.critical(f"[{self.site_name}] 💥 Критична помилка: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self.results
        finally:
            await self.client.stop()