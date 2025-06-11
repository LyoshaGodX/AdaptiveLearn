#!/usr/bin/env python
"""
Скрипт для импорта заданий в базу данных из различных форматов
Поддерживает JSON, CSV и Excel форматы
Работает с temp_dir
Поддерживает создание новых заданий и обновление существующих
"""

import os
import sys
import json
import csv
from datetime import datetime
from django.utils.dateparse import parse_datetime

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')

import django
django.setup()

from django.db import transaction
from methodist.models import Task, TaskAnswer
from skills.models import Skill, Course

# Импортируем функции конвертации
from task_converter import markdown_to_json

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

class TaskImporter:
    def __init__(self):
        self.created_count = 0
        self.updated_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.errors = []
    
    def import_tasks_from_json(self, json_file, update_existing=False, dry_run=False):
        """
        Импортирует задания из JSON файла
        
        Args:
            json_file (str): Путь к JSON файлу (ищется в temp_dir если не абсолютный путь)
            update_existing (bool): Обновлять существующие задания
            dry_run (bool): Режим тестирования без изменений в БД
        
        Returns:
            dict: Статистика импорта
        """
        # Если путь не абсолютный, ищем файл в temp_dir
        if not os.path.isabs(json_file):
            json_file = os.path.join(get_temp_dir(), json_file)
        
        if not os.path.exists(json_file):
            print(f"Ошибка: Файл {json_file} не найден!")
            return None
        
        print(f"Загружаем данные из файла: {json_file}")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Ошибка разбора JSON: {e}")
            return None
        except Exception as e:
            print(f"Ошибка чтения файла: {e}")
            return None
        
        if 'tasks' not in data:
            print("Ошибка: В файле отсутствует секция 'tasks'")
            return None
        
        tasks_data = data['tasks']
        total_tasks = len(tasks_data)
        
        print(f"Найдено заданий для импорта: {total_tasks}")
        
        if dry_run:
            print("РЕЖИМ ТЕСТИРОВАНИЯ: Изменения не будут сохранены в базу данных")
        
        # Импортируем задания
        for i, task_data in enumerate(tasks_data, 1):
            print(f"Обрабатываем задание {i}/{total_tasks}: {task_data.get('title', 'Без названия')}")
            
            if dry_run:
                self._validate_task_data(task_data)
            else:                self._import_single_task(task_data, update_existing)
        
        # Добавляем недостающие варианты ответов
        self._add_missing_answers(dry_run)
        
        # Возвращаем статистику
        stats = {
            'total_processed': total_tasks,
            'created': self.created_count,
            'updated': self.updated_count,
            'skipped': self.skipped_count,
            'errors': self.error_count,
            'error_details': self.errors
        }
        
        self._print_import_stats(stats, dry_run)
        return stats
    
    def import_tasks_from_csv(self, csv_file, update_existing=False, dry_run=False):
        """
        Импортирует задания из CSV файла
        
        Args:
            csv_file (str): Путь к CSV файлу (ищется в temp_dir если не абсолютный путь)
            update_existing (bool): Обновлять существующие задания
            dry_run (bool): Режим тестирования без изменений в БД
        
        Returns:
            dict: Статистика импорта
        """
        # Если путь не абсолютный, ищем файл в temp_dir
        if not os.path.isabs(csv_file):
            csv_file = os.path.join(get_temp_dir(), csv_file)
        
        if not os.path.exists(csv_file):
            print(f"Ошибка: Файл {csv_file} не найден!")
            return None
        
        print(f"Загружаем данные из CSV файла: {csv_file}")
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                csv_data = list(reader)
        except Exception as e:
            print(f"Ошибка чтения CSV файла: {e}")
            return None
        
        total_tasks = len(csv_data)
        print(f"Найдено строк для импорта: {total_tasks}")
        
        if dry_run:
            print("РЕЖИМ ТЕСТИРОВАНИЯ: Изменения не будут сохранены в базу данных")
        
        # Импортируем задания
        for i, row in enumerate(csv_data, 1):
            print(f"Обрабатываем строку {i}/{total_tasks}: {row.get('Название', 'Без названия')}")
            
            # Конвертируем CSV данные в формат задания
            task_data = self._convert_csv_row_to_task_data(row)
            
            if dry_run:
                self._validate_task_data(task_data)
            else:
                self._import_single_task(task_data, update_existing)
        
        # Добавляем недостающие варианты ответов
        self._add_missing_answers(dry_run)
        
        # Возвращаем статистику
        stats = {
            'total_processed': total_tasks,
            'created': self.created_count,
            'updated': self.updated_count,
            'skipped': self.skipped_count,
            'errors': self.error_count,
            'error_details': self.errors
        }
        
        self._print_import_stats(stats, dry_run)
        return stats
    
    def import_tasks_from_excel(self, excel_file, update_existing=False, dry_run=False):
        """
        Импортирует задания из Excel файла
        
        Args:
            excel_file (str): Путь к Excel файлу (ищется в temp_dir если не абсолютный путь)
            update_existing (bool): Обновлять существующие задания
            dry_run (bool): Режим тестирования без изменений в БД
        
        Returns:
            dict: Статистика импорта
        """
        if not PANDAS_AVAILABLE:
            print("Ошибка: pandas не установлен. Установите: pip install pandas openpyxl")
            return None
        
        # Если путь не абсолютный, ищем файл в temp_dir
        if not os.path.isabs(excel_file):
            excel_file = os.path.join(get_temp_dir(), excel_file)
        
        if not os.path.exists(excel_file):
            print(f"Ошибка: Файл {excel_file} не найден!")
            return None
        
        print(f"Загружаем данные из Excel файла: {excel_file}")
        
        try:
            # Читаем лист с заданиями
            df = pd.read_excel(excel_file, sheet_name='Tasks')
            excel_data = df.to_dict('records')
        except Exception as e:
            print(f"Ошибка чтения Excel файла: {e}")
            return None
        
        total_tasks = len(excel_data)
        print(f"Найдено строк для импорта: {total_tasks}")
        
        if dry_run:
            print("РЕЖИМ ТЕСТИРОВАНИЯ: Изменения не будут сохранены в базу данных")
          # Импортируем задания
        for i, row in enumerate(excel_data, 1):
            print(f"Обрабатываем строку {i}/{total_tasks}: {row.get('Название', 'Без названия')}")
            
            # Конвертируем Excel данные в формат задания
            task_data = self._convert_csv_row_to_task_data(row)
            
            if dry_run:
                self._validate_task_data(task_data)
            else:
                self._import_single_task(task_data, update_existing)
        
        # Добавляем недостающие варианты ответов
        self._add_missing_answers(dry_run)
        
        # Возвращаем статистику
        stats = {
            'total_processed': total_tasks,
            'created': self.created_count,
            'updated': self.updated_count,
            'skipped': self.skipped_count,
            'errors': self.error_count,
            'error_details': self.errors
        }
        
        self._print_import_stats(stats, dry_run)
        return stats
    
    def import_tasks_from_markdown(self, markdown_file, update_existing=False, dry_run=False):
        """
        Импортирует задания из Markdown файла
        
        Args:
            markdown_file (str): Путь к Markdown файлу (ищется в temp_dir если не абсолютный путь)
            update_existing (bool): Обновлять существующие задания
            dry_run (bool): Режим тестирования без изменений в БД
        
        Returns:
            dict: Статистика импорта
        """
        # Если путь не абсолютный, ищем файл в temp_dir
        if not os.path.isabs(markdown_file):
            markdown_file = os.path.join(get_temp_dir(), markdown_file)
        
        if not os.path.exists(markdown_file):
            print(f"Ошибка: Файл {markdown_file} не найден!")
            return None
        
        print(f"Загружаем данные из Markdown файла: {markdown_file}")
        print("🔄 Конвертируем Markdown в JSON...")
        
        try:
            # Конвертируем Markdown в JSON во временный файл
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as temp_file:
                temp_json_path = temp_file.name
            
            # Используем функцию конвертации из task_converter
            result_json_path = markdown_to_json(markdown_file, temp_json_path)
            
            if not result_json_path or not os.path.exists(result_json_path):
                print("❌ Ошибка конвертации Markdown в JSON")
                return None
            
            print("✅ Конвертация завершена, начинаем импорт...")
            
            # Теперь импортируем из созданного JSON файла
            stats = self.import_tasks_from_json(result_json_path, update_existing, dry_run)
            
            # Удаляем временный файл
            try:
                os.unlink(result_json_path)
            except:
                pass  # Игнорируем ошибки удаления временного файла
            
            return stats
            
        except Exception as e:
            print(f"Ошибка при обработке Markdown файла: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _convert_csv_row_to_task_data(self, row):
        """Конвертирует строку CSV/Excel в формат данных задания"""
        # Парсим навыки
        skills = []
        if row.get('Навыки (ID)'):
            skill_ids = [x.strip() for x in str(row['Навыки (ID)']).split(';') if x.strip()]
            for skill_id in skill_ids:
                try:
                    skill = Skill.objects.get(id=int(skill_id))
                    skills.append({
                        'id': skill.id,
                        'name': skill.name,
                        'is_base': skill.is_base,
                        'description': skill.description
                    })
                except (ValueError, Skill.DoesNotExist):
                    pass
        
        # Парсим курсы
        courses = []
        if row.get('Курсы (ID)'):
            course_ids = [x.strip() for x in str(row['Курсы (ID)']).split(';') if x.strip()]
            for course_id in course_ids:
                try:
                    course = Course.objects.get(id=course_id)
                    courses.append({
                        'id': course.id,
                        'name': course.name,
                        'description': course.description
                    })
                except Course.DoesNotExist:
                    pass
        
        # Парсим варианты ответов
        answers = []
        if row.get('Варианты ответов'):
            answer_texts = str(row['Варианты ответов']).split(' | ')
            correct_answers = str(row.get('Правильные ответы', '')).split(';')
            
            for i, answer_text in enumerate(answer_texts):
                if answer_text.strip():
                    # Убираем номер из начала ответа
                    clean_answer = answer_text.strip()
                    if '. ' in clean_answer:
                        clean_answer = clean_answer.split('. ', 1)[1]
                    
                    is_correct = any(clean_answer in correct.strip() for correct in correct_answers)
                    
                    answers.append({
                        'text': clean_answer,
                        'is_correct': is_correct,
                        'order': i
                    })
        
        return {
            'id': int(row.get('ID', 0)) if row.get('ID') else None,
            'title': str(row.get('Название', '')),
            'task_type': str(row.get('Тип задания', 'single')),
            'difficulty': str(row.get('Сложность', 'beginner')),
            'question_text': str(row.get('Вопрос', '')),
            'correct_answer': str(row.get('Правильный ответ (поле)', '')),
            'explanation': str(row.get('Объяснение', '')),
            'is_active': bool(row.get('Активно', True)),
            'skills': skills,
            'courses': courses,
            'answers': answers
        }
    
    def _validate_task_data(self, task_data):
        """Валидирует данные задания без сохранения в БД"""
        try:
            required_fields = ['title', 'task_type', 'difficulty', 'question_text']
            for field in required_fields:
                if not task_data.get(field):
                    raise ValueError(f"Отсутствует обязательное поле: {field}")
            
            # Проверяем тип задания
            valid_types = ['single', 'multiple', 'true_false']
            if task_data['task_type'] not in valid_types:
                raise ValueError(f"Неверный тип задания: {task_data['task_type']}")
            
            # Проверяем уровень сложности
            valid_difficulties = ['beginner', 'intermediate', 'advanced']
            if task_data['difficulty'] not in valid_difficulties:
                raise ValueError(f"Неверный уровень сложности: {task_data['difficulty']}")
            
            print(f"    ✓ Валидация прошла успешно")
            
        except Exception as e:
            print(f"    ✗ Ошибка валидации: {e}")
            self.error_count += 1
            self.errors.append(f"Валидация задания '{task_data.get('title', 'N/A')}': {e}")
    
    def _import_single_task(self, task_data, update_existing):
        """Импортирует одно задание"""
        try:
            task_id = task_data.get('id')
            task = None
            
            # Проверяем, существует ли задание
            if task_id:
                try:
                    task = Task.objects.get(id=task_id)
                    if not update_existing:
                        print(f"    ⚠ Задание с ID {task_id} уже существует, пропускаем")
                        self.skipped_count += 1
                        return
                except Task.DoesNotExist:
                    pass
            
            with transaction.atomic():
                # Создаем или обновляем задание
                if task:
                    # Обновляем существующее
                    for field in ['title', 'task_type', 'difficulty', 'question_text', 
                                  'correct_answer', 'explanation', 'is_active']:
                        if field in task_data:
                            setattr(task, field, task_data[field])
                    
                    task.save()
                    print(f"    ✓ Задание обновлено (ID: {task.id})")
                    self.updated_count += 1
                else:
                    # Создаем новое
                    task = Task.objects.create(
                        title=task_data['title'],
                        task_type=task_data['task_type'],
                        difficulty=task_data['difficulty'],
                        question_text=task_data['question_text'],
                        correct_answer=task_data.get('correct_answer', ''),
                        explanation=task_data.get('explanation', ''),
                        is_active=task_data.get('is_active', True)
                    )
                    print(f"    ✓ Задание создано (ID: {task.id})")
                    self.created_count += 1
                  # Обновляем связи с навыками
                if 'skills' in task_data and task_data['skills']:
                    skills = []
                    for skill_data in task_data['skills']:
                        if 'id' in skill_data:
                            # Поиск по ID
                            try:
                                skill = Skill.objects.get(id=skill_data['id'])
                                skills.append(skill)
                            except Skill.DoesNotExist:
                                print(f"    ⚠ Навык с ID {skill_data['id']} не найден")
                        elif 'name' in skill_data:
                            # Поиск по имени
                            try:
                                skill = Skill.objects.get(name=skill_data['name'])
                                skills.append(skill)
                            except Skill.DoesNotExist:
                                print(f"    ⚠ Навык '{skill_data['name']}' не найден")
                    
                    if skills:
                        task.skills.set(skills)
                        print(f"    ✓ Связано навыков: {len(skills)}")
                
                # Обновляем связи с курсами
                if 'courses' in task_data and task_data['courses']:
                    courses = []
                    for course_data in task_data['courses']:
                        if 'id' in course_data:
                            # Поиск по ID
                            try:
                                course = Course.objects.get(id=course_data['id'])
                                courses.append(course)
                            except Course.DoesNotExist:
                                print(f"    ⚠ Курс с ID {course_data['id']} не найден")
                        elif 'name' in course_data:
                            # Поиск по имени
                            try:
                                course = Course.objects.get(name=course_data['name'])
                                courses.append(course)
                            except Course.DoesNotExist:
                                print(f"    ⚠ Курс '{course_data['name']}' не найден")
                    
                    if courses:
                        task.courses.set(courses)
                        print(f"    ✓ Связано курсов: {len(courses)}")
                
                # Обновляем варианты ответов
                if 'answers' in task_data and task_data['answers']:
                    # Удаляем старые варианты ответов
                    task.answers.all().delete()
                    
                    # Создаем новые
                    for answer_data in task_data['answers']:
                        TaskAnswer.objects.create(
                            task=task,
                            text=answer_data['text'],
                            is_correct=answer_data['is_correct'],
                            order=answer_data['order']
                        )
                    print(f"    ✓ Создано вариантов ответов: {len(task_data['answers'])}")
        
        except Exception as e:
            print(f"    ✗ Ошибка импорта: {e}")
            self.error_count += 1
            self.errors.append(f"Импорт задания '{task_data.get('title', 'N/A')}': {e}")
    
    def _print_import_stats(self, stats, dry_run=False):
        """Выводит статистику импорта"""
        print("\n" + "="*50)
        if dry_run:
            print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ ИМПОРТА")
        else:
            print("РЕЗУЛЬТАТЫ ИМПОРТА")
        print("="*50)
        
        print(f"Всего обработано: {stats['total_processed']}")
        print(f"Создано новых: {stats['created']}")
        print(f"Обновлено: {stats['updated']}")
        print(f"Пропущено: {stats['skipped']}")
        print(f"Ошибок: {stats['errors']}")
        
        if stats['error_details']:
            print("\nДетали ошибок:")
            for error in stats['error_details']:
                print(f"  - {error}")

    def _add_missing_answers(self, dry_run=False):
        """Автоматически добавляет недостающие варианты ответов к заданиям"""
        if dry_run:
            return  # В режиме тестирования не добавляем варианты ответов
        
        print("\n🔧 Проверяем задания без вариантов ответов...")
        
        tasks_without_answers = []
        for task in Task.objects.all():
            if task.answers.count() == 0:
                tasks_without_answers.append(task)
        
        if not tasks_without_answers:
            print("✓ Все задания имеют варианты ответов")
            return
        
        print(f"Найдено заданий без вариантов ответов: {len(tasks_without_answers)}")
        
        for task in tasks_without_answers:
            try:
                self._create_default_answers(task)
            except Exception as e:
                print(f"⚠ Ошибка при добавлении вариантов для '{task.title}': {e}")
    
    def _create_default_answers(self, task):
        """Создает стандартные варианты ответов для задания в зависимости от типа"""
        if task.task_type == 'true_false':
            # Для true_false создаем стандартные варианты "Верно/Неверно"
            TaskAnswer.objects.create(
                task=task,
                text='Верно',
                is_correct=False,  # По умолчанию считаем, что утверждение неверно
                order=0
            )
            TaskAnswer.objects.create(
                task=task,
                text='Неверно',
                is_correct=True,   # По умолчанию правильный ответ
                order=1
            )
            print(f"    ✓ Добавлены стандартные варианты True/False для '{task.title}'")
            
        elif task.task_type == 'single':
            # Для single создаем варианты на основе содержимого вопроса
            answers = self._generate_single_answers(task)
            for i, (text, is_correct) in enumerate(answers):
                TaskAnswer.objects.create(
                    task=task,
                    text=text,
                    is_correct=is_correct,
                    order=i
                )
            print(f"    ✓ Добавлены варианты single choice для '{task.title}'")
            
        elif task.task_type == 'multiple':
            # Для multiple создаем варианты на основе содержимого вопроса
            answers = self._generate_multiple_answers(task)
            for i, (text, is_correct) in enumerate(answers):
                TaskAnswer.objects.create(
                    task=task,
                    text=text,
                    is_correct=is_correct,
                    order=i
                )
            print(f"    ✓ Добавлены варианты multiple choice для '{task.title}'")
    
    def _generate_single_answers(self, task):
        """Генерирует варианты ответов для single choice на основе содержимого"""
        # Интеллектуальная генерация на основе ключевых слов в вопросе
        title_lower = task.title.lower()
        question_lower = task.question_text.lower()
        
        # Специальные случаи для распространенных типов вопросов
        if 'type()' in question_lower or 'тип' in title_lower:
            return [
                ("<class 'float'>", True),
                ("<type 'float'>", False),
                ("<class 'int'>", False),
                ("float", False),
            ]
        elif 'синтаксис' in title_lower or 'создать' in question_lower:
            return [
                ('var x = 10', False),
                ('x: int = 10', False),
                ('x = 10', True),
                ('int x = 10', False),
            ]
        elif 'кэш' in title_lower or 'is' in question_lower:
            return [
                ('True', True),
                ('False', False),
                ('Ошибка', False),
                ('None', False),
            ]
        else:
            # Общие варианты по умолчанию
            return [
                ('Вариант A', True),
                ('Вариант B', False),
                ('Вариант C', False),
                ('Вариант D', False),
            ]
    
    def _generate_multiple_answers(self, task):
        """Генерирует варианты ответов для multiple choice на основе содержимого"""
        title_lower = task.title.lower()
        question_lower = task.question_text.lower()
        
        # Специальные случаи для распространенных типов вопросов
        if 'имен' in title_lower or 'переменн' in title_lower:
            return [
                ('1variable', False),
                ('my_variable', True),
                ('var-name', False),
                ('_temp123', True),
                ('my variable', False),
                ('total1', True),
            ]
        elif 'преобразов' in title_lower or 'числ' in title_lower:
            return [
                ('int("42")', True),
                ('float("42")', True),
                ('eval("42")', True),
                ('str(42)', False),
                ('"42" + 0', False),
            ]
        elif 'тип' in title_lower and 'изменя' in title_lower:
            return [
                ('x = "42"', True),
                ('x = 3.14', True),
                ('x = 42', False),
                ('x = [42]', True),
                ('x = x + 0', False),
            ]
        else:
            # Общие варианты по умолчанию
            return [
                ('Правильный вариант 1', True),
                ('Правильный вариант 2', True),
                ('Неправильный вариант 1', False),
                ('Неправильный вариант 2', False),
                ('Неправильный вариант 3', False),
            ]

def list_import_files():
    """Выводит список файлов для импорта в temp_dir"""
    temp_dir = get_temp_dir()
    files = []
    
    for file in os.listdir(temp_dir):
        if file.endswith(('.json', '.csv', '.xlsx', '.md')):
            files.append(file)
    
    if files:
        print("Доступные файлы для импорта в temp_dir:")
        for file in sorted(files):
            print(f"  - {file}")
    else:
        print("В temp_dir не найдено файлов для импорта (.json, .csv, .xlsx, .md)")
    
    return files

if __name__ == '__main__':
    print("=" * 50)
    print("СКРИПТ ИМПОРТА ЗАДАНИЙ")
    print("=" * 50)
    
    importer = TaskImporter()
    
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python import_tasks.py <файл> [опции]")
        print("\nОпции:")
        print("  --update          - обновлять существующие задания")
        print("  --dry-run         - режим тестирования (без изменений в БД)")
        print("  --list            - показать доступные файлы")
        print("\nПримеры:")
        print("  python import_tasks.py tasks_export_20231201_120000.json")
        print("  python import_tasks.py tasks.csv --update")
        print("  python import_tasks.py tasks.xlsx --dry-run")
        print("  python import_tasks.py \"Переменные и типы данных.md\"")
        print("  python import_tasks.py --list")
        sys.exit(1)
    
    # Показать список файлов
    if '--list' in sys.argv:
        list_import_files()
        sys.exit(0)
    
    filename = sys.argv[1]
    update_existing = '--update' in sys.argv
    dry_run = '--dry-run' in sys.argv
      # Определяем формат файла
    if filename.endswith('.json'):
        stats = importer.import_tasks_from_json(filename, update_existing, dry_run)
    elif filename.endswith('.csv'):
        stats = importer.import_tasks_from_csv(filename, update_existing, dry_run)
    elif filename.endswith('.xlsx'):
        stats = importer.import_tasks_from_excel(filename, update_existing, dry_run)
    elif filename.endswith('.md'):
        stats = importer.import_tasks_from_markdown(filename, update_existing, dry_run)
    else:
        print(f"Неподдерживаемый формат файла: {filename}")
        print("Поддерживаемые форматы: .json, .csv, .xlsx, .md")
        sys.exit(1)
    
    if stats:
        if not dry_run and (stats['created'] > 0 or stats['updated'] > 0):
            print(f"\n✓ Импорт завершен успешно!")
        elif dry_run:
            print(f"\n✓ Тестирование завершено!")
    
    print("\nГотово!")
