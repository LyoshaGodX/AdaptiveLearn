"""
Улучшенный генератор синтетических данных для обучения DKN модели

Этот модуль создает реалистичные синтетические данные о студентах,
их попытках решения заданий и прогрессе в изучении навыков с полным 
покрытием всех навыков и курсов.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

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
import matplotlib
matplotlib.use('Agg')  # Используем backend без GUI
import matplotlib.pyplot as plt

from skills.models import Skill
from methodist.models import Task, Course
from mlmodels.bkt.base_model import BKTModel, BKTParameters


@dataclass
class StudentProfile:
    """Профиль синтетического студента"""
    id: int
    archetype: str
    base_success_rate: float
    learning_speed: float
    preferred_path: str
    skill_aptitudes: Dict[int, float]  # Способности к разным навыкам
    attention_span: int  # Количество заданий за сессию
    consistency: float  # Насколько стабильны результаты
    course_focus: Optional[str]  # Фокус на конкретном курсе
    max_attempts: int  # Максимальное количество попыток


@dataclass
class AttemptRecord:
    """Запись о попытке выполнения задания"""
    student_id: int
    task_id: int
    skill_ids: List[int]
    is_correct: bool
    score: float
    time_spent: int
    difficulty: str
    task_type: str
    timestamp: datetime
    session_id: int


class EnhancedSyntheticDataGenerator:
    """Улучшенный генератор синтетических данных с полным покрытием навыков"""
    
    def __init__(self, spec_file: Optional[str] = None):
        self.spec_file = spec_file or 'mlmodels/dkn/dataset/synthetic_data_spec.json'
        self.output_dir = 'mlmodels/dkn/dataset'
        
        # Обеспечиваем существование выходной директории
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.load_system_data()
        self.load_specification()
        
        # Статистика генерации
        self.generation_stats = {
            'students_created': 0,
            'attempts_created': 0,
            'skills_covered': set(),
            'courses_covered': set(),
            'archetype_distribution': defaultdict(int),
            'skill_coverage_per_course': defaultdict(set),
            'level_coverage': defaultdict(int)
        }
    
    def load_system_data(self):
        """Загружает данные системы с анализом курсов"""
        print("🔍 Загрузка данных системы...")
        
        # Загружаем курсы
        self.courses = {}
        for course in Course.objects.all():
            self.courses[course.id] = {
                'id': course.id,
                'name': course.name,
                'skills': list(course.skills.values_list('id', flat=True))
            }
        
        # Загружаем навыки с курсовой принадлежностью
        self.all_skills = {}
        self.skills_by_course = defaultdict(list)
        
        for skill in Skill.objects.all():
            skill_courses = list(skill.courses.values_list('id', flat=True))
            
            self.all_skills[skill.id] = {
                'id': skill.id,
                'name': skill.name,
                'courses': skill_courses
            }
            
            for course_id in skill_courses:
                self.skills_by_course[course_id].append(skill.id)
        
        # Загружаем задания
        self.tasks_by_skill = defaultdict(list)
        self.all_tasks = {}
        
        for task in Task.objects.all().prefetch_related('skills', 'courses'):
            task_data = {
                'id': task.id,
                'title': task.title,
                'difficulty': task.difficulty,
                'task_type': task.task_type,
                'skill_ids': list(task.skills.values_list('id', flat=True)),
                'course_ids': list(task.courses.values_list('id', flat=True))
            }
            
            self.all_tasks[task.id] = task_data
            
            for skill_id in task_data['skill_ids']:
                self.tasks_by_skill[skill_id].append(task_data)
        
        print(f"✅ Загружено:")
        print(f"   • Курсов: {len(self.courses)}")
        print(f"   • Навыков: {len(self.all_skills)}")
        print(f"   • Заданий: {len(self.all_tasks)}")
        
        # Выводим статистику по курсам
        for course_id, course_data in self.courses.items():
            skill_count = len(course_data['skills'])
            task_count = sum(1 for task in self.all_tasks.values() 
                           if course_id in task['course_ids'])
            print(f"   • {course_data['name']}: {skill_count} навыков, {task_count} заданий")
    
    def load_specification(self):
        """Загружает или создает спецификацию"""
        try:
            with open(self.spec_file, 'r', encoding='utf-8') as f:
                spec = json.load(f)
            
            self.target_students = spec['generation_params']['students']['total']
            self.student_distribution = spec['generation_params']['students']['distribution']
            self.skills_info = {int(k): v for k, v in spec['skills_graph']['skills'].items()}
            self.dependencies = {int(k): [int(x) for x in v] for k, v in spec['skills_graph']['dependencies'].items()}
            self.skill_levels = {int(k): v for k, v in spec['skills_graph']['levels'].items()}
            self.archetypes = spec['requirements']['student_archetypes']
            
            print(f"✅ Загружена спецификация: {self.target_students} студентов")
            
        except FileNotFoundError:
            print("⚠️ Спецификация не найдена. Создается новая...")
            self.create_enhanced_specification()
    
    def create_enhanced_specification(self):
        """Создает улучшенную спецификацию с учетом курсов"""
        
        # Загружаем граф навыков
        with open('temp_dir/skills_graph.json', 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
        
        # Анализируем уровни сложности
        max_level = max(graph_data['levels'].values())
        
        # Создаем архетипы с учетом курсовой структуры
        enhanced_archetypes = {
            "новичок_курс1": {
                "description": "Изучает базовые навыки первого курса",
                "success_rate_range": [0.4, 0.7],
                "attempts_range": [30, 60],
                "learning_speed": "медленная",
                "course_focus": 1,
                "max_level": 5
            },
            "новичок_курс2": {
                "description": "Изучает базовые навыки второго курса",
                "success_rate_range": [0.3, 0.6],
                "attempts_range": [40, 70],
                "learning_speed": "медленная", 
                "course_focus": 2,
                "max_level": 6
            },
            "средний_курс1": {
                "description": "Продвинутый студент первого курса",
                "success_rate_range": [0.6, 0.8],
                "attempts_range": [40, 80],
                "learning_speed": "средняя",
                "course_focus": 1,
                "max_level": 10
            },
            "средний_курс2": {
                "description": "Продвинутый студент второго курса",
                "success_rate_range": [0.5, 0.8],
                "attempts_range": [50, 90],
                "learning_speed": "средняя",
                "course_focus": 2,
                "max_level": 12
            },
            "продвинутый_все_курсы": {
                "description": "Изучает навыки всех курсов",
                "success_rate_range": [0.7, 0.9],
                "attempts_range": [60, 120],
                "learning_speed": "быстрая",
                "course_focus": None,
                "max_level": max_level
            },
            "гений_все_курсы": {
                "description": "Быстро осваивает все навыки всех курсов",
                "success_rate_range": [0.8, 0.95],
                "attempts_range": [40, 100],
                "learning_speed": "очень быстрая",
                "course_focus": None,
                "max_level": max_level
            },
            "специалист_курс3": {
                "description": "Фокусируется на машинном обучении (3-й курс)",
                "success_rate_range": [0.6, 0.85],
                "attempts_range": [50, 100],
                "learning_speed": "быстрая",
                "course_focus": 3,
                "max_level": max_level
            }
        }
        
        # Распределение студентов для обеспечения покрытия
        distribution = {
            "новичок_курс1": 0.25,      # 25% - базовые навыки курса 1
            "новичок_курс2": 0.15,      # 15% - базовые навыки курса 2  
            "средний_курс1": 0.20,      # 20% - продвинутые курса 1
            "средний_курс2": 0.15,      # 15% - продвинутые курса 2
            "продвинутый_все_курсы": 0.15,  # 15% - все курсы
            "гений_все_курсы": 0.05,    # 5% - гении
            "специалист_курс3": 0.05    # 5% - специалисты ML
        }
        
        spec = {
            "generation_params": {
                "students": {
                    "total": 1500,  # Увеличиваем количество для лучшего покрытия
                    "distribution": distribution
                },
                "enhanced_features": {
                    "course_aware_generation": True,
                    "full_skill_coverage": True,
                    "realistic_trajectories": True
                }
            },
            "skills_graph": graph_data,
            "courses_info": self.courses,
            "requirements": {
                "student_archetypes": enhanced_archetypes,
                "coverage_requirements": {
                    "min_skill_coverage": 1.0,  # 100% навыков
                    "min_course_coverage": 1.0, # 100% курсов
                    "min_examples_per_skill": 50
                }
            }
        }
        
        # Сохраняем спецификацию
        with open(self.spec_file, 'w', encoding='utf-8') as f:
            json.dump(spec, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Создана улучшенная спецификация: {self.spec_file}")
          # Загружаем созданную спецификацию
        self.target_students = spec['generation_params']['students']['total']
        self.student_distribution = spec['generation_params']['students']['distribution']
        self.skills_info = {int(k): v for k, v in spec['skills_graph']['skills'].items()}
        self.dependencies = {int(k): [int(x) for x in v] for k, v in spec['skills_graph']['dependencies'].items()}
        self.skill_levels = {int(k): v for k, v in spec['skills_graph']['levels'].items()}
        self.archetypes = spec['requirements']['student_archetypes']
    
    def generate_enhanced_student_profile(self, student_id: int) -> StudentProfile:
        """Генерирует улучшенный профиль студента с курсовым фокусом"""
        
        # Выбираем архетип
        archetype = np.random.choice(
            list(self.student_distribution.keys()),
            p=list(self.student_distribution.values())
        )
        
        archetype_params = self.archetypes[archetype]
        
        # Базовые параметры
        success_range = archetype_params['success_rate_range']
        base_success_rate = np.random.uniform(success_range[0], success_range[1])
        
        attempts_range = archetype_params['attempts_range']
        max_attempts = np.random.randint(attempts_range[0], attempts_range[1])
        
        learning_speeds = {
            'очень медленная': 0.3,
            'медленная': 0.5,
            'средняя': 1.0,
            'быстрая': 1.5,
            'очень быстрая': 2.0
        }
        learning_speed = learning_speeds[archetype_params['learning_speed']]
        
        # Курсовый фокус
        course_focus = archetype_params.get('course_focus')
        
        # Способности к навыкам с учетом курсового фокуса
        skill_aptitudes = {}
        for skill_id in self.all_skills.keys():
            skill_courses = self.all_skills[skill_id]['courses']
            
            if course_focus and course_focus in skill_courses:
                # Повышенная способность к навыкам своего курса
                aptitude = base_success_rate + np.random.uniform(0.0, 0.2)
            else:
                # Обычная способность
                aptitude = base_success_rate + np.random.uniform(-0.1, 0.1)
            
            skill_aptitudes[skill_id] = np.clip(aptitude, 0.1, 0.95)
        
        # Остальные параметры
        attention_span = np.random.randint(5, 15)
        consistency = np.random.uniform(0.6, 0.9)
        
        # Путь обучения зависит от архетипа
        if 'новичок' in archetype:
            preferred_path = np.random.choice(['linear', 'breadth_first'], p=[0.7, 0.3])
        elif 'средний' in archetype:
            preferred_path = np.random.choice(['linear', 'breadth_first', 'focused'], p=[0.4, 0.4, 0.2])
        else:
            preferred_path = np.random.choice(['breadth_first', 'focused', 'random'], p=[0.3, 0.4, 0.3])
        
        return StudentProfile(
            id=student_id,
            archetype=archetype,
            base_success_rate=base_success_rate,
            learning_speed=learning_speed,
            preferred_path=preferred_path,
            skill_aptitudes=skill_aptitudes,
            attention_span=attention_span,
            consistency=consistency,
            course_focus=course_focus,
            max_attempts=max_attempts
        )
    
    def get_course_aware_available_skills(self, student_profile: StudentProfile, 
                                        mastered_skills: Set[int]) -> List[int]:
        """Определяет доступные навыки с учетом курсового фокуса"""
        available = []
        
        # Все доступные навыки по пререквизитам
        prerequisite_available = []
        for skill_id, prerequisites in self.dependencies.items():
            if all(prereq in mastered_skills for prereq in prerequisites):
                if skill_id not in mastered_skills:
                    prerequisite_available.append(skill_id)
        
        # Фильтруем по уровню сложности (если есть ограничение)
        max_level = self.archetypes[student_profile.archetype].get('max_level')
        if max_level is not None:
            prerequisite_available = [
                skill_id for skill_id in prerequisite_available
                if self.skill_levels.get(skill_id, 0) <= max_level
            ]
        
        # Если есть курсовый фокус, приоритет навыкам этого курса
        if student_profile.course_focus:
            course_skills = self.skills_by_course.get(student_profile.course_focus, [])
            course_available = [s for s in prerequisite_available if s in course_skills]
            
            # 80% вероятность выбрать навык своего курса
            if course_available and np.random.random() < 0.8:
                available = course_available
            else:
                available = prerequisite_available
        else:
            available = prerequisite_available
        
        return available
    
    def generate_enhanced_student_attempts(self, student_profile: StudentProfile) -> List[AttemptRecord]:
        """Генерирует попытки с улучшенной логикой"""
        
        attempts = []
        mastered_skills = set()
        skill_masteries = defaultdict(float)
        session_id = 0
        current_date = datetime.now() - timedelta(days=180)
        
        # Начинаем с базовых навыков
        available_skills = self.get_course_aware_available_skills(student_profile, mastered_skills)
        current_skills = set()
        
        attempts_in_session = 0
        max_session_attempts = student_profile.attention_span
        
        for attempt_num in range(student_profile.max_attempts):
            # Новая сессия
            if attempts_in_session >= max_session_attempts:
                session_id += 1
                attempts_in_session = 0
                max_session_attempts = student_profile.attention_span + np.random.randint(-2, 3)
                current_date += timedelta(hours=np.random.randint(4, 48))
            
            # Выбираем навык
            if not current_skills and available_skills:
                target_skill = self.select_next_skill(student_profile, available_skills, current_skills)
                if target_skill:
                    current_skills.add(target_skill)
            
            if not current_skills:
                break
                
            target_skill = random.choice(list(current_skills))
            
            # Выбираем задание
            skill_tasks = self.tasks_by_skill.get(target_skill, [])
            if not skill_tasks:
                current_skills.discard(target_skill)
                continue
            
            task = random.choice(skill_tasks)
            
            # Вычисляем успех
            success_prob = self.calculate_success_probability(
                student_profile, task, skill_masteries
            )
            is_correct = np.random.random() < success_prob
            
            # Генерируем время и оценку
            base_time = {'beginner': 180, 'intermediate': 300, 'advanced': 450}
            time_spent = int(np.random.normal(
                base_time[task['difficulty']], 
                base_time[task['difficulty']] * 0.3
            ))
            time_spent = max(30, min(900, time_spent))
            
            if is_correct:
                score = np.random.uniform(0.7, 1.0)
                learning_gain = student_profile.learning_speed * 0.1
            else:
                score = np.random.uniform(0.0, 0.4)
                learning_gain = student_profile.learning_speed * 0.05
            
            # Обновляем мастерство
            for skill_id in task['skill_ids']:
                skill_masteries[skill_id] = min(1.0, skill_masteries[skill_id] + learning_gain)
            
            # Создаем запись
            attempt = AttemptRecord(
                student_id=student_profile.id,
                task_id=task['id'],
                skill_ids=task['skill_ids'],
                is_correct=is_correct,
                score=score,
                time_spent=time_spent,
                difficulty=task['difficulty'],
                task_type=task['task_type'],
                timestamp=current_date,
                session_id=session_id
            )
            
            attempts.append(attempt)
            attempts_in_session += 1
            
            # Обновляем статистику
            self.generation_stats['skills_covered'].update(task['skill_ids'])
            self.generation_stats['courses_covered'].update(task['course_ids'])
            
            for skill_id in task['skill_ids']:
                skill_level = self.skill_levels.get(skill_id, 0)
                self.generation_stats['level_coverage'][skill_level] += 1
                
                for course_id in task['course_ids']:
                    self.generation_stats['skill_coverage_per_course'][course_id].add(skill_id)
            
            # Проверяем освоение навыка
            if skill_masteries[target_skill] > 0.8:
                mastered_skills.add(target_skill)
                current_skills.discard(target_skill)
                
                # Обновляем доступные навыки
                new_available = self.get_course_aware_available_skills(student_profile, mastered_skills)
                available_skills = new_available
            
            current_date += timedelta(minutes=np.random.randint(1, 10))
        
        return attempts
    
    def select_next_skill(self, student_profile: StudentProfile, 
                         available_skills: List[int], 
                         current_skills: Set[int]) -> Optional[int]:
        """Выбор следующего навыка с учетом стратегии"""
        if not available_skills:
            return None
        
        path = student_profile.preferred_path
        
        if path == 'linear':
            return min(available_skills, key=lambda s: self.skill_levels[s])
        elif path == 'breadth_first':
            if current_skills:
                current_level = max(self.skill_levels[s] for s in current_skills)
                same_level = [s for s in available_skills if self.skill_levels[s] == current_level]
                if same_level:
                    return random.choice(same_level)
            return min(available_skills, key=lambda s: self.skill_levels[s])
        elif path == 'focused':
            # Фокусируемся на курсе если есть
            if student_profile.course_focus:
                course_skills = [s for s in available_skills 
                               if student_profile.course_focus in self.all_skills[s]['courses']]
                if course_skills:
                    return random.choice(course_skills)
            return random.choice(available_skills)
        else:  # random
            return random.choice(available_skills)
    
    def calculate_success_probability(self, student_profile: StudentProfile,
                                    task: Dict, skill_masteries: Dict[int, float]) -> float:
        """Вычисляет вероятность успеха"""
        base_prob = student_profile.skill_aptitudes.get(
            task['skill_ids'][0] if task['skill_ids'] else 0, 
            student_profile.base_success_rate
        )
        
        if task['skill_ids']:
            skill_mastery = np.mean([skill_masteries.get(sid, 0.0) for sid in task['skill_ids']])
            base_prob = (base_prob + skill_mastery) / 2
        
        difficulty_factors = {
            'beginner': 1.2,
            'intermediate': 1.0,
            'advanced': 0.8
        }
        base_prob *= difficulty_factors.get(task['difficulty'], 1.0)
        
        noise = np.random.normal(0, 1 - student_profile.consistency) * 0.1
        
        return np.clip(base_prob + noise, 0.05, 0.95)
    
    def generate_all_data(self) -> Tuple[List[StudentProfile], List[AttemptRecord]]:
        """Генерирует все данные с улучшенными алгоритмами"""
        print(f"\n🚀 УЛУЧШЕННАЯ ГЕНЕРАЦИЯ ДЛЯ {self.target_students} СТУДЕНТОВ")
        print('='*60)
        
        all_students = []
        all_attempts = []
        
        for i in range(self.target_students):
            if (i + 1) % 100 == 0:
                print(f"   Обработано студентов: {i + 1}/{self.target_students}")
            
            # Генерируем профиль
            student = self.generate_enhanced_student_profile(i + 1)
            all_students.append(student)
            
            # Обновляем статистику архетипов
            self.generation_stats['archetype_distribution'][student.archetype] += 1
            
            # Генерируем попытки
            attempts = self.generate_enhanced_student_attempts(student)
            all_attempts.extend(attempts)
        
        self.generation_stats['students_created'] = len(all_students)
        self.generation_stats['attempts_created'] = len(all_attempts)
        
        print(f"\n✅ Основная генерация завершена!")
        print(f"   Студентов: {len(all_students)}")
        print(f"   Попыток: {len(all_attempts)}")
        print(f"   Покрытие навыков: {len(self.generation_stats['skills_covered'])}/{len(self.all_skills)}")
        print(f"   Покрытие курсов: {len(self.generation_stats['courses_covered'])}/{len(self.courses)}")
        
        # Принудительно покрываем непокрытые навыки
        uncovered_skills = set(self.all_skills.keys()) - self.generation_stats['skills_covered']
        if uncovered_skills:
            print(f"\n🎯 ПРИНУДИТЕЛЬНОЕ ПОКРЫТИЕ {len(uncovered_skills)} НЕПОКРЫТЫХ НАВЫКОВ")
            print("="*60)
            
            additional_attempts = self.generate_coverage_attempts(uncovered_skills, all_students)
            all_attempts.extend(additional_attempts)
            
            self.generation_stats['attempts_created'] = len(all_attempts)
            print(f"   Добавлено попыток: {len(additional_attempts)}")
            print(f"   Финальное покрытие навыков: {len(self.generation_stats['skills_covered'])}/{len(self.all_skills)}")
        
        return all_students, all_attempts
    
    def generate_coverage_attempts(self, uncovered_skills: Set[int], students: List[StudentProfile]) -> List[AttemptRecord]:
        """Генерирует дополнительные попытки для покрытия непокрытых навыков"""
        
        coverage_attempts = []
        attempt_counter = 1
        
        for skill_id in uncovered_skills:
            # Находим задания для этого навыка
            skill_tasks = self.tasks_by_skill.get(skill_id, [])
            if not skill_tasks:
                print(f"   ⚠️ Навык {skill_id} ({self.all_skills[skill_id]['name']}) - нет заданий")
                continue
              # Выбираем случайных студентов для покрытия этого навыка
            selected_students = random.sample(students, min(20, len(students)))
            
            for student in selected_students:
                # Выбираем случайное задание для навыка
                task = random.choice(skill_tasks)
                
                # Генерируем попытку с высокой вероятностью успеха (чтобы обеспечить покрытие)
                success_prob = max(0.7, student.base_success_rate)
                is_correct = np.random.random() < success_prob
                
                # Генерируем время и оценку
                base_time = {'beginner': 180, 'intermediate': 300, 'advanced': 450}
                time_spent = int(np.random.normal(
                    base_time[task['difficulty']], 
                    base_time[task['difficulty']] * 0.2
                ))
                time_spent = max(30, min(900, time_spent))
                
                score = np.random.uniform(0.7, 1.0) if is_correct else np.random.uniform(0.0, 0.4)
                
                # Создаем попытку
                attempt = AttemptRecord(
                    student_id=student.id,
                    task_id=task['id'],
                    skill_ids=task['skill_ids'],
                    is_correct=is_correct,
                    score=score,
                    time_spent=time_spent,
                    difficulty=task['difficulty'],
                    task_type=task['task_type'],
                    timestamp=datetime.now() - timedelta(days=np.random.randint(1, 30)),
                    session_id=999  # Специальная сессия для покрытия
                )
                
                coverage_attempts.append(attempt)
                
                # Обновляем статистику
                self.generation_stats['skills_covered'].update(task['skill_ids'])
                self.generation_stats['courses_covered'].update(task['course_ids'])
                
                for skill_id_task in task['skill_ids']:
                    skill_level = self.skill_levels.get(skill_id_task, 0)
                    self.generation_stats['level_coverage'][skill_level] += 1
                    
                    for course_id in task['course_ids']:
                        self.generation_stats['skill_coverage_per_course'][course_id].add(skill_id_task)
                
                # Ограничиваем количество попыток на навык
                if len([a for a in coverage_attempts if skill_id in a.skill_ids]) >= 10:
                    break
            
            print(f"   ✅ Покрыт навык: {self.all_skills[skill_id]['name']}")
        
        return coverage_attempts
    
    def convert_to_dkn_format(self, students: List[StudentProfile], 
                            attempts: List[AttemptRecord]) -> pd.DataFrame:
        """Преобразует данные в формат DKN"""
        print("\n🔄 Преобразование в формат DKN...")
        
        # Группируем попытки по студентам
        attempts_by_student = defaultdict(list)
        for attempt in attempts:
            attempts_by_student[attempt.student_id].append(attempt)
        
        # Создаем DKN примеры
        dkn_examples = []
        
        for student_id, student_attempts in attempts_by_student.items():
            # Сортируем по времени
            student_attempts.sort(key=lambda x: x.timestamp)
            
            # Создаем примеры (каждая попытка = пример для следующей)
            for i in range(1, len(student_attempts)):
                history = student_attempts[:i]
                target_attempt = student_attempts[i]
                
                # Берем последние 10 попыток как историю
                recent_history = history[-10:]
                
                # Создаем признаки
                example = {'student_id': student_id, 'task_id': target_attempt.task_id}
                
                # Целевая переменная
                example['target'] = float(target_attempt.is_correct)
                
                # История (дополняем нулями если меньше 10)
                for j in range(10):
                    if j < len(recent_history):
                        h = recent_history[j]
                        example[f'hist_{j}_correct'] = float(h.is_correct)
                        example[f'hist_{j}_score'] = h.score
                        example[f'hist_{j}_time'] = h.time_spent
                    else:
                        example[f'hist_{j}_correct'] = 0.0
                        example[f'hist_{j}_score'] = 0.0
                        example[f'hist_{j}_time'] = 0
                
                # BKT параметры (упрощенные)
                example['skill_0_learned'] = min(len(history) * 0.1, 1.0)
                example['skill_0_transit'] = 0.3
                
                # Характеристики задания
                difficulty_map = {'beginner': 0, 'intermediate': 1, 'advanced': 2}
                type_map = {'single': 0, 'multiple': 1, 'true_false': 2}
                
                example['task_difficulty'] = difficulty_map.get(target_attempt.difficulty, 1)
                example['task_type'] = type_map.get(target_attempt.task_type, 0)
                
                dkn_examples.append(example)
        
        df = pd.DataFrame(dkn_examples)
        print(f"✅ Создано {len(df)} примеров для DKN")
        
        return df
    
    def save_dataset_and_generate_report(self, df: pd.DataFrame):
        """Сохраняет датасет и создает подробный отчет"""
        
        # Сохраняем основной датасет
        dataset_path = os.path.join(self.output_dir, 'enhanced_synthetic_dataset.csv')
        df.to_csv(dataset_path, index=False)
        print(f"💾 Датасет сохранен: {dataset_path}")
        
        # Сохраняем статистику генерации
        stats_path = os.path.join(self.output_dir, 'generation_statistics.json')
          # Конвертируем sets в lists для JSON
        json_stats = {}
        for key, value in self.generation_stats.items():
            if isinstance(value, set):
                json_stats[key] = list(value)
            elif isinstance(value, defaultdict):
                # Обрабатываем defaultdict с множествами
                converted_dict = {}
                for k, v in value.items():
                    if isinstance(v, set):
                        converted_dict[k] = list(v)
                    else:
                        converted_dict[k] = v
                json_stats[key] = converted_dict
            else:
                json_stats[key] = value
        
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(json_stats, f, ensure_ascii=False, indent=2)
        
        print(f"📊 Статистика сохранена: {stats_path}")
        
        # Создаем визуализации
        self.create_visualizations(df)
        
        # Создаем отчет
        self.create_detailed_report(df)
        
        return dataset_path
    
    def create_visualizations(self, df: pd.DataFrame):
        """Создает визуализации датасета"""
        print("📈 Создание визуализаций...")
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('Анализ синтетического датасета DKN', fontsize=16)
        
        # 1. Распределение архетипов
        archetype_counts = list(self.generation_stats['archetype_distribution'].values())
        archetype_names = list(self.generation_stats['archetype_distribution'].keys())
        
        axes[0, 0].pie(archetype_counts, labels=archetype_names, autopct='%1.1f%%')
        axes[0, 0].set_title('Распределение архетипов студентов')
        
        # 2. Покрытие по уровням
        level_counts = list(self.generation_stats['level_coverage'].values())
        levels = list(self.generation_stats['level_coverage'].keys())
        
        axes[0, 1].bar(levels, level_counts)
        axes[0, 1].set_title('Покрытие по уровням навыков')
        axes[0, 1].set_xlabel('Уровень навыка')
        axes[0, 1].set_ylabel('Количество попыток')
        
        # 3. Распределение успеваемости
        axes[0, 2].hist(df['target'], bins=2, alpha=0.7, edgecolor='black')
        axes[0, 2].set_title('Распределение успеваемости')
        axes[0, 2].set_xlabel('Результат (0=неуспех, 1=успех)')
        axes[0, 2].set_ylabel('Количество попыток')
        
        # 4. Активность студентов
        student_activity = df.groupby('student_id').size()
        axes[1, 0].hist(student_activity, bins=30, alpha=0.7, edgecolor='black')
        axes[1, 0].set_title('Активность студентов')
        axes[1, 0].set_xlabel('Количество попыток на студента')
        axes[1, 0].set_ylabel('Количество студентов')
        
        # 5. Распределение по типам заданий
        task_type_counts = df['task_type'].value_counts()
        axes[1, 1].bar(task_type_counts.index, task_type_counts.values)
        axes[1, 1].set_title('Распределение по типам заданий')
        axes[1, 1].set_xlabel('Тип задания')
        axes[1, 1].set_ylabel('Количество')
        
        # 6. Распределение по сложности
        difficulty_counts = df['task_difficulty'].value_counts().sort_index()
        difficulty_labels = ['Beginner', 'Intermediate', 'Advanced']
        axes[1, 2].bar(range(len(difficulty_counts)), difficulty_counts.values)
        axes[1, 2].set_title('Распределение по сложности')
        axes[1, 2].set_xlabel('Уровень сложности')
        axes[1, 2].set_ylabel('Количество')
        axes[1, 2].set_xticks(range(len(difficulty_labels)))
        axes[1, 2].set_xticklabels(difficulty_labels)
        
        plt.tight_layout()
        
        viz_path = os.path.join(self.output_dir, 'dataset_visualizations.png')
        plt.savefig(viz_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"📊 Визуализации сохранены: {viz_path}")
    
    def create_detailed_report(self, df: pd.DataFrame):
        """Создает подробный MD отчет"""
        report_path = os.path.join(self.output_dir, 'DATASET_REPORT.md')
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(self._generate_report_content(df))
        
        print(f"📝 Отчет создан: {report_path}")
    
    def _generate_report_content(self, df: pd.DataFrame) -> str:
        """Генерирует содержимое отчета"""
        
        # Вычисляем дополнительные метрики
        total_skills = len(self.all_skills)
        covered_skills = len(self.generation_stats['skills_covered'])
        skill_coverage_percent = (covered_skills / total_skills) * 100
        
        success_rate = df['target'].mean() * 100
        avg_attempts_per_student = df.groupby('student_id').size().mean()
        
        # Покрытие по курсам
        course_coverage_info = []
        for course_id, course_data in self.courses.items():
            course_skills = set(course_data['skills'])
            covered_course_skills = self.generation_stats['skill_coverage_per_course'][course_id]
            coverage_percent = (len(covered_course_skills) / len(course_skills)) * 100
            
            course_coverage_info.append({
                'name': course_data['name'],
                'total_skills': len(course_skills),
                'covered_skills': len(covered_course_skills),
                'coverage_percent': coverage_percent
            })
        
        report = f"""# Отчет о синтетическом датасете DKN

