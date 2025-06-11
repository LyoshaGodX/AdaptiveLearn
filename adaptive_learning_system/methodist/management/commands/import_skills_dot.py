import re
import os
from django.core.management.base import BaseCommand
from methodist.models import Skill, Course

class Command(BaseCommand):
    help = 'Импорт навыков и зависимостей из DOT-файла'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, help='Путь к DOT-файлу')

    def handle(self, *args, **options):
        file_path = options.get('file')
        
        if not file_path:
            file_path = r"c:\Users\AKlem\Documents\Python projects\AdaptiveLearn\temp_dir\skills_graph.dot"
        
        self.import_skills_from_dot(file_path)

    def import_skills_from_dot(self, dot_file_path):
        """Импортирует навыки и зависимости из DOT-файла"""
        self.stdout.write(f"Начинаем импорт из файла: {dot_file_path}")
        
        # Проверяем существование файла
        if not os.path.exists(dot_file_path):
            self.stdout.write(self.style.ERROR(f"Ошибка: Файл {dot_file_path} не существует"))
            return
        
        # Чтение DOT-файла
        with open(dot_file_path, 'r', encoding='utf-8') as file:
            dot_content = file.read()
        
        # Создаем курсы
        self.stdout.write("Создаем курсы...")
        courses = {
            "C1": {
                "name": "Основы программирования на Python", 
                "description": "Введение в Python: синтаксис, базовые структуры данных, простые алгоритмы."
            },
            "C2": {
                "name": "Алгоритмы и структуры данных", 
                "description": "Расширенное изучение алгоритмов и структур данных, необходимых для решения сложных задач."
            },
            "C3": {
                "name": "Введение в машинное обучение", 
                "description": "Базовые концепции машинного обучения, методы классификации, регрессии и кластеризации."
            }
        }
        
        # Создаем или обновляем курсы в базе данных
        course_objects = {}
        for course_id, course_info in courses.items():
            course_obj, created = Course.objects.update_or_create(
                id=course_id,
                defaults={
                    'name': course_info['name'],
                    'description': course_info['description']
                }
            )
            course_objects[course_id] = course_obj
            status = "создан" if created else "обновлен"
            self.stdout.write(f"Курс '{course_obj.name}' ({course_id}) {status}")
        
        # Обработка узлов (навыков)
        self.stdout.write("Обрабатываем навыки...")
        skill_pattern = r'([A-Za-z0-9]+)\s*\[label="([^"]+)"(?:,\s*shape=([^,\]]+))?(?:,\s*color=([^,\]]+))?\];'
        skills_data = re.findall(skill_pattern, dot_content)
        
        # Словарь для хранения соответствия ID и объектов навыков
        skill_objects = {}
        
        # Создание навыков
        for skill_id, skill_name, shape, color in skills_data:
            is_base = shape == "box" or color == "blue"
            
            skill_obj, created = Skill.objects.update_or_create(
                name=skill_name,
                defaults={'is_base': is_base}
            )
            
            skill_objects[skill_id] = skill_obj
            status = "создан" if created else "обновлен"
            self.stdout.write(f"Навык '{skill_obj.name}' ({skill_id}) {status}")
        
        # Добавление связей между навыками (зависимостей)
        self.stdout.write("Устанавливаем зависимости между навыками...")
        dependency_pattern = r'([A-Za-z0-9]+)\s*->\s*([A-Za-z0-9]+);'
        dependencies = re.findall(dependency_pattern, dot_content)
        
        for prereq_id, skill_id in dependencies:
            if prereq_id in skill_objects and skill_id in skill_objects:
                prereq_obj = skill_objects[prereq_id]
                skill_obj = skill_objects[skill_id]
                
                # Добавляем предпосылку, если она еще не добавлена
                if not skill_obj.prerequisites.filter(id=prereq_obj.id).exists():
                    skill_obj.prerequisites.add(prereq_obj)
                    self.stdout.write(f"Добавлена зависимость: '{prereq_obj.name}' -> '{skill_obj.name}'")
            else:
                self.stdout.write(self.style.WARNING(f"Не удалось найти навык для зависимости: {prereq_id} -> {skill_id}"))
        
        # Распределение навыков по курсам
        self.stdout.write("Распределяем навыки по курсам...")
        # Словарь соответствия навыков и курсов
        skill_to_course = {
            # Курс C1: Основы программирования на Python
            "S1": "C1",  # Основы синтаксиса Python
            "S2": "C1",  # Переменные и типы данных
            "S3": "C1",  # Условные операторы
            "S4": "C1",  # Циклы
            "S5": "C1",  # Функции
            "S6": "C1",  # Работа со строками
            "S7": "C1",  # Списки и кортежи
            "S8": "C1",  # Словари и множества
            "S9": "C1",  # Файловый ввод-вывод
            
            # Курс C2: Алгоритмы и структуры данных
            "S10": "C2", # Основы алгоритмов
            "S11": "C2", # Сложность алгоритмов
            "S12": "C2", # Алгоритмы сортировки
            "S13": "C2", # Алгоритмы поиска
            "S14": "C2", # Рекурсия
            "S15": "C2", # Динамическое программирование
            "S16": "C2", # Графы
            "S17": "C2", # Деревья
            "S18": "C2", # Жадные алгоритмы
            
            # Курс C3: Введение в машинное обучение
            "S19": "C3", # Основы машинного обучения
            "S20": "C3", # Регрессия
            "S21": "C3", # Классификация
            "S22": "C3", # Кластеризация
            "S23": "C3", # Оценка моделей
            "S24": "C3", # Деревья решений
            "S25": "C3", # Нейронные сети
            "S26": "C3", # Обучение с подкреплением
            "S27": "C3", # Обработка естественного языка
        }
        
        # Добавляем навыки к курсам
        for skill_id, course_id in skill_to_course.items():
            if skill_id in skill_objects and course_id in course_objects:
                skill_obj = skill_objects[skill_id]
                course_obj = course_objects[course_id]
                
                # Добавляем курс к навыку, если он еще не добавлен
                if not skill_obj.courses.filter(id=course_obj.id).exists():
                    skill_obj.courses.add(course_obj)
                    self.stdout.write(f"Навык '{skill_obj.name}' добавлен к курсу '{course_obj.name}'")
            else:
                self.stdout.write(self.style.WARNING(f"Не удалось связать навык {skill_id} с курсом {course_id}"))
        
        self.stdout.write(self.style.SUCCESS("Импорт успешно завершен!"))
