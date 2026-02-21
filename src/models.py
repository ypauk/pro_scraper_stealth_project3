# src/models.py
"""
Моделі даних для Rozetka
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
import re


class RozetkaItem(BaseModel):
    """Модель для товару з Rozetka"""

    # Основні поля
    title: str = Field(..., description="Назва товару")
    price: str = Field(..., description="Поточна ціна")
    old_price: Optional[str] = Field(None, description="Стара ціна (до знижки)")
    availability: str = Field(..., description="Наявність (Є в наявності / Немає)")

    # Характеристики
    rating: Optional[float] = Field(None, description="Рейтинг (0-5)")
    reviews_count: Optional[int] = Field(None, description="Кількість відгуків")

    # Медіа
    image_url: Optional[str] = Field(None, description="URL зображення")
    url: str = Field(..., description="Посилання на товар")

    # Специфікації (короткі)
    seller: Optional[str] = Field(None, description="Продавець")
    code: Optional[str] = Field(None, description="Код товару")

    @field_validator('price', 'old_price', mode='before')
    @classmethod
    def clean_price(cls, v: Optional[str]) -> Optional[str]:
        """Очищає ціну від зайвих символів"""
        if v and isinstance(v, str):
            # Видаляємо "₴" та пробіли
            return v.replace('₴', '').strip()
        return v

    @field_validator('title', 'availability', mode='before')
    @classmethod
    def clean_text(cls, v: str) -> str:
        """Очищає текст від зайвих пробілів"""
        if isinstance(v, str):
            return ' '.join(v.split())
        return str(v)

    @field_validator('url', mode='before')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Перевіряє, що URL правильний"""
        if isinstance(v, str):
            if v.startswith('//'):
                return f"https:{v}"
            if not v.startswith('http'):
                return f"https://rozetka.com.ua{v}"
        return v

    @property
    def price_value(self) -> int:
        """Числове значення ціни (для сортування/аналітики)"""
        if not self.price:
            return 0
        digits = re.sub(r'[^\d]', '', self.price)
        return int(digits) if digits else 0

    @property
    def discount_percent(self) -> Optional[int]:
        """Відсоток знижки"""
        if self.old_price and self.price:
            old = re.sub(r'[^\d]', '', self.old_price)
            new = re.sub(r'[^\d]', '', self.price)
            if old and new and int(old) > 0:
                old_val = int(old)
                new_val = int(new)
                return round((old_val - new_val) / old_val * 100)
        return None

    @property
    def is_available(self) -> bool:
        """Чи є товар в наявності"""
        return 'наявності' in self.availability.lower()

    @property
    def has_discount(self) -> bool:
        """Чи є знижка на товар"""
        return self.discount_percent is not None and self.discount_percent > 0

    def to_dict(self) -> dict:
        """Конвертує в словник для збереження"""
        return {
            'title': self.title,
            'price': self.price,
            'price_value': self.price_value,
            'old_price': self.old_price,
            'discount_percent': self.discount_percent,
            'availability': self.availability,
            'is_available': self.is_available,
            'rating': self.rating,
            'reviews_count': self.reviews_count,
            'url': self.url,
            'image_url': self.image_url,
            'seller': self.seller,
            'code': self.code
        }

    def __str__(self) -> str:
        """Коротке представлення"""
        discount = f" (знижка {self.discount_percent}%)" if self.has_discount else ""
        return f"{self.title[:50]}... | {self.price}{discount} | {self.rating}⭐"


class ScraperResult(BaseModel):
    """Модель для результатів скрапінгу"""
    total_found: int = Field(..., description="Загальна кількість знайдених товарів")
    items: List[RozetkaItem] = Field(default_factory=list, description="Список товарів")

    @property
    def total_price(self) -> int:
        """Сумарна вартість всіх товарів"""
        return sum(item.price_value for item in self.items)

    @property
    def average_price(self) -> float:
        """Середня ціна"""
        if not self.items:
            return 0
        return self.total_price / len(self.items)

    @property
    def average_rating(self) -> float:
        """Середній рейтинг"""
        ratings = [item.rating for item in self.items if item.rating]
        if not ratings:
            return 0
        return sum(ratings) / len(ratings)

    @property
    def items_with_discount(self) -> int:
        """Кількість товарів зі знижкою"""
        return sum(1 for item in self.items if item.has_discount)

    def to_dict(self) -> dict:
        """Конвертує в словник для збереження"""
        return {
            'total_found': self.total_found,
            'items': [item.to_dict() for item in self.items],
            'statistics': {
                'total_price': self.total_price,
                'average_price': round(self.average_price, 2),
                'average_rating': round(self.average_rating, 2),
                'items_count': len(self.items),
                'items_with_discount': self.items_with_discount,
                'discount_percent': round(self.items_with_discount / len(self.items) * 100, 1) if self.items else 0
            }
        }