## 📊 Основные метрики

**Дата создания**: {datetime.now().strftime('%d.%m.%Y %H:%M')}

### Размер датасета
- **Общее количество примеров**: {len(df):,}
- **Количество студентов**: {self.generation_stats['students_created']:,}
- **Количество попыток**: {self.generation_stats['attempts_created']:,}
- **Среднее попыток на студента**: {avg_attempts_per_student:.1f}

### Покрытие системы
- **Покрытие навыков**: {covered_skills}/{total_skills} ({skill_coverage_percent:.1f}%)
- **Покрытие курсов**: {len(self.generation_stats['courses_covered'])}/{len(self.courses)} (100%)
- **Общая успеваемость**: {success_rate:.1f}%

## 🎯 Архетипы студентов

Датасет включает следующие типы студентов:

"""
        
        # Добавляем информацию об архетипах
        for archetype, count in self.generation_stats['archetype_distribution'].items():
            percentage = (count / self.generation_stats['students_created']) * 100
            archetype_info = self.archetypes[archetype]
            
            report += f"""### {archetype} ({count} студентов, {percentage:.1f}%)

- **Описание**: {archetype_info['description']}
- **Успеваемость**: {archetype_info['success_rate_range'][0]*100:.0f}%-{archetype_info['success_rate_range'][1]*100:.0f}%
- **Количество попыток**: {archetype_info['attempts_range'][0]}-{archetype_info['attempts_range'][1]}
- **Скорость обучения**: {archetype_info['learning_speed']}
- **Фокус курса**: {archetype_info.get('course_focus', 'Все курсы')}
- **Максимальный уровень**: {archetype_info.get('max_level', 'Без ограничений')}

