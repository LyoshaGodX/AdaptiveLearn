#!/usr/bin/env python
"""
Скрипт для создания сводки по импортированным заданиям
"""

import os
import sys

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')

import django
django.setup()

from methodist.models import Task, TaskAnswer

def create_summary():
    """Создает сводку по всем заданиям в базе данных"""
    
    tasks = Task.objects.all().prefetch_related('answers', 'skills', 'courses').order_by('id')
    
    print(f"Всего заданий в базе данных: {tasks.count()}")
    print("=" * 80)
    
    type_counts = {}
    difficulty_counts = {}
    
    for task in tasks:
        # Подсчет статистики
        type_counts[task.task_type] = type_counts.get(task.task_type, 0) + 1
        difficulty_counts[task.difficulty] = difficulty_counts.get(task.difficulty, 0) + 1
        
        # Информация о задании
        print(f"ID: {task.id}")
        print(f"Название: {task.title}")
        print(f"Тип: {task.task_type}")
        print(f"Сложность: {task.difficulty}")
        print(f"Навыки: {', '.join([skill.name for skill in task.skills.all()])}")
        print(f"Курсы: {', '.join([course.name for course in task.courses.all()])}")
        print(f"Вариантов ответов: {task.answers.count()}")
        
        if task.answers.count() > 0:
            print("Варианты ответов:")
            for answer in task.answers.all().order_by('order'):
                status = "✓" if answer.is_correct else "✗"
                print(f"  {answer.order + 1}. {answer.text} {status}")
        
        print("-" * 80)
    
    print("\n📊 СТАТИСТИКА:")
    print(f"Типы заданий:")
    for task_type, count in type_counts.items():
        print(f"  {task_type}: {count}")
    
    print(f"Уровни сложности:")
    for difficulty, count in difficulty_counts.items():
        print(f"  {difficulty}: {count}")

if __name__ == '__main__':
    print("=" * 80)
    print("СВОДКА ПО ИМПОРТИРОВАННЫМ ЗАДАНИЯМ")
    print("=" * 80)
    
    create_summary()
