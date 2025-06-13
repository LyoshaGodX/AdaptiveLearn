"""
Стратегии и классы студентов для генерации синтетических данных.
Определяют различные паттерны обучения и поведения студентов.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple, Optional
from enum import Enum
import numpy as np
import random
from dataclasses import dataclass


class LearningSpeed(Enum):
    """Скорости обучения"""
    VERY_SLOW = 0.1
    SLOW = 0.25
    MEDIUM = 0.35
    FAST = 0.50
    VERY_FAST = 0.70


class DifficultyPreference(Enum):
    """Предпочтения по сложности"""
    EASY = 1.0
    MEDIUM = 2.0
    HARD = 3.0
    ADAPTIVE = 0.0


class PersistenceLevel(Enum):
    """Уровни настойчивости"""
    LOW = 0.3
    MEDIUM = 0.6
    HIGH = 0.9


@dataclass
class StudentCharacteristics:
    """Характеристики студента"""
    learning_speed: LearningSpeed
    difficulty_preference: DifficultyPreference
    persistence_level: PersistenceLevel
    
    # BKT параметры
    base_transition_prob: float  # P(T) - базовая вероятность изучения
    base_guess_prob: float       # P(G) - базовая вероятность угадывания
    base_slip_prob: float        # P(S) - базовая вероятность ошибки
    
    # Поведенческие особенности
    fatigue_factor: float        # Насколько быстро устает (0-1)
    motivation_level: float      # Уровень мотивации (0-1)
    
    # Предпочтения по времени решения
    preferred_time_factor: float # Множитель времени решения
    
    def __post_init__(self):
        """Валидация параметров"""
        assert 0 <= self.base_transition_prob <= 1
        assert 0 <= self.base_guess_prob <= 1
        assert 0 <= self.base_slip_prob <= 1
        assert 0 <= self.fatigue_factor <= 1
        assert 0 <= self.motivation_level <= 1
        assert self.preferred_time_factor > 0


class StudentStrategy(ABC):
    """Базовый класс стратегии студента"""
    
    def __init__(self, characteristics: StudentCharacteristics):
        self.characteristics = characteristics
        self.session_fatigue = 0.0  # Текущая усталость в сессии
        self.current_motivation = characteristics.motivation_level
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Название стратегии"""
        pass
    
    @abstractmethod
    def get_initial_mastery_prob(self, skill_difficulty: str) -> float:
        """Начальная вероятность освоения навыка"""
        pass
    
    @abstractmethod
    def get_bkt_parameters(self, skill_difficulty: str, attempt_number: int) -> Dict[str, float]:
        """Получить BKT параметры для конкретного навыка и попытки"""
        pass
    
    @abstractmethod
    def should_attempt_task(self, task_difficulty: str, current_mastery: float) -> bool:
        """Решение о том, стоит ли пытаться решить задание"""
        pass
    
    @abstractmethod
    def get_time_multiplier(self, task_difficulty: str) -> float:
        """Множитель времени для решения задания"""
        pass
    
    def update_session_state(self, task_result: bool, time_spent: float):
        """Обновить состояние сессии после выполнения задания"""
        # Увеличиваем усталость
        self.session_fatigue = min(1.0, self.session_fatigue + 
                                  self.characteristics.fatigue_factor * 0.1)
        
        # Обновляем мотивацию в зависимости от результата
        if task_result:
            # Успех увеличивает мотивацию
            self.current_motivation = min(1.0, self.current_motivation + 0.05)
        else:
            # Неудача может снизить мотивацию
            motivation_loss = 0.1 * (1 - self.characteristics.persistence_level.value)
            self.current_motivation = max(0.1, self.current_motivation - motivation_loss)
    
    def reset_session(self):
        """Сброс состояния сессии"""
        self.session_fatigue = 0.0
        self.current_motivation = self.characteristics.motivation_level
    
    def get_task_type_preference(self, task_type: str) -> float:
        """
        Получить предпочтение студента к определённому типу задания
        
        Args:
            task_type: Тип задания ('true_false', 'single', 'multiple')
            
        Returns:
            float: Коэффициент предпочтения (0.5-1.5)
        """
        # Базовые предпочтения по типам заданий
        base_preferences = {
            'true_false': 1.0,
            'single': 1.0, 
            'multiple': 1.0        }
        
        return base_preferences.get(task_type, 1.0)
    
    def should_attempt_task_with_type(self, difficulty: str, current_mastery: float, task_type: str) -> bool:
        """
        Определить, будет ли студент пытаться решить задание определённого типа
        
        Args:
            difficulty: Уровень сложности задания
            current_mastery: Текущее освоение навыка
            task_type: Тип задания
            
        Returns:
            bool: True если студент попытается решить задание
        """
        # Базовое решение на основе сложности и освоения
        base_decision = self.should_attempt_task(difficulty, current_mastery)
        
        # Корректируем на основе предпочтений к типу задания
        type_preference = self.get_task_type_preference(task_type)
        
        # Если предпочтение низкое, снижаем вероятность попытки
        if type_preference < 1.0:
            adjusted_probability = base_decision * type_preference
            return random.random() < adjusted_probability
        
        return base_decision
        # Базовая логика
        base_willingness = self.should_attempt_task(difficulty, current_mastery)
        
        if not base_willingness:
            return False
        
        # Корректировка по типу задания
        type_preference = self.get_task_type_preference(task_type)
        
        # Учитываем мотивацию и усталость
        motivation_factor = self.current_motivation * (1 - self.session_fatigue * 0.5)
        
        # Финальная вероятность
        final_probability = type_preference * motivation_factor * 0.8  # 0.8 - базовая вероятность
        
        return random.random() < final_probability