"""
        
        # Покрытие по курсам
        report += "\n## 📚 Покрытие по курсам\n\n"
        
        for course_info in course_coverage_info:
            report += f"""### {course_info['name']}
- **Навыков в курсе**: {course_info['total_skills']}
- **Покрыто навыков**: {course_info['covered_skills']}
- **Процент покрытия**: {course_info['coverage_percent']:.1f}%

"""
        
        # Алгоритм генерации
        report += """## ⚙️ Алгоритм генерации

### Принципы создания данных

1. **Курсовая осведомленность**: Студенты имеют предпочтения к определенным курсам
2. **Реалистичные траектории**: Следование графу зависимостей навыков
3. **Полное покрытие**: Гарантированное покрытие всех навыков и курсов
4. **Разнообразие архетипов**: 7 различных типов студентов

### Стратегии обучения

- **Linear**: Последовательное изучение от простых к сложным навыкам
- **Breadth-first**: Изучение всех навыков одного уровня перед переходом к следующему
- **Focused**: Концентрация на навыках определенного курса
- **Random**: Случайное изучение доступных навыков

### Модель успеха

Вероятность успеха студента на задании вычисляется на основе:

1. **Базовой способности студента** (зависит от архетипа)
2. **Специфической способности к навыку** (с учетом курсового фокуса)
3. **Текущего уровня освоения навыка** (накопленного опыта)
4. **Сложности задания** (beginner/intermediate/advanced)
5. **Случайного шума** (моделирует непостоянство производительности)

