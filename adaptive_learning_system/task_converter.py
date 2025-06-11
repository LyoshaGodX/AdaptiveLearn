#!/usr/bin/env python
"""
Конвертер заданий между JSON и человекочитаемым Markdown форматом
Позволяет экспортировать задания в удобный для LLM формат и импортировать обратно
"""

import os
import sys
import json
import re
from datetime import datetime

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')

import django
django.setup()

from methodist.models import Task, TaskAnswer
from skills.models import Skill, Course

def get_temp_dir():
    """Получает путь к temp_dir"""
    temp_dir = os.path.join(os.path.dirname(__file__), '..', 'temp_dir')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    return temp_dir

def json_to_markdown(json_file, markdown_file=None):
    """
    Конвертирует JSON файл с заданиями в человекочитаемый Markdown формат
    
    Args:
        json_file (str): Путь к JSON файлу
        markdown_file (str): Путь к выходному Markdown файлу
    
    Returns:
        str: Путь к созданному файлу
    """
    # Если путь не абсолютный, ищем файл в temp_dir
    if not os.path.isabs(json_file):
        json_file = os.path.join(get_temp_dir(), json_file)
    
    if not os.path.exists(json_file):
        print(f"Ошибка: Файл {json_file} не найден!")
        return None
    
    # Генерируем имя выходного файла если не указано
    if markdown_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        markdown_file = f"tasks_readable_{timestamp}.md"
    
    # Если путь не абсолютный, сохраняем в temp_dir
    if not os.path.isabs(markdown_file):
        markdown_file = os.path.join(get_temp_dir(), markdown_file)
    
    print(f"Конвертируем {json_file} в {markdown_file}")
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Ошибка чтения JSON файла: {e}")
        return None
    
    if 'tasks' not in data:
        print("Ошибка: В файле отсутствует секция 'tasks'")
        return None
    
    markdown_content = []
    markdown_content.append("# Задания для системы адаптивного обучения")
    markdown_content.append("")
    markdown_content.append(f"Экспортировано: {data.get('metadata', {}).get('export_date', 'N/A')}")
    markdown_content.append(f"Всего заданий: {len(data['tasks'])}")
    markdown_content.append("")
    markdown_content.append("---")
    markdown_content.append("")
    
    for i, task in enumerate(data['tasks'], 1):
        task_md = _task_to_markdown(task, i)
        markdown_content.append(task_md)
        markdown_content.append("")
        markdown_content.append("---")
        markdown_content.append("")
    
    # Добавляем руководство по формату в конец файла
    markdown_content.extend(_get_format_guide())
    
    try:
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(markdown_content))
        
        print(f"✓ Конвертация завершена!")
        print(f"Файл сохранен: {markdown_file}")
        print(f"Конвертировано заданий: {len(data['tasks'])}")
        
        return markdown_file
        
    except Exception as e:
        print(f"Ошибка записи файла: {e}")
        return None

def _task_to_markdown(task, task_number):
    """Конвертирует одно задание в Markdown формат"""
    
    lines = []
    lines.append(f"## Задание {task_number}")
    lines.append("")
    lines.append("```")
    lines.append(f"ЗАДАНИЕ: {task['title']}")
    lines.append(f"ТИП: {task['task_type']}")
    lines.append(f"СЛОЖНОСТЬ: {task['difficulty']}")
    
    # Навыки
    if task.get('skills'):
        skills_names = [skill['name'] for skill in task['skills']]
        lines.append(f"НАВЫКИ: {'; '.join(skills_names)}")
    
    # Курсы
    if task.get('courses'):
        courses_names = [course['name'] for course in task['courses']]
        lines.append(f"КУРСЫ: {'; '.join(courses_names)}")
    
    lines.append("")
    lines.append("ВОПРОС:")
    
    # Очищаем и форматируем текст вопроса
    question_text = task['question_text']
    question_text = question_text.replace('\r\n', '\n').replace('\r', '\n')
    question_text = question_text.strip()
    
    lines.append(question_text)
    lines.append("")
    
    # Варианты ответов (если есть)
    if task.get('answers') and task['answers']:
        lines.append("ВАРИАНТЫ:")
        
        # Сортируем по порядку
        answers = sorted(task['answers'], key=lambda x: x['order'])
        
        for i, answer in enumerate(answers):
            letter = chr(65 + i)  # A, B, C, D...
            lines.append(f"{letter}) {answer['text']}")
        
        lines.append("")
        
        # Правильные ответы
        if task['task_type'] == 'single':
            correct_answers = [answer for answer in answers if answer['is_correct']]
            if correct_answers:
                correct_idx = answers.index(correct_answers[0])
                correct_letter = chr(65 + correct_idx)
                lines.append(f"ПРАВИЛЬНЫЙ: {correct_letter}")
        
        elif task['task_type'] == 'multiple':
            correct_answers = [answer for answer in answers if answer['is_correct']]
            if correct_answers:
                correct_letters = []
                for answer in correct_answers:
                    correct_idx = answers.index(answer)
                    correct_letters.append(chr(65 + correct_idx))
                lines.append(f"ПРАВИЛЬНЫЕ: {', '.join(correct_letters)}")
        
        elif task['task_type'] == 'true_false':
            correct_answers = [answer for answer in answers if answer['is_correct']]
            if correct_answers:
                lines.append(f"ПРАВИЛЬНЫЙ: {correct_answers[0]['text']}")
    
    else:
        # Для заданий без вариантов ответов
        if task.get('correct_answer'):
            lines.append(f"ПРАВИЛЬНЫЙ ОТВЕТ: {task['correct_answer']}")
    
    # Объяснение
    if task.get('explanation') and task['explanation'].strip():
        lines.append(f"ОБЪЯСНЕНИЕ: {task['explanation'].strip()}")
    
    lines.append("```")
    
    return '\n'.join(lines)

