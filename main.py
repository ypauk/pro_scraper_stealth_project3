# main.py
"""
Головний файл для запуску скрапера Rozetka
"""

import asyncio
import sys
import argparse
from pathlib import Path
from loguru import logger
from datetime import datetime

# Додаємо шлях до проекту
sys.path.append(str(Path(__file__).parent))

from src.scraper import Scraper
from src.exporter import Exporter
from src.settings import (
    LOG_DIR, MAX_ITEMS, VALID_PROXY_LIST,
    get_rozetka_url, CATEGORIES, DEFAULT_CATEGORY
)
from src.stealth import get_stealth_for_site


def setup_logging():
    """Налаштування логування"""
    logger.remove()

    # Консольне логування (кольорове)
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True
    )

    # Файлове логування (детальне)
    log_file = LOG_DIR / f"rozetka_scraper_{datetime.now().strftime('%Y%m%d')}.log"
    logger.add(
        log_file,
        rotation="10 MB",
        retention="10 days",
        level="DEBUG",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )

    return log_file


def parse_arguments():
    """Парсинг аргументів командного рядка"""
    parser = argparse.ArgumentParser(
        description="Скрапер для Rozetka.ua",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Приклади використання:
  python main.py --category notebooks                    # Ноутбуки
  python main.py --category smartphones --max-items 100  # 100 смартфонів
  python main.py --query "iphone 15"                      # Пошук iphone 15
  python main.py --headless --format json                 # Без вікна, JSON формат
  python main.py --category tv --discount-only            # Тільки товари зі знижкою
  python main.py --min-price 10000 --max-price 30000      # Фільтр за ціною
        """
    )

    parser.add_argument(
        '--category',
        type=str,
        default=None,
        choices=list(CATEGORIES.keys()),
        help=f'Категорія товарів: {", ".join(CATEGORIES.keys())}'
    )

    parser.add_argument(
        '--query',
        type=str,
        default=None,
        help='Пошуковий запит (наприклад: "iphone 15", "samsung tv")'
    )

    parser.add_argument(
        '--max-items',
        type=int,
        default=MAX_ITEMS,
        help=f'Максимальна кількість товарів (за замовчуванням: {MAX_ITEMS})'
    )

    parser.add_argument(
        '--concurrent',
        type=int,
        default=2,
        help='Максимальна кількість одночасних сторінок (за замовчуванням: 2)'
    )

    parser.add_argument(
        '--headless',
        action='store_true',
        help='Запуск в headless режимі (без вікна браузера)'
    )

    parser.add_argument(
        '--no-proxy',
        action='store_true',
        help='Вимкнути використання проксі (не рекомендується)'
    )

    parser.add_argument(
        '--format',
        type=str,
        default='csv',
        choices=['csv', 'json', 'both', 'excel'],
        help='Формат збереження результатів (csv, json, both, excel)'
    )

    parser.add_argument(
        '--delay',
        type=float,
        default=3.0,
        help='Мінімальна затримка між запитами в секундах'
    )

    parser.add_argument(
        '--discount-only',
        action='store_true',
        help='Збирати тільки товари зі знижкою'
    )

    parser.add_argument(
        '--min-price',
        type=int,
        default=None,
        help='Мінімальна ціна (фільтр)'
    )

    parser.add_argument(
        '--max-price',
        type=int,
        default=None,
        help='Максимальна ціна (фільтр)'
    )

    parser.add_argument(
        '--min-rating',
        type=float,
        default=None,
        choices=[1.0, 2.0, 3.0, 4.0, 4.5],
        help='Мінімальний рейтинг (1.0, 2.0, 3.0, 4.0, 4.5)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Режим налагодження (детальні логи)'
    )

    return parser.parse_args()


async def main():
    """Головна функція запуску скрапера для Rozetka"""

    # 1. Парсимо аргументи командного рядка
    args = parse_arguments()

    # 2. Налаштовуємо логування
    log_file = setup_logging()

    # 3. Перевіряємо параметри
    if not args.category and not args.query:
        logger.warning("⚠️ Не вказано категорію або пошуковий запит")
        logger.info("ℹ️ Використовую категорію за замовчуванням: notebooks")
        args.category = DEFAULT_CATEGORY

    # 4. Формуємо URL
    search_url = get_rozetka_url(args.category, args.query)

    logger.info("=" * 70)
    logger.info("🚀 ЗАПУСК СКРАПЕРА ДЛЯ ROZETKA.UA")
    logger.info("=" * 70)

    if args.category:
        logger.info(f"📁 Категорія: {args.category}")
    if args.query:
        logger.info(f"🔍 Пошуковий запит: {args.query}")

    logger.info(f"🔗 URL: {search_url}")
    logger.info(f"📊 Максимум товарів: {args.max_items}")
    logger.info(f"🔄 Макс. одночасних сторінок: {args.concurrent}")
    logger.info(f"📁 Лог-файл: {log_file}")

    if args.headless:
        logger.info("🖥️ Режим: без вікна браузера (headless)")
    else:
        logger.info("🖥️ Режим: з вікном браузера")

    if args.discount_only:
        logger.info("🏷️ Фільтр: тільки товари зі знижкою")

    if args.min_price or args.max_price:
        logger.info(f"💰 Фільтр ціни: {args.min_price or 'мін'} - {args.max_price or 'макс'} грн")

    if args.min_rating:
        logger.info(f"⭐ Фільтр рейтингу: від {args.min_rating}")

    if args.no_proxy:
        logger.warning("⚠️ Проксі ВИМКНЕНО! Це небезпечно для вашого IP!")
    else:
        logger.info(f"🔌 Проксі: {len(VALID_PROXY_LIST)} шт.")

    logger.info("=" * 70)

    # 5. Перевіряємо наявність проксі
    if not args.no_proxy and not VALID_PROXY_LIST:
        logger.error("❌ Немає доступних проксі! Використовуйте --no-proxy або перевірте налаштування .env файлу")
        return

    # 6. Створюємо стелс для українського сайту
    try:
        stealth = get_stealth_for_site('ukraine')
        logger.success("🕵️ Стелс для Rozetka створено")
    except Exception as e:
        logger.error(f"❌ Помилка створення стелсу: {e}")
        return

    # 7. Ініціалізуємо скрапер
    scraper = Scraper(
        max_items=args.max_items,
        stealth=stealth,
        site_name="Rozetka",
        max_concurrent=args.concurrent,
        discount_only=args.discount_only,
        min_price=args.min_price,
        max_price=args.max_price,
        min_rating=args.min_rating
    )

    # 8. Запускаємо скрапер
    try:
        logger.info(f"🔄 Початок збору даних з Rozetka...")
        start_time = datetime.now()

        results = await scraper.run(search_url)

        elapsed = datetime.now() - start_time

        # 9. Обробка результатів
        if results:
            logger.success("=" * 70)
            logger.success("🏁 СКРАПЕР УСПІШНО ЗАВЕРШЕНО!")
            logger.info(f"📊 Всього зібрано: {len(results)} товарів")

            # Статистика по цінах
            total_sum = sum(item.price_value for item in results)
            avg_price = total_sum / len(results) if results else 0
            min_price = min(item.price_value for item in results)
            max_price = max(item.price_value for item in results)

            logger.info(f"💰 Середня ціна: {avg_price:,.0f} грн")
            logger.info(f"💵 Мінімальна ціна: {min_price:,.0f} грн")
            logger.info(f"💎 Максимальна ціна: {max_price:,.0f} грн")

            # Статистика по знижках
            discount_items = [item for item in results if item.has_discount]
            if discount_items:
                avg_discount = sum(item.discount_percent for item in discount_items) / len(discount_items)
                logger.info(f"🏷️ Товарів зі знижкою: {len(discount_items)} ({avg_discount:.1f}% в середньому)")

            # Статистика по рейтингу
            rated_items = [item for item in results if item.rating]
            if rated_items:
                avg_rating = sum(item.rating for item in rated_items) / len(rated_items)
                logger.info(f"⭐ Середній рейтинг: {avg_rating:.2f}")

            logger.info(f"⏱️ Час виконання: {elapsed.total_seconds():.1f} сек")
            logger.info("=" * 70)

            # Зберігаємо результати
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if args.category:
                name_part = args.category
            elif args.query:
                name_part = args.query.replace(' ', '_')
            else:
                name_part = "rozetka"

            base_filename = f"rozetka_{name_part}_{timestamp}"

            saved_files = []

            if args.format in ['csv', 'both']:
                csv_file = Exporter.to_csv(results, f"{base_filename}.csv")
                saved_files.append(csv_file)

            if args.format in ['json', 'both']:
                json_file = Exporter.to_json(results, f"{base_filename}.json")
                saved_files.append(json_file)

            if args.format in ['excel', 'both']:
                excel_file = Exporter.to_excel(results, f"{base_filename}.xlsx")
                saved_files.append(excel_file)

            logger.info(f"📁 Результати збережено в data/:")
            for file in saved_files:
                logger.info(f"   - {file}")
            logger.success("=" * 70)

            # Показуємо перші 5 товарів для прикладу
            logger.info("📋 Приклади зібраних товарів:")
            for i, item in enumerate(results[:5], 1):
                discount = f" (знижка {item.discount_percent}%)" if item.has_discount else ""
                rating = f" | {item.rating}⭐" if item.rating else ""
                logger.info(f"   {i}. {item.title[:60]}... | {item.price}{discount}{rating}")

            return results
        else:
            logger.warning("🤔 Товари не знайдено. Можливі причини:")
            logger.warning("   • Змінились селектори на сайті")
            logger.warning("   • Проблеми з підключенням")
            logger.warning("   • Блокування від Rozetka")
            logger.warning("   • Немає товарів в цій категорії")
            return None

    except KeyboardInterrupt:
        logger.warning("\n⏹️ Виконання перервано користувачем")
        logger.info("💡 Прогрес збережено в checkpoint.json")
        return None
    except Exception as e:
        logger.critical(f"💥 Критична помилка: {e}")
        if args.debug:
            import traceback
            logger.error(traceback.format_exc())
        logger.info("🆘 Якщо помилка повторюється, перевірте:")
        logger.info("   • Налаштування проксі в .env")
        logger.info("   • Доступність сайту rozetka.com.ua")
        logger.info("   • Селектори в парсері")
        return None


def list_categories():
    """Виводить список доступних категорій"""
    print("\n📁 Доступні категорії Rozetka:")
    print("-" * 40)
    for cat, cat_id in CATEGORIES.items():
        print(f"   • {cat}: {cat_id}")
    print("-" * 40)


def print_help():
    """Виводить довідку по використанню"""
    help_text = """
    🔷 СКРАПЕР ДЛЯ ROZETKA.UA 🔷

    Використання:
      python main.py [опції]

    ПРИКЛАДИ:
      # Ноутбуки
      python main.py --category notebooks

      # 100 смартфонів з рейтингом від 4.5
      python main.py --category smartphones --max-items 100 --min-rating 4.5

      # Пошук iPhone 15 зі знижкою
      python main.py --query "iphone 15" --discount-only

      # Товари в ціновому діапазоні
      python main.py --category tv --min-price 10000 --max-price 30000

      # Всі формати + без вікна
      python main.py --category headphones --format both --headless

    ОПЦІЇ:
      --category CAT       Категорія: notebooks, smartphones, tv, tablets, headphones
      --query TEXT         Пошуковий запит
      --max-items N        Максимальна кількість товарів
      --concurrent N       Макс. одночасних сторінок (1-3)
      --headless           Запуск без вікна браузера
      --no-proxy           Вимкнути проксі (НЕБЕЗПЕЧНО!)
      --format FORMAT      Формат: csv, json, both, excel
      --discount-only      Тільки товари зі знижкою
      --min-price N        Мінімальна ціна
      --max-price N        Максимальна ціна
      --min-rating N       Мінімальний рейтинг (1.0-5.0)
      --debug              Режим налагодження
      --help               Ця довідка
      --list-categories    Список категорій
    """
    print(help_text)


if __name__ == "__main__":
    # Спеціальні команди
    if '--help' in sys.argv or '-h' in sys.argv:
        print_help()
        sys.exit(0)

    if '--list-categories' in sys.argv:
        list_categories()
        sys.exit(0)

    # Запуск основної програми
    asyncio.run(main())