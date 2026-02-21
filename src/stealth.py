# src/stealth.py - ФІНАЛЬНА ВЕРСІЯ З ЕКСПОРТОМ
"""
Модуль ручного стелсу для Playwright з підтримкою конфігурації
"""

import random
import asyncio
from loguru import logger
from src.stealth_config import StealthConfig, USA_CONFIG, UKRAINE_CONFIG, GOOGLE_CONFIG, LINKEDIN_CONFIG


class ManualStealth:
    """
    Клас для ручного маскування автоматизації з конфігом
    """

    def __init__(self, config: StealthConfig):
        self.config = config
        logger.debug(f"📋 Конфіг: {config.timezone}")

    async def create_context(self, browser):
        """Створює контекст з налаштуваннями"""
        context = await browser.new_context(
            locale=self.config.languages[0],
            timezone_id=self.config.timezone,
            viewport={
                'width': self.config.screen_size[0],
                'height': self.config.screen_size[1]
            },
            extra_http_headers={
                'Accept-Language': ', '.join(self.config.languages),
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            }
        )
        logger.debug(f"📦 Контекст створено з locale: {self.config.languages[0]}")
        return context

    async def apply_to_page(self, page):
        """Додаткові маскування"""
        await page.add_init_script("""
            // WebGL маскування
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter.call(this, parameter);
            };

            // Ховаємо webdriver
            Object.defineProperty(Object.getPrototypeOf(navigator), 'webdriver', {
                get: () => undefined
            });
        """)
        logger.debug("🕵️ Додаткові маскування застосовано")

    async def check_languages(self, page):
        """Перевіряє встановлені мови"""
        langs = await page.evaluate("navigator.languages")
        lang = await page.evaluate("navigator.language")
        timezone = await page.evaluate("Intl.DateTimeFormat().resolvedOptions().timeZone")

        logger.info(f"🔍 navigator.languages: {langs}")
        logger.info(f"🔍 navigator.language: {lang}")
        logger.info(f"🔍 Часовий пояс: {timezone}")

        return langs


# Фабрика для створення стелсу під сайт
def get_stealth_for_site(site: str) -> ManualStealth:
    """Повертає налаштований стелс для конкретного сайту"""
    configs = {
        'amazon': USA_CONFIG,
        'ebay': USA_CONFIG,
        'google': GOOGLE_CONFIG,
        'linkedin': LINKEDIN_CONFIG,
        'ukraine': UKRAINE_CONFIG,
    }
    config = configs.get(site, USA_CONFIG)
    logger.debug(f"🎯 Створено стелс для сайту: {site}")
    return ManualStealth(config)


# ЕКСПОРТУЄМО ВСЕ, ЩО ПОТРІБНО
__all__ = ['ManualStealth', 'get_stealth_for_site']