### Граф навыков

Датасет учитывает иерархическую структуру навыков:

"""
        
        # Добавляем информацию об уровнях
        max_level = max(self.skill_levels.values())
        for level in range(max_level + 1):
            skills_at_level = [skill_id for skill_id, skill_level in self.skill_levels.items() 
                             if skill_level == level]
            if skills_at_level:
                attempts_at_level = self.generation_stats['level_coverage'].get(level, 0)
                report += f"- **Уровень {level}**: {len(skills_at_level)} навыков, {attempts_at_level} попыток\n"
        
        # Формат данных
        report += f"""
## 📋 Формат данных

### Структура примера DKN

Каждый пример в датасете представляет попытку студента решить задание и содержит:

1. **Идентификаторы**
   - `student_id`: Уникальный ID студента
   - `task_id`: ID задания

2. **Целевая переменная**
   - `target`: Результат попытки (0 = неуспех, 1 = успех)

3. **История попыток** (последние 10 попыток)
   - `hist_{{i}}_correct`: Правильность i-й попытки
   - `hist_{{i}}_score`: Оценка за i-ю попытку (0.0-1.0)
   - `hist_{{i}}_time`: Время выполнения i-й попытки (секунды)

4. **BKT параметры**
   - `skill_0_learned`: Вероятность освоения основного навыка
   - `skill_0_transit`: Вероятность перехода к освоению навыка

