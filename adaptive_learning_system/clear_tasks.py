#!/usr/bin/env python
"""
Скрипт для очистки всех заданий из базы данных
"""

import os
import sys

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')

import django
django.setup()

from methodist.models import Task, TaskAnswer

def clear_all_tasks():
    """Удаляет все задания и варианты ответов из базы данных"""
    
    # Считаем количество заданий перед удалением
    tasks_count = Task.objects.count()
    answers_count = TaskAnswer.objects.count()
    
    print(f"Найдено заданий: {tasks_count}")
    print(f"Найдено вариантов ответов: {answers_count}")
    
    if tasks_count == 0:
        print("База данных уже пуста")
        return
    
    # Удаляем все варианты ответов (каскадно удалятся при удалении заданий)
    # Удаляем все задания
    Task.objects.all().delete()
    
    print(f"✓ Удалено заданий: {tasks_count}")
    print(f"✓ Удалено вариантов ответов: {answers_count}")

if __name__ == '__main__':
    print("=" * 50)
    print("ОЧИСТКА БАЗЫ ДАННЫХ ЗАДАНИЙ")
    print("=" * 50)
    
    try:
        clear_all_tasks()
        print("\n✓ Очистка завершена!")
    except Exception as e:
        print(f"Ошибка при очистке: {e}")
        import traceback
        traceback.print_exc()