def markdown_to_json(markdown_file, json_file=None):
    """
    Конвертирует Markdown файл с заданиями в JSON формат для импорта
    
    Args:
        markdown_file (str): Путь к Markdown файлу
        json_file (str): Путь к выходному JSON файлу
    
    Returns:
        str: Путь к созданному файлу
    """
    # Если путь не абсолютный, ищем файл в temp_dir
    if not os.path.isabs(markdown_file):
        markdown_file = os.path.join(get_temp_dir(), markdown_file)
    
    if not os.path.exists(markdown_file):
        print(f"Ошибка: Файл {markdown_file} не найден!")
        return None
    
    # Генерируем имя выходного файла если не указано
    if json_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = f"tasks_from_markdown_{timestamp}.json"
    
    # Если путь не абсолютный, сохраняем в temp_dir
    if not os.path.isabs(json_file):
        json_file = os.path.join(get_temp_dir(), json_file)
    
    print(f"Конвертируем {markdown_file} в {json_file}")
    
    try:
        with open(markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Ошибка чтения Markdown файла: {e}")
        return None
    
    # Парсим задания из Markdown
    tasks = _parse_tasks_from_markdown(content)
    
    if not tasks:
        print("Ошибка: Не найдено заданий в файле")
        return None
    
    # Создаем JSON структуру
    json_data = {
        'metadata': {
            'export_date': datetime.now().isoformat(),
            'total_tasks': len(tasks),
            'version': '1.0',
            'format': 'JSON',
            'description': 'Import from Markdown format',
            'source_file': os.path.basename(markdown_file)
        },
        'tasks': tasks
    }
    
    try:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ Конвертация завершена!")
        print(f"Файл сохранен: {json_file}")
        print(f"Конвертировано заданий: {len(tasks)}")
        
        return json_file
        
    except Exception as e:
        print(f"Ошибка записи JSON файла: {e}")
        return None

def _parse_tasks_from_markdown(content):
    """Парсит задания из Markdown содержимого"""
    tasks = []
    
    # Ищем блоки заданий между ## Задание N и следующим ## или концом файла
    sections = re.split(r'(## Задание \d+)', content)
    
    # Объединяем заголовки с их содержимым
    for i in range(1, len(sections), 2):
        if i + 1 < len(sections):
            section_content = sections[i + 1]
            # Ищем блок между первой и последней парой ```
            lines = section_content.split('\n')
            
            start_idx = -1
            end_idx = -1
            
            for j, line in enumerate(lines):
                if line.strip() == '```' and start_idx == -1:
                    start_idx = j + 1
                elif line.strip() == '```' and start_idx != -1:
                    end_idx = j
                    break
            
            if start_idx != -1 and end_idx != -1:
                task_block = '\n'.join(lines[start_idx:end_idx])
                task = _parse_single_task(task_block)
                if task:
                    tasks.append(task)
    
    return tasks

def _parse_single_task(block):
    """Парсит одно задание из текстового блока"""
    lines = [line.strip() for line in block.split('\n')]
    task = {}
    
    current_section = None
    question_lines = []
    variants = []
    
    for line in lines:
        if not line:
            continue
        
        # Основные поля
        if line.startswith('ЗАДАНИЕ:'):
            task['title'] = line[8:].strip()
        elif line.startswith('ТИП:'):
            task['task_type'] = line[4:].strip()
        elif line.startswith('СЛОЖНОСТЬ:'):
            task['difficulty'] = line[10:].strip()
        elif line.startswith('НАВЫКИ:'):
            skills_text = line[7:].strip()
            task['skills'] = [{'name': skill.strip()} for skill in skills_text.split(';') if skill.strip()]
        elif line.startswith('КУРСЫ:'):
            courses_text = line[6:].strip()
            task['courses'] = [{'name': course.strip()} for course in courses_text.split(';') if course.strip()]
        
        # Секции
        elif line == 'ВОПРОС:':
            current_section = 'question'
        elif line == 'ВАРИАНТЫ:':
            current_section = 'variants'
        elif line.startswith('ПРАВИЛЬНЫЙ:'):
            task['correct_single'] = line[11:].strip()
        elif line.startswith('ПРАВИЛЬНЫЕ:'):
            task['correct_multiple'] = line[11:].strip()
        elif line.startswith('ПРАВИЛЬНЫЙ ОТВЕТ:'):
            task['correct_answer'] = line[17:].strip()
        elif line.startswith('ОБЪЯСНЕНИЕ:'):
            task['explanation'] = line[11:].strip()
        
        # Содержимое секций
        elif current_section == 'question':
            question_lines.append(line)
        elif current_section == 'variants' and re.match(r'^[A-Z]\)', line):
            variants.append(line)
    
    # Собираем вопрос
    if question_lines:
        task['question_text'] = '\n'.join(question_lines)
    
    # Обрабатываем варианты ответов
    if variants:
        answers = []
        for i, variant in enumerate(variants):
            # Убираем букву и скобку
            text = re.sub(r'^[A-Z]\)\s*', '', variant)
            
            is_correct = False
            
            # Определяем правильность ответа
            if task.get('correct_single'):
                expected_letter = task['correct_single']
                current_letter = chr(65 + i)
                is_correct = (current_letter == expected_letter)
            
            elif task.get('correct_multiple'):
                correct_letters = [letter.strip() for letter in task['correct_multiple'].split(',')]
                current_letter = chr(65 + i)
                is_correct = (current_letter in correct_letters)
            
            elif task.get('task_type') == 'true_false':
                # Для true_false ищем совпадение с правильным ответом
                correct_text = task.get('correct_single', '')
                is_correct = (text.lower().strip() == correct_text.lower().strip())
            
            answers.append({
                'text': text,
                'is_correct': is_correct,
                'order': i
            })
        
        task['answers'] = answers
    
    # Устанавливаем значения по умолчанию
    task.setdefault('correct_answer', task.get('correct_answer', ''))
    task.setdefault('explanation', task.get('explanation', ''))
    task.setdefault('is_active', True)
    
    # Проверяем обязательные поля
    required_fields = ['title', 'task_type', 'difficulty', 'question_text']
    for field in required_fields:
        if not task.get(field):
            print(f"Предупреждение: Отсутствует поле {field} в задании {task.get('title', 'N/A')}")
            return None
    
    return task

def _get_format_guide():
    """Возвращает руководство по формату в конце файла"""
    return [
        "",
        "# 📝 Руководство по формату заданий",
        "",
        "## Структура задания:",
        "",
        "```",
        "ЗАДАНИЕ: Название задания",
        "ТИП: single|multiple|true_false",
        "СЛОЖНОСТЬ: beginner|intermediate|advanced",
        "НАВЫКИ: Навык 1; Навык 2; Навык 3",
        "КУРСЫ: Курс 1; Курс 2",
        "",
        "ВОПРОС:",
        "Текст вопроса...",
        "",
        "ВАРИАНТЫ:",
        "A) Вариант 1",
        "B) Вариант 2", 
        "C) Вариант 3",
        "",
        "ПРАВИЛЬНЫЙ: A (для single)",
        "ПРАВИЛЬНЫЕ: A, C (для multiple)",
        "ПРАВИЛЬНЫЙ ОТВЕТ: текст (если нет вариантов)",
        "",
        "ОБЪЯСНЕНИЕ: Пояснение к ответу",
        "```",
        "",
        "## Типы заданий:",
        "- **single** - один правильный ответ",
        "- **multiple** - несколько правильных ответов",
        "- **true_false** - верно/неверно",
        "",
        "## Уровни сложности:",
        "- **beginner** - начальный",
        "- **intermediate** - средний", 
        "- **advanced** - продвинутый",
        "",
        "## Примечания:",
        "- Навыки и курсы разделяются точкой с запятой",
        "- Для multiple заданий правильные ответы через запятую",
        "- Объяснение необязательно, но желательно"
    ]

if __name__ == '__main__':
    print("=" * 50)
    print("КОНВЕРТЕР ЗАДАНИЙ: JSON ↔ MARKDOWN")
    print("=" * 50)
    
    if len(sys.argv) < 3:
        print("Использование:")
        print("  python task_converter.py json2md <input.json> [output.md]")
        print("  python task_converter.py md2json <input.md> [output.json]")
        print("\nПримеры:")
        print("  python task_converter.py json2md tasks_export.json")
        print("  python task_converter.py md2json tasks_readable.md tasks_new.json")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    input_file = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    if command == 'json2md':
        result = json_to_markdown(input_file, output_file)
    elif command == 'md2json':
        result = markdown_to_json(input_file, output_file)
    else:
        print(f"Неизвестная команда: {command}")
        print("Доступные команды: json2md, md2json")
        sys.exit(1)
    
    if result:
        print("\n✓ Конвертация завершена успешно!")
    else:
        print("\n✗ Ошибка конвертации!")
    
    print("\nГотово!")
