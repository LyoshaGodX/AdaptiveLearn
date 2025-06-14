#!/usr/bin/env python
"""
Улучшенный генератор синтетических данных с полным покрытием навыков
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

import json
import numpy as np
import pandas as pd
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime, timedelta
import random
from dataclasses import dataclass
from collections import defaultdict

from skills.models import Skill
from methodist.models import Task
from mlmodels.bkt.base_model import BKTModel, BKTParameters


@dataclass
class EnhancedStudentProfile:
    """Улучшенный профиль синтетического студента"""
    id: int
    archetype: str
    course_focus: str  # Какой курс изучает студент
    base_success_rate: float
    learning_speed: float
    max_attempts: int  # Максимальное количество попыток
    skill_aptitudes: Dict[int, float]
    target_skills: Set[int]  # Целевые навыки для данного студента


class EnhancedSyntheticDataGenerator:
    """Улучшенный генератор с гарантированным покрытием"""
    
    def __init__(self, spec_file='temp_dir/synthetic_data_spec.json'):
        self.load_specification(spec_file)
        self.load_existing_tasks()
        self.setup_course_profiles()
    
    def setup_course_profiles(self):
        """Настройка профилей курсов"""
        self.course_profiles = {
            'python_course': {
                'name': 'Основы программирования на Python',
                'target_skills': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 17, 18, 19, 20],
                'min_attempts': 60,
                'max_attempts': 100,
                'success_rate_range': (0.4, 0.8)
            },
            'algorithms_course': {
                'name': 'Алгоритмы и структуры данных',
                'target_skills': [12, 13, 21, 22, 23, 24, 25],
                'min_attempts': 40,
                'max_attempts': 80,
                'success_rate_range': (0.3, 0.7)
            },
            'ml_course': {
                'name': 'Введение в машинное обучение',
                'target_skills': [26, 27, 28, 29, 30],
                'min_attempts': 30,
                'max_attempts': 60,
                'success_rate_range': (0.5, 0.9)
            },
            'advanced_student': {
                'name': 'Продвинутый студент (все курсы)',
                'target_skills': list(range(1, 31)),  # Все навыки
                'min_attempts': 120,
                'max_attempts': 200,
                'success_rate_range': (0.6, 0.95)
            }
        }
    
    def load_specification(self, spec_file):
        """Загружает спецификацию для генерации данных"""
        try:
            with open(spec_file, 'r', encoding='utf-8') as f:
                spec = json.load(f)
            
            self.skills_info = {int(k): v for k, v in spec['skills_graph']['skills_info'].items()}
            self.dependencies = {int(k): [int(x) for x in v] for k, v in spec['skills_graph']['dependencies'].items()}
            self.skill_levels = {int(k): v for k, v in spec['skills_graph']['levels'].items()}
            
            print(f"✅ Загружена спецификация с {len(self.skills_info)} навыками")
            
        except FileNotFoundError:
            print("❌ Файл спецификации не найден. Запустите analyze_dkn_data_requirements.py")
            sys.exit(1)
    
    def load_existing_tasks(self):
        """Загружает существующие задания из базы данных"""
        self.tasks_by_skill = defaultdict(list)
        self.all_tasks = {}
        
        tasks = Task.objects.all().prefetch_related('skills')
        for task in tasks:
            task_data = {
                'id': task.id,
                'title': task.title,
                'difficulty': task.difficulty,
                'task_type': task.task_type,
                'skill_ids': [skill.id for skill in task.skills.all()]
            }
            
            self.all_tasks[task.id] = task_data
            
            # Добавляем задание ко всем связанным навыкам
            for skill in task.skills.all():
                self.tasks_by_skill[skill.id].append(task_data)
        
        print(f"✅ Загружено {len(self.all_tasks)} заданий")
    
    def generate_balanced_students(self, total_students=1000):
        """Генерирует сбалансированное распределение студентов"""
        students = []
        
        # Распределение по курсам
        course_distribution = {
            'python_course': 0.4,      # 40% - студенты Python курса
            'algorithms_course': 0.25, # 25% - студенты алгоритмов  
            'ml_course': 0.2,         # 20% - студенты ML
            'advanced_student': 0.15   # 15% - продвинутые студенты
        }
        
        student_id = 1
        for course_type, proportion in course_distribution.items():
            num_students = int(total_students * proportion)
            
            for _ in range(num_students):
                student = self.generate_course_student(student_id, course_type)
                students.append(student)
                student_id += 1
        
        print(f"✅ Сгенерировано {len(students)} студентов")
        return students
    
    def generate_course_student(self, student_id: int, course_type: str) -> EnhancedStudentProfile:
        """Генерирует студента для конкретного курса"""
        profile = self.course_profiles[course_type]
        
        # Базовая успеваемость
        success_range = profile['success_rate_range']
        base_success_rate = np.random.uniform(success_range[0], success_range[1])
        
        # Количество попыток
        max_attempts = np.random.randint(profile['min_attempts'], profile['max_attempts'])
        
        # Способности к навыкам
        skill_aptitudes = {}
        for skill_id in profile['target_skills']:
            # Способности варьируются вокруг базовой успеваемости
            aptitude = max(0.1, min(0.95, np.random.normal(base_success_rate, 0.15)))
            skill_aptitudes[skill_id] = aptitude
        
        return EnhancedStudentProfile(
            id=student_id,
            archetype=course_type,
            course_focus=profile['name'],
            base_success_rate=base_success_rate,
            learning_speed=np.random.uniform(0.5, 2.0),
            max_attempts=max_attempts,
            skill_aptitudes=skill_aptitudes,
            target_skills=set(profile['target_skills'])
        )
    
    def generate_student_attempts_enhanced(self, student: EnhancedStudentProfile) -> List:
        """Генерирует попытки для студента с гарантированным покрытием целевых навыков"""
        attempts = []
        mastered_skills = set()
        skill_masteries = defaultdict(float)
        session_id = 0
        current_date = datetime.now() - timedelta(days=180)
        
        # Список навыков для изучения (целевые навыки студента)
        target_skills = list(student.target_skills)
        available_skills = []
        
        # Начинаем с базовых навыков из целевых
        for skill_id in target_skills:
            prerequisites = self.dependencies.get(skill_id, [])
            if not prerequisites or all(prereq in mastered_skills for prereq in prerequisites):
                available_skills.append(skill_id)
        
        current_skills = set(available_skills[:3])  # Начинаем с 3 навыков
        attempts_count = 0
        
        while attempts_count < student.max_attempts and target_skills:
            if not current_skills:
                # Добавляем новые доступные навыки
                for skill_id in target_skills:
                    if skill_id not in mastered_skills:
                        prerequisites = self.dependencies.get(skill_id, [])
                        if all(prereq in mastered_skills for prereq in prerequisites):
                            current_skills.add(skill_id)
                            break
                
                if not current_skills:
                    break
            
            # Выбираем навык для изучения
            target_skill = random.choice(list(current_skills))
            
            # Выбираем задание для этого навыка
            skill_tasks = self.tasks_by_skill.get(target_skill, [])
            if not skill_tasks:
                current_skills.discard(target_skill)
                continue
            
            task = random.choice(skill_tasks)
            
            # Вычисляем успех
            skill_aptitude = student.skill_aptitudes.get(target_skill, student.base_success_rate)
            current_mastery = skill_masteries[target_skill]
            success_prob = (skill_aptitude + current_mastery) / 2
            
            # Корректировка на основе сложности
            difficulty_factors = {'beginner': 1.2, 'intermediate': 1.0, 'advanced': 0.8}
            success_prob *= difficulty_factors.get(task['difficulty'], 1.0)
            success_prob = np.clip(success_prob, 0.05, 0.95)
            
            is_correct = np.random.random() < success_prob
            
            # Генерируем время и оценку
            base_time = {'beginner': 180, 'intermediate': 300, 'advanced': 450}
            time_spent = max(30, min(900, int(np.random.normal(base_time[task['difficulty']], 60))))
            score = np.random.uniform(0.7, 1.0) if is_correct else np.random.uniform(0.0, 0.4)
            
            # Обновляем освоенность навыка
            if is_correct:
                learning_rate = student.learning_speed * 0.12
                skill_masteries[target_skill] = min(1.0, skill_masteries[target_skill] + learning_rate)
            else:
                learning_rate = student.learning_speed * 0.05
                skill_masteries[target_skill] = min(1.0, skill_masteries[target_skill] + learning_rate)
            
            # Создаем запись о попытке
            attempt = {
                'student_id': student.id,
                'task_id': task['id'],
                'skill_ids': task['skill_ids'],
                'is_correct': is_correct,
                'score': score,
                'time_spent': time_spent,
                'difficulty': task['difficulty'],
                'task_type': task['task_type'],
                'timestamp': current_date,
                'session_id': session_id
            }
            
            attempts.append(attempt)
            attempts_count += 1
            
            # Проверяем, освоен ли навык
            if skill_masteries[target_skill] > 0.75:
                mastered_skills.add(target_skill)
                current_skills.discard(target_skill)
                target_skills.remove(target_skill) if target_skill in target_skills else None
                
                # Добавляем новые доступные навыки
                for skill_id in list(target_skills):
                    if skill_id not in mastered_skills:
                        prerequisites = self.dependencies.get(skill_id, [])
                        if all(prereq in mastered_skills for prereq in prerequisites):
                            current_skills.add(skill_id)
            
            # Продвигаем время
            current_date += timedelta(minutes=np.random.randint(5, 60))
        
        return attempts
    
    def generate_enhanced_dataset(self):
        """Генерирует улучшенный датасет с полным покрытием"""
        print('\n🚀 ГЕНЕРАТОР УЛУЧШЕННЫХ СИНТЕТИЧЕСКИХ ДАННЫХ')
        print('='*60)
        
        # Генерируем студентов
        students = self.generate_balanced_students(1000)
        
        # Генерируем попытки
        all_attempts = []
        skills_covered = set()
        
        print('\n🔄 Генерация попыток...')
        for i, student in enumerate(students):
            if (i + 1) % 100 == 0:
                print(f"   Студент {i + 1}/1000")
            
            attempts = self.generate_student_attempts_enhanced(student)
            all_attempts.extend(attempts)
            
            # Отслеживаем покрытые навыки
            for attempt in attempts:
                for skill_id in attempt['skill_ids']:
                    skills_covered.add(skill_id)
        
        print(f'\n✅ Генерация завершена!')
        print(f'   Студентов: {len(students)}')
        print(f'   Попыток: {len(all_attempts)}')
        print(f'   Покрытие навыков: {len(skills_covered)}/30')
        
        # Преобразуем в DKN формат
        dkn_data = self.convert_to_dkn_format(all_attempts)
        
        # Сохраняем
        df = pd.DataFrame(dkn_data)
        df.to_csv('temp_dir/enhanced_synthetic_dataset.csv', index=False)
        
        print(f'💾 Улучшенный датасет сохранен: enhanced_synthetic_dataset.csv')
        print(f'   Размер: {df.shape}')
        
        return df
    
    def convert_to_dkn_format(self, attempts):
        """Преобразует попытки в формат DKN"""
        print('\n🔄 Преобразование в формат DKN...')
        
        # Группируем попытки по студентам
        student_attempts = defaultdict(list)
        for attempt in attempts:
            student_attempts[attempt['student_id']].append(attempt)
        
        dkn_examples = []
        
        for student_id, student_attempts_list in student_attempts.items():
            # Сортируем попытки по времени
            student_attempts_list.sort(key=lambda x: x['timestamp'])
            
            # Создаем примеры DKN
            for i in range(1, len(student_attempts_list)):
                # История (предыдущие попытки)
                history = student_attempts_list[:i]
                current_attempt = student_attempts_list[i]
                
                # Берем последние 10 попыток как историю
                recent_history = history[-10:] if len(history) >= 10 else history
                
                example = self.create_dkn_example(
                    student_id=student_id,
                    history=recent_history,
                    target_attempt=current_attempt
                )
                
                dkn_examples.append(example)
        
        print(f'✅ Создано {len(dkn_examples)} примеров DKN')
        return dkn_examples
    
    def create_dkn_example(self, student_id, history, target_attempt):
        """Создает один пример для DKN"""
        example = {
            'student_id': student_id,
            'task_id': target_attempt['task_id'],
            'target': float(target_attempt['is_correct'])
        }
        
        # История попыток (последние 10)
        for i in range(10):
            if i < len(history):
                attempt = history[-(i+1)]  # Берем с конца
                example[f'hist_{i}_correct'] = float(attempt['is_correct'])
                example[f'hist_{i}_score'] = attempt['score']
                example[f'hist_{i}_time'] = attempt['time_spent']
            else:
                example[f'hist_{i}_correct'] = 0.0
                example[f'hist_{i}_score'] = 0.0
                example[f'hist_{i}_time'] = 0
        
        # BKT параметры (упрощенные)
        # Для первого навыка в задании
        target_skills = target_attempt['skill_ids']
        if target_skills:
            main_skill = target_skills[0]
            # Вычисляем примерные BKT параметры на основе истории
            skill_attempts = [a for a in history if main_skill in a['skill_ids']]
            if skill_attempts:
                recent_success = sum(a['is_correct'] for a in skill_attempts[-5:]) / min(5, len(skill_attempts))
                example['skill_0_learned'] = min(0.9, recent_success)
                example['skill_0_transit'] = 0.3  # Фиксированный параметр
            else:
                example['skill_0_learned'] = 0.1
                example['skill_0_transit'] = 0.3
        else:
            example['skill_0_learned'] = 0.1
            example['skill_0_transit'] = 0.3
        
        # Характеристики задания
        difficulty_map = {'beginner': 0, 'intermediate': 1, 'advanced': 2}
        type_map = {'single': 0, 'multiple': 1, 'true_false': 2}
        
        example['task_difficulty'] = difficulty_map.get(target_attempt['difficulty'], 1)
        example['task_type'] = type_map.get(target_attempt['task_type'], 0)
        
        return example


def main():
    """Основная функция"""
    generator = EnhancedSyntheticDataGenerator()
    df = generator.generate_enhanced_dataset()
    
    print('\n🎉 ГОТОВО!')
    print(f'✅ Создан улучшенный датасет: {df.shape[0]} примеров')
    print('📁 Файл: temp_dir/enhanced_synthetic_dataset.csv')


if __name__ == "__main__":
    main()
