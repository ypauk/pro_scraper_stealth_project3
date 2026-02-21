# src/proxy_fetcher.py
"""
Автоматичне отримання проксі з Webshare API
Підтримує 100+ проксі через пагінацію
"""

import requests
import os
from pathlib import Path
from loguru import logger
import yaml
from dotenv import load_dotenv

load_dotenv()


class WebshareProxyFetcher:
    """Клас для автоматичного отримання проксі з Webshare"""

    def __init__(self, api_token: str = None):
        """
        Args:
            api_token: API ключ з Webshare (якщо None, бере з .env)
        """
        self.api_token = api_token or os.getenv("WEBSHARE_API_TOKEN")
        if not self.api_token:
            raise ValueError("❌ API token не знайдено! Додайте WEBSHARE_API_TOKEN в .env файл")

        self.base_url = "https://proxy.webshare.io/api/v2"
        self.headers = {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json"
        }
        self.proxies = []
        self.username = os.getenv("WEBSHARE_USERNAME")
        self.password = os.getenv("WEBSHARE_PASSWORD")

    def fetch_all_proxies(self) -> list:
        """
        Отримує ВСІ проксі через API з автоматичною пагінацією
        Підтримує 100, 500, 1000+ проксі

        Returns:
            list: Список всіх проксі
        """
        all_proxies = []
        page = 1
        page_size = 100  # Максимум 100 на сторінку

        logger.info("🔄 Завантаження всіх проксі з Webshare...")

        while True:
            try:
                # Додаємо параметр mode
                url = f"{self.base_url}/proxy/list/?page={page}&page_size={page_size}&mode=direct"

                response = requests.get(
                    url,
                    headers=self.headers,
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])

                    if not results:
                        break

                    for proxy in results:
                        proxy_config = {
                            "server": f"http://{proxy['proxy_address']}:{proxy['port']}",
                            "username": proxy['username'],
                            "password": proxy['password']
                        }
                        all_proxies.append(proxy_config)

                    logger.info(f"📦 Сторінка {page}: +{len(results)} проксі (всього: {len(all_proxies)})")

                    # Перевіряємо чи є наступна сторінка
                    if data.get("next"):
                        page += 1
                    else:
                        break

                elif response.status_code == 429:
                    logger.warning("⏳ Rate limit, очікування 10 секунд...")
                    import time
                    time.sleep(10)
                    continue
                else:
                    logger.error(f"❌ Помилка API: {response.status_code} - {response.text}")
                    break

            except Exception as e:
                logger.error(f"❌ Помилка: {e}")
                break

        self.proxies = all_proxies
        logger.success(f"✅ Завантажено ВСІ проксі: {len(all_proxies)} шт.")

        return all_proxies

    def get_proxy_list(self, mode: str = "direct") -> list:
        """
        Простий метод отримання проксі з першої сторінки

        Args:
            mode: "direct" або "backbone"
        """
        try:
            url = f"{self.base_url}/proxy/list/?mode={mode}"
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                proxies = []

                for proxy in data.get("results", []):
                    proxy_config = {
                        "server": f"http://{proxy['proxy_address']}:{proxy['port']}",
                        "username": proxy['username'],
                        "password": proxy['password']
                    }
                    proxies.append(proxy_config)

                logger.success(f"✅ Отримано {len(proxies)} проксі")
                return proxies
            else:
                logger.error(f"❌ Помилка: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            logger.error(f"❌ Помилка: {e}")
            return []

    def get_rotating_endpoint(self) -> dict:
        """
        Повертає конфіг для ротаційного ендпоінту

        Returns:
            dict: Конфіг для ротаційного проксі
        """
        return {
            "server": "http://p.webshare.io:80",
            "username": self.username,
            "password": self.password
        }

    def save_to_yaml(self, proxies: list, config_path: str = "config.yaml"):
        """
        Зберігає проксі в YAML файл

        Args:
            proxies: Список проксі
            config_path: Шлях до config.yaml
        """
        try:
            # Перевіряємо чи існує файл
            config_file = Path(config_path)

            if config_file.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
            else:
                config = {}

            # Оновлюємо проксі
            config['proxies'] = proxies

            # Зберігаємо назад
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False, indent=2)

            logger.success(f"✅ {len(proxies)} проксі збережено в {config_path}")

        except Exception as e:
            logger.error(f"❌ Помилка збереження: {e}")


# Зручна функція для використання
def update_proxies_from_webshare(use_rotating: bool = False):
    """
    Оновлює проксі з Webshare

    Args:
        use_rotating: Якщо True - використовує ротаційний ендпоінт,
                      якщо False - завантажує всі проксі
    """
    fetcher = WebshareProxyFetcher()

    if use_rotating:
        # Простий ротаційний ендпоінт (один запис)
        proxies = [fetcher.get_rotating_endpoint()]
        logger.info("🔄 Використовую ротаційний ендпоінт")

        # Зберігаємо в YAML
        fetcher.save_to_yaml(proxies)
        return proxies
    else:
        # Всі проксі з пагінацією (для 100+ шт)
        proxies = fetcher.fetch_all_proxies()

        if proxies:
            fetcher.save_to_yaml(proxies)
            return proxies
        else:
            # Якщо не вдалося, пробуємо простий метод
            logger.warning("⚠️ Спробую простий метод get_proxy_list...")
            proxies = fetcher.get_proxy_list()
            if proxies:
                fetcher.save_to_yaml(proxies)
                return proxies

            logger.warning("⚠️ Не вдалося отримати проксі, використовую старі")
            return None