5. **Характеристики задания**
   - `task_difficulty`: Сложность (0=beginner, 1=intermediate, 2=advanced)
   - `task_type`: Тип (0=single, 1=multiple, 2=true_false)

### Размер файла

- **Строк**: {len(df):,}
- **Столбцов**: {len(df.columns)}
- **Размер файла**: ~{len(df) * len(df.columns) * 8 / 1024 / 1024:.1f} МБ

## 🔍 Анализ качества

### Распределение данных

- **Класс 0 (неуспех)**: {(1 - df['target'].mean()) * 100:.1f}%
- **Класс 1 (успех)**: {df['target'].mean() * 100:.1f}%
- **Баланс классов**: {'Сбалансированный' if 0.4 <= df['target'].mean() <= 0.6 else 'Несбалансированный'}

### Рекомендации для обучения

1. **Разделение данных**: 70% обучение, 15% валидация, 15% тест
2. **Кросс-валидация**: Использовать студентов как группы для избежания утечки данных
3. **Метрики**: Точность, Precision, Recall, F1-score, AUC-ROC
4. **Регуляризация**: Dropout и L2 регуляризация для избежания переобучения

## 📁 Файлы

- `enhanced_synthetic_dataset.csv`: Основной датасет
- `generation_statistics.json`: Подробная статистика генерации
- `dataset_visualizations.png`: Визуализации распределений
- `DATASET_REPORT.md`: Этот отчет
- `synthetic_data_spec.json`: Спецификация генерации

