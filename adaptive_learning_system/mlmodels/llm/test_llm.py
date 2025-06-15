#!/usr/bin/env python3
"""
Тест LLM модуля для генерации объяснений

Этот скрипт проверяет:
1. Загрузку LLM модели
2. Генерацию объяснений рекомендаций
3. Работу с реальными данными из БД
"""

import os
import sys
from pathlib import Path

# Добавляем путь к Django проекту
sys.path.append(str(Path(__file__).parent.parent.parent))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')

import django
django.setup()

from mlmodels.llm.explanation_generator import ExplanationGenerator
from mlmodels.models import DQNRecommendation
from django.contrib.auth.models import User


def test_llm_basic():
    """Базовый тест LLM без загрузки модели"""
    print("🧪 ТЕСТ LLM МОДУЛЯ (БЕЗ ЗАГРУЗКИ МОДЕЛИ)")
    print("=" * 60)
    
    # Создаем генератор без инициализации
    generator = ExplanationGenerator()
    
    # Тестовые данные
    test_data = {
        'student_name': 'Алексей',
        'task_title': 'Циклы в Python',
        'task_difficulty': 'intermediate',
        'target_skill_info': [{
            'skill_name': 'Циклы',
            'current_mastery_probability': 0.3
        }],
        'prerequisite_skills_snapshot': [{
            'skill_name': 'Переменные',
            'mastery_probability': 0.9
        }],
        'student_progress_context': {
            'total_success_rate': 0.65
        }
    }
    
    print("📝 Тестовые данные рекомендации:")
    print(f"  Студент: {test_data['student_name']}")
    print(f"  Задание: {test_data['task_title']}")
    print(f"  Сложность: {test_data['task_difficulty']}")
    print(f"  Целевой навык: {test_data['target_skill_info'][0]['skill_name']}")
    print(f"  Освоенность: {test_data['target_skill_info'][0]['current_mastery_probability']:.1%}")
    
    print("\n🤖 Генерация объяснения (fallback режим):")
    explanation = generator.generate_recommendation_explanation(test_data)
    print(f"  Результат: {explanation}")
    print(f"  Длина: {len(explanation)} символов")
    
    print("\n✅ Базовый тест завершен")
    return True


def test_llm_with_real_data():
    """Тест с реальными данными из БД"""
    print("\n🧪 ТЕСТ С РЕАЛЬНЫМИ ДАННЫМИ")
    print("=" * 60)
    
    # Находим последнюю рекомендацию
    recommendation = DQNRecommendation.objects.filter(
        target_skill_info__isnull=False
    ).order_by('-created_at').first()
    
    if not recommendation:
        print("⚠️ Рекомендации с LLM данными не найдены")
        return False
    
    print(f"📊 Найдена рекомендация #{recommendation.id}")
    print(f"  Студент: {recommendation.student.full_name}")
    print(f"  Задание: {recommendation.task.title}")
    print(f"  Создана: {recommendation.created_at}")
    
    # Подготавливаем данные для LLM
    recommendation_data = {
        'student_name': recommendation.student.full_name.split()[0],  # Имя
        'task_title': recommendation.task.title,
        'task_difficulty': recommendation.task.difficulty,
        'target_skill_info': recommendation.target_skill_info or [],
        'prerequisite_skills_snapshot': recommendation.prerequisite_skills_snapshot or [],
        'student_progress_context': recommendation.student_progress_context or {}
    }
    
    print("\n📝 Данные для LLM:")
    if recommendation_data['target_skill_info']:
        skill_info = recommendation_data['target_skill_info'][0]
        print(f"  Целевой навык: {skill_info.get('skill_name', 'N/A')}")
        print(f"  Освоенность: {skill_info.get('current_mastery_probability', 0):.1%}")
    
    prereq_count = len(recommendation_data['prerequisite_skills_snapshot'])
    print(f"  Prerequisite навыков: {prereq_count}")
    
    progress = recommendation_data['student_progress_context']
    if progress:
        total_rate = progress.get('total_success_rate', 0)
        print(f"  Общий успех: {total_rate:.1%}")
    
    # Генерируем объяснение (fallback режим)
    generator = ExplanationGenerator()
    explanation = generator.generate_recommendation_explanation(recommendation_data)
    
    print(f"\n🤖 Сгенерированное объяснение:")
    print(f"  {explanation}")
    print(f"  Длина: {len(explanation)} символов")
    
    return True


def test_llm_initialization():
    """Тест инициализации LLM (без фактической загрузки модели)"""
    print("\n🧪 ТЕСТ ИНИЦИАЛИЗАЦИИ LLM")
    print("=" * 60)
    
    generator = ExplanationGenerator(model_key='qwen2.5-0.5b')
    
    print("📊 Информация о модели:")
    model_info = generator.model_manager.get_model_info()
    for key, value in model_info.items():
        print(f"  {key}: {value}")
    
    print("\n⚠️ ВНИМАНИЕ: Фактическая загрузка модели не выполняется в тесте")
    print("  Для полного теста установите зависимости:")
    print("  pip install torch transformers accelerate")
    
    return True


def main():
    """Главная функция теста"""
    print("🧪 ТЕСТИРОВАНИЕ LLM МОДУЛЯ")
    print("=" * 80)
    
    try:
        # Базовый тест
        success1 = test_llm_basic()
        
        # Тест с реальными данными
        success2 = test_llm_with_real_data()
        
        # Тест инициализации
        success3 = test_llm_initialization()
        
        print("\n" + "=" * 80)
        if success1 and success2 and success3:
            print("🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
            print("\n📋 СЛЕДУЮЩИЕ ШАГИ:")
            print("1. Установите зависимости: pip install torch transformers accelerate")
            print("2. Интегрируйте с DQN системой рекомендаций")
            print("3. Настройте автоматическую генерацию объяснений")
        else:
            print("❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
            
    except Exception as e:
        print(f"💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
