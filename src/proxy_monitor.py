# src/proxy_monitor.py
"""
Моніторинг стану проксі та захист від витоку IP
"""

from loguru import logger
from src.settings import VALID_PROXY_LIST
import time
from collections import deque
from datetime import datetime


class ProxyMonitor:
    """Моніторинг та статистика використання проксі"""

    def __init__(self):
        self.usage_stats = {}
        for proxy in VALID_PROXY_LIST:
            server = proxy['server']
            self.usage_stats[server] = {
                'used': 0,
                'failed': 0,
                'last_used': None,
                'total_time': 0,
                'fastest': float('inf'),
                'slowest': 0
            }

        self.recent_failures = deque(maxlen=100)
        self.start_time = time.time()
        self.total_requests = 0
        self.successful_requests = 0

        logger.info(f"📊 ProxyMonitor ініціалізовано для {len(VALID_PROXY_LIST)} проксі")

    def log_proxy_usage(self, proxy_server: str, success: bool, response_time: float = None):
        """Логує використання проксі"""
        if proxy_server in self.usage_stats:
            self.usage_stats[proxy_server]['used'] += 1
            self.usage_stats[proxy_server]['last_used'] = datetime.now().strftime('%H:%M:%S')
            self.total_requests += 1

            if response_time:
                self.usage_stats[proxy_server]['total_time'] += response_time
                if response_time < self.usage_stats[proxy_server]['fastest']:
                    self.usage_stats[proxy_server]['fastest'] = response_time
                if response_time > self.usage_stats[proxy_server]['slowest']:
                    self.usage_stats[proxy_server]['slowest'] = response_time

            if not success:
                self.usage_stats[proxy_server]['failed'] += 1
                self.recent_failures.append({
                    'proxy': proxy_server,
                    'time': datetime.now().strftime('%H:%M:%S'),
                    'error': 'Connection failed'
                })
            else:
                self.successful_requests += 1

    def check_proxy_health(self) -> bool:
        """Перевіряє чи є хоч одне робоче проксі"""
        if not VALID_PROXY_LIST:
            logger.critical("=" * 60)
            logger.critical("🔴 КРИТИЧНО: ВСІ ПРОКСІ МЕРТВІ!")
            logger.critical("=" * 60)
            logger.critical("📊 Статистика помилок:")
            for failure in list(self.recent_failures)[-5:]:  # Останні 5 помилок
                logger.critical(f"   • {failure['time']} - {failure['proxy']}")
            logger.critical("=" * 60)
            logger.critical("🛡️ ЗАХИСТ: Програма буде зупинена")
            logger.critical("💡 Рішення: Оновіть список проксі в config.yaml")
            logger.critical("=" * 60)
            return False
        return True

    def print_stats(self):
        """Виводить статистику використання проксі"""
        logger.info("=" * 70)
        logger.info("📊 СТАТИСТИКА ВИКОРИСТАННЯ ПРОКСІ")
        logger.info("=" * 70)

        # Загальна статистика
        runtime = int(time.time() - self.start_time)
        hours = runtime // 3600
        minutes = (runtime % 3600) // 60
        seconds = runtime % 60

        logger.info(f"⏱️  Час роботи: {hours}г {minutes}хв {seconds}с")
        logger.info(f"📈 Всього запитів: {self.total_requests}")
        logger.info(f"✅ Успішних: {self.successful_requests}")
        logger.info(f"❌ Помилок: {self.total_requests - self.successful_requests}")

        if self.total_requests > 0:
            success_rate = (self.successful_requests / self.total_requests) * 100
            logger.info(f"📊 Успішність: {success_rate:.1f}%")

        logger.info("-" * 70)
        logger.info("📋 Деталі по кожному проксі:")
        logger.info("-" * 70)

        for proxy, stats in self.usage_stats.items():
            if stats['used'] > 0:
                status = "✅" if stats['failed'] == 0 else "⚠️"
                success_rate = ((stats['used'] - stats['failed']) / stats['used']) * 100

                avg_time = stats['total_time'] / stats['used'] if stats['used'] > 0 else 0

                logger.info(f"   {status} {proxy}")
                logger.info(f"      Використано: {stats['used']} разів")
                logger.info(f"      Помилок: {stats['failed']}")
                logger.info(f"      Успішність: {success_rate:.1f}%")
                if avg_time > 0:
                    logger.info(
                        f"      Сер. час: {avg_time:.2f}с (мін: {stats['fastest']:.2f}с, макс: {stats['slowest']:.2f}с)")
                logger.info(f"      Останнє використання: {stats['last_used']}")
                logger.info("-" * 70)

        # Останні помилки
        if self.recent_failures:
            logger.warning("⚠️ Останні помилки:")
            for failure in list(self.recent_failures)[-5:]:
                logger.warning(f"   • {failure['time']} - {failure['proxy']}")

        logger.info("=" * 70)

    def get_working_proxies_count(self) -> int:
        """Повертає кількість робочих проксі"""
        return len(VALID_PROXY_LIST)

    def get_fastest_proxy(self) -> str:
        """Повертає найшвидше проксі"""
        fastest = None
        fastest_time = float('inf')

        for proxy, stats in self.usage_stats.items():
            if stats['used'] > 0 and stats['fastest'] < fastest_time:
                fastest_time = stats['fastest']
                fastest = proxy

        return fastest