#!/usr/bin/env python3
"""
Краткий тест LLM модуля - показывает промпты и результаты
"""

import os
import sys
from pathlib import Path

# Добавляем путь к Django проекту
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')

import django
django.setup()

from mlmodels.llm.explanation_generator import ExplanationGenerator
from mlmodels.llm.prompt_templates import PromptTemplates

def test_llm_generation():
    """Основной тест генерации LLM"""
    print("=== ТЕСТ LLM ГЕНЕРАЦИИ ===\n")
    
    # Инициализируем LLM
    generator = ExplanationGenerator(model_key='gemma-2b', device='auto')
    
    if not generator.is_initialized:
        print("Загружаем LLM модель...")
        success = generator.initialize(use_quantization=True)
        if not success:
            print("❌ Ошибка загрузки модели")
            return
        print("✅ Модель загружена\n")
    
    # Создаем шаблоны промптов
    templates = PromptTemplates()
    
    # Тестовые случаи
    test_cases = [
        {
            'name': 'Новичок',
            'student_name': 'Анна',
            'task_title': 'Переменные Python',
            'task_difficulty': 'beginner',
            'task_type': 'true_false',
            'target_skill': 'Python основы',
            'target_skill_mastery': 0.1,
            'prerequisite_skills': [],
            'dependent_skills': [{'skill_name': 'Циклы'}],
            'student_progress': {'total_success_rate': 0.2}
        },
        {
            'name': 'Средний',
            'student_name': 'Михаил',
            'task_title': 'Цикл for',
            'task_difficulty': 'intermediate',
            'task_type': 'single',
            'target_skill': 'Циклы',
            'target_skill_mastery': 0.4,
            'prerequisite_skills': [{'skill_name': 'Python основы', 'mastery_probability': 0.8}],
            'dependent_skills': [{'skill_name': 'Функции'}],
            'student_progress': {'total_success_rate': 0.6}
        },
        {
            'name': 'Продвинутый',
            'student_name': 'Елена',
            'task_title': 'Рекурсия',
            'task_difficulty': 'advanced',
            'task_type': 'multiple',
            'target_skill': 'Алгоритмы',
            'target_skill_mastery': 0.7,
            'prerequisite_skills': [{'skill_name': 'Функции', 'mastery_probability': 0.9}],
            'dependent_skills': [{'skill_name': 'Структуры данных'}],
            'student_progress': {'total_success_rate': 0.8}
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"--- ТЕСТ {i}: {case['name']} ---")
        
        # Создаем промпт
        prompt = templates.recommendation_explanation_prompt(
            student_name=case['student_name'],
            task_title=case['task_title'],
            task_difficulty=case['task_difficulty'],
            task_type=case['task_type'],
            target_skill=case['target_skill'],
            target_skill_mastery=case['target_skill_mastery'],
            prerequisite_skills=case['prerequisite_skills'],
            dependent_skills=case['dependent_skills'],
            student_progress=case['student_progress']
        )
        
        print(f"ПРОМПТ:")
        print(f"  {prompt}")
        print(f"  (Длина: {len(prompt)} символов)")
        
        # Генерируем ответ
        data = {
            'student_name': case['student_name'],
            'task_title': case['task_title'],
            'task_difficulty': case['task_difficulty'],
            'task_type': case['task_type'],
            'target_skill_info': [{'skill_name': case['target_skill'], 'current_mastery_probability': case['target_skill_mastery']}],
            'prerequisite_skills_snapshot': case['prerequisite_skills'],
            'dependent_skills_snapshot': case['dependent_skills'],
            'student_progress_context': case['student_progress']
        }
        
        result = generator.generate_recommendation_explanation(data)
        
        print(f"\nРЕЗУЛЬТАТ:")
        if result:
            print(f"  {result}")
            print(f"  (Длина: {len(result)} символов)")
        else:
            print("  [ПУСТОЙ ОТВЕТ]")
        
        print(f"\n{'='*50}\n")


def main():
    """Главная функция"""
    try:
        user_input = input("Загрузить LLM для тестирования? (y/N): ").strip().lower()
        
        if user_input in ['y', 'yes', 'д', 'да']:
            test_llm_generation()
        else:
            print("Тест пропущен")
        
    except KeyboardInterrupt:
        print("\nТест прерван")
    except Exception as e:
        print(f"Ошибка: {e}")


if __name__ == "__main__":
    main()
