"""
Утиліти для роботи з проксі
Тестування, валідація, ротація та моніторинг
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from loguru import logger

# Для синхронних тестів
import requests
from concurrent.futures import ThreadPoolExecutor


@dataclass
class ProxyTestResult:
    """Результат тестування проксі"""
    server: str
    is_working: bool
    response_time: float
    ip: str = None
    country: str = None
    error: str = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class ProxyTester:
    """
    Клас для тестування працездатності проксі
    Підтримує як Playwright так і requests
    """

    def __init__(self, timeout: int = 10):
        """
        Args:
            timeout: Таймаут в секундах для кожного тесту
        """
        self.timeout = timeout
        self.test_urls = [
            "http://httpbin.org/ip",
            "http://httpbin.org/get",
            "http://api.ipify.org?format=json"
        ]

    async def test_with_playwright(self, proxy: dict) -> ProxyTestResult:
        """
        Тестує проксі через Playwright (найточніше, бо емулює браузер)

        Args:
            proxy: Словник з конфігом проксі {'server': 'http://ip:port', ...}

        Returns:
            ProxyTestResult з результатами тесту
        """
        server = proxy.get('server', 'unknown')
        start_time = time.time()

        try:
            logger.debug(f"🧪 Тестуємо проксі (Playwright): {server}")

            async with async_playwright() as p:
                # Запускаємо браузер з проксі
                browser = await p.chromium.launch(
                    headless=True,  # Не показуємо вікно
                    proxy=proxy
                )

                # Створюємо контекст з таймаутом
                context = await browser.new_context()
                page = await context.new_page()

                # Тест 1: Перевірка з'єднання та отримання IP
                try:
                    await page.goto("http://httpbin.org/ip",
                                    timeout=self.timeout * 1000)
                    content = await page.text_content("body")

                    # Парсимо JSON відповідь
                    import json
                    ip_data = json.loads(content)
                    current_ip = ip_data.get('origin', 'unknown')

                except PlaywrightTimeoutError:
                    await browser.close()
                    return ProxyTestResult(
                        server=server,
                        is_working=False,
                        response_time=time.time() - start_time,
                        error="Timeout - проксі не відповідає"
                    )

                # Тест 2: Перевірка швидкості
                speed_start = time.time()
                await page.goto("http://httpbin.org/delay/1",
                                timeout=self.timeout * 1000)
                speed_end = time.time()
                response_time = speed_end - speed_start

                # Закриваємо браузер
                await browser.close()

                # Тест 3: Спроба визначити країну (опціонально)
                country = await self._get_country_from_ip(current_ip)

                return ProxyTestResult(
                    server=server,
                    is_working=True,
                    response_time=response_time,
                    ip=current_ip,
                    country=country
                )

        except Exception as e:
            error_msg = str(e)
            logger.debug(f"❌ Помилка проксі {server}: {error_msg[:100]}")

            return ProxyTestResult(
                server=server,
                is_working=False,
                response_time=time.time() - start_time,
                error=error_msg[:200]
            )

    def test_with_requests(self, proxy: dict) -> ProxyTestResult:
        """
        Швидке тестування проксі через requests (без браузера)
        Використовуй для попередньої фільтрації

        Args:
            proxy: Словник з конфігом проксі
        """
        server = proxy.get('server', 'unknown')
        start_time = time.time()

        try:
            # Конвертуємо формат Playwright -> requests
            proxies = {
                "http": server,
                "https": server
            }

            # Додаємо автентифікацію якщо є
            auth = None
            if "username" in proxy and "password" in proxy:
                from requests.auth import HTTPProxyAuth
                auth = HTTPProxyAuth(proxy["username"], proxy["password"])

            response = requests.get(
                "http://httpbin.org/ip",
                proxies=proxies,
                auth=auth,
                timeout=self.timeout
            )

            response_time = time.time() - start_time
            ip_data = response.json()
            current_ip = ip_data.get('origin', 'unknown')

            return ProxyTestResult(
                server=server,
                is_working=True,
                response_time=response_time,
                ip=current_ip
            )

        except Exception as e:
            return ProxyTestResult(
                server=server,
                is_working=False,
                response_time=time.time() - start_time,
                error=str(e)[:200]
            )

    async def _get_country_from_ip(self, ip: str) -> str:
        """Визначає країну за IP (опціонально)"""
        try:
            response = requests.get(f"http://ip-api.com/json/{ip}", timeout=2)
            data = response.json()
            return data.get('country', 'unknown')
        except:
            return 'unknown'

    async def test_batch(self, proxy_list: List[dict],
                         max_workers: int = 5,
                         use_playwright: bool = False) -> List[ProxyTestResult]:
        """
        Тестує список проксі паралельно

        Args:
            proxy_list: Список проксі для тестування
            max_workers: Кількість одночасних тестів
            use_playwright: Використовувати Playwright (повільніше, але точніше)

        Returns:
            List[ProxyTestResult]: Результати тестування
        """
        logger.info(f"🧪 Початок тестування {len(proxy_list)} проксі...")

        results = []

        if use_playwright:
            # Асинхронне тестування з Playwright
            semaphore = asyncio.Semaphore(max_workers)

            async def test_with_limit(proxy):
                async with semaphore:
                    return await self.test_with_playwright(proxy)

            tasks = [test_with_limit(proxy) for proxy in proxy_list]
            results = await asyncio.gather(*tasks)
        else:
            # Синхронне тестування з requests (швидше)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = list(executor.map(
                    lambda p: self.test_with_requests(p),
                    proxy_list
                ))

        # Статистика
        working = [r for r in results if r.is_working]
        logger.success(f"✅ Знайдено {len(working)}/{len(proxy_list)} робочих проксі")

        return results


class ProxyManager:
    """
    Менеджер проксі з автоматичною ротацією та чорним списком
    """

    def __init__(self, proxy_list: List[dict] = None):
        """
        Args:
            proxy_list: Початковий список проксі
        """
        self.all_proxies = proxy_list or []
        self.working_proxies = []
        self.blacklist = []  # Проксі, які не працюють
        self.current_index = 0
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "rotations": 0
        }

    def add_proxy(self, proxy: dict):
        """Додає проксі до пулу"""
        self.all_proxies.append(proxy)

    def remove_proxy(self, proxy: dict):
        """Видаляє проксі з пулу"""
        if proxy in self.all_proxies:
            self.all_proxies.remove(proxy)
        if proxy in self.working_proxies:
            self.working_proxies.remove(proxy)

    def mark_failed(self, proxy: dict):
        """Позначає проксі як несправне і додає в чорний список"""
        self.stats["failed_requests"] += 1
        self.remove_proxy(proxy)
        if proxy not in self.blacklist:
            self.blacklist.append(proxy)
            logger.warning(f"⛔ Проксі додано до чорного списку: {proxy.get('server')}")

    def mark_success(self, proxy: dict):
        """Позначає успішний запит"""
        self.stats["successful_requests"] += 1

    def get_next_proxy(self) -> Optional[dict]:
        """
        Повертає наступне проксі з ротацією (round-robin)

        Returns:
            dict: Конфіг проксі або None якщо немає робочих проксі
        """
        if not self.working_proxies:
            # Якщо немає підтверджено робочих, використовуємо всі
            available = self.all_proxies
        else:
            available = self.working_proxies

        if not available:
            logger.error("❌ Немає доступних проксі!")
            return None

        self.current_index = (self.current_index + 1) % len(available)
        proxy = available[self.current_index]
        self.stats["rotations"] += 1
        self.stats["total_requests"] += 1

        logger.debug(f"🔄 Ротація: використовується проксі #{self.current_index + 1}")
        return proxy.copy()  # Повертаємо копію

    async def verify_and_update(self, tester: ProxyTester):
        """
        Перевіряє всі проксі і оновлює список робочих

        Args:
            tester: Екземпляр ProxyTester
        """
        if not self.all_proxies:
            return

        logger.info("🔍 Запуск перевірки всіх проксі...")
        results = await tester.test_batch(self.all_proxies, use_playwright=True)

        self.working_proxies = [
            r.server for r in results if r.is_working
        ]

        logger.info(f"📊 Статистика проксі: {len(self.working_proxies)} робочих, "
                    f"{len(self.blacklist)} в чорному списку")

    def get_stats(self) -> dict:
        """Повертає статистику використання проксі"""
        return {
            **self.stats,
            "total_proxies": len(self.all_proxies),
            "working_proxies": len(self.working_proxies),
            "blacklisted": len(self.blacklist),
            "success_rate": self.stats["successful_requests"] / max(self.stats["total_requests"], 1)
        }


# Функція для швидкого пошуку робочих проксі
async def find_working_proxies(proxy_list: List[dict],
                               min_speed: float = 5.0) -> List[dict]:
    """
    Швидко знаходить робочі проксі зі списку

    Args:
        proxy_list: Список проксі для перевірки
        min_speed: Мінімальна швидкість в секундах

    Returns:
        List[dict]: Список робочих проксі
    """
    tester = ProxyTester(timeout=5)

    # Спочатку швидка перевірка через requests
    logger.info("🚀 Швидке тестування проксі...")
    quick_results = tester.test_batch(proxy_list, use_playwright=False)

    # Фільтруємо тільки робочі
    working_quick = []
    for result in quick_results:
        if isinstance(result, ProxyTestResult) and result.is_working:
            # Знаходимо оригінальний проксі
            for proxy in proxy_list:
                if proxy.get('server') == result.server:
                    working_quick.append(proxy)
                    break

    logger.info(f"⚡ Знайдено {len(working_quick)} потенційно робочих проксі")

    # Перевіряємо їх через Playwright (точніше)
    if working_quick:
        logger.info("🎭 Фінальна перевірка через Playwright...")
        final_results = await tester.test_batch(working_quick, use_playwright=True)

        working_final = []
        for result in final_results:
            if result.is_working and result.response_time < min_speed:
                for proxy in working_quick:
                    if proxy.get('server') == result.server:
                        working_final.append(proxy)
                        logger.success(f"✅ {result.server} - {result.response_time:.2f}с - {result.ip}")
                        break

        return working_final

    return []


# Функція для збереження робочих проксі в файл
def save_working_proxies(proxies: List[dict], filename: str = "working_proxies.json"):
    """
    Зберігає список робочих проксі в JSON файл

    Args:
        proxies: Список проксі
        filename: Ім'я файлу
    """
    filepath = Path("data") / filename
    filepath.parent.mkdir(exist_ok=True)

    # Видаляємо паролі перед збереженням!
    safe_proxies = []
    for p in proxies:
        safe_p = {"server": p["server"]}
        if "username" in p:
            safe_p["username"] = p["username"][:3] + "***"
        safe_p["has_auth"] = "password" in p
        safe_proxies.append(safe_p)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(safe_proxies, f, indent=2, ensure_ascii=False)

    logger.success(f"💾 Робочі проксі збережено: {filepath}")


# Функція для тестування швидкості всіх проксі
async def benchmark_proxies(proxy_list: List[dict]) -> List[Tuple[dict, float]]:
    """
    Тестує швидкість всіх проксі і повертає відсортований список

    Args:
        proxy_list: Список проксі

    Returns:
        List[Tuple[dict, float]]: Відсортовані за швидкістю (швидші перші)
    """
    tester = ProxyTester()
    results = await tester.test_batch(proxy_list, use_playwright=True)

    proxy_speed = []
    for result in results:
        if result.is_working:
            for proxy in proxy_list:
                if proxy.get('server') == result.server:
                    proxy_speed.append((proxy, result.response_time))
                    break

    # Сортуємо за швидкістю
    proxy_speed.sort(key=lambda x: x[1])

    logger.info("📊 ТОП-5 найшвидших проксі:")
    for i, (proxy, speed) in enumerate(proxy_speed[:5], 1):
        logger.info(f"   {i}. {proxy['server']} - {speed:.2f}с")

    return proxy_speed


# Експортуємо основні класи та функції
__all__ = [
    'ProxyTester',
    'ProxyManager',
    'ProxyTestResult',
    'find_working_proxies',
    'save_working_proxies',
    'benchmark_proxies'
]