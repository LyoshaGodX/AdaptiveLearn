#!/usr/bin/env python
"""
Скрипт для добавления недостающих вариантов ответов к новым заданиям
"""

import os
import sys

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')

import django
django.setup()

from methodist.models import Task, TaskAnswer

def add_missing_answers():
    """Добавляет недостающие варианты ответов к заданиям"""
    
    tasks_without_answers = []
    for task in Task.objects.all():
        if task.answers.count() == 0:
            tasks_without_answers.append(task)
    
    print(f"Найдено заданий без вариантов ответов: {len(tasks_without_answers)}")
    
    # Задание 11: "Что такое переменная в Python" (true_false)
    try:
        task = Task.objects.get(id=11, task_type='true_false', title__contains='Что такое переменная')
        if task.answers.count() == 0:
            TaskAnswer.objects.create(task=task, text='Верно', is_correct=False, order=0)
            TaskAnswer.objects.create(task=task, text='Неверно', is_correct=True, order=1)
            print(f"✓ Добавлены варианты ответов для '{task.title}'")
    except Task.DoesNotExist:
        pass
    
    # Задание 12: "Выбор правильного синтаксиса переменной" (single)
    try:
        task = Task.objects.get(id=12, task_type='single', title__contains='правильного синтаксиса')
        if task.answers.count() == 0:
            answers_data = [
                ('var x = 10', False),
                ('x: int = 10', False),
                ('x = 10', True),
                ('int x = 10', False),
            ]
            for i, (text, is_correct) in enumerate(answers_data):
                TaskAnswer.objects.create(task=task, text=text, is_correct=is_correct, order=i)
            print(f"✓ Добавлены варианты ответов для '{task.title}'")
    except Task.DoesNotExist:
        pass
    
    # Задание 14: "Тип переменной определяется автоматически" (true_false)
    try:
        task = Task.objects.get(id=14, task_type='true_false', title__contains='Тип переменной определяется')
        if task.answers.count() == 0:
            TaskAnswer.objects.create(task=task, text='Верно', is_correct=False, order=0)
            TaskAnswer.objects.create(task=task, text='Неверно', is_correct=True, order=1)
            print(f"✓ Добавлены варианты ответов для '{task.title}'")
    except Task.DoesNotExist:
        pass
    
    # Задание 15: "Что выведет функция type()" (single)
    try:
        task = Task.objects.get(id=15, task_type='single', title__contains='type()')
        if task.answers.count() == 0:
            answers_data = [
                ("<class 'float'>", True),
                ("<type 'float'>", False),
                ("<float>", False),
                ("float", False),
            ]
            for i, (text, is_correct) in enumerate(answers_data):
                TaskAnswer.objects.create(task=task, text=text, is_correct=is_correct, order=i)
            print(f"✓ Добавлены варианты ответов для '{task.title}'")
    except Task.DoesNotExist:
        pass
    
    # Задание 18: "Работа с кэшированием целых чисел" (single)
    try:
        task = Task.objects.get(id=18, task_type='single', title__contains='кэшированием')
        if task.answers.count() == 0:
            answers_data = [
                ('True', True),
                ('False', False),
                ('Ошибка', False),
                ('None', False),
            ]
            for i, (text, is_correct) in enumerate(answers_data):
                TaskAnswer.objects.create(task=task, text=text, is_correct=is_correct, order=i)
            print(f"✓ Добавлены варианты ответов для '{task.title}'")
    except Task.DoesNotExist:
        pass

if __name__ == '__main__':
    print("=" * 50)
    print("ДОБАВЛЕНИЕ НЕДОСТАЮЩИХ ВАРИАНТОВ ОТВЕТОВ")
    print("=" * 50)
    
    add_missing_answers()
    
    print("\n✓ Добавление завершено!")