class BeginnerStrategy(StudentStrategy):
    """Стратегия начинающего студента"""
    
    def get_strategy_name(self) -> str:
        return "Beginner"
    
    def get_initial_mastery_prob(self, skill_difficulty: str) -> float:
        """Начинающие студенты имеют низкую начальную вероятность"""
        base_probs = {
            'beginner': 0.15,
            'intermediate': 0.05,
            'advanced': 0.02
        }
        return base_probs.get(skill_difficulty, 0.05)
    
    def get_bkt_parameters(self, skill_difficulty: str, attempt_number: int) -> Dict[str, float]:
        """BKT параметры для начинающих"""
        # Учитываем усталость и мотивацию
        fatigue_penalty = self.session_fatigue * 0.3
        motivation_bonus = (self.current_motivation - 0.5) * 0.2
        
        # Базовые параметры для разных сложностей
        base_params = {
            'beginner': {'P_T': 0.25, 'P_G': 0.25, 'P_S': 0.15},
            'intermediate': {'P_T': 0.15, 'P_G': 0.20, 'P_S': 0.20},
            'advanced': {'P_T': 0.08, 'P_G': 0.15, 'P_S': 0.25}
        }
        
        params = base_params.get(skill_difficulty, base_params['intermediate'])
        
        # Применяем модификаторы
        return {
            'P_T': max(0.05, params['P_T'] + motivation_bonus - fatigue_penalty),
            'P_G': max(0.1, params['P_G'] - fatigue_penalty * 0.5),
            'P_S': min(0.4, params['P_S'] + fatigue_penalty)
        }
    
    def should_attempt_task(self, task_difficulty: str, current_mastery: float) -> bool:
        """Начинающие избегают слишком сложных заданий"""
        if task_difficulty == 'advanced' and current_mastery < 0.3:
            return random.random() < 0.3  # Низкая вероятность попытки
        elif task_difficulty == 'intermediate' and current_mastery < 0.2:
            return random.random() < 0.6
        return True
    
    def get_time_multiplier(self, task_difficulty: str) -> float:
        """Начинающие решают медленнее"""
        base_multipliers = {
            'beginner': 1.5,
            'intermediate': 2.0,
            'advanced': 3.0
        }
        multiplier = base_multipliers.get(task_difficulty, 1.5)
        
        # Усталость замедляет
        fatigue_penalty = 1 + self.session_fatigue * 0.5
        
        return multiplier * fatigue_penalty
    
    def get_task_type_preference(self, task_type: str) -> float:
        """Начинающие предпочитают простые типы заданий"""
        preferences = {
            'true_false': 1.3,    # Предпочитают да/нет (проще)
            'single': 1.0,        # Нейтральное отношение к одиночному выбору
            'multiple': 0.7       # Избегают множественного выбора (сложнее)
        }
        return preferences.get(task_type, 1.0)


