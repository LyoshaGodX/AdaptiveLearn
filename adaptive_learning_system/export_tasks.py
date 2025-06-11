#!/usr/bin/env python
"""
Скрипт для экспорта всех заданий из базы данных в различные форматы
Поддерживает JSON, CSV и Excel форматы
Экспортирует в temp_dir
Включает все поля заданий, связанные навыки, курсы и варианты ответов
"""

import os
import sys
import json
import csv
from datetime import datetime

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')

import django
django.setup()

from methodist.models import Task, TaskAnswer
from skills.models import Skill, Course

# Пытаемся импортировать pandas для Excel
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

def get_temp_dir():
    """Получает путь к temp_dir"""
    temp_dir = os.path.join(os.path.dirname(__file__), '..', 'temp_dir')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    return temp_dir

def export_tasks_to_json(output_file=None):
    """
    Экспортирует все задания в JSON файл
    
    Args:
        output_file (str): Путь к выходному файлу. Если None, создается автоматически.
    
    Returns:
        str: Путь к созданному файлу
    """
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"tasks_export_{timestamp}.json"
    
    # Получаем все задания с предзагрузкой связанных данных
    tasks = Task.objects.all().prefetch_related(
        'skills', 'courses', 'answers'
    ).order_by('id')
    
    exported_data = {
        'metadata': {
            'export_date': datetime.now().isoformat(),
            'total_tasks': tasks.count(),
            'version': '1.0',
            'format': 'JSON',
            'description': 'Export of all tasks from adaptive learning system'
        },
        'tasks': []
    }
    
    print(f"Экспортируем {tasks.count()} заданий в JSON...")
    
    for task in tasks:
        task_data = _get_task_data(task)
        exported_data['tasks'].append(task_data)
        print(f"  Обработано задание: {task.title}")
    
    # Сохраняем в temp_dir
    output_path = os.path.join(get_temp_dir(), output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(exported_data, f, ensure_ascii=False, indent=2)
    
    _print_export_stats(output_path, exported_data['tasks'])
    return output_path

def export_tasks_to_csv(output_file=None):
    """
    Экспортирует все задания в CSV файл
    
    Args:
        output_file (str): Путь к выходному файлу. Если None, создается автоматически.
    
    Returns:
        str: Путь к созданному файлу
    """
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"tasks_export_{timestamp}.csv"
    
    # Получаем все задания с предзагрузкой связанных данных
    tasks = Task.objects.all().prefetch_related(
        'skills', 'courses', 'answers'
    ).order_by('id')
    
    print(f"Экспортируем {tasks.count()} заданий в CSV...")
    
    # Подготавливаем данные для CSV
    csv_data = []
    for task in tasks:
        row = _prepare_task_row_for_csv(task)
        csv_data.append(row)
        print(f"  Обработано задание: {task.title}")
    
    # Сохраняем в temp_dir
    output_path = os.path.join(get_temp_dir(), output_file)
    
    if csv_data:
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
            writer.writeheader()
            writer.writerows(csv_data)
    
    print(f"\nЭкспорт в CSV завершен!")
    print(f"Файл сохранен: {output_path}")
    print(f"Экспортировано заданий: {len(csv_data)}")
    
    return output_path

def export_tasks_to_excel(output_file=None):
    """
    Экспортирует все задания в Excel файл
    
    Args:
        output_file (str): Путь к выходному файлу. Если None, создается автоматически.
    
    Returns:
        str: Путь к созданному файлу
    """
    if not PANDAS_AVAILABLE:
        print("Ошибка: pandas не установлен. Установите: pip install pandas openpyxl")
        return None
    
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"tasks_export_{timestamp}.xlsx"
    
    # Получаем все задания с предзагрузкой связанных данных
    tasks = Task.objects.all().prefetch_related(
        'skills', 'courses', 'answers'
    ).order_by('id')
    
    print(f"Экспортируем {tasks.count()} заданий в Excel...")
    
    # Подготавливаем данные для Excel
    excel_data = []
    answers_data = []
    
    for task in tasks:
        row = _prepare_task_row_for_csv(task)
        excel_data.append(row)
        
        # Добавляем варианты ответов в отдельный лист
        for answer in task.answers.all():
            answers_data.append({
                'task_id': task.id,
                'task_title': task.title,
                'answer_text': answer.text,
                'is_correct': answer.is_correct,
                'order': answer.order
            })
        
        print(f"  Обработано задание: {task.title}")
    
    # Сохраняем в temp_dir
    output_path = os.path.join(get_temp_dir(), output_file)
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Основной лист с заданиями
        df_tasks = pd.DataFrame(excel_data)
        df_tasks.to_excel(writer, sheet_name='Tasks', index=False)
        
        # Лист с вариантами ответов
        if answers_data:
            df_answers = pd.DataFrame(answers_data)
            df_answers.to_excel(writer, sheet_name='Answers', index=False)
    
    print(f"\nЭкспорт в Excel завершен!")
    print(f"Файл сохранен: {output_path}")
    print(f"Экспортировано заданий: {len(excel_data)}")
    print(f"Создано листов: Tasks, Answers")
    
    return output_path

def _get_task_data(task):
    """Получает данные задания в формате для JSON"""
    # Основные данные задания
    task_data = {
        'id': task.id,
        'title': task.title,
        'task_type': task.task_type,
        'difficulty': task.difficulty,
        'question_text': task.question_text,
        'correct_answer': task.correct_answer,
        'explanation': task.explanation,
        'is_active': task.is_active,
        'created_at': task.created_at.isoformat() if task.created_at else None,
        'updated_at': task.updated_at.isoformat() if task.updated_at else None,
    }
    
    # Связанные навыки
    task_data['skills'] = []
    for skill in task.skills.all():
        task_data['skills'].append({
            'id': skill.id,
            'name': skill.name,
            'is_base': skill.is_base,
            'description': skill.description
        })
    
    # Связанные курсы
    task_data['courses'] = []
    for course in task.courses.all():
        task_data['courses'].append({
            'id': course.id,
            'name': course.name,
            'description': course.description
        })
    
    # Варианты ответов
    task_data['answers'] = []
    for answer in task.answers.all().order_by('order'):
        task_data['answers'].append({
            'text': answer.text,
            'is_correct': answer.is_correct,
            'order': answer.order
        })
    
    return task_data

def _prepare_task_row_for_csv(task):
    """Подготавливает строку задания для CSV/Excel"""
    # Получаем связанные данные
    skills_names = '; '.join([skill.name for skill in task.skills.all()])
    skills_ids = '; '.join([str(skill.id) for skill in task.skills.all()])
    courses_names = '; '.join([course.name for course in task.courses.all()])
    courses_ids = '; '.join([str(course.id) for course in task.courses.all()])
    
    # Варианты ответов
    answers = task.answers.all().order_by('order')
    answers_text = ' | '.join([f"{a.order+1}. {a.text}" for a in answers])
    correct_answers = '; '.join([f"{a.order+1}. {a.text}" for a in answers if a.is_correct])
    
    return {
        'ID': task.id,
        'Название': task.title,
        'Тип задания': task.task_type,
        'Сложность': task.difficulty,
        'Вопрос': task.question_text,
        'Правильный ответ (поле)': task.correct_answer,
        'Объяснение': task.explanation,
        'Активно': task.is_active,
        'Дата создания': task.created_at.strftime('%Y-%m-%d %H:%M:%S') if task.created_at else '',
        'Дата обновления': task.updated_at.strftime('%Y-%m-%d %H:%M:%S') if task.updated_at else '',
        'Навыки (названия)': skills_names,
        'Навыки (ID)': skills_ids,
        'Курсы (названия)': courses_names,
        'Курсы (ID)': courses_ids,
        'Варианты ответов': answers_text,
        'Правильные ответы': correct_answers,
        'Количество вариантов': answers.count()
    }

def _print_export_stats(output_path, tasks_data):
    """Выводит статистику экспорта"""
    print(f"\nЭкспорт завершен!")
    print(f"Файл сохранен: {output_path}")
    print(f"Экспортировано заданий: {len(tasks_data)}")
    
    # Статистика по типам заданий
    task_types = {}
    difficulties = {}
    for task in tasks_data:
        task_type = task['task_type']
        difficulty = task['difficulty']
        task_types[task_type] = task_types.get(task_type, 0) + 1
        difficulties[difficulty] = difficulties.get(difficulty, 0) + 1
    
    print(f"\nСтатистика по типам заданий:")
    for task_type, count in task_types.items():
        print(f"  {task_type}: {count}")
    
    print(f"\nСтатистика по уровням сложности:")
    for difficulty, count in difficulties.items():
        print(f"  {difficulty}: {count}")

def export_specific_tasks(task_ids, output_file=None, format='json'):
    """
    Экспортирует конкретные задания по их ID
    
    Args:
        task_ids (list): Список ID заданий для экспорта
        output_file (str): Путь к выходному файлу
        format (str): Формат экспорта ('json', 'csv', 'excel')
    
    Returns:
        str: Путь к созданному файлу
    """
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = 'json' if format == 'json' else ('csv' if format == 'csv' else 'xlsx')
        output_file = f"tasks_specific_export_{timestamp}.{ext}"
    
    tasks = Task.objects.filter(id__in=task_ids).prefetch_related(
        'skills', 'courses', 'answers'
    ).order_by('id')
    
    if not tasks.exists():
        print("Задания с указанными ID не найдены!")
        return None
    
    print(f"Экспортируем {tasks.count()} конкретных заданий в формате {format.upper()}...")
    
    if format == 'csv':
        return _export_tasks_list_to_csv(tasks, output_file)
    elif format == 'excel':
        return _export_tasks_list_to_excel(tasks, output_file)
    else:  # json
        return _export_tasks_list_to_json(tasks, output_file, task_ids)

def _export_tasks_list_to_json(tasks, output_file, task_ids=None):
    """Экспорт списка заданий в JSON"""
    exported_data = {
        'metadata': {
            'export_date': datetime.now().isoformat(),
            'total_tasks': tasks.count(),
            'exported_task_ids': task_ids or [task.id for task in tasks],
            'version': '1.0',
            'format': 'JSON',
            'description': 'Export of specific tasks from adaptive learning system'
        },
        'tasks': []
    }
    
    for task in tasks:
        task_data = _get_task_data(task)
        exported_data['tasks'].append(task_data)
        print(f"  Обработано задание: {task.title}")
    
    output_path = os.path.join(get_temp_dir(), output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(exported_data, f, ensure_ascii=False, indent=2)
    
    _print_export_stats(output_path, exported_data['tasks'])
    return output_path

def _export_tasks_list_to_csv(tasks, output_file):
    """Экспорт списка заданий в CSV"""
    csv_data = []
    for task in tasks:
        row = _prepare_task_row_for_csv(task)
        csv_data.append(row)
        print(f"  Обработано задание: {task.title}")
    
    output_path = os.path.join(get_temp_dir(), output_file)
    
    if csv_data:
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=csv_data[0].keys())
            writer.writeheader()
            writer.writerows(csv_data)
    
    print(f"\nЭкспорт в CSV завершен!")
    print(f"Файл сохранен: {output_path}")
    print(f"Экспортировано заданий: {len(csv_data)}")
    
    return output_path

def _export_tasks_list_to_excel(tasks, output_file):
    """Экспорт списка заданий в Excel"""
    if not PANDAS_AVAILABLE:
        print("Ошибка: pandas не установлен. Установите: pip install pandas openpyxl")
        return None
    
    excel_data = []
    answers_data = []
    
    for task in tasks:
        row = _prepare_task_row_for_csv(task)
        excel_data.append(row)
        
        for answer in task.answers.all():
            answers_data.append({
                'task_id': task.id,
                'task_title': task.title,
                'answer_text': answer.text,
                'is_correct': answer.is_correct,
                'order': answer.order
            })
        
        print(f"  Обработано задание: {task.title}")
    
    output_path = os.path.join(get_temp_dir(), output_file)
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df_tasks = pd.DataFrame(excel_data)
        df_tasks.to_excel(writer, sheet_name='Tasks', index=False)
        
        if answers_data:
            df_answers = pd.DataFrame(answers_data)
            df_answers.to_excel(writer, sheet_name='Answers', index=False)
    
    print(f"\nЭкспорт в Excel завершен!")
    print(f"Файл сохранен: {output_path}")
    print(f"Экспортировано заданий: {len(excel_data)}")
    
    return output_path

def export_tasks_by_filter(format='json', **filters):
    """
    Экспортирует задания по фильтрам
    
    Args:
        format (str): Формат экспорта ('json', 'csv', 'excel')
        **filters: Фильтры для заданий (task_type, difficulty, skills__name, courses__id и т.д.)
    
    Returns:
        str: Путь к созданному файлу
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = 'json' if format == 'json' else ('csv' if format == 'csv' else 'xlsx')
    output_file = f"tasks_filtered_export_{timestamp}.{ext}"
    
    tasks = Task.objects.filter(**filters).prefetch_related(
        'skills', 'courses', 'answers'
    ).order_by('id')
    
    if not tasks.exists():
        print("Задания с указанными фильтрами не найдены!")
        return None
    
    print(f"Найдено заданий по фильтрам: {tasks.count()}")
    print(f"Фильтры: {filters}")
    
    if format == 'csv':
        return _export_tasks_list_to_csv(tasks, output_file)
    elif format == 'excel':
        return _export_tasks_list_to_excel(tasks, output_file)
    else:  # json
        return _export_tasks_list_to_json(tasks, output_file)

if __name__ == '__main__':
    print("=" * 50)
    print("СКРИПТ ЭКСПОРТА ЗАДАНИЙ")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        # Определяем формат экспорта
        format_arg = 'json'  # по умолчанию
        if '--format' in sys.argv:
            format_idx = sys.argv.index('--format')
            if format_idx + 1 < len(sys.argv):
                format_arg = sys.argv[format_idx + 1].lower()
                if format_arg not in ['json', 'csv', 'excel']:
                    print(f"Неподдерживаемый формат: {format_arg}")
                    print("Доступные форматы: json, csv, excel")
                    sys.exit(1)
        
        if command == 'all':
            # Экспорт всех заданий
            if format_arg == 'csv':
                export_tasks_to_csv()
            elif format_arg == 'excel':
                export_tasks_to_excel()
            else:
                export_tasks_to_json()
                
        elif command == 'ids':
            # Экспорт конкретных заданий по ID
            if len(sys.argv) < 3:
                print("Использование: python export_tasks.py ids 1,2,3 [--format json|csv|excel]")
                sys.exit(1)
            
            try:
                task_ids = [int(x.strip()) for x in sys.argv[2].split(',')]
                export_specific_tasks(task_ids, format=format_arg)
            except ValueError:
                print("Ошибка: Неверный формат ID заданий. Используйте: 1,2,3")
                sys.exit(1)
                
        elif command == 'type':
            # Экспорт по типу задания
            if len(sys.argv) < 3:
                print("Использование: python export_tasks.py type single [--format json|csv|excel]")
                print("Доступные типы: single, multiple, true_false")
                sys.exit(1)
            
            task_type = sys.argv[2]
            export_tasks_by_filter(format=format_arg, task_type=task_type)
            
        elif command == 'difficulty':
            # Экспорт по уровню сложности
            if len(sys.argv) < 3:
                print("Использование: python export_tasks.py difficulty beginner [--format json|csv|excel]")
                print("Доступные уровни: beginner, intermediate, advanced")
                sys.exit(1)
            
            difficulty = sys.argv[2]
            export_tasks_by_filter(format=format_arg, difficulty=difficulty)
            
        elif command == 'course':
            # Экспорт по курсу
            if len(sys.argv) < 3:
                print("Использование: python export_tasks.py course C1 [--format json|csv|excel]")
                sys.exit(1)
            
            course_id = sys.argv[2]
            export_tasks_by_filter(format=format_arg, courses__id=course_id)
            
        else:
            print(f"Неизвестная команда: {command}")
            print("\nДоступные команды:")
            print("  all                    - экспорт всех заданий")
            print("  ids 1,2,3             - экспорт конкретных заданий")
            print("  type single           - экспорт по типу")
            print("  difficulty beginner   - экспорт по сложности")
            print("  course C1             - экспорт по курсу")
            print("\nДоступные форматы (--format):")
            print("  json                  - JSON формат (по умолчанию)")
            print("  csv                   - CSV формат")
            print("  excel                 - Excel формат (.xlsx)")
    else:
        # По умолчанию экспортируем все задания в JSON
        print("Команда не указана. Экспортируем все задания в JSON...")
        export_tasks_to_json()
    
    print("\nГотово!")
