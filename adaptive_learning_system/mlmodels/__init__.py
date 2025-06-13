"""
MLModels - приложение для машинного обучения в адаптивной системе образования

Включает:
- BKT (Bayesian Knowledge Tracing) модель
- Интерфейсы для работы с данными
- Генерацию синтетических данных
- Стратегии студентов
"""

# Отложенные импорты для избежания проблем с загрузкой Django
__version__ = "1.0.0"

def get_bkt_models():
    """Получить BKT модели"""
    from .bkt import BKTModel, BKTParameters, BKTTrainer
    return BKTModel, BKTParameters, BKTTrainer

def get_data_interfaces():
    """Получить интерфейсы для работы с данными"""
    from .data_interfaces import (
        DatabaseInterface,
        SkillsGraph
    )
    return DatabaseInterface, SkillsGraph

def get_student_strategies():
    """Получить стратегии студентов"""
    from .student_strategies import (
        StudentStrategy,
        StudentStrategyFactory,
        BeginnerStrategy,
        IntermediateStrategy,
        AdvancedStrategy,
        GiftedStrategy,
        StruggleStrategy
    )
    return (StudentStrategy, StudentStrategyFactory, BeginnerStrategy,
            IntermediateStrategy, AdvancedStrategy, GiftedStrategy, StruggleStrategy)

def get_synthetic_data():
    """Получить генератор синтетических данных"""
    from .synthetic_data import SyntheticDataGenerator, SyntheticStudent, SyntheticAttempt
    return SyntheticDataGenerator, SyntheticStudent, SyntheticAttempt

__all__ = [
    'get_bkt_models',
    'get_data_interfaces', 
    'get_student_strategies',
    'get_synthetic_data'
]