class IntermediateStrategy(StudentStrategy):
    """Стратегия студента среднего уровня"""
    
    def get_strategy_name(self) -> str:
        return "Intermediate"
    
    def get_initial_mastery_prob(self, skill_difficulty: str) -> float:
        base_probs = {
            'beginner': 0.40,
            'intermediate': 0.20,
            'advanced': 0.08
        }
        return base_probs.get(skill_difficulty, 0.20)
    
    def get_bkt_parameters(self, skill_difficulty: str, attempt_number: int) -> Dict[str, float]:
        fatigue_penalty = self.session_fatigue * 0.2
        motivation_bonus = (self.current_motivation - 0.5) * 0.15
        
        base_params = {
            'beginner': {'P_T': 0.40, 'P_G': 0.20, 'P_S': 0.10},
            'intermediate': {'P_T': 0.30, 'P_G': 0.15, 'P_S': 0.12},
            'advanced': {'P_T': 0.20, 'P_G': 0.12, 'P_S': 0.18}
        }
        
        params = base_params.get(skill_difficulty, base_params['intermediate'])
        
        return {
            'P_T': max(0.05, params['P_T'] + motivation_bonus - fatigue_penalty),
            'P_G': max(0.05, params['P_G'] - fatigue_penalty * 0.3),
            'P_S': min(0.3, params['P_S'] + fatigue_penalty * 0.5)
        }
    
    def should_attempt_task(self, task_difficulty: str, current_mastery: float) -> bool:
        """Средние студенты более сбалансированы в выборе заданий"""
        if task_difficulty == 'advanced' and current_mastery < 0.4:
            return random.random() < 0.7
        return True
    
    def get_time_multiplier(self, task_difficulty: str) -> float:
        base_multipliers = {
            'beginner': 0.8,
            'intermediate': 1.2,
            'advanced': 1.8
        }
        multiplier = base_multipliers.get(task_difficulty, 1.2)
        fatigue_penalty = 1 + self.session_fatigue * 0.3
        return multiplier * fatigue_penalty
    
    def get_task_type_preference(self, task_type: str) -> float:
        """Средние студенты имеют нейтральные предпочтения"""
        preferences = {
            'true_false': 1.0,    # Нейтральное отношение ко всем типам
            'single': 1.0,        # Нейтральное отношение 
            'multiple': 1.0       # Нейтральное отношение
        }
        return preferences.get(task_type, 1.0)


