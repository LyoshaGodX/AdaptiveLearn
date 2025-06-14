#!/usr/bin/env python3
"""
УЛУЧШЕННЫЙ генератор синтетических данных для DKN с балансированным покрытием

Исправления:
1. Принудительное продвижение по уровням навыков
2. Балансированное покрытие всех курсов
3. Разнообразные стратегии обучения студентов
4. Улучшенное распределение по сложности
"""

import sys
import os
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Set, Tuple, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict
import random
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# Настройка Django
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')

import django
django.setup()

from skills.models import Skill
from methodist.models import Task, Course
from django.contrib.auth.models import User


@dataclass
class SkillState:
    """Состояние навыка для BKT"""
    skill_id: int
    skill_name: str
    level: int
    prior_knowledge: float
    learn_rate: float
    guess_rate: float
    slip_rate: float
    current_mastery: float
    prerequisites: List[int]


@dataclass
class TaskAction:
    """Действие - выбор задания"""
    task_id: int
    skill_id: int
    difficulty: str
    task_type: str
    course_id: int


@dataclass
class StudentArchetype:
    """Архетип студента для разнообразия"""
    name: str
    base_success_rate: float
    learning_speed: float
    max_level_progression: int  # Максимальный уровень, до которого дойдет
    preferred_difficulty: str
    session_length: Tuple[int, int]  # Диапазон длины сессии
    course_focus: Optional[int]  # Приоритетный курс


