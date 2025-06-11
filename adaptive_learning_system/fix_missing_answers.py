#!/usr/bin/env python
"""
Скрипт для добавления недостающих вариантов ответов к заданиям
"""

import os
import sys

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')

import django
django.setup()

from methodist.models import Task, TaskAnswer

def fix_missing_answers():
    """Добавляет недостающие варианты ответов к заданиям"""
    
    # Задание 8: "Тип переменной определяется автоматически" (true_false)
    try:
        task8 = Task.objects.get(id=8, task_type='true_false')
        
        # Удаляем старые варианты если есть
        task8.answers.all().delete()
        
        # Создаем варианты для true_false
        TaskAnswer.objects.create(
            task=task8,
            text='Верно',
            is_correct=False,  # Неверно, так как Python использует динамическую типизацию
            order=0
        )
        
        TaskAnswer.objects.create(
            task=task8,
            text='Неверно',
            is_correct=True,   # Правильно
            order=1
        )
        
        print(f"✓ Добавлены варианты ответов для задания '{task8.title}'")
        
    except Task.DoesNotExist:
        print("⚠ Задание 8 не найдено")
    
    # Задание 9: "Что выведет функция type()" (single)
    try:
        task9 = Task.objects.get(id=9, task_type='single')
        
        # Удаляем старые варианты если есть
        task9.answers.all().delete()
        
        # Создаем варианты для single choice
        answers_data = [
            ("<class 'float'>", True),
            ("<class 'int'>", False),
            ("<class 'str'>", False),
            ("<type 'float'>", False),
        ]
        
        for i, (text, is_correct) in enumerate(answers_data):
            TaskAnswer.objects.create(
                task=task9,
                text=text,
                is_correct=is_correct,
                order=i
            )
        
        print(f"✓ Добавлены варианты ответов для задания '{task9.title}'")
        
    except Task.DoesNotExist:
        print("⚠ Задание 9 не найдено")
    
    # Задание 10 уже имеет варианты ответов
    try:
        task10 = Task.objects.get(id=10, task_type='multiple')
        if task10.answers.count() > 0:
            print(f"✓ Задание '{task10.title}' уже имеет варианты ответов")
        else:
            print(f"⚠ Задание '{task10.title}' не имеет вариантов ответов")
    except Task.DoesNotExist:
        print("⚠ Задание 10 не найдено")

if __name__ == '__main__':
    print("=" * 50)
    print("ИСПРАВЛЕНИЕ НЕДОСТАЮЩИХ ВАРИАНТОВ ОТВЕТОВ")
    print("=" * 50)
    
    fix_missing_answers()
    
    print("\n✓ Исправление завершено!")
