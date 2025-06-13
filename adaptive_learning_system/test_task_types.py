#!/usr/bin/env python
"""
Тест системы с учетом типов заданий и уровней сложности
"""

import os
import sys
import django
from pathlib import Path

# Настройка Django
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

from mlmodels.bkt.base_model import BKTModel, BKTParameters, TaskCharacteristics
from mlmodels.student_strategies.strategies import StudentStrategyFactory
from methodist.models import TaskType, DifficultyLevel


def test_bkt_with_task_types():
    """Тест BKT модели с разными типами заданий"""
    print("🧪 ТЕСТ BKT МОДЕЛИ С ТИПАМИ ЗАДАНИЙ")
    print("=" * 50)
    
    # Создаем BKT модель
    bkt_model = BKTModel()
    
    # Устанавливаем параметры для навыка
    skill_id = 1
    base_params = BKTParameters(P_L0=0.1, P_T=0.3, P_G=0.2, P_S=0.1)
    bkt_model.set_skill_parameters(skill_id, base_params)
    
    student_id = 1
    
    print(f"Базовые параметры BKT: P(L0)={base_params.P_L0}, P(T)={base_params.P_T}, P(G)={base_params.P_G}, P(S)={base_params.P_S}")
    print()
    
    # Тестируем разные типы заданий
    task_types = [
        ('true_false', 'beginner'),
        ('single', 'intermediate'), 
        ('multiple', 'advanced')
    ]
    
    for task_type, difficulty in task_types:
        print(f"--- Тип задания: {task_type}, Сложность: {difficulty} ---")
        
        # Создаем характеристики задания
        task_chars = TaskCharacteristics(task_type=task_type, difficulty=difficulty)
        
        # Получаем адаптированные параметры
        adapted_params = bkt_model._adjust_parameters_for_task(base_params, task_chars)
        
        print(f"Адаптированные параметры:")
        print(f"  P(G) = {adapted_params.P_G:.3f} (было {base_params.P_G:.3f})")
        print(f"  P(S) = {adapted_params.P_S:.3f} (было {base_params.P_S:.3f})")
        print(f"  P(T) = {adapted_params.P_T:.3f} (было {base_params.P_T:.3f})")
        
        # Предсказываем вероятность успеха
        p_success = bkt_model.predict_performance(student_id, skill_id, task_chars)
        print(f"  Вероятность успеха: {p_success:.3f}")
        
        print()


def test_student_preferences():
    """Тест предпочтений студентов по типам заданий"""
    print("👥 ТЕСТ ПРЕДПОЧТЕНИЙ СТУДЕНТОВ ПО ТИПАМ ЗАДАНИЙ")
    print("=" * 50)
    
    strategy_types = ['beginner', 'intermediate', 'advanced', 'gifted', 'struggle']
    task_types = ['true_false', 'single', 'multiple']
    
    for strategy_type in strategy_types:
        print(f"--- Стратегия: {strategy_type.upper()} ---")
        
        strategy = StudentStrategyFactory.create_strategy(strategy_type)
        
        for task_type in task_types:
            preference = strategy.get_task_type_preference(task_type)
            
            # Интерпретация предпочтения
            if preference > 1.2:
                preference_str = "сильно предпочитает"
            elif preference > 1.0:
                preference_str = "предпочитает"
            elif preference == 1.0:
                preference_str = "нейтрально"
            elif preference > 0.8:
                preference_str = "слегка избегает"
            else:
                preference_str = "избегает"
            
            print(f"  {task_type:12}: {preference:.2f} ({preference_str})")
        
        print()


def test_task_attempt_decisions():
    """Тест решений о попытках выполнения заданий"""
    print("🎯 ТЕСТ РЕШЕНИЙ О ПОПЫТКАХ ВЫПОЛНЕНИЯ ЗАДАНИЙ")
    print("=" * 50)
    
    strategy = StudentStrategyFactory.create_strategy('beginner')
    
    task_scenarios = [
        ('true_false', 'beginner', 0.3),
        ('single', 'intermediate', 0.3), 
        ('multiple', 'advanced', 0.3),
        ('true_false', 'advanced', 0.8),
        ('multiple', 'beginner', 0.8)
    ]
    
    print("Для начинающего студента:")
    print()
    
    for task_type, difficulty, mastery in task_scenarios:
        print(f"Задание: {task_type}, сложность: {difficulty}, освоение: {mastery:.1f}")
        
        # Тестируем решение 100 раз для получения вероятности
        attempts = 0
        for _ in range(100):
            if strategy.should_attempt_task_with_type(difficulty, mastery, task_type):
                attempts += 1
        
        probability = attempts / 100
        print(f"  Вероятность попытки: {probability:.2f}")
        print()


def main():
    """Основная функция тестирования"""
    print("ТЕСТИРОВАНИЕ СИСТЕМЫ С ТИПАМИ ЗАДАНИЙ И СЛОЖНОСТЬЮ")
    print("=" * 70)
    print()
    
    try:
        # Тест 1: BKT модель с типами заданий
        test_bkt_with_task_types()
        
        # Тест 2: Предпочтения студентов
        test_student_preferences()
        
        # Тест 3: Решения о попытках
        test_task_attempt_decisions()
        
        print("✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ УСПЕШНО!")
        
    except Exception as e:
        print(f"❌ ОШИБКА ВО ВРЕМЯ ТЕСТИРОВАНИЯ: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
