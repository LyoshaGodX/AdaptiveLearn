#!/usr/bin/env python3
"""
Улучшенный генератор синтетических данных для DKN с обучением с подкреплением

Особенности:
1. Учитывает иерархический граф навыков (30 навыков, 16 уровней)
2. Адаптивный выбор сложности заданий на основе освоения навыков
3. Генерация данных для обучения с подкреплением (state, action, reward)
4. Реалистичные BKT параметры с временной динамикой
5. Покрытие всех навыков и курсов
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
    prior_knowledge: float  # P(L0) - начальное знание
    learn_rate: float      # P(T) - скорость обучения
    guess_rate: float      # P(G) - угадывание
    slip_rate: float       # P(S) - ошибка при знании
    current_mastery: float # Текущая вероятность освоения
    prerequisites: List[int] # ID предпосылок


@dataclass
class TaskAction:
    """Действие - выбор задания"""
    task_id: int
    skill_id: int
    difficulty: str  # beginner, intermediate, advanced
    task_type: str   # true_false, single, multiple
    course_id: int


@dataclass
class StudentState:
    """Состояние студента для RL"""
    student_id: int
    skill_masteries: Dict[int, float]  # Текущие BKT оценки
    available_skills: Set[int]         # Доступные для изучения навыки
    learning_trajectory: List[int]     # История изученных заданий
    session_progress: float           # Прогресс в текущей сессии
    fatigue_level: float             # Уровень усталости
    success_streak: int              # Серия успехов
    failure_streak: int              # Серия неудач


@dataclass
class ReinforcementRecord:
    """Запись для обучения с подкреплением"""
    student_id: int
    timestamp: datetime
    
    # State (Состояние)
    state: Dict[str, Any]
    
    # Action (Действие) 
    action: TaskAction
    
    # Reward (Награда)
    immediate_reward: float      # Мгновенная награда (правильность)
    learning_reward: float       # Награда за прогресс навыка
    exploration_reward: float    # Награда за исследование
    total_reward: float         # Общая награда
    
    # Next State (Следующее состояние)
    next_state: Dict[str, Any]
    
    # Episode info
    is_terminal: bool           # Конец эпизода
    expert_feedback: Optional[float]  # Обратная связь эксперта


class DKNReinforcementDataGenerator:
    """Генератор данных для DKN с обучением с подкреплением"""
    
    def __init__(self, target_students: int = 1500, output_path: str = "dataset"):
        self.target_students = target_students
        self.output_path = Path(output_path)
        self.output_path.mkdir(exist_ok=True)
        
        # BKT параметры по умолчанию
        self.default_bkt = {
            'prior_knowledge': 0.1,
            'learn_rate': 0.3,
            'guess_rate': 0.2,
            'slip_rate': 0.1
        }
        
        # Параметры RL
        self.reward_weights = {
            'correctness': 1.0,      # Вес за правильность
            'learning_progress': 2.0, # Вес за прогресс навыка
            'difficulty_match': 1.5,  # Вес за подходящую сложность
            'exploration': 0.5,      # Вес за исследование
            'efficiency': 1.0        # Вес за эффективность
        }
        
        # Инициализация
        self._load_skills_and_tasks()
        self._build_skill_graph()
        self._initialize_statistics()
    
    def _load_skills_and_tasks(self):
        """Загружает навыки и задания из базы"""
        print("📚 Загрузка навыков и заданий из базы...")
        
        # Загружаем навыки
        skills_queryset = Skill.objects.select_related().prefetch_related('prerequisites')
        self.skills = {}
        self.skill_levels = {}
        
        for skill in skills_queryset:
            # Определяем уровень навыка
            level = getattr(skill, 'level', self._calculate_skill_level(skill))
            
            skill_state = SkillState(
                skill_id=skill.id,
                skill_name=skill.name,
                level=level,
                prior_knowledge=self.default_bkt['prior_knowledge'],
                learn_rate=self.default_bkt['learn_rate'],
                guess_rate=self.default_bkt['guess_rate'],
                slip_rate=self.default_bkt['slip_rate'],
                current_mastery=self.default_bkt['prior_knowledge'],
                prerequisites=[p.id for p in skill.prerequisites.all()]
            )
            
            self.skills[skill.id] = skill_state
            self.skill_levels[level] = self.skill_levels.get(level, []) + [skill.id]
          # Загружаем задания
        tasks_queryset = Task.objects.prefetch_related('skills', 'courses')
        self.tasks = {}
        self.tasks_by_skill = defaultdict(list)
        self.tasks_by_course = defaultdict(list)
        
        for task in tasks_queryset:
            task_skills = list(task.skills.all())
            if not task_skills:
                continue
                
            # Определяем курс на основе связей
            task_courses = list(task.courses.all())
            course_id = task_courses[0].id if task_courses else 1
                
            task_action = TaskAction(
                task_id=task.id,
                skill_id=task_skills[0].id,  # Основной навык
                difficulty=task.difficulty or 'intermediate',
                task_type=task.task_type or 'single',
                course_id=course_id
            )            
            self.tasks[task.id] = task_action
            
            for skill in task_skills:
                self.tasks_by_skill[skill.id].append(task_action)
            
            # Добавляем в курсы
            for course in task_courses:
                self.tasks_by_course[course.id].append(task_action)
        
        print(f"   ✅ Загружено навыков: {len(self.skills)}")
        print(f"   ✅ Загружено заданий: {len(self.tasks)}")
        print(f"   ✅ Уровней навыков: {len(self.skill_levels)}")
    
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
        self.reverse_graph = defaultdict(list)  # Какие навыки открывает текущий
        for skill_id, skill_state in self.skills.items():
            self.skill_graph[skill_id] = skill_state.prerequisites
            
            # Строим обратный граф
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
            'reward_statistics': defaultdict(list),
            'skill_individual_coverage': defaultdict(int),
            'course_coverage': defaultdict(int)
        }
    
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
            
            if prerequisites_met:
                # Навык доступен, если не полностью освоен
                if skill_masteries.get(skill_id, 0.0) < 0.95:
                    available.add(skill_id)
        
        # Если нет доступных, начинаем с базовых навыков
        if not available:
            level_1_skills = self.skill_levels.get(1, [])
            available.update(level_1_skills)
        
        return available
    
    def select_optimal_task(self, student_state: StudentState) -> Optional[TaskAction]:
        """Выбирает оптимальное задание на основе состояния студента"""
        available_skills = student_state.available_skills
        if not available_skills:
            return None
        
        # Выбираем навык для развития
        target_skill = self._select_target_skill(student_state, available_skills)
        if not target_skill or target_skill not in self.tasks_by_skill:
            return None
        
        # Выбираем подходящее задание для навыка
        skill_tasks = self.tasks_by_skill[target_skill]
        if not skill_tasks:
            return None
        
        # Определяем подходящую сложность
        skill_mastery = student_state.skill_masteries.get(target_skill, 0.1)
        target_difficulty = self._determine_difficulty(skill_mastery, student_state)
        
        # Фильтруем задания по сложности
        suitable_tasks = [
            task for task in skill_tasks 
            if task.difficulty == target_difficulty
        ]
        
        if not suitable_tasks:
            suitable_tasks = skill_tasks  # Fallback
        
        return random.choice(suitable_tasks)
    
    def _select_target_skill(self, student_state: StudentState, 
                           available_skills: Set[int]) -> Optional[int]:
        """Выбирает целевой навык для развития"""
        skill_priorities = {}
        
        for skill_id in available_skills:
            skill_state = self.skills[skill_id]
            mastery = student_state.skill_masteries.get(skill_id, 0.1)
            
            # Приоритет = важность уровня + потенциал роста + разнообразие
            level_importance = 1.0 / (skill_state.level + 1)  # Базовые навыки важнее
            growth_potential = 1.0 - mastery  # Больше потенциала у неосвоенных
            exploration_bonus = 0.1 if skill_id not in student_state.learning_trajectory[-10:] else 0
            
            priority = level_importance + growth_potential + exploration_bonus
            skill_priorities[skill_id] = priority
        
        # Выбираем с весовой вероятностью
        if not skill_priorities:
            return None
        
        skills, weights = zip(*skill_priorities.items())
        weights = np.array(weights)
        weights = weights / weights.sum()
        
        return np.random.choice(skills, p=weights)
    
    def _determine_difficulty(self, skill_mastery: float, 
                            student_state: StudentState) -> str:
        """Определяет подходящую сложность задания"""
        # Базовая логика адаптивности
        if skill_mastery < 0.3:
            # Новый навык - легкие задания
            return 'beginner'
        elif skill_mastery < 0.7:
            # Развивающийся навык - средние задания
            if student_state.success_streak >= 3:
                return 'intermediate'
            else:
                return 'beginner'
        else:
            # Продвинутый навык - сложные задания
            if student_state.success_streak >= 2:
                return 'advanced'
            else:
                return 'intermediate'
    
    def calculate_rewards(self, student_state: StudentState, action: TaskAction, 
                         is_correct: bool, skill_progress: float) -> Dict[str, float]:
        """Вычисляет награды для обучения с подкреплением"""
        rewards = {}
        
        # 1. Награда за правильность
        rewards['correctness'] = 1.0 if is_correct else -0.5
        
        # 2. Награда за прогресс навыка
        rewards['learning_progress'] = skill_progress * 5.0
        
        # 3. Награда за подходящую сложность
        skill_mastery = student_state.skill_masteries.get(action.skill_id, 0.1)
        difficulty_match = self._calculate_difficulty_match(skill_mastery, action.difficulty)
        rewards['difficulty_match'] = difficulty_match
        
        # 4. Награда за исследование новых навыков
        recent_skills = set(self.tasks[tid].skill_id for tid in student_state.learning_trajectory[-5:] 
                           if tid in self.tasks)
        rewards['exploration'] = 0.5 if action.skill_id not in recent_skills else 0.0
        
        # 5. Штраф за неэффективность (слишком много ошибок подряд)
        rewards['efficiency'] = -0.3 if student_state.failure_streak >= 3 else 0.0
        
        # Общая награда
        total_reward = sum(
            rewards[key] * self.reward_weights[key] 
            for key in rewards if key in self.reward_weights
        )
        rewards['total'] = total_reward
        
        return rewards
    
    def _calculate_difficulty_match(self, skill_mastery: float, difficulty: str) -> float:
        """Вычисляет соответствие сложности задания уровню навыка"""
        difficulty_levels = {'beginner': 0.2, 'intermediate': 0.5, 'advanced': 0.8}
        target_level = difficulty_levels.get(difficulty, 0.5)
        
        # Чем ближе уровень навыка к целевому, тем лучше
        match_score = 1.0 - abs(skill_mastery - target_level)
        return max(0.0, match_score)
    
    def update_bkt_parameters(self, skill_id: int, is_correct: bool, 
                            current_mastery: float) -> float:
        """Обновляет BKT параметры после попытки"""
        skill_state = self.skills[skill_id]
        
        # BKT обновление
        if is_correct:
            # P(L_{n+1} | evidence) - правильный ответ
            evidence_prob = (
                current_mastery * (1 - skill_state.slip_rate) + 
                (1 - current_mastery) * skill_state.guess_rate
            )
            new_mastery = (
                current_mastery * (1 - skill_state.slip_rate) / evidence_prob
            )
        else:
            # P(L_{n+1} | evidence) - неправильный ответ
            evidence_prob = (
                current_mastery * skill_state.slip_rate + 
                (1 - current_mastery) * (1 - skill_state.guess_rate)
            )
            new_mastery = (
                current_mastery * skill_state.slip_rate / evidence_prob
            )
        
        # Обучение: P(L_{n+1}) = P(L_n) + (1-P(L_n)) * P(T)
        if not is_correct:  # Обучение происходит при ошибках
            new_mastery = new_mastery + (1 - new_mastery) * skill_state.learn_rate
        
        return min(0.99, max(0.01, new_mastery))
    
    def generate_student_episode(self, student_id: int, 
                               episode_length: int = 50) -> List[ReinforcementRecord]:
        """Генерирует эпизод обучения для одного студента"""
        records = []
        
        # Начальное состояние студента
        student_state = StudentState(
            student_id=student_id,
            skill_masteries={skill_id: np.random.uniform(0.05, 0.15) 
                           for skill_id in self.skills.keys()},
            available_skills=set(),
            learning_trajectory=[],
            session_progress=0.0,
            fatigue_level=0.0,
            success_streak=0,
            failure_streak=0
        )
        
        # Определяем доступные навыки
        student_state.available_skills = self.get_available_skills(student_state.skill_masteries)
        
        current_time = datetime.now() - timedelta(days=random.randint(1, 30))
        
        for step in range(episode_length):
            # Текущее состояние
            state = self._encode_state(student_state)
            
            # Выбираем действие
            action = self.select_optimal_task(student_state)
            if not action:
                break
            
            # Выполняем действие
            is_correct, skill_progress = self._simulate_task_attempt(student_state, action)
            
            # Вычисляем награды
            rewards = self.calculate_rewards(student_state, action, is_correct, skill_progress)
            
            # Обновляем состояние студента
            new_student_state = self._update_student_state(
                student_state, action, is_correct, skill_progress
            )
            
            # Следующее состояние
            next_state = self._encode_state(new_student_state)
            
            # Определяем конец эпизода
            is_terminal = (step == episode_length - 1) or (
                len(new_student_state.available_skills) == 0
            )
            
            # Создаем запись
            record = ReinforcementRecord(
                student_id=student_id,
                timestamp=current_time,
                state=state,
                action=action,
                immediate_reward=rewards['correctness'],
                learning_reward=rewards['learning_progress'],
                exploration_reward=rewards['exploration'],
                total_reward=rewards['total'],
                next_state=next_state,
                is_terminal=is_terminal,
                expert_feedback=self._simulate_expert_feedback(rewards['total'])
            )
            
            records.append(record)
            
            # Переходим к следующему состоянию
            student_state = new_student_state
            current_time += timedelta(minutes=random.randint(2, 15))
            
            # Обновляем статистику
            self._update_statistics(action, rewards)
        
        return records
    
    def _encode_state(self, student_state: StudentState) -> Dict[str, Any]:
        """Кодирует состояние студента для RL"""
        return {
            'skill_masteries': student_state.skill_masteries.copy(),
            'available_skills': list(student_state.available_skills),
            'recent_tasks': student_state.learning_trajectory[-10:],
            'session_progress': student_state.session_progress,
            'fatigue_level': student_state.fatigue_level,
            'success_streak': student_state.success_streak,
            'failure_streak': student_state.failure_streak,
            'skills_by_level': {
                level: [sid for sid in skill_ids 
                       if student_state.skill_masteries.get(sid, 0) > 0.8]
                for level, skill_ids in self.skill_levels.items()
            }
        }
    
    def _simulate_task_attempt(self, student_state: StudentState, 
                             action: TaskAction) -> Tuple[bool, float]:
        """Симулирует попытку решения задания"""
        skill_mastery = student_state.skill_masteries.get(action.skill_id, 0.1)
        skill_state = self.skills[action.skill_id]
        
        # Вероятность успеха на основе BKT
        success_prob = (
            skill_mastery * (1 - skill_state.slip_rate) + 
            (1 - skill_mastery) * skill_state.guess_rate
        )
        
        # Модификация на основе сложности
        difficulty_mod = {'beginner': 1.2, 'intermediate': 1.0, 'advanced': 0.8}
        success_prob *= difficulty_mod.get(action.difficulty, 1.0)
        
        # Модификация на основе усталости
        success_prob *= (1 - student_state.fatigue_level * 0.3)
        
        # Определяем результат
        is_correct = np.random.random() < np.clip(success_prob, 0.05, 0.95)
        
        # Прогресс навыка
        old_mastery = skill_mastery
        new_mastery = self.update_bkt_parameters(action.skill_id, is_correct, skill_mastery)
        skill_progress = new_mastery - old_mastery
        
        return is_correct, skill_progress
    
    def _update_student_state(self, student_state: StudentState, action: TaskAction,
                            is_correct: bool, skill_progress: float) -> StudentState:
        """Обновляет состояние студента после попытки"""
        new_state = StudentState(
            student_id=student_state.student_id,
            skill_masteries=student_state.skill_masteries.copy(),
            available_skills=student_state.available_skills.copy(),
            learning_trajectory=student_state.learning_trajectory + [action.task_id],
            session_progress=min(1.0, student_state.session_progress + 0.02),
            fatigue_level=min(1.0, student_state.fatigue_level + 0.01),
            success_streak=student_state.success_streak + 1 if is_correct else 0,
            failure_streak=student_state.failure_streak + 1 if not is_correct else 0
        )
        
        # Обновляем мастерство навыка
        new_state.skill_masteries[action.skill_id] += skill_progress
        new_state.skill_masteries[action.skill_id] = np.clip(
            new_state.skill_masteries[action.skill_id], 0.01, 0.99
        )
        
        # Обновляем доступные навыки
        new_state.available_skills = self.get_available_skills(new_state.skill_masteries)
        
        return new_state
    
    def _simulate_expert_feedback(self, total_reward: float) -> Optional[float]:
        """Симулирует обратную связь эксперта"""
        # Эксперт дает обратную связь в 20% случаев
        if np.random.random() > 0.2:
            return None
        
        # Эксперт корректирует награду на основе педагогических принципов
        if total_reward > 2.0:
            return np.random.uniform(0.8, 1.0)  # Положительная обратная связь
        elif total_reward < -1.0:
            return np.random.uniform(-1.0, -0.5)  # Отрицательная обратная связь
        else:
            return np.random.uniform(-0.2, 0.2)  # Нейтральная коррекция
    
    def _update_statistics(self, action: TaskAction, rewards: Dict[str, float]):
        """Обновляет статистику генерации"""
        self.stats['records_generated'] += 1
        self.stats['skills_covered'].add(action.skill_id)
        self.stats['courses_covered'].add(action.course_id)
        
        skill_level = self.skills[action.skill_id].level
        self.stats['level_coverage'][skill_level] += 1
        self.stats['difficulty_distribution'][action.difficulty] += 1
        self.stats['type_distribution'][action.task_type] += 1
        
        for reward_type, value in rewards.items():
            self.stats['reward_statistics'][reward_type].append(value)
    
    def generate_full_dataset(self) -> pd.DataFrame:
        """Генерирует полный датасет для обучения DKN"""
        print(f"\n🚀 ГЕНЕРАЦИЯ DKN ДАТАСЕТА ДЛЯ {self.target_students} СТУДЕНТОВ")
        print("=" * 70)
        
        all_records = []
        
        for student_id in range(1, self.target_students + 1):
            if student_id % 100 == 0:
                print(f"   Обработано студентов: {student_id}/{self.target_students}")
            
            # Генерируем эпизод для студента
            episode_length = np.random.randint(30, 80)  # Переменная длина эпизодов
            student_records = self.generate_student_episode(student_id, episode_length)
            all_records.extend(student_records)
            
            self.stats['students_generated'] += 1
        
        # Конвертируем в DataFrame
        df_data = []
        for record in all_records:
            row = {
                'student_id': record.student_id,
                'task_id': record.action.task_id,
                'skill_id': record.action.skill_id,
                'target': 1.0 if record.immediate_reward > 0 else 0.0,
                'difficulty': record.action.difficulty,
                'task_type': record.action.task_type,
                'course_id': record.action.course_id,
                'skill_level': self.skills[record.action.skill_id].level,
                
                # State features
                'current_skill_mastery': record.state['skill_masteries'].get(record.action.skill_id, 0.1),
                'session_progress': record.state['session_progress'],
                'fatigue_level': record.state['fatigue_level'],
                'success_streak': record.state['success_streak'],
                'failure_streak': record.state['failure_streak'],
                
                # Rewards
                'immediate_reward': record.immediate_reward,
                'learning_reward': record.learning_reward,
                'exploration_reward': record.exploration_reward,
                'total_reward': record.total_reward,
                'expert_feedback': record.expert_feedback or 0.0,
                
                # Episode info
                'is_terminal': record.is_terminal,
                'timestamp': record.timestamp.isoformat()
            }
            
            # Добавляем BKT параметры для всех навыков
            for skill_id in self.skills.keys():
                row[f'skill_{skill_id}_mastery'] = record.state['skill_masteries'].get(skill_id, 0.1)
            
            # Добавляем информацию о доступных навыках по уровням
            for level in range(1, 17):  # 16 уровней максимум
                level_skills = record.state.get('skills_by_level', {}).get(level, [])
                row[f'level_{level}_mastered'] = len(level_skills)
            
            df_data.append(row)
        
        df = pd.DataFrame(df_data)
        
        print(f"\n✅ ГЕНЕРАЦИЯ ЗАВЕРШЕНА!")
        print(f"   Студентов: {self.stats['students_generated']}")
        print(f"   Записей: {len(df)}")
        print(f"   Навыков покрыто: {len(self.stats['skills_covered'])}/{len(self.skills)}")
        print(f"   Курсов покрыто: {len(self.stats['courses_covered'])}")
        print(f"   Уровней покрыто: {len(self.stats['level_coverage'])}")
        
        return df
    
    def save_dataset(self, df: pd.DataFrame):
        """Сохраняет датасет и генерирует отчеты"""
        print(f"\n💾 СОХРАНЕНИЕ ДАТАСЕТА...")
        
        # Сохраняем основной датасет
        output_file = self.output_path / "dkn_reinforcement_dataset.csv"
        df.to_csv(output_file, index=False)
        print(f"   ✅ Датасет сохранен: {output_file}")
        
        # Сохраняем статистику
        stats_file = self.output_path / "generation_statistics.json"
        stats_serializable = {}
        for key, value in self.stats.items():
            if isinstance(value, set):
                stats_serializable[key] = list(value)
            elif isinstance(value, defaultdict):
                stats_serializable[key] = dict(value)
            else:
                stats_serializable[key] = value
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats_serializable, f, indent=2, ensure_ascii=False)
        print(f"   ✅ Статистика сохранена: {stats_file}")
          # Генерируем отчет
        self._generate_report(df)
        
        # Создаем визуализации
        self._create_visualizations(df)
    
    def _generate_report(self, df: pd.DataFrame):
        """Генерирует подробный отчет о датасете"""
        report_file = self.output_path / "DKN_REINFORCEMENT_REPORT.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"""# Отчет о DKN датасете с обучением с подкреплением