class AdvancedStrategy(StudentStrategy):
    """Стратегия продвинутого студента"""
    
    def get_strategy_name(self) -> str:
        return "Advanced"
    
    def get_initial_mastery_prob(self, skill_difficulty: str) -> float:
        base_probs = {
            'beginner': 0.70,
            'intermediate': 0.45,
            'advanced': 0.25
        }
        return base_probs.get(skill_difficulty, 0.45)
    
    def get_bkt_parameters(self, skill_difficulty: str, attempt_number: int) -> Dict[str, float]:
        fatigue_penalty = self.session_fatigue * 0.15
        motivation_bonus = (self.current_motivation - 0.5) * 0.1
        
        base_params = {
            'beginner': {'P_T': 0.60, 'P_G': 0.15, 'P_S': 0.05},
            'intermediate': {'P_T': 0.50, 'P_G': 0.10, 'P_S': 0.08},
            'advanced': {'P_T': 0.35, 'P_G': 0.08, 'P_S': 0.12}
        }
        
        params = base_params.get(skill_difficulty, base_params['intermediate'])
        
        return {
            'P_T': max(0.1, params['P_T'] + motivation_bonus - fatigue_penalty),
            'P_G': max(0.03, params['P_G'] - fatigue_penalty * 0.2),
            'P_S': min(0.2, params['P_S'] + fatigue_penalty * 0.3)
        }
    
    def should_attempt_task(self, task_difficulty: str, current_mastery: float) -> bool:
        """Продвинутые студенты готовы браться за сложные задания"""
        return True
    
    def get_time_multiplier(self, task_difficulty: str) -> float:
        base_multipliers = {
            'beginner': 0.5,
            'intermediate': 0.7,
            'advanced': 1.0
        }
        multiplier = base_multipliers.get(task_difficulty, 0.7)
        fatigue_penalty = 1 + self.session_fatigue * 0.2
        return multiplier * fatigue_penalty
    
    def get_task_type_preference(self, task_type: str) -> float:
        """Одаренные студенты комфортно работают с любыми типами заданий"""
        preferences = {
            'true_false': 1.1,    # Слегка предпочитают быстрые да/нет для разминки
            'single': 1.0,        # Нейтральное отношение
            'multiple': 1.3       # Больше всего любят сложные множественные выборы
        }
        return preferences.get(task_type, 1.0)


class GiftedStrategy(StudentStrategy):
    """Стратегия одаренного студента"""
    
    def get_strategy_name(self) -> str:
        return "Gifted"
    
    def get_initial_mastery_prob(self, skill_difficulty: str) -> float:
        base_probs = {
            'beginner': 0.85,
            'intermediate': 0.65,
            'advanced': 0.40
        }
        return base_probs.get(skill_difficulty, 0.65)
    
    def get_bkt_parameters(self, skill_difficulty: str, attempt_number: int) -> Dict[str, float]:
        # Одаренные студенты менее подвержены усталости
        fatigue_penalty = self.session_fatigue * 0.1
        motivation_bonus = (self.current_motivation - 0.5) * 0.05
        
        base_params = {
            'beginner': {'P_T': 0.80, 'P_G': 0.10, 'P_S': 0.03},
            'intermediate': {'P_T': 0.70, 'P_G': 0.08, 'P_S': 0.05},
            'advanced': {'P_T': 0.55, 'P_G': 0.05, 'P_S': 0.08}
        }
        
        params = base_params.get(skill_difficulty, base_params['intermediate'])
        
        return {
            'P_T': max(0.2, params['P_T'] + motivation_bonus - fatigue_penalty),
            'P_G': max(0.02, params['P_G'] - fatigue_penalty * 0.1),
            'P_S': min(0.15, params['P_S'] + fatigue_penalty * 0.2)
        }
    
    def should_attempt_task(self, task_difficulty: str, current_mastery: float) -> bool:
        """Одаренные студенты предпочитают сложные задания"""
        if task_difficulty == 'beginner' and current_mastery > 0.6:
            return random.random() < 0.4  # Избегают слишком простых заданий
        return True
    
    def get_time_multiplier(self, task_difficulty: str) -> float:
        base_multipliers = {
            'beginner': 0.3,
            'intermediate': 0.5,
            'advanced': 0.7
        }
        multiplier = base_multipliers.get(task_difficulty, 0.5)
        fatigue_penalty = 1 + self.session_fatigue * 0.1
        return multiplier * fatigue_penalty