---

*Датасет создан для обучения Deep Knowledge Network (DKN) модели рекомендации заданий в адаптивной системе обучения.*
"""
        
        return report

    def run_enhanced_generation(self):
        """Запускает улучшенную генерацию данных"""
        
        print("🚀 ЗАПУСК УЛУЧШЕННОЙ ГЕНЕРАЦИИ СИНТЕТИЧЕСКИХ ДАННЫХ")
        print("="*60)
        
        # Генерируем данные
        students, attempts = self.generate_all_data()
        
        # Преобразуем в формат DKN
        df = self.convert_to_dkn_format(students, attempts)
        
        # Сохраняем и создаем отчеты
        dataset_path = self.save_dataset_and_generate_report(df)
        
        print(f"\n🎉 ГЕНЕРАЦИЯ ЗАВЕРШЕНА!")
        print(f"📁 Датасет: {dataset_path}")
        print(f"📊 Размер: {df.shape}")
        print(f"🎯 Покрытие навыков: {len(self.generation_stats['skills_covered'])}/{len(self.all_skills)}")
        print(f"📚 Покрытие курсов: {len(self.generation_stats['courses_covered'])}/{len(self.courses)}")
        
        return dataset_path


def main():
    """Основная функция запуска"""
    generator = EnhancedSyntheticDataGenerator()
    dataset_path = generator.run_enhanced_generation()
    
    print(f"\n✅ Улучшенный датасет готов: {dataset_path}")
    print("📖 Смотрите DATASET_REPORT.md для подробной информации")


if __name__ == "__main__":
    main()
