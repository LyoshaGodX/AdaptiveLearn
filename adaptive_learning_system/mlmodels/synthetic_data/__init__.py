"""
Генерация синтетических данных для обучения и тестирования моделей
"""

from .generator import (
    SyntheticDataGenerator,
    SyntheticStudent,
    SyntheticAttempt
)

__all__ = [
    'SyntheticDataGenerator',
    'SyntheticStudent', 
    'SyntheticAttempt'
]
