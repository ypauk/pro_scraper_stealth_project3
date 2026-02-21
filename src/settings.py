# src/settings.py
import yaml
from pathlib import Path
from loguru import logger
import sys

# ============================================
# БАЗОВІ НАЛАШТУВАННЯ
# ============================================

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = DATA_DIR / "logs"
CONFIG_PATH = BASE_DIR / "config.yaml"

# Створюємо необхідні папки
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


# ============================================
# ЗАВАНТАЖЕННЯ КОНФІГУРАЦІЇ
# ============================================

def load_config():
    """Завантажує конфігурацію з YAML файлу"""
    if not CONFIG_PATH.exists():
        logger.warning(f"⚠️ Файл {CONFIG_PATH} не знайдено!")
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


config = load_config()

# ============================================
# НАЛАШТУВАННЯ ДЛЯ ROZETKA
# ============================================

# Базові URL для Rozetka
ROZETKA_BASE_URL = "https://rozetka.com.ua/ua"

# Категорії товарів
CATEGORIES = {
    'notebooks': 'c80004',  # Ноутбуки
    'smartphones': 'c80003',  # Смартфони
    'tv': 'c80001',  # Телевізори
    'tablets': 'c130309',  # Планшети
    'headphones': 'c80021',  # Навушники
    'laptops': 'c80004',  # Аліас для notebooks
    'phones': 'c80003'  # Аліас для smartphones
}

# За замовчуванням
DEFAULT_CATEGORY = 'notebooks'
DEFAULT_QUERY = ''

# Кількість елементів для збору
MAX_ITEMS = config.get("scraping", {}).get("max_items", 200)

# Затримки між запитами (секунди)
delays_cfg = config.get("delays", {"min": 2, "max": 5})
BASE_DELAY = (delays_cfg["min"], delays_cfg["max"])

# Налаштування браузера
browser_cfg = config.get("browser", {})
HEADLESS = browser_cfg.get("headless", False)
TIMEOUT = browser_cfg.get("timeout", 60000)  # 60 секунд

# User Agents для маскування
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0"
]


# ============================================
# КЛАС ПОМИЛКИ ДЛЯ ПРОКСІ
# ============================================

class NoProxyAvailableError(Exception):
    """Виняток, коли немає доступних проксі"""
    pass


# ============================================
# ВАЛІДАЦІЯ ПРОКСІ
# ============================================

def validate_proxy(proxy):
    """Перевіряє чи проксі має правильний формат"""
    if not isinstance(proxy, dict):
        return False
    if "server" not in proxy:
        return False
    if not proxy["server"].startswith(("http://", "https://")):
        return False
    try:
        address = proxy["server"].split("://")[1]
        if ":" not in address:
            return False
        port = int(address.split(":")[1])
        if not (1 <= port <= 65535):
            return False
    except:
        return False

    if "username" in proxy and not isinstance(proxy["username"], str):
        return False
    if "password" in proxy and not isinstance(proxy["password"], str):
        return False

    return True


# ============================================
# АВТОМАТИЧНЕ ЗАВАНТАЖЕННЯ ПРОКСІ
# ============================================

from src.proxy_fetcher import WebshareProxyFetcher

logger.info("🔄 Завантаження проксі з Webshare API...")

try:
    fetcher = WebshareProxyFetcher()
    auto_proxies = fetcher.fetch_all_proxies()

    if auto_proxies:
        RAW_PROXY_LIST = auto_proxies
        logger.success(f"✅ Завантажено {len(auto_proxies)} проксі")
    else:
        logger.warning("⚠️ API не повернув проксі, використовую резервний список")
        RAW_PROXY_LIST = config.get("proxies", [])
except Exception as e:
    logger.warning(f"⚠️ Помилка завантаження проксі: {e}")
    RAW_PROXY_LIST = config.get("proxies", [])

# ============================================
# ФІЛЬТРАЦІЯ ПРОКСІ
# ============================================

VALID_PROXY_LIST = []
INVALID_PROXY_LIST = []

for proxy in RAW_PROXY_LIST:
    if validate_proxy(proxy):
        VALID_PROXY_LIST.append(proxy)
    else:
        INVALID_PROXY_LIST.append(proxy)


# ============================================
# ПЕРЕВІРКА НАЯВНОСТІ ПРОКСІ
# ============================================

def validate_proxy_list():
    """Жорстка перевірка наявності проксі"""
    if not VALID_PROXY_LIST:
        logger.critical("=" * 60)
        logger.critical("🔴 КРИТИЧНА ПОМИЛКА: НЕМАЄ ДОСТУПНИХ ПРОКСІ!")
        logger.critical("=" * 60)
        logger.critical("🛡️ ЗАХИСТ: Програма зупинена - робота без проксі ЗАБОРОНЕНА!")
        logger.critical("=" * 60)
        raise NoProxyAvailableError("Немає доступних проксі для роботи")
    return VALID_PROXY_LIST


# Виконуємо перевірку
try:
    VALID_PROXY_LIST = validate_proxy_list()
    logger.info(f"📊 Доступно {len(VALID_PROXY_LIST)} робочих проксі")
except NoProxyAvailableError:
    sys.exit(1)

# Налаштування ротації
USE_PROXY_ROTATION = len(VALID_PROXY_LIST) > 1
if USE_PROXY_ROTATION:
    logger.info(f"🔄 Увімкнено ротацію {len(VALID_PROXY_LIST)} проксі")


# ============================================
# ФУНКЦІЯ ДЛЯ ФОРМУВАННЯ URL ROZETKA
# ============================================

def get_rozetka_url(category: str = None, query: str = None) -> str:
    """
    Формує URL для Rozetka залежно від категорії або пошукового запиту

    Args:
        category: Категорія товару (notebooks, smartphones, tv, tablets, headphones)
        query: Пошуковий запит

    Returns:
        str: URL для скрапінгу
    """
    if query:
        # Пошук по всьому сайту
        return f"{ROZETKA_BASE_URL}/search/?text={query}"
    else:
        # Категорія товарів
        cat = category or DEFAULT_CATEGORY
        cat_id = CATEGORIES.get(cat.lower(), CATEGORIES[DEFAULT_CATEGORY])
        return f"{ROZETKA_BASE_URL}/{cat}/{cat_id}/"


# ============================================
# ФІНАЛЬНІ НАЛАШТУВАННЯ
# ============================================

logger.info("=" * 50)
logger.info(f"🚀 Проєкт налаштовано для Rozetka")
logger.info(f"📌 Базовий URL: {ROZETKA_BASE_URL}")
logger.info(f"📊 Макс. товарів: {MAX_ITEMS}")
logger.info(f"🔌 Проксі: {len(VALID_PROXY_LIST)} шт.")
logger.info(f"🔄 Ротація: {'Так' if USE_PROXY_ROTATION else 'Ні'}")
logger.info("=" * 50)