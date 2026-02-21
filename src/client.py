# src/client.py
import os
import random
from playwright.async_api import async_playwright
# Видалено AUTH_FILE з імпорту
from src.settings import HEADLESS, USER_AGENTS, TIMEOUT, VALID_PROXY_LIST
from loguru import logger
from fake_useragent import UserAgent


class BrowserClient:
    def __init__(self, proxy: dict = None):
        self.playwright = None
        self.browser = None

        # ===== ЖОРСТКА ПЕРЕВІРКА ПРОКСІ =====
        if proxy is None:
            if VALID_PROXY_LIST:
                self.proxy = VALID_PROXY_LIST[0]
                logger.info(f"🔌 Автоматично вибрано проксі: {self.proxy['server']}")
            else:
                logger.critical("=" * 60)
                logger.critical("🔴 КРИТИЧНА ПОМИЛКА: СПРОБА СТВОРЕННЯ КЛІЄНТА БЕЗ ПРОКСІ!")
                logger.critical("=" * 60)
                logger.critical("🛡️ ЗАХИСТ: Програма буде зупинена")
                logger.critical("💡 Рішення: Додайте проксі в config.yaml або перевірте .env файл")
                logger.critical("=" * 60)
                raise Exception("BrowserClient не може бути створений без проксі")
        else:
            self.proxy = proxy

        # Ініціалізуємо генератор випадкових User-Agents
        try:
            self.ua_generator = UserAgent()
            logger.success("✅ fake-useragent успішно ініціалізовано")
        except Exception as e:
            logger.warning(f"⚠️ Не вдалося ініціалізувати fake-useragent: {e}. Буде використано ручний список.")
            self.ua_generator = None

        # Логуємо статус проксі при ініціалізації
        if self.proxy:
            masked_proxy = self._mask_proxy_data(self.proxy)
            logger.info(f"🔌 Клієнт ініціалізовано з проксі: {masked_proxy}")

            proxy_server = self.proxy.get('server', '')
            if 'http://' in proxy_server:
                logger.debug("📡 Тип проксі: HTTP")
            elif 'https://' in proxy_server:
                logger.debug("📡 Тип проксі: HTTPS")
            elif 'socks' in proxy_server.lower():
                logger.debug("📡 Тип проксі: SOCKS")

            if 'username' in self.proxy and 'password' in self.proxy:
                logger.debug("🔐 Проксі вимагає автентифікацію (логін/пароль)")
        else:
            logger.critical("🔴 КРИТИЧНО: КЛІЄНТ СТВОРЕНО БЕЗ ПРОКСІ!")
            raise Exception("Клієнт не може працювати без проксі")

    def _mask_proxy_data(self, proxy: dict) -> dict:
        """Маскує чутливі дані проксі для безпечного логування"""
        masked = proxy.copy()
        if 'username' in masked:
            username = masked['username']
            masked['username'] = f"{username[:3]}***" if len(username) > 3 else "***"
        if 'password' in masked:
            masked['password'] = '********'
        return masked

    def get_random_ua(self) -> str:
        """Метод для отримання надійного User-Agent"""
        if self.ua_generator:
            try:
                ua = self.ua_generator.random
                ua_short = ua[:50] + "..." if len(ua) > 50 else ua
                logger.info(f"🌐 Використано динамічний User-Agent: {ua_short}")
                return ua
            except Exception as e:
                logger.warning(f"📡 Збій мережевої бази User-Agents: {e}")

        fallback_ua = random.choice(USER_AGENTS)
        logger.info(f"💾 Використано User-Agent з ручного списку: {fallback_ua[:50]}...")
        return fallback_ua

    async def start(self):
        """Запуск браузера з обов'язковим проксі"""
        self.playwright = await async_playwright().start()
        logger.debug("🎭 Playwright запущено")

        # ===== ФІНАЛЬНА ПЕРЕВІРКА ПЕРЕД ЗАПУСКОМ =====
        if not self.proxy:
            logger.critical("🔴 СПРОБА ЗАПУСКУ БРАУЗЕРА БЕЗ ПРОКСІ!")
            logger.critical("🛡️ ЗАХИСТ: Запуск заборонено")
            logger.debug(f"VALID_PROXY_LIST: {VALID_PROXY_LIST}")
            logger.debug(f"self.proxy: {self.proxy}")
            raise Exception("Запуск браузера без проксі заборонено!")

        launch_options = {
            "headless": HEADLESS,
            "proxy": self._mask_proxy_data(self.proxy) if self.proxy else None
        }
        logger.info(f"🔌 ЗАПУСК З ПРОКСІ: {self._mask_proxy_data(self.proxy)['server']}")
        logger.debug(f"⚙️ Параметри запуску браузера: {launch_options}")

        try:
            self.browser = await self.playwright.chromium.launch(
                headless=HEADLESS,
                proxy=self.proxy if self.proxy else None
            )

            browser_version = self.browser.version
            logger.info(f"🚀 Браузер Chromium v{browser_version} запущено")
            logger.success(f"🔌 Проксі підключено: {self._mask_proxy_data(self.proxy)['server']}")

        except Exception as e:
            logger.error(f"❌ Помилка запуску браузера: {e}")
            if self.proxy:
                logger.error(f"🔴 Можлива проблема з проксі: {self._mask_proxy_data(self.proxy)['server']}")
                logger.error("💡 Перевір: 1) Чи працює проксі? 2) Чи правильний формат?")
            raise e

    async def stop(self):
        """Повне закриття браузера"""
        try:
            if self.browser:
                await self.browser.close()
                logger.debug("🛑 Браузер закрито")
            if self.playwright:
                await self.playwright.stop()
                logger.debug("🎭 Playwright зупинено")
            logger.success("🛑 Асинхронний клієнт повністю зупинено.")
        except Exception as e:
            logger.error(f"❌ Помилка при зупинці клієнта: {e}")

    async def check_proxy_health(self) -> bool:
        """Перевіряє працездатність проксі через httpbin"""
        if not self.proxy:
            logger.critical("🔴 НЕМАЄ ПРОКСІ ДЛЯ ПЕРЕВІРКИ!")
            return False

        try:
            context = await self.browser.new_context()
            page = await context.new_page()

            logger.info(f"🩺 Перевірка працездатності проксі: {self._mask_proxy_data(self.proxy)['server']}")
            await page.goto("https://httpbin.org/ip", timeout=10000)
            content = await page.text_content("body")

            await context.close()
            logger.success(f"✅ Проксі працює! Відповідь: {content}")
            return True

        except Exception as e:
            logger.error(f"❌ Проксі не працює: {e}")
            return False