# src/semaphore_manager.py
"""
Менеджер для контролю паралельних запитів (Semaphore)
Дозволяє уникнути блокування та перевантаження сайтів
"""

import asyncio
from loguru import logger
from typing import Optional, Dict, Any
import time


class SemaphoreManager:
    """
    Клас для керування паралельними запитами
    Використовується як "світлофор" для обмеження кількості одночасних задач
    """

    def __init__(self, max_concurrent: int = 3, site_name: str = "default"):
        """
        Args:
            max_concurrent: Максимальна кількість одночасних запитів
            site_name: Назва сайту для логування
        """
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.max_concurrent = max_concurrent
        self.site_name = site_name
        self.active_tasks = 0
        self.total_tasks = 0
        self.waiting_tasks = 0
        self.start_time = None

    async def acquire(self, task_name: str = "") -> bool:
        """
        Отримати дозвіл на виконання (зайти на "зелене світло")

        Args:
            task_name: Назва задачі для логування

        Returns:
            bool: True якщо дозвіл отримано
        """
        self.waiting_tasks += 1
        logger.debug(f"[{self.site_name}] ⏳ Задача '{task_name}' чекає... (в черзі: {self.waiting_tasks})")

        # Чекаємо на звільнення місця
        await self.semaphore.acquire()

        self.waiting_tasks -= 1
        self.active_tasks += 1
        self.total_tasks += 1

        logger.debug(
            f"[{self.site_name}] ✅ Задача '{task_name}' стартує (активних: {self.active_tasks}/{self.max_concurrent})")
        return True

    def release(self, task_name: str = ""):
        """
        Звільнити дозвіл (вийти з "зеленого світла")

        Args:
            task_name: Назва задачі для логування
        """
        self.active_tasks -= 1
        self.semaphore.release()
        logger.debug(
            f"[{self.site_name}] 🔓 Задача '{task_name}' завершилась (активних: {self.active_tasks}/{self.max_concurrent})")

    async def run_with_semaphore(self, coro, task_name: str = ""):
        """
        Запустити корутину з контролем Semaphore (автоматично acquire/release)

        Args:
            coro: Асинхронна функція для виконання
            task_name: Назва задачі

        Returns:
            Результат виконання корутини
        """
        await self.acquire(task_name)
        try:
            if self.start_time is None:
                self.start_time = time.time()

            result = await coro
            return result
        finally:
            self.release(task_name)

    def get_stats(self) -> Dict[str, Any]:
        """Повертає статистику роботи Semaphore"""
        runtime = time.time() - self.start_time if self.start_time else 0
        return {
            'site': self.site_name,
            'max_concurrent': self.max_concurrent,
            'total_tasks': self.total_tasks,
            'current_active': self.active_tasks,
            'current_waiting': self.waiting_tasks,
            'runtime_seconds': round(runtime, 2)
        }

    def print_stats(self):
        """Виводить статистику в логи"""
        stats = self.get_stats()
        logger.info(f"📊 Semaphore статистика для {stats['site']}:")
        logger.info(f"   • Макс. одночасно: {stats['max_concurrent']}")
        logger.info(f"   • Всього задач: {stats['total_tasks']}")
        logger.info(f"   • Час роботи: {stats['runtime_seconds']} сек")


# Глобальний менеджер для різних сайтів
_semaphores: Dict[str, SemaphoreManager] = {}


def get_semaphore(site_name: str, max_concurrent: int = 3) -> SemaphoreManager:
    """
    Отримати або створити Semaphore для конкретного сайту

    Args:
        site_name: Назва сайту
        max_concurrent: Максимальна кількість одночасних запитів

    Returns:
        SemaphoreManager для сайту
    """
    if site_name not in _semaphores:
        _semaphores[site_name] = SemaphoreManager(max_concurrent, site_name)
        logger.info(f"🚦 Створено Semaphore для {site_name} (макс. {max_concurrent} одночасно)")
    return _semaphores[site_name]


class AsyncTaskGroup:
    """
    Група асинхронних задач з контролем навантаження
    Дозволяє запускати кілька задач з обмеженням паралельності
    """

    def __init__(self, max_concurrent: int = 3, name: str = "group"):
        """
        Args:
            max_concurrent: Максимальна кількість одночасних задач
            name: Назва групи для логування
        """
        self.semaphore = get_semaphore(name, max_concurrent)
        self.tasks = []
        self.name = name

    def add_task(self, coro, task_name: str = ""):
        """
        Додати задачу до групи

        Args:
            coro: Асинхронна функція
            task_name: Назва задачі
        """
        self.tasks.append((coro, task_name))

    async def run_all(self) -> list:
        """
        Запустити всі задачі з контролем Semaphore

        Returns:
            list: Результати виконання
        """
        logger.info(f"🚀 Запуск групи '{self.name}' з {len(self.tasks)} задач")

        # Запускаємо всі задачі з контролем
        results = []
        for i, (coro, task_name) in enumerate(self.tasks):
            result = await self.semaphore.run_with_semaphore(
                coro,
                task_name or f"task_{i + 1}"
            )
            results.append(result)

        self.semaphore.print_stats()
        return results

    async def run_parallel(self) -> list:
        """
        Запустити всі задачі ПАРАЛЕЛЬНО з контролем Semaphore

        Returns:
            list: Результати виконання
        """
        logger.info(f"🚀 Паралельний запуск групи '{self.name}' з {len(self.tasks)} задач")

        # Створюємо задачі з контролем
        controlled_tasks = [
            self.semaphore.run_with_semaphore(coro, task_name)
            for coro, task_name in self.tasks
        ]

        # Запускаємо паралельно
        results = await asyncio.gather(*controlled_tasks, return_exceptions=True)

        self.semaphore.print_stats()
        return results


# Простий декоратор для контролю навантаження
def with_semaphore(site_name: str = "default", max_concurrent: int = 3):
    """
    Декоратор для обмеження паралельних викликів функції

    Args:
        site_name: Назва сайту
        max_concurrent: Максимальна кількість одночасних викликів
    """
    semaphore = get_semaphore(site_name, max_concurrent)

    def decorator(func):
        async def wrapper(*args, **kwargs):
            async with semaphore.semaphore:
                return await func(*args, **kwargs)

        return wrapper

    return decorator