#!/usr/bin/env python3
"""
Тест алгоритмического объяснения без LLM
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

from mlmodels.llm.prompt_templates import PromptTemplates

def test_algorithmic_explanation():
    """Тест алгоритмического объяснения"""
    print("=== ТЕСТ АЛГОРИТМИЧЕСКОГО ОБЪЯСНЕНИЯ ===\n")
    
    # Создаем шаблоны промптов
    templates = PromptTemplates()
    
    # Тестовые данные
    test_case = {
        'student_name': 'Анна',
        'task_title': 'Переменные в Python',
        'task_difficulty': 'beginner',
        'task_type': 'true_false',
        'target_skill': 'Python основы',
        'target_skill_mastery': 0.1,
        'prerequisite_skills': [],
        'dependent_skills': [{'skill_name': 'Циклы'}],
        'student_progress': {'total_success_rate': 0.2}
    }
    
    print("📋 Тестовые данные:")
    print(f"   Студент: {test_case['student_name']}")
    print(f"   Задание: {test_case['task_title']}")
    print(f"   Навык: {test_case['target_skill']} ({test_case['target_skill_mastery']:.0%})")
    print(f"   Успешность: {test_case['student_progress']['total_success_rate']:.0%}")
    
    # Генерируем полный промпт
    full_prompt = templates.recommendation_explanation_prompt(
        student_name=test_case['student_name'],
        task_title=test_case['task_title'],
        task_difficulty=test_case['task_difficulty'],
        task_type=test_case['task_type'],
        target_skill=test_case['target_skill'],
        target_skill_mastery=test_case['target_skill_mastery'],
        prerequisite_skills=test_case['prerequisite_skills'],
        dependent_skills=test_case['dependent_skills'],
        student_progress=test_case['student_progress']
    )
    
    print(f"\n🤖 ПОЛНЫЙ ПРОМПТ С 'Сократи данный комментарий:':")
    print(f"   {full_prompt}")
    print(f"   Длина: {len(full_prompt)} символов")
    
    # Удаляем строку "Сократи данный комментарий:"
    if full_prompt.startswith("Сократи данный комментарий:\n\n"):
        clean_explanation = full_prompt[len("Сократи данный комментарий:\n\n"):]
    else:
        clean_explanation = full_prompt
    
    print(f"\n✨ АЛГОРИТМИЧЕСКОЕ ОБЪЯСНЕНИЕ (БЕЗ LLM-ПРОМПТА):")
    print(f"   {clean_explanation}")
    print(f"   Длина: {len(clean_explanation)} символов")
    
    print(f"\n✅ Тест завершен успешно!")

if __name__ == "__main__":
    test_algorithmic_explanation()
