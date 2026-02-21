# src/stealth_config.py
"""
Конфігурація стелсу для різних сайтів
"""

from dataclasses import dataclass
from typing import List, Optional
import random


@dataclass
class StealthConfig:
    """
    Клас для налаштування параметрів стелсу
    """

    # Часовий пояс
    timezone: str = 'Europe/Kiev'

    # Мови браузера
    languages: List[str] = None

    # Розмір екрану
    screen_size: tuple = (1920, 1080)

    # WebGL налаштування
    webgl_vendor: str = 'Intel Inc.'
    webgl_renderer: str = 'Intel Iris OpenGL Engine'

    def __post_init__(self):
        if self.languages is None:
            self.languages = ['uk-UA', 'uk', 'en-US', 'en', 'ru']


# === КОНФІГИ ДЛЯ РІЗНИХ САЙТІВ ===

UKRAINE_CONFIG = StealthConfig(
    timezone='Europe/Kiev',
    languages=['uk-UA', 'uk', 'ru', 'en-US', 'en'],
    screen_size=(1366, 768)
)

USA_CONFIG = StealthConfig(
    timezone='America/New_York',
    languages=['en-US', 'en'],
    screen_size=(1920, 1080)
)

GOOGLE_CONFIG = StealthConfig(
    timezone='America/Los_Angeles',
    languages=['en-US', 'en'],
    screen_size=(1536, 864)
)

LINKEDIN_CONFIG = StealthConfig(
    timezone='America/New_York',
    languages=['en-US', 'en'],
    screen_size=(1920, 1080)
)

TEST_CONFIG = StealthConfig(
    timezone='Europe/Kiev',
    languages=['uk-UA', 'uk', 'en-US', 'en'],
    screen_size=(1920, 1080)
)