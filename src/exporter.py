# src/exporter.py
"""
Модуль для експорту даних в різні формати (CSV, JSON, Excel)
"""

import csv
import json
from typing import Any, List, Optional
from pathlib import Path
from datetime import datetime
from loguru import logger

from src.settings import DATA_DIR


class Exporter:
    """Клас для експорту даних в різні формати"""

    @staticmethod
    def append_to_csv(item: Any, filename: str = "rozetka_live.csv") -> Optional[Path]:
        """
        Додає один запис в CSV файл (для live-режиму)

        Args:
            item: Об'єкт товару (Pydantic модель)
            filename: Ім'я файлу

        Returns:
            Path: Шлях до файлу або None при помилці
        """
        filepath = DATA_DIR / filename
        file_exists = filepath.exists()

        try:
            # Конвертуємо об'єкт в словник
            row = item.to_dict() if hasattr(item, 'to_dict') else item.model_dump()
            fieldnames = row.keys()

            with open(filepath, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)

            logger.debug(f"💾 Запис додано до {filename}")
            return filepath

        except Exception as e:
            logger.error(f"❌ Помилка додавання до CSV: {e}")
            return None

    @staticmethod
    def to_csv(data: List[Any], filename: str = "rozetka_results.csv") -> Optional[Path]:
        """
        Зберігає всі дані в CSV файл

        Args:
            data: Список об'єктів товарів
            filename: Ім'я файлу

        Returns:
            Path: Шлях до файлу або None при помилці
        """
        if not data:
            logger.warning("⚠️ Немає даних для експорту в CSV")
            return None

        filepath = DATA_DIR / filename

        try:
            # Отримуємо всі поля з першого об'єкта
            fieldnames = data[0].to_dict().keys()

            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for item in data:
                    writer.writerow(item.to_dict())

            logger.success(f"💾 CSV збережено: {filepath} ({len(data)} записів)")
            return filepath

        except Exception as e:
            logger.error(f"❌ Помилка експорту в CSV: {e}")
            return None

    @staticmethod
    def to_json(data: List[Any], filename: str = "rozetka_results.json") -> Optional[Path]:
        """
        Зберігає всі дані в JSON файл

        Args:
            data: Список об'єктів товарів
            filename: Ім'я файлу

        Returns:
            Path: Шлях до файлу або None при помилці
        """
        if not data:
            logger.warning("⚠️ Немає даних для експорту в JSON")
            return None

        filepath = DATA_DIR / filename

        try:
            # Конвертуємо всі об'єкти в словники
            json_data = [item.to_dict() for item in data]

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2, default=str)

            logger.success(f"💾 JSON збережено: {filepath} ({len(data)} записів)")
            return filepath

        except Exception as e:
            logger.error(f"❌ Помилка експорту в JSON: {e}")
            return None

    @staticmethod
    def to_excel(data: List[Any], filename: str = "rozetka_results.xlsx") -> Optional[Path]:
        """
        Зберігає всі дані в Excel файл

        Args:
            data: Список об'єктів товарів
            filename: Ім'я файлу

        Returns:
            Path: Шлях до файлу або None при помилці
        """
        if not data:
            logger.warning("⚠️ Немає даних для експорту в Excel")
            return None

        filepath = DATA_DIR / filename

        try:
            # Спроба імпортувати pandas (опціональна залежність)
            try:
                import pandas as pd
            except ImportError:
                logger.warning("⚠️ pandas не встановлено. Встановіть: pip install pandas openpyxl")
                logger.info("💡 Продовжую без Excel експорту")
                return None

            # Конвертуємо дані в DataFrame
            df = pd.DataFrame([item.to_dict() for item in data])

            # Додаємо мета-інформацію
            if 'price_value' in df.columns:
                logger.debug(f"📊 Діапазон цін: {df['price_value'].min():,} - {df['price_value'].max():,} грн")

            if 'rating' in df.columns:
                avg_rating = df['rating'].mean()
                logger.debug(f"📊 Середній рейтинг: {avg_rating:.2f}")

            # Зберігаємо в Excel
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Товари', index=False)

                # Додаємо аркуш зі статистикою
                stats_data = {
                    'Показник': [
                        'Дата експорту',
                        'Кількість товарів',
                        'Середня ціна (грн)',
                        'Мінімальна ціна (грн)',
                        'Максимальна ціна (грн)',
                        'Товарів зі знижкою',
                        'Середній рейтинг',
                        'Категорія'
                    ],
                    'Значення': [
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        len(data),
                        round(df['price_value'].mean()) if 'price_value' in df.columns else 'N/A',
                        df['price_value'].min() if 'price_value' in df.columns else 'N/A',
                        df['price_value'].max() if 'price_value' in df.columns else 'N/A',
                        len(df[df['discount_percent'].notna()]) if 'discount_percent' in df.columns else 'N/A',
                        round(df['rating'].mean(), 2) if 'rating' in df.columns and df[
                            'rating'].notna().any() else 'N/A',
                        'Rozetka'
                    ]
                }

                stats_df = pd.DataFrame(stats_data)
                stats_df.to_excel(writer, sheet_name='Статистика', index=False)

                # Автоматичне налаштування ширини колонок
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width

            logger.success(f"💾 Excel збережено: {filepath} ({len(data)} записів)")
            return filepath

        except Exception as e:
            logger.error(f"❌ Помилка експорту в Excel: {e}")
            return None

    @staticmethod
    def to_markdown(data: List[Any], filename: str = "rozetka_results.md") -> Optional[Path]:
        """
        Зберігає всі дані в Markdown формат (для звітів)

        Args:
            data: Список об'єктів товарів
            filename: Ім'я файлу

        Returns:
            Path: Шлях до файлу або None при помилці
        """
        if not data:
            logger.warning("⚠️ Немає даних для експорту в Markdown")
            return None

        filepath = DATA_DIR / filename

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                # Заголовок
                f.write(f"# Звіт про товари Rozetka\n\n")
                f.write(f"**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**Кількість товарів:** {len(data)}\n\n")

                # Статистика
                f.write("## Загальна статистика\n\n")

                price_values = [item.price_value for item in data]
                if price_values:
                    f.write(f"- **Середня ціна:** {sum(price_values) / len(price_values):,.0f} грн\n")
                    f.write(f"- **Мінімальна ціна:** {min(price_values):,} грн\n")
                    f.write(f"- **Максимальна ціна:** {max(price_values):,} грн\n\n")

                discount_items = [item for item in data if item.has_discount]
                if discount_items:
                    f.write(
                        f"- **Товарів зі знижкою:** {len(discount_items)} ({len(discount_items) / len(data) * 100:.1f}%)\n\n")

                # Таблиця з товарами
                f.write("## Список товарів\n\n")
                f.write("| # | Назва | Ціна | Знижка | Рейтинг | Наявність |\n")
                f.write("|---|-------|------|--------|---------|-----------|\n")

                for i, item in enumerate(data[:50], 1):  # Обмежуємо до 50 для читабельності
                    title = item.title[:50] + "..." if len(item.title) > 50 else item.title
                    discount = f"{item.discount_percent}%" if item.has_discount else "-"
                    rating = f"{item.rating}⭐" if item.rating else "-"
                    availability = "✅" if item.is_available else "❌"

                    f.write(f"| {i} | {title} | {item.price} | {discount} | {rating} | {availability} |\n")

                if len(data) > 50:
                    f.write(f"\n*... та ще {len(data) - 50} товарів*\n")

            logger.success(f"💾 Markdown збережено: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"❌ Помилка експорту в Markdown: {e}")
            return None

    @staticmethod
    def to_all_formats(data: List[Any], base_filename: str = "rozetka_results") -> dict:
        """
        Зберігає дані в усі доступні формати

        Args:
            data: Список об'єктів товарів
            base_filename: Базове ім'я файлу (без розширення)

        Returns:
            dict: Словник з результатами для кожного формату
        """
        results = {}

        # CSV
        csv_result = Exporter.to_csv(data, f"{base_filename}.csv")
        if csv_result:
            results['csv'] = csv_result

        # JSON
        json_result = Exporter.to_json(data, f"{base_filename}.json")
        if json_result:
            results['json'] = json_result

        # Excel
        excel_result = Exporter.to_excel(data, f"{base_filename}.xlsx")
        if excel_result:
            results['excel'] = excel_result

        # Markdown
        md_result = Exporter.to_markdown(data, f"{base_filename}.md")
        if md_result:
            results['markdown'] = md_result

        logger.success(f"📦 Експорт завершено. Збережено {len(results)} форматів")
        return results

    @staticmethod
    def print_summary(data: List[Any]) -> None:
        """
        Виводить коротку статистику по даних

        Args:
            data: Список об'єктів товарів
        """
        if not data:
            logger.warning("⚠️ Немає даних для аналізу")
            return

        logger.info("=" * 60)
        logger.info("📊 АНАЛІЗ ЗІБРАНИХ ДАНИХ")
        logger.info("=" * 60)

        # Загальна кількість
        logger.info(f"📦 Всього товарів: {len(data)}")

        # Ціни
        price_values = [item.price_value for item in data]
        if price_values:
            logger.info(f"💰 Середня ціна: {sum(price_values) / len(price_values):,.0f} грн")
            logger.info(f"💵 Мінімальна ціна: {min(price_values):,} грн")
            logger.info(f"💎 Максимальна ціна: {max(price_values):,} грн")

        # Знижки
        discount_items = [item for item in data if item.has_discount]
        if discount_items:
            avg_discount = sum(item.discount_percent for item in discount_items) / len(discount_items)
            logger.info(f"🏷️ Товарів зі знижкою: {len(discount_items)} ({len(discount_items) / len(data) * 100:.1f}%)")
            logger.info(f"📉 Середня знижка: {avg_discount:.1f}%")

        # Рейтинги
        rated_items = [item for item in data if item.rating]
        if rated_items:
            avg_rating = sum(item.rating for item in rated_items) / len(rated_items)
            logger.info(f"⭐ Середній рейтинг: {avg_rating:.2f}")

            # Розподіл рейтингів
            five_star = sum(1 for item in rated_items if item.rating >= 4.5)
            four_star = sum(1 for item in rated_items if 4.0 <= item.rating < 4.5)
            three_star = sum(1 for item in rated_items if 3.0 <= item.rating < 4.0)
            logger.info(f"   • 5⭐: {five_star} товарів")
            logger.info(f"   • 4⭐: {four_star} товарів")
            logger.info(f"   • 3⭐: {three_star} товарів")

        # Наявність
        available = sum(1 for item in data if item.is_available)
        logger.info(f"✅ В наявності: {available} товарів ({available / len(data) * 100:.1f}%)")

        logger.info("=" * 60)


# Функція-помічник для швидкого збереження
def save_results(data: List[Any], formats: List[str] = None, base_filename: str = None) -> dict:
    """
    Швидке збереження результатів

    Args:
        data: Список об'єктів товарів
        formats: Список форматів (csv, json, excel, markdown, all)
        base_filename: Базове ім'я файлу

    Returns:
        dict: Результати збереження
    """
    if not base_filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"rozetka_{timestamp}"

    if not formats:
        formats = ['csv', 'json']

    if 'all' in formats:
        return Exporter.to_all_formats(data, base_filename)

    results = {}

    if 'csv' in formats:
        results['csv'] = Exporter.to_csv(data, f"{base_filename}.csv")

    if 'json' in formats:
        results['json'] = Exporter.to_json(data, f"{base_filename}.json")

    if 'excel' in formats:
        results['excel'] = Exporter.to_excel(data, f"{base_filename}.xlsx")

    if 'markdown' in formats:
        results['markdown'] = Exporter.to_markdown(data, f"{base_filename}.md")

    return results