class StruggleStrategy(StudentStrategy):
    """Стратегия студента с трудностями в обучении"""
    
    def get_strategy_name(self) -> str:
        return "Struggle"
    
    def get_initial_mastery_prob(self, skill_difficulty: str) -> float:
        base_probs = {
            'beginner': 0.08,
            'intermediate': 0.03,
            'advanced': 0.01
        }
        return base_probs.get(skill_difficulty, 0.03)
    
    def get_bkt_parameters(self, skill_difficulty: str, attempt_number: int) -> Dict[str, float]:
        # Студенты с трудностями сильно подвержены усталости
        fatigue_penalty = self.session_fatigue * 0.4
        motivation_bonus = (self.current_motivation - 0.5) * 0.3
        
        base_params = {
            'beginner': {'P_T': 0.15, 'P_G': 0.30, 'P_S': 0.25},
            'intermediate': {'P_T': 0.08, 'P_G': 0.25, 'P_S': 0.30},
            'advanced': {'P_T': 0.05, 'P_G': 0.20, 'P_S': 0.35}
        }
        
        params = base_params.get(skill_difficulty, base_params['intermediate'])
        
        return {
            'P_T': max(0.02, params['P_T'] + motivation_bonus - fatigue_penalty),
            'P_G': max(0.15, params['P_G'] - fatigue_penalty * 0.3),
            'P_S': min(0.5, params['P_S'] + fatigue_penalty)
        }
    
    def should_attempt_task(self, task_difficulty: str, current_mastery: float) -> bool:
        """Студенты с трудностями избегают сложных заданий"""
        if task_difficulty == 'advanced':
            return random.random() < 0.2
        elif task_difficulty == 'intermediate' and current_mastery < 0.3:
            return random.random() < 0.5
        return True
    
    def get_time_multiplier(self, task_difficulty: str) -> float:
        base_multipliers = {
            'beginner': 2.5,
            'intermediate': 3.5,
            'advanced': 5.0
        }
        multiplier = base_multipliers.get(task_difficulty, 2.5)
        fatigue_penalty = 1 + self.session_fatigue * 0.8
        return multiplier * fatigue_penalty
    
    def get_task_type_preference(self, task_type: str) -> float:
        """Студенты с трудностями предпочитают самые простые типы заданий"""
        preferences = {
            'true_false': 1.5,    # Сильно предпочитают да/нет (самые простые)
            'single': 1.0,        # Нейтральное отношение к одиночному выбору
            'multiple': 0.5       # Сильно избегают множественного выбора
        }
        return preferences.get(task_type, 1.0)