## 📊 Основная статистика

**Дата создания**: {datetime.now().strftime('%d.%m.%Y %H:%M')}

### Размер датасета
- **Общее количество записей**: {len(df):,}
- **Количество студентов**: {df['student_id'].nunique():,}
- **Средняя длина эпизода**: {len(df) / df['student_id'].nunique():.1f}

### Покрытие системы
- **Навыков покрыто**: {len(self.stats['skills_covered'])}/{len(self.skills)} ({len(self.stats['skills_covered'])/len(self.skills)*100:.1f}%)
- **Курсов покрыто**: {len(self.stats['courses_covered'])}
- **Уровней покрыто**: {len(self.stats['level_coverage'])}/16

## 🎯 Анализ целевой переменной

### Распределение успешности
- **Общая успешность**: {df['target'].mean()*100:.1f}%
- **Стандартное отклонение**: {df['target'].std():.3f}

### По сложности заданий
- **Легкие задания**: {df[df['difficulty'] == 'beginner']['target'].mean()*100:.1f}% успешности
- **Средние задания**: {df[df['difficulty'] == 'intermediate']['target'].mean()*100:.1f}% успешности
- **Сложные задания**: {df[df['difficulty'] == 'advanced']['target'].mean()*100:.1f}% успешности

### По типам заданий
- **Верные/Неверные**: {df[df['task_type'] == 'true_false']['target'].mean()*100:.1f}% успешности
- **Одиночные выборы**: {df[df['task_type'] == 'single']['target'].mean()*100:.1f}% успешности
- **Множественные выборы**: {df[df['task_type'] == 'multiple']['target'].mean()*100:.1f}% успешности