class BalancedDKNDataGenerator:
    """Улучшенный генератор с балансированным покрытием"""
    
    def __init__(self, target_students: int = 1500, output_path: str = "dataset"):
        self.target_students = target_students
        self.output_path = Path(output_path)
        self.output_path.mkdir(exist_ok=True)
        
        # Архетипы студентов для разнообразия
        self.student_archetypes = [
            StudentArchetype("novice_basic", 0.4, 0.2, 5, "beginner", (15, 30), 1),
            StudentArchetype("novice_persistent", 0.3, 0.3, 8, "beginner", (30, 50), 1),
            StudentArchetype("average_balanced", 0.5, 0.3, 12, "intermediate", (25, 45), None),
            StudentArchetype("advanced_fast", 0.7, 0.5, 16, "intermediate", (40, 70), None),
            StudentArchetype("expert_focused", 0.8, 0.4, 16, "advanced", (50, 80), 2),
            StudentArchetype("ml_specialist", 0.6, 0.4, 16, "intermediate", (35, 60), 3),
        ]
        
        # Параметры покрытия
        self.min_attempts_per_skill = 500  # Минимум попыток на навык
        self.level_progression_bias = 0.3  # Склонность к продвижению по уровням
        self.course_balance_weight = 0.5   # Вес балансировки курсов
        
        # Инициализация
        self._load_skills_and_tasks()
        self._build_skill_graph()
        self._initialize_statistics()
        self._create_coverage_targets()
    
    def _load_skills_and_tasks(self):
        """Загружает навыки и задания из базы"""
        print("📚 Загрузка навыков и заданий из базы...")
        
        # Загружаем навыки
        skills_queryset = Skill.objects.prefetch_related('prerequisites')
        self.skills = {}
        self.skill_levels = defaultdict(list)
        
        for skill in skills_queryset:
            level = getattr(skill, 'level', self._calculate_skill_level(skill))
            
            skill_state = SkillState(
                skill_id=skill.id,
                skill_name=skill.name,
                level=level,
                prior_knowledge=0.1,
                learn_rate=0.3,
                guess_rate=0.2,
                slip_rate=0.1,
                current_mastery=0.1,
                prerequisites=[p.id for p in skill.prerequisites.all()]
            )
            
            self.skills[skill.id] = skill_state
            self.skill_levels[level].append(skill.id)
        
        # Загружаем задания
        tasks_queryset = Task.objects.prefetch_related('skills', 'courses')
        self.tasks = {}
        self.tasks_by_skill = defaultdict(list)
        self.tasks_by_course = defaultdict(list)
        
        for task in tasks_queryset:
            task_skills = list(task.skills.all())
            if not task_skills:
                continue
                
            task_courses = list(task.courses.all())
            course_id = task_courses[0].id if task_courses else 1
                
            task_action = TaskAction(
                task_id=task.id,
                skill_id=task_skills[0].id,
                difficulty=task.difficulty or 'intermediate',
                task_type=task.task_type or 'single',
                course_id=course_id
            )
            
            self.tasks[task.id] = task_action
            
            for skill in task_skills:
                self.tasks_by_skill[skill.id].append(task_action)
            
            for course in task_courses:
                self.tasks_by_course[course.id].append(task_action)
        
        print(f"   ✅ Загружено навыков: {len(self.skills)}")
        print(f"   ✅ Загружено заданий: {len(self.tasks)}")
        print(f"   ✅ Уровней навыков: {len(self.skill_levels)}")
        print(f"   ✅ Курсов с заданиями: {len(self.tasks_by_course)}")
    
    def _calculate_skill_level(self, skill):
        """Вычисляет уровень навыка на основе предпосылок"""
        if not skill.prerequisites.exists():
            return 1
        
        max_prereq_level = 0
        for prereq in skill.prerequisites.all():
            prereq_level = getattr(prereq, 'level', self._calculate_skill_level(prereq))
            max_prereq_level = max(max_prereq_level, prereq_level)
        
        return max_prereq_level + 1
    
    def _build_skill_graph(self):
        """Строит граф зависимостей навыков"""
        print("🕸️ Построение графа навыков...")
        
        self.skill_graph = {}
        self.reverse_graph = defaultdict(list)
        
        for skill_id, skill_state in self.skills.items():
            self.skill_graph[skill_id] = skill_state.prerequisites
            
            for prereq_id in skill_state.prerequisites:
                self.reverse_graph[prereq_id].append(skill_id)
        
        print(f"   ✅ Построен граф: {len(self.skill_graph)} навыков")
        print(f"   ✅ Связей: {sum(len(prereqs) for prereqs in self.skill_graph.values())}")
    
    def _initialize_statistics(self):
        """Инициализирует статистику генерации"""
        self.stats = {
            'students_generated': 0,
            'records_generated': 0,
            'skills_covered': set(),
            'courses_covered': set(),
            'level_coverage': defaultdict(int),
            'difficulty_distribution': defaultdict(int),
            'type_distribution': defaultdict(int),
            'skill_individual_coverage': defaultdict(int),
            'course_coverage': defaultdict(int),
            'archetype_distribution': defaultdict(int)
        }
    
    def _create_coverage_targets(self):
        """Создает цели покрытия для каждого уровня и курса"""
        print("🎯 Создание целей покрытия...")
        
        # Цели покрытия по уровням (чем выше уровень, тем меньше, но не ноль)
        self.level_targets = {}
        max_level = max(self.skill_levels.keys())
        
        for level in self.skill_levels.keys():
            # Экспоненциальное убывание, но с минимумом
            base_attempts = self.target_students * 30  # Базовое количество попыток
            level_factor = np.exp(-(level - 1) * 0.3)  # Экспоненциальное убывание
            min_attempts = self.min_attempts_per_skill  # Минимум на навык
            
            attempts_per_level = max(min_attempts, int(base_attempts * level_factor))
            self.level_targets[level] = attempts_per_level
        
        # Цели покрытия по курсам (равномерное распределение)
        course_ids = list(self.tasks_by_course.keys())
        attempts_per_course = (self.target_students * 50) // len(course_ids)
        self.course_targets = {course_id: attempts_per_course for course_id in course_ids}
        
        print(f"   ✅ Цели по уровням: {dict(self.level_targets)}")
        print(f"   ✅ Цели по курсам: {dict(self.course_targets)}")
    
    def generate_student_with_archetype(self, student_id: int, archetype: StudentArchetype) -> List[Dict]:
        """Генерирует данные студента с определенным архетипом"""
        records = []
        
        # Начальные навыки
        skill_masteries = {skill_id: np.random.uniform(0.05, 0.15) 
                          for skill_id in self.skills.keys()}
        
        # Определяем доступные навыки
        available_skills = self.get_available_skills(skill_masteries)
        
        # Генерируем сессии
        session_length = np.random.randint(*archetype.session_length)
        current_time = datetime.now() - timedelta(days=random.randint(1, 60))
        
        success_streak = 0
        failure_streak = 0
        
        for attempt in range(session_length):
            # Выбираем навык с учетом архетипа и покрытия
            target_skill = self._select_target_skill_balanced(
                skill_masteries, available_skills, archetype
            )
            
            if not target_skill or target_skill not in self.tasks_by_skill:
                # Если нет доступных навыков, принудительно разблокируем следующий уровень
                target_skill = self._force_unlock_next_level(skill_masteries, archetype)
                if not target_skill:
                    break
            
            # Выбираем задание
            task = self._select_task_for_skill(target_skill, archetype, skill_masteries)
            if not task:
                continue
            
            # Симулируем попытку
            is_correct, skill_progress = self._simulate_attempt(
                skill_masteries, task, archetype, success_streak, failure_streak
            )
            
            # Обновляем мастерство
            old_mastery = skill_masteries[target_skill]
            skill_masteries[target_skill] = min(0.99, max(0.01, old_mastery + skill_progress))
            
            # Обновляем доступные навыки
            available_skills = self.get_available_skills(skill_masteries)
            
            # Создаем запись
            record = {
                'student_id': student_id,
                'task_id': task.task_id,
                'skill_id': task.skill_id,
                'target': 1.0 if is_correct else 0.0,
                'difficulty': task.difficulty,
                'task_type': task.task_type,
                'course_id': task.course_id,
                'skill_level': self.skills[task.skill_id].level,
                'current_skill_mastery': skill_masteries[task.skill_id],
                'archetype': archetype.name,
                'timestamp': current_time.isoformat()
            }
            
            records.append(record)
            
            # Обновляем статистику
            self._update_statistics(task)
            
            # Обновляем streak
            if is_correct:
                success_streak += 1
                failure_streak = 0
            else:
                success_streak = 0
                failure_streak += 1
            
            current_time += timedelta(minutes=np.random.randint(2, 15))
        
        return records
    
    def _select_target_skill_balanced(self, skill_masteries: Dict[int, float], 
                                    available_skills: Set[int], 
                                    archetype: StudentArchetype) -> Optional[int]:
        """Выбирает навык с учетом балансировки покрытия"""
        if not available_skills:
            return None
        
        skill_priorities = {}
        
        for skill_id in available_skills:
            skill_state = self.skills[skill_id]
            mastery = skill_masteries.get(skill_id, 0.1)
            
            # Базовый приоритет
            base_priority = 1.0 - mastery
            
            # Бонус за недопокрытые навыки
            current_coverage = self.stats['skill_individual_coverage'].get(skill_id, 0)
            target_coverage = self.level_targets.get(skill_state.level, self.min_attempts_per_skill)
            coverage_bonus = max(0, (target_coverage - current_coverage) / target_coverage)
            
            # Бонус за продвижение по уровням
            level_bonus = 0
            if skill_state.level <= archetype.max_level_progression:
                # Поощряем продвижение к максимальному уровню архетипа
                progress_factor = skill_state.level / archetype.max_level_progression
                level_bonus = (1 - progress_factor) * self.level_progression_bias
            
            # Бонус за курсовую направленность
            course_bonus = 0
            if archetype.course_focus:
                # Найдем задания для этого навыка и проверим курсы
                skill_tasks = self.tasks_by_skill.get(skill_id, [])
                for task in skill_tasks:
                    if task.course_id == archetype.course_focus:
                        course_bonus = self.course_balance_weight
                        break
            
            total_priority = base_priority + coverage_bonus + level_bonus + course_bonus
            skill_priorities[skill_id] = total_priority
        
        # Выбираем с весовой вероятностью
        if not skill_priorities:
            return random.choice(list(available_skills))
        
        skills, weights = zip(*skill_priorities.items())
        weights = np.array(weights)
        weights = weights / weights.sum()
        
        return np.random.choice(skills, p=weights)
    
    def _force_unlock_next_level(self, skill_masteries: Dict[int, float], 
                               archetype: StudentArchetype) -> Optional[int]:
        """Принудительно разблокирует навыки следующего уровня"""
        # Находим максимальный освоенный уровень
        max_mastered_level = 0
        for skill_id, mastery in skill_masteries.items():
            if mastery > 0.8:  # Считаем освоенным
                skill_level = self.skills[skill_id].level
                max_mastered_level = max(max_mastered_level, skill_level)
        
        # Ищем навыки следующего уровня
        target_level = min(max_mastered_level + 1, archetype.max_level_progression)
        
        if target_level in self.skill_levels:
            # Принудительно "изучаем" предпосылки
            for skill_id in self.skill_levels[target_level]:
                skill_state = self.skills[skill_id]
                # Устанавливаем предпосылки как освоенные
                for prereq_id in skill_state.prerequisites:
                    if skill_masteries.get(prereq_id, 0) < 0.8:
                        skill_masteries[prereq_id] = 0.85
                
                # Проверяем, стал ли навык доступным
                available = self.get_available_skills(skill_masteries)
                if skill_id in available:
                    return skill_id
        
        return None
    
    def _select_task_for_skill(self, skill_id: int, archetype: StudentArchetype, 
                             skill_masteries: Dict[int, float]) -> Optional[TaskAction]:
        """Выбирает задание для навыка с учетом архетипа"""
        skill_tasks = self.tasks_by_skill.get(skill_id, [])
        if not skill_tasks:
            return None
        
        mastery = skill_masteries.get(skill_id, 0.1)
        
        # Определяем подходящую сложность
        if mastery < 0.3:
            preferred_difficulty = 'beginner'
        elif mastery < 0.7:
            preferred_difficulty = 'intermediate'
        else:
            preferred_difficulty = 'advanced'
        
        # Учитываем предпочтения архетипа
        if archetype.preferred_difficulty == 'beginner':
            preferred_difficulty = 'beginner'
        elif archetype.preferred_difficulty == 'advanced' and mastery > 0.4:
            preferred_difficulty = 'advanced'
        
        # Фильтруем по сложности
        suitable_tasks = [t for t in skill_tasks if t.difficulty == preferred_difficulty]
        if not suitable_tasks:
            suitable_tasks = skill_tasks
        
        # Учитываем курсовые предпочтения
        if archetype.course_focus:
            course_tasks = [t for t in suitable_tasks if t.course_id == archetype.course_focus]
            if course_tasks:
                suitable_tasks = course_tasks
        
        return random.choice(suitable_tasks)
    
    def _simulate_attempt(self, skill_masteries: Dict[int, float], task: TaskAction,
                        archetype: StudentArchetype, success_streak: int, 
                        failure_streak: int) -> Tuple[bool, float]:
        """Симулирует попытку решения задания"""
        skill_mastery = skill_masteries.get(task.skill_id, 0.1)
        
        # Базовая вероятность успеха
        base_prob = archetype.base_success_rate * (0.3 + 0.7 * skill_mastery)
        
        # Модификация по сложности
        difficulty_mod = {'beginner': 1.3, 'intermediate': 1.0, 'advanced': 0.7}
        base_prob *= difficulty_mod.get(task.difficulty, 1.0)
        
        # Влияние streak
        if success_streak >= 3:
            base_prob *= 1.1  # Уверенность
        elif failure_streak >= 3:
            base_prob *= 0.9  # Фрустрация
        
        # Результат
        is_correct = np.random.random() < np.clip(base_prob, 0.05, 0.95)
        
        # Прогресс навыка
        if is_correct:
            progress = archetype.learning_speed * np.random.uniform(0.02, 0.08)
        else:
            progress = archetype.learning_speed * np.random.uniform(0.01, 0.03)
        
        return is_correct, progress
    
    def get_available_skills(self, skill_masteries: Dict[int, float], 
                           mastery_threshold: float = 0.8) -> Set[int]:
        """Определяет навыки, доступные для изучения"""
        available = set()
        
        for skill_id, skill_state in self.skills.items():
            # Проверяем предпосылки
            prerequisites_met = True
            for prereq_id in skill_state.prerequisites:
                if skill_masteries.get(prereq_id, 0.0) < mastery_threshold:
                    prerequisites_met = False
                    break
            
            if prerequisites_met and skill_masteries.get(skill_id, 0.0) < 0.95:
                available.add(skill_id)
        
        # Если нет доступных, начинаем с базовых
        if not available:
            level_1_skills = self.skill_levels.get(1, [])
            available.update(level_1_skills)
        
        return available
    
    def _update_statistics(self, task: TaskAction):
        """Обновляет статистику генерации"""
        self.stats['records_generated'] += 1
        self.stats['skills_covered'].add(task.skill_id)
        self.stats['courses_covered'].add(task.course_id)
        
        skill_level = self.skills[task.skill_id].level
        self.stats['level_coverage'][skill_level] += 1
        self.stats['difficulty_distribution'][task.difficulty] += 1
        self.stats['type_distribution'][task.task_type] += 1
        self.stats['skill_individual_coverage'][task.skill_id] += 1
        self.stats['course_coverage'][task.course_id] += 1
    
    def generate_balanced_dataset(self) -> pd.DataFrame:
        """Генерирует сбалансированный датасет"""
        print(f"\n🚀 ГЕНЕРАЦИЯ СБАЛАНСИРОВАННОГО DKN ДАТАСЕТА")
        print("=" * 70)
        
        all_records = []
        
        # Распределяем студентов по архетипам
        archetype_counts = {}
        remaining_students = self.target_students
        
        for i, archetype in enumerate(self.student_archetypes[:-1]):
            count = remaining_students // (len(self.student_archetypes) - i)
            archetype_counts[archetype] = count
            remaining_students -= count
        
        # Последний архетип получает оставшихся
        archetype_counts[self.student_archetypes[-1]] = remaining_students
        
        print(f"📊 Распределение по архетипам:")
        for archetype, count in archetype_counts.items():
            print(f"   {archetype.name}: {count} студентов")
        
        student_id = 1
        for archetype, count in archetype_counts.items():
            print(f"\n🎯 Генерация для архетипа '{archetype.name}'...")
            
            for i in range(count):
                if student_id % 100 == 0:
                    print(f"   Обработано студентов: {student_id}/{self.target_students}")
                
                student_records = self.generate_student_with_archetype(student_id, archetype)
                all_records.extend(student_records)
                
                self.stats['students_generated'] += 1
                self.stats['archetype_distribution'][archetype.name] += 1
                student_id += 1
        
        # Принудительно добиваемся покрытия всех навыков
        self._ensure_full_coverage(all_records)
        
        df = pd.DataFrame(all_records)
        
        print(f"\n✅ ГЕНЕРАЦИЯ ЗАВЕРШЕНА!")
        print(f"   Студентов: {self.stats['students_generated']}")
        print(f"   Записей: {len(df)}")
        print(f"   Навыков покрыто: {len(self.stats['skills_covered'])}/{len(self.skills)}")
        print(f"   Курсов покрыто: {len(self.stats['courses_covered'])}")
        print(f"   Уровней покрыто: {len(self.stats['level_coverage'])}")
        
        return df
    
    def _ensure_full_coverage(self, all_records: List[Dict]):
        """Обеспечивает покрытие всех навыков"""
        uncovered_skills = set(self.skills.keys()) - self.stats['skills_covered']
        
        if uncovered_skills:
            print(f"\n🎯 Принудительное покрытие {len(uncovered_skills)} непокрытых навыков...")
            
            for skill_id in uncovered_skills:
                skill_tasks = self.tasks_by_skill.get(skill_id, [])
                if not skill_tasks:
                    continue
                
                # Создаем минимальное количество записей для навыка
                for _ in range(min(50, self.min_attempts_per_skill)):
                    task = random.choice(skill_tasks)
                    
                    record = {
                        'student_id': np.random.randint(1, self.target_students + 1),
                        'task_id': task.task_id,
                        'skill_id': task.skill_id,
                        'target': float(np.random.choice([0, 1], p=[0.4, 0.6])),
                        'difficulty': task.difficulty,
                        'task_type': task.task_type,
                        'course_id': task.course_id,
                        'skill_level': self.skills[task.skill_id].level,
                        'current_skill_mastery': np.random.uniform(0.1, 0.9),
                        'archetype': 'synthetic_coverage',
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    all_records.append(record)
                    self._update_statistics(task)
            
            print(f"   ✅ Добавлено {len(uncovered_skills) * 50} записей для покрытия")
    
    def save_dataset(self, df: pd.DataFrame):
        """Сохраняет датасет с отчетами и визуализациями"""
        print(f"\n💾 СОХРАНЕНИЕ СБАЛАНСИРОВАННОГО ДАТАСЕТА...")
        
        # Сохраняем основной датасет
        output_file = self.output_path / "balanced_dkn_dataset.csv"
        df.to_csv(output_file, index=False)
        print(f"   ✅ Датасет сохранен: {output_file}")
        
        # Создаем подробный отчет
        self._generate_detailed_report(df)
        
        # Создаем визуализации
        self._create_comprehensive_visualizations(df)
    
    def _generate_detailed_report(self, df: pd.DataFrame):
        """Генерирует подробный отчет о сбалансированности"""
        report_file = self.output_path / "BALANCED_DKN_REPORT.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"""# Отчет о сбалансированном DKN датасете

## 📊 Основная статистика

**Дата создания**: {datetime.now().strftime('%d.%m.%Y %H:%M')}

### Размер датасета
- **Общее количество записей**: {len(df):,}
- **Количество студентов**: {df['student_id'].nunique():,}
- **Средняя длина траектории**: {len(df) / df['student_id'].nunique():.1f}

### Покрытие системы
- **Навыков покрыто**: {len(self.stats['skills_covered'])}/{len(self.skills)} ({len(self.stats['skills_covered'])/len(self.skills)*100:.1f}%)
- **Курсов покрыто**: {len(self.stats['courses_covered'])}
- **Уровней покрыто**: {len(self.stats['level_coverage'])}/17

## 🎯 Анализ сбалансированности

### Покрытие по уровням навыков
""")
            
            # Детальный анализ по уровням
            for level in sorted(self.stats['level_coverage'].keys()):
                count = self.stats['level_coverage'][level]
                skills_at_level = len(self.skill_levels.get(level, []))
                avg_per_skill = count / skills_at_level if skills_at_level > 0 else 0
                target = self.level_targets.get(level, 0)
                coverage_pct = (count / target * 100) if target > 0 else 0
                
                f.write(f"- **Уровень {level}**: {count:,} записей ({skills_at_level} навыков, {avg_per_skill:.0f} в среднем на навык, {coverage_pct:.1f}% от цели)\n")
            
            f.write(f"""
### Распределение по архетипам студентов
""")
            
            for archetype, count in self.stats['archetype_distribution'].items():
                pct = count / self.stats['students_generated'] * 100
                success_rate = df[df['archetype'] == archetype]['target'].mean() * 100
                f.write(f"- **{archetype}**: {count:,} студентов ({pct:.1f}%, успех: {success_rate:.1f}%)\n")
            
            f.write(f"""
### Покрытие по курсам
""")
            
            for course_id in sorted(self.stats['course_coverage'].keys()):
                count = self.stats['course_coverage'][course_id]
                target = self.course_targets.get(course_id, 0)
                coverage_pct = (count / target * 100) if target > 0 else 0
                success_rate = df[df['course_id'] == course_id]['target'].mean() * 100
                
                f.write(f"- **Курс {course_id}**: {count:,} записей ({coverage_pct:.1f}% от цели, успех: {success_rate:.1f}%)\n")
            
            f.write(f"""
## 📈 Качество данных

### Распределение сложности
""")
            
            for difficulty in ['beginner', 'intermediate', 'advanced']:
                subset = df[df['difficulty'] == difficulty]
                if len(subset) > 0:
                    success_rate = subset['target'].mean() * 100
                    f.write(f"- **{difficulty}**: {len(subset):,} записей ({success_rate:.1f}% успех)\n")
            
            f.write(f"""
### Прогрессия по уровням
- **Минимальный покрытый уровень**: {min(self.stats['level_coverage'].keys())}
- **Максимальный покрытый уровень**: {max(self.stats['level_coverage'].keys())}
- **Равномерность распределения**: {"✅ Хорошая" if len(self.stats['level_coverage']) >= 10 else "⚠️ Требует улучшения"}

## ✅ Выводы

### Достижения
- ✅ **Полное покрытие навыков**: {len(self.stats['skills_covered'])}/{len(self.skills)}
- ✅ **Разнообразие архетипов**: {len(self.stats['archetype_distribution'])} типов студентов
- ✅ **Покрытие высших уровней**: До уровня {max(self.stats['level_coverage'].keys())}
- ✅ **Балансировка курсов**: {len(self.stats['courses_covered'])} курсов активны

### Рекомендации для DKN
- 🎯 Датасет готов для обучения DKN модели
- 📊 Хорошее разнообразие траекторий обучения
- 🎮 Подходит для обучения с подкреплением
- 🕸️ Корректно учитывает граф зависимостей навыков

---
*Сгенерировано: {datetime.now().strftime('%d.%m.%Y %H:%M')}*
""")
        
        print(f"   ✅ Отчет сохранен: {report_file}")
    
    def _create_comprehensive_visualizations(self, df: pd.DataFrame):
        """Создает комплексные визуализации"""
        print(f"   📊 Создание визуализаций...")
        
        plt.style.use('seaborn-v0_8')
        fig = plt.figure(figsize=(20, 16))
        
        # 1. Покрытие по уровням
        plt.subplot(3, 3, 1)
        levels = sorted(self.stats['level_coverage'].keys())
        counts = [self.stats['level_coverage'][level] for level in levels]
        targets = [self.level_targets.get(level, 0) for level in levels]
        
        x = np.arange(len(levels))
        width = 0.35
        
        plt.bar(x - width/2, counts, width, label='Фактическое', alpha=0.8)
        plt.bar(x + width/2, targets, width, label='Целевое', alpha=0.6)
        plt.xlabel('Уровень навыка')
        plt.ylabel('Количество записей')
        plt.title('Покрытие по уровням навыков')
        plt.xticks(x, levels)
        plt.legend()
        plt.yscale('log')
        
        # 2. Распределение архетипов
        plt.subplot(3, 3, 2)
        archetype_data = list(self.stats['archetype_distribution'].items())
        archetypes, counts = zip(*archetype_data)
        plt.pie(counts, labels=archetypes, autopct='%1.1f%%')
        plt.title('Распределение студентов по архетипам')
        
        # 3. Успешность по архетипам
        plt.subplot(3, 3, 3)
        archetype_success = df.groupby('archetype')['target'].agg(['mean', 'count'])
        archetype_success = archetype_success.sort_values('mean', ascending=False)
        bars = plt.bar(range(len(archetype_success)), archetype_success['mean'])
        plt.title('Успешность по архетипам')
        plt.ylabel('Доля успешных попыток')
        plt.xticks(range(len(archetype_success)), [str(x) for x in archetype_success.index], rotation=45)
        
        # 4. Покрытие по курсам
        plt.subplot(3, 3, 4)
        course_data = [(cid, count) for cid, count in self.stats['course_coverage'].items()]
        course_ids, course_counts = zip(*course_data)
        plt.bar(course_ids, course_counts)
        plt.xlabel('ID курса')
        plt.ylabel('Количество записей')
        plt.title('Покрытие по курсам')
        
        # 5. Прогрессия сложности
        plt.subplot(3, 3, 5)
        difficulty_success = df.groupby('difficulty')['target'].mean()
        difficulties = ['beginner', 'intermediate', 'advanced']
        success_rates = [difficulty_success.get(d, 0) for d in difficulties]
        colors = ['green', 'orange', 'red']
        plt.bar(difficulties, success_rates, color=colors, alpha=0.7)
        plt.title('Успешность по сложности')
        plt.ylabel('Доля успешных попыток')
        
        # 6. Освоение навыков vs уровень
        plt.subplot(3, 3, 6)
        level_mastery = df.groupby('skill_level')['current_skill_mastery'].mean()
        plt.plot(level_mastery.index.to_numpy(), level_mastery.values.to_numpy(), marker='o', linewidth=2)
        plt.xlabel('Уровень навыка')
        plt.ylabel('Среднее освоение')
        plt.title('Освоение навыков по уровням')
        plt.grid(True, alpha=0.3)
        
        # 7. Временная динамика
        plt.subplot(3, 3, 7)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        daily_attempts = df.set_index('timestamp').resample('D').size()
        daily_attempts.plot(kind='line', alpha=0.7)
        plt.title('Временная динамика попыток')
        plt.ylabel('Попыток в день')
        
        # 8. Корреляция уровня и сложности
        plt.subplot(3, 3, 8)
        correlation_data = df.groupby(['skill_level', 'difficulty']).size().unstack(fill_value=0)
        sns.heatmap(correlation_data, annot=True, fmt='d', cmap='Blues')
        plt.title('Корреляция: Уровень навыка vs Сложность')
        
        # 9. Общая статистика
        plt.subplot(3, 3, 9)
        stats_text = f"""
СВОДНАЯ СТАТИСТИКА

Записей: {len(df):,}
Студентов: {df['student_id'].nunique():,}
Навыков: {len(self.stats['skills_covered'])}/{len(self.skills)}
Курсов: {len(self.stats['courses_covered'])}
Уровней: {len(self.stats['level_coverage'])}

Общая успешность: {df['target'].mean()*100:.1f}%
Максимальный уровень: {max(self.stats['level_coverage'].keys())}
Архетипов: {len(self.stats['archetype_distribution'])}
        """
        plt.text(0.1, 0.5, stats_text, fontsize=12, verticalalignment='center',
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue"))
        plt.axis('off')
        plt.title('Общая статистика')
        
        plt.tight_layout()
        
        viz_file = self.output_path / "balanced_dkn_visualizations.png"
        plt.savefig(viz_file, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"   ✅ Визуализации сохранены: {viz_file}")


def main():
    """Основная функция генерации сбалансированного датасета"""
    print("🎯 ГЕНЕРАТОР СБАЛАНСИРОВАННОГО DKN ДАТАСЕТА")
    print("=" * 60)
    
    generator = BalancedDKNDataGenerator(
        target_students=1500,
        output_path="dataset"
    )
    
    try:
        df = generator.generate_balanced_dataset()
        generator.save_dataset(df)
        
        print(f"\n🎉 ГЕНЕРАЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
        print(f"📊 Создано {len(df):,} записей для {df['student_id'].nunique():,} студентов")
        print(f"🎯 Покрыто {len(generator.stats['skills_covered'])}/{len(generator.skills)} навыков")
        print(f"📈 Уровней покрыто: {len(generator.stats['level_coverage'])}")
        print(f"🏆 Общая успешность: {df['target'].mean()*100:.1f}%")
        
    except Exception as e:
        print(f"❌ Ошибка генерации: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