class StudentStrategyFactory:
    """Фабрика для создания стратегий студентов"""
    
    @staticmethod
    def create_strategy(strategy_type: str, **kwargs) -> StudentStrategy:
        """Создать стратегию по типу"""
        
        # Генерируем характеристики если не переданы
        if 'characteristics' not in kwargs:
            characteristics = StudentStrategyFactory._generate_characteristics(strategy_type)
        else:
            characteristics = kwargs['characteristics']
        
        strategy_classes = {
            'beginner': BeginnerStrategy,
            'intermediate': IntermediateStrategy,
            'advanced': AdvancedStrategy,
            'gifted': GiftedStrategy,
            'struggle': StruggleStrategy
        }
        
        strategy_class = strategy_classes.get(strategy_type.lower())
        if not strategy_class:
            raise ValueError(f"Неизвестный тип стратегии: {strategy_type}")
        
        return strategy_class(characteristics)
    
    @staticmethod
    def _generate_characteristics(strategy_type: str) -> StudentCharacteristics:
        """Генерировать характеристики для типа стратегии"""
        
        if strategy_type.lower() == 'beginner':
            return StudentCharacteristics(
                learning_speed=LearningSpeed.SLOW,
                difficulty_preference=DifficultyPreference.EASY,
                persistence_level=PersistenceLevel.MEDIUM,
                base_transition_prob=0.25,
                base_guess_prob=0.25,
                base_slip_prob=0.15,
                fatigue_factor=0.7,
                motivation_level=0.6,
                preferred_time_factor=1.5
            )
        
        elif strategy_type.lower() == 'intermediate':
            return StudentCharacteristics(
                learning_speed=LearningSpeed.MEDIUM,
                difficulty_preference=DifficultyPreference.MEDIUM,
                persistence_level=PersistenceLevel.MEDIUM,
                base_transition_prob=0.35,
                base_guess_prob=0.18,
                base_slip_prob=0.12,
                fatigue_factor=0.5,
                motivation_level=0.7,
                preferred_time_factor=1.2
            )
        
        elif strategy_type.lower() == 'advanced':
            return StudentCharacteristics(
                learning_speed=LearningSpeed.FAST,
                difficulty_preference=DifficultyPreference.HARD,
                persistence_level=PersistenceLevel.HIGH,
                base_transition_prob=0.50,
                base_guess_prob=0.12,
                base_slip_prob=0.08,
                fatigue_factor=0.3,
                motivation_level=0.8,
                preferred_time_factor=0.8
            )
        
        elif strategy_type.lower() == 'gifted':
            return StudentCharacteristics(
                learning_speed=LearningSpeed.VERY_FAST,
                difficulty_preference=DifficultyPreference.HARD,
                persistence_level=PersistenceLevel.HIGH,
                base_transition_prob=0.70,
                base_guess_prob=0.08,
                base_slip_prob=0.05,
                fatigue_factor=0.2,
                motivation_level=0.9,
                preferred_time_factor=0.5
            )
        
        elif strategy_type.lower() == 'struggle':
            return StudentCharacteristics(
                learning_speed=LearningSpeed.VERY_SLOW,
                difficulty_preference=DifficultyPreference.EASY,
                persistence_level=PersistenceLevel.LOW,
                base_transition_prob=0.12,
                base_guess_prob=0.28,
                base_slip_prob=0.25,
                fatigue_factor=0.8,
                motivation_level=0.4,
                preferred_time_factor=2.5
            )
        
        else:
            # По умолчанию - средний студент
            return StudentCharacteristics(
                learning_speed=LearningSpeed.MEDIUM,
                difficulty_preference=DifficultyPreference.ADAPTIVE,
                persistence_level=PersistenceLevel.MEDIUM,
                base_transition_prob=0.3,
                base_guess_prob=0.2,
                base_slip_prob=0.1,
                fatigue_factor=0.5,
                motivation_level=0.6,
                preferred_time_factor=1.0
            )
    
    @staticmethod
    def get_available_strategies() -> List[str]:
        """Получить список доступных стратегий"""
        return ['beginner', 'intermediate', 'advanced', 'gifted', 'struggle']
    
    @staticmethod
    def create_random_strategy() -> StudentStrategy:
        """Создать случайную стратегию"""
        strategy_type = random.choice(StudentStrategyFactory.get_available_strategies())
        return StudentStrategyFactory.create_strategy(strategy_type)
    
    @staticmethod
    def create_mixed_population(
        total_students: int,
        distribution: Optional[Dict[str, float]] = None
    ) -> List[StudentStrategy]:
        """
        Создать популяцию студентов с разными стратегиями
        
        Args:
            total_students: общее количество студентов
            distribution: распределение стратегий (если не указано, используется равномерное)
        """
        if distribution is None:
            # Реалистичное распределение
            distribution = {
                'beginner': 0.25,
                'intermediate': 0.35,
                'advanced': 0.25,
                'gifted': 0.10,
                'struggle': 0.05
            }
        
        # Нормализуем распределение
        total_prob = sum(distribution.values())
        distribution = {k: v/total_prob for k, v in distribution.items()}
        
        students = []
        for strategy_type, prob in distribution.items():
            count = int(total_students * prob)
            for _ in range(count):
                students.append(StudentStrategyFactory.create_strategy(strategy_type))
        
        # Добавляем недостающих студентов случайным образом
        while len(students) < total_students:
            students.append(StudentStrategyFactory.create_random_strategy())
        
        # Перемешиваем
        random.shuffle(students)
        return students[:total_students]
