#!/usr/bin/env python3
"""
Тест реальной загрузки LLM модели

ВНИМАНИЕ: Этот тест загружает настоящую LLM модель, 
что может занять время и требует достаточно памяти.
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


def test_real_llm_loading():
    """Тест реальной загрузки и генерации с LLM"""
    print("🧪 ТЕСТ РЕАЛЬНОЙ ЗАГРУЗКИ LLM")
    print("=" * 60)
    
    # Создаем генератор
    generator = ExplanationGenerator(model_key='qwen2.5-0.5b', device='auto')
    
    print("📊 Информация о модели:")
    model_info = generator.model_manager.get_model_info()
    for key, value in model_info.items():
        print(f"  {key}: {value}")
    
    print(f"\n🚀 Инициализируем LLM модель...")
    print("   ⚠️ Это может занять несколько минут при первом запуске")
    
    # Инициализируем модель
    success = generator.initialize(use_quantization=True)
    
    if not success:
        print("❌ Ошибка инициализации LLM")
        return False
    
    print("✅ LLM успешно инициализирована!")
    
    # Тестовые данные
    test_data = {
        'student_name': 'Алексей',
        'task_title': 'Работа со словарями',
        'task_difficulty': 'beginner',
        'target_skill_info': [{
            'skill_name': 'Словари в Python',
            'current_mastery_probability': 0.2
        }],
        'prerequisite_skills_snapshot': [{
            'skill_name': 'Основы Python',
            'mastery_probability': 0.8
        }],
        'student_progress_context': {
            'total_success_rate': 0.75
        }
    }
    
    print("\n🤖 Генерируем объяснение с помощью LLM...")
    explanation = generator.generate_recommendation_explanation(test_data)
    
    print(f"\n📝 РЕЗУЛЬТАТ:")
    print(f"  {explanation}")
    print(f"  Длина: {len(explanation)} символов")
    
    # Тест с реальными данными
    print("\n🧪 ТЕСТ С РЕАЛЬНЫМИ ДАННЫМИ ИЗ БД")
    recommendation = DQNRecommendation.objects.filter(
        target_skill_info__isnull=False
    ).order_by('-created_at').first()
    
    if recommendation:
        print(f"📊 Рекомендация #{recommendation.id}")
        print(f"  Студент: {recommendation.student.full_name}")
        print(f"  Задание: {recommendation.task.title}")
        
        recommendation_data = {
            'student_name': recommendation.student.full_name.split()[0],
            'task_title': recommendation.task.title,
            'task_difficulty': recommendation.task.difficulty,
            'target_skill_info': recommendation.target_skill_info or [],
            'prerequisite_skills_snapshot': recommendation.prerequisite_skills_snapshot or [],
            'student_progress_context': recommendation.student_progress_context or {}
        }
        
        real_explanation = generator.generate_recommendation_explanation(recommendation_data)
        print(f"\n📝 ОБЪЯСНЕНИЕ ДЛЯ РЕАЛЬНОЙ РЕКОМЕНДАЦИИ:")
        print(f"  {real_explanation}")
        print(f"  Длина: {len(real_explanation)} символов")
    
    print("\n✅ Тест завершен успешно!")
    return True


def main():
    """Главная функция"""
    print("🧪 ТЕСТИРОВАНИЕ РЕАЛЬНОЙ LLM")
    print("=" * 80)
    
    try:
        success = test_real_llm_loading()
        
        print("\n" + "=" * 80)
        if success:
            print("🎉 ТЕСТ РЕАЛЬНОЙ LLM ПРОШЕЛ УСПЕШНО!")
            print("\n📋 LLM ГОТОВА К ИНТЕГРАЦИИ:")
            print("1. Модель успешно загружается и генерирует текст")
            print("2. Можно интегрировать в recommendation_manager_fixed.py")
            print("3. Настроить автоматическое сохранение объяснений в БД")
        else:
            print("❌ ТЕСТ НЕ ПРОШЕЛ")
            
    except Exception as e:
        print(f"💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