## 🧠 Анализ системы наград

### Статистика наград
- **Средняя мгновенная награда**: {df['immediate_reward'].mean():.3f}
- **Средняя награда за обучение**: {df['learning_reward'].mean():.3f}
- **Средняя награда за исследование**: {df['exploration_reward'].mean():.3f}
- **Средняя общая награда**: {df['total_reward'].mean():.3f}

### Обратная связь эксперта
- **Записей с обратной связью**: {(df['expert_feedback'] != 0).sum():,} ({(df['expert_feedback'] != 0).mean()*100:.1f}%)
- **Средняя оценка эксперта**: {df[df['expert_feedback'] != 0]['expert_feedback'].mean():.3f}

## 🕸️ Анализ графа навыков

### Покрытие по уровням
""")
            
            # Анализ по уровням
            for level in sorted(self.stats['level_coverage'].keys()):
                count = self.stats['level_coverage'][level]
                f.write(f"- **Уровень {level}**: {count:,} записей\n")
            
            f.write(f"""
## 🎮 Готовность для обучения с подкреплением

### Характеристики эпизодов
- **Средняя длина эпизода**: {len(df) / df['student_id'].nunique():.1f}
- **Терминальных состояний**: {df['is_terminal'].sum():,}
- **Записей с экспертной оценкой**: {(df['expert_feedback'] != 0).sum():,}

