import re
import os
from django.core.management.base import BaseCommand
from skills.models import Skill, Course

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
            },
        }
        
        # Создаем или обновляем курсы в базе данных
        course_objects = {}
        for course_id, course_data in courses.items():
            course_obj, created = Course.objects.update_or_create(
                id=course_id,
                defaults={
                    "name": course_data["name"],
                    "description": course_data["description"]
                }
            )
            course_objects[course_id] = course_obj
            self.stdout.write(f"{'Создан' if created else 'Обновлен'} курс: {course_obj.name}")
        
        # Извлекаем имена навыков из файла
        skill_pattern = re.compile(r'"([^"]+)";')
        skill_names = skill_pattern.findall(dot_content)
        
        # Определяем базовые навыки
        base_skills = [
            "Переменные и типы данных", "Операторы и выражения", "Условные операторы",
            "Циклы", "Функции и процедуры", "Обработка ошибок", 
            "Модули и пакеты", "Работа с файлами", "Логические операторы",
            "Списки и словари", "Введение в ООП", "Основы алгоритмов",
            "Сложность алгоритмов", "Рекурсия", "Объектно-ориентированное программирование"
        ]
        
        # Словари для хранения навыков по курсам
        course_specific_skills = {
            "C1": [
                "Работа с вводом/выводом данных", "Примитивы сериализации (JSON, CSV)",
                "Контейнеры данных (tuple, set)", "Регулярные выражения",
                "Работа с библиотеками Python (math, random)"
            ],
            "C2": [
                "Деревья (обход, поиск)", "Графы (поиск в ширину и глубину)",
                "Хэш-таблицы", "Сортировки (быстрая, пузырьковая, слиянием)",
                "Поиск оптимального пути (A*, Dijkstra)"
            ],
            "C3": [
                "Основы регрессии", "Классификация данных",
                "Методы кластеризации", "Введение в нейросети",
                "Обработка признаков (Feature Engineering)"
            ]
        }
        
        # Создаем навыки в базе данных
        skill_objects = {}
        
        # Создаем или обновляем базовые навыки
        self.stdout.write("Создаем базовые навыки...")
        for skill_name in base_skills:
            if skill_name in skill_names:
                skill_obj, created = Skill.objects.update_or_create(
                    name=skill_name,
                    defaults={"is_base": True}
                )
                skill_objects[skill_name] = skill_obj
                self.stdout.write(f"{'Создан' if created else 'Обновлен'} базовый навык: {skill_name}")
        
        # Создаем или обновляем специфические навыки для каждого курса
        self.stdout.write("Создаем специфические навыки по курсам...")
        for course_id, skills_list in course_specific_skills.items():
            for skill_name in skills_list:
                if skill_name in skill_names:
                    skill_obj, created = Skill.objects.update_or_create(
                        name=skill_name,
                        defaults={"is_base": False}
                    )
                    # Добавляем связь с курсом
                    skill_obj.courses.add(course_objects[course_id])
                    skill_objects[skill_name] = skill_obj
                    self.stdout.write(f"{'Создан' if created else 'Обновлен'} навык курса {course_id}: {skill_name}")
        
        # Также добавляем базовые навыки во все курсы
        self.stdout.write("Связываем базовые навыки с курсами...")
        for base_skill_name in base_skills:
            if base_skill_name in skill_objects:
                for course_id in courses.keys():
                    skill_objects[base_skill_name].courses.add(course_objects[course_id])
        
        # Извлечение зависимостей
        dependency_pattern = re.compile(r'"([^"]+)" -> "([^"]+)"')
        dependencies = dependency_pattern.findall(dot_content)
        
        # Создаем зависимости между навыками
        self.stdout.write("Создаем зависимости между навыками...")
        for prereq_name, skill_name in dependencies:
            if prereq_name in skill_objects and skill_name in skill_objects:
                skill_objects[skill_name].prerequisites.add(skill_objects[prereq_name])
                self.stdout.write(f"Добавлена зависимость: {prereq_name} -> {skill_name}")
        
        self.stdout.write(self.style.SUCCESS("Импорт данных завершен успешно!"))