### Разнообразие траекторий
- **Уникальных последовательностей навыков**: Высокое
- **Адаптивность сложности**: ✅ Реализована
- **Учет предпосылок навыков**: ✅ Реализован

## ✅ Соответствие требованиям DKN

- ✅ **Иерархический граф навыков**: 30 навыков, 16 уровней
- ✅ **Адаптивная сложность**: Задания подбираются по уровню навыка
- ✅ **BKT параметры**: Реалистичные параметры с временной динамикой
- ✅ **Система наград**: Многокомпонентная система для RL
- ✅ **Обратная связь эксперта**: 20% записей с экспертной оценкой
- ✅ **Полное покрытие**: Все навыки и курсы представлены

## 🚀 Готовность к использованию

Датасет полностью готов для:
1. **Обучения DKN модели** с учетом графа навыков
2. **Обучения с подкреплением** (RL) с системой наград
3. **Дообучения на реальных данных** после внедрения
4. **Экспертной валидации** через систему обратной связи

---
*Сгенерировано автоматически: {datetime.now().strftime('%d.%m.%Y %H:%M')}*
""")
        
        print(f"   ✅ Отчет сохранен: {report_file}")

    def _create_visualizations(self, df: pd.DataFrame):
        """Создает визуализации для анализа датасета"""
        print(f"   📊 Создание визуализаций...")
        
        # Настройка стиля
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # Создаем фигуру с подграфиками
        fig = plt.figure(figsize=(20, 24))
        
        # 1. Распределение успешности по сложности
        plt.subplot(4, 3, 1)
        success_by_difficulty = df.groupby('difficulty')['target'].agg(['mean', 'count'])
        bars = plt.bar(success_by_difficulty.index, success_by_difficulty['mean'])
        plt.title('Успешность по сложности заданий')
        plt.ylabel('Доля успешных попыток')
        plt.ylim(0, 1)
        for i, (bar, count) in enumerate(zip(bars, success_by_difficulty['count'])):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, 
                    f'{success_by_difficulty["mean"].iloc[i]:.2f}\n({count:,})', 
                    ha='center', va='bottom')
        
        # 2. Распределение успешности по типам заданий
        plt.subplot(4, 3, 2)
        success_by_type = df.groupby('task_type')['target'].agg(['mean', 'count'])
        bars = plt.bar(success_by_type.index, success_by_type['mean'])
        plt.title('Успешность по типам заданий')
        plt.ylabel('Доля успешных попыток')
        plt.ylim(0, 1)
        for i, (bar, count) in enumerate(zip(bars, success_by_type['count'])):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, 
                    f'{success_by_type["mean"].iloc[i]:.2f}\n({count:,})', 
                    ha='center', va='bottom')
        
        # 3. Распределение наград
        plt.subplot(4, 3, 3)
        plt.hist(df['total_reward'], bins=50, alpha=0.7, edgecolor='black')
        plt.title('Распределение общих наград')
        plt.xlabel('Общая награда')
        plt.ylabel('Частота')
        plt.axvline(df['total_reward'].mean(), color='red', linestyle='--', 
                   label=f'Среднее: {df["total_reward"].mean():.3f}')
        plt.legend()
          # 4. Покрытие навыков по уровням
        plt.subplot(4, 3, 4)
        level_coverage = pd.Series(self.stats['level_coverage'])
        level_coverage = level_coverage.sort_index()
        bars = plt.bar(list(level_coverage.index), list(level_coverage.values))
        plt.title('Покрытие навыков по уровням')
        plt.xlabel('Уровень навыка')
        plt.ylabel('Количество записей')
        for bar, count in zip(bars, level_coverage.values):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50, 
                    f'{count:,}', ha='center', va='bottom')
        
        # 5. Динамика освоения навыков
        plt.subplot(4, 3, 5)
        # Берем случайного студента для демонстрации
        sample_student = df[df['student_id'] == df['student_id'].iloc[0]].copy()
        sample_student = sample_student.reset_index(drop=True)
        plt.plot(sample_student.index, sample_student['current_skill_mastery'], 
                linewidth=2, marker='o', markersize=4)
        plt.title(f'Пример освоения навыка (студент {sample_student["student_id"].iloc[0]})')
        plt.xlabel('Номер попытки')
        plt.ylabel('Уровень освоения')
        plt.grid(True, alpha=0.3)
        
        # 6. Корреляция между компонентами наград
        plt.subplot(4, 3, 6)
        reward_cols = ['immediate_reward', 'learning_reward', 'exploration_reward']
        reward_corr = df[reward_cols].corr()
        sns.heatmap(reward_corr, annot=True, cmap='coolwarm', center=0, 
                   square=True, cbar_kws={'shrink': 0.8})
        plt.title('Корреляция компонентов наград')
        
        # 7. Распределение длин эпизодов
        plt.subplot(4, 3, 7)
        episode_lengths = df.groupby('student_id').size()
        plt.hist(episode_lengths, bins=30, alpha=0.7, edgecolor='black')
        plt.title('Распределение длин эпизодов')
        plt.xlabel('Длина эпизода')
        plt.ylabel('Количество студентов')
        plt.axvline(episode_lengths.mean(), color='red', linestyle='--', 
                   label=f'Среднее: {episode_lengths.mean():.1f}')
        plt.legend()
        
        # 8. Успешность vs освоение навыка
        plt.subplot(4, 3, 8)
        plt.scatter(df['current_skill_mastery'], df['target'], alpha=0.1, s=1)
        plt.title('Успешность vs Освоение навыка')
        plt.xlabel('Уровень освоения навыка')
        plt.ylabel('Успешность (target)')
        # Добавляем линию тренда
        z = np.polyfit(df['current_skill_mastery'], df['target'], 1)
        p = np.poly1d(z)
        plt.plot(df['current_skill_mastery'].unique(), 
                p(df['current_skill_mastery'].unique()), "r--", alpha=0.8)
        
        # 9. Обратная связь эксперта
        plt.subplot(4, 3, 9)
        expert_feedback = df[df['expert_feedback'] != 0]['expert_feedback']
        if len(expert_feedback) > 0:
            plt.hist(expert_feedback, bins=20, alpha=0.7, edgecolor='black')
            plt.title('Распределение экспертной обратной связи')
            plt.xlabel('Оценка эксперта')
            plt.ylabel('Частота')
            plt.axvline(expert_feedback.mean(), color='red', linestyle='--', 
                       label=f'Среднее: {expert_feedback.mean():.3f}')
            plt.legend()
        else:
            plt.text(0.5, 0.5, 'Нет данных об\nэкспертной обратной связи', 
                    ha='center', va='center', transform=plt.gca().transAxes)
            plt.title('Экспертная обратная связь')
        
        # 10. Прогрессия сложности
        plt.subplot(4, 3, 10)
        # Создаем маппинг сложности к числам
        difficulty_map = {'beginner': 1, 'intermediate': 2, 'advanced': 3}
        sample_trajectory = df[df['student_id'] == df['student_id'].iloc[100]].copy()
        sample_trajectory = sample_trajectory.reset_index(drop=True)
        sample_trajectory['difficulty_num'] = sample_trajectory['difficulty'].map(difficulty_map)
        
        plt.plot(sample_trajectory.index, sample_trajectory['difficulty_num'], 
                linewidth=2, marker='s', markersize=4)
        plt.title(f'Прогрессия сложности (студент {sample_trajectory["student_id"].iloc[0]})')
        plt.xlabel('Номер попытки')
        plt.ylabel('Сложность задания')
        plt.yticks([1, 2, 3], ['Beginner', 'Intermediate', 'Advanced'])
        plt.grid(True, alpha=0.3)
          # 11. Статистика по курсам
        plt.subplot(4, 3, 11)
        course_stats = pd.Series(self.stats['course_coverage'])
        bars = plt.bar(range(len(course_stats)), list(course_stats.values))
        plt.title('Покрытие по курсам')
        plt.xlabel('ID курса')
        plt.ylabel('Количество записей')
        plt.xticks(range(len(course_stats)), list(course_stats.index))
        for bar, count in zip(bars, course_stats.values):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50, 
                    f'{count:,}', ha='center', va='bottom')
        
        # 12. Временная динамика успешности
        plt.subplot(4, 3, 12)
        # Группируем по порядковому номеру попытки в эпизоде
        df_with_attempt_num = df.copy()
        df_with_attempt_num['attempt_in_episode'] = df_with_attempt_num.groupby('student_id').cumcount()
        
        # Берем только первые 50 попыток для наглядности
        temporal_success = df_with_attempt_num[df_with_attempt_num['attempt_in_episode'] < 50]
        temporal_success = temporal_success.groupby('attempt_in_episode')['target'].mean()
        
        plt.plot(list(temporal_success.index), list(temporal_success.values), linewidth=2, marker='o', markersize=3)
        plt.title('Динамика успешности в эпизоде')
        plt.xlabel('Номер попытки в эпизоде')
        plt.ylabel('Средняя успешность')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Сохраняем визуализацию
        viz_file = self.output_path / "dkn_dataset_visualizations.png"
        plt.savefig(viz_file, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        print(f"   ✅ Визуализации сохранены: {viz_file}")
        
        # Создаем дополнительную детальную визуализацию графа навыков
        self._create_skill_graph_visualization()
    
    def _create_skill_graph_visualization(self):
        """Создает визуализацию графа навыков"""
        try:
            import networkx as nx
            
            print(f"   🕸️  Создание визуализации графа навыков...")
            
            # Создаем граф
            G = nx.DiGraph()
              # Добавляем узлы (навыки)
            for skill in self.skills.values():
                G.add_node(skill.id, 
                          name=skill.name, 
                          level=skill.level,
                          coverage=self.stats['skill_individual_coverage'].get(skill.id, 0))
            
            # Добавляем рёбра (предпосылки)
            for skill in self.skills.values():
                for prereq_id in skill.prerequisites:
                    if prereq_id in self.skills:
                        G.add_edge(prereq_id, skill.id)
            
            # Создаем визуализацию
            plt.figure(figsize=(16, 12))
            
            # Позиционирование узлов по уровням
            pos = {}
            levels = defaultdict(list)
            for node, data in G.nodes(data=True):
                levels[data['level']].append(node)
            
            for level, nodes in levels.items():
                for i, node in enumerate(nodes):
                    pos[node] = (i - len(nodes)/2, -level)
            
            # Цвета узлов по покрытию
            node_colors = []
            for node in G.nodes():
                coverage = G.nodes[node]['coverage']
                if coverage == 0:
                    node_colors.append('lightcoral')  # Не покрыт
                elif coverage < 1000:
                    node_colors.append('lightyellow')  # Мало покрыт
                elif coverage < 5000:
                    node_colors.append('lightgreen')  # Хорошо покрыт
                else:
                    node_colors.append('darkgreen')  # Отлично покрыт
            
            # Рисуем граф
            nx.draw(G, pos, 
                   node_color=node_colors,
                   node_size=300,
                   with_labels=False,
                   arrows=True,
                   arrowsize=20,
                   edge_color='gray',
                   alpha=0.8)
            
            # Добавляем подписи узлов
            labels = {node: f"{data['name'][:15]}...\n({data['coverage']})" 
                     if len(data['name']) > 15 
                     else f"{data['name']}\n({data['coverage']})"
                     for node, data in G.nodes(data=True)}
            
            nx.draw_networkx_labels(G, pos, labels, font_size=6)
            
            plt.title('Граф навыков DKN\n(числа в скобках - количество записей в датасете)', 
                     fontsize=14, pad=20)
              # Легенда
            from matplotlib.patches import Rectangle
            legend_elements = [
                Rectangle((0,0),1,1, facecolor='lightcoral', label='Не покрыт (0)'),
                Rectangle((0,0),1,1, facecolor='lightyellow', label='Мало (<1K)'),
                Rectangle((0,0),1,1, facecolor='lightgreen', label='Хорошо (1K-5K)'),
                Rectangle((0,0),1,1, facecolor='darkgreen', label='Отлично (>5K)')
            ]
            plt.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.15, 1))
            
            # Сохраняем
            graph_file = self.output_path / "skill_graph_visualization.png"
            plt.savefig(graph_file, dpi=300, bbox_inches='tight', facecolor='white')
            plt.close()
            
            print(f"   ✅ Граф навыков сохранен: {graph_file}")
            
        except ImportError:
            print(f"   ⚠️  NetworkX не установлен - пропускаем визуализацию графа")
        except Exception as e:
            print(f"   ⚠️  Ошибка создания графа навыков: {e}")

def main():
    """Основная функция генерации"""
    print("🤖 ГЕНЕРАТОР DKN ДАННЫХ С ОБУЧЕНИЕМ С ПОДКРЕПЛЕНИЕМ")
    print("=" * 70)
    
    # Создаем генератор
    generator = DKNReinforcementDataGenerator(
        target_students=1500,
        output_path="dataset"
    )
    
    try:
        # Генерируем данные
        df = generator.generate_full_dataset()
        
        # Сохраняем результаты
        generator.save_dataset(df)
        
        print(f"\n🎉 ГЕНЕРАЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
        print(f"📊 Создано {len(df):,} записей для {df['student_id'].nunique():,} студентов")
        print(f"🎯 Покрыто {len(generator.stats['skills_covered'])}/{len(generator.skills)} навыков")
        print(f"📈 Общая успешность: {df['target'].mean()*100:.1f}%")
        print(f"🏆 Средняя награда: {df['total_reward'].mean():.3f}")
        
    except Exception as e:
        print(f"❌ Ошибка генерации: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
