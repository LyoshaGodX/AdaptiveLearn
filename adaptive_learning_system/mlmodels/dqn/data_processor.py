"""
Обработчик данных для DQN модели

Этот модуль подготавливает данные из Django моделей в формат, 
подходящий для обучения DQN модели с учётом:
- Графа навыков и prerequisite ограничений
- BKT параметров для всех навыков студента
- Истории попыток и успехов
- Параметров заданий (тип, сложность, навык)
"""

import torch
from torch.utils.data import Dataset, DataLoader
import numpy as np
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime, timedelta
import pandas as pd
import json

# Django imports
from django.contrib.auth.models import User
from skills.models import Skill
from methodist.models import Task
from mlmodels.models import TaskAttempt, StudentSkillMastery
from student.models import StudentProfile


class DQNEnvironment:
    """Среда для DQN агента с учётом графа навыков"""
    
    def __init__(self, student_id: int):
        self.student_id = student_id
        self.student_profile = self._get_student_profile()
        self.skills_graph = self._build_skills_graph()
        self.task_to_skills = self._build_task_skills_mapping()
        
        # Создаем маппинг между ID задач и индексами действий
        self.task_ids = sorted(list(self.task_to_skills.keys()))
        self.task_id_to_action = {task_id: idx for idx, task_id in enumerate(self.task_ids)}
        self.action_to_task_id = {idx: task_id for idx, task_id in enumerate(self.task_ids)}
        
        self.current_session_length = 0
        self.max_session_length = 20
        
    def _get_student_profile(self):
        """Получает профиль студента"""
        user = User.objects.get(id=self.student_id)
        profile, created = StudentProfile.objects.get_or_create(user=user)
        return profile
        
    def _build_skills_graph(self) -> Dict[int, Set[int]]:
        """Строит граф навыков с prerequisite зависимостями"""
        skills_graph = {}
        
        for skill in Skill.objects.all():
            prerequisites = set()
            # Получаем prerequisite навыки
            for prereq in skill.prerequisites.all():
                prerequisites.add(prereq.id)
            skills_graph[skill.id] = prerequisites
            
        return skills_graph
    
    def _build_task_skills_mapping(self) -> Dict[int, Set[int]]:
        """Строит маппинг заданий на навыки"""
        task_skills = {}
        
        for task in Task.objects.all():
            skills = set()
            for skill in task.skills.all():
                skills.add(skill.id)
            task_skills[task.id] = skills
            
        return task_skills
    
    def get_available_actions(self, bkt_params: torch.Tensor, skill_to_id: Dict[int, int]) -> List[int]:
        """
        Возвращает список доступных заданий с учётом prerequisite и уровня освоения навыков
        
        Args:
            bkt_params: BKT параметры [num_skills, 1] - вероятность знания для каждого навыка
            skill_to_id: маппинг skill_db_id -> skill_idx
            
        Returns:
            List[int]: список индексов доступных заданий
        """
        available_tasks = []
        
        # Создаем обратный маппинг для быстрого поиска
        id_to_skill = {idx: skill_id for skill_id, idx in skill_to_id.items()}
        
        # Получаем статистику попыток студента для фильтрации
        task_attempts_stats = self._get_task_attempts_stats()
        
        for task_id, required_skills in self.task_to_skills.items():
            if not required_skills:
                continue
                
            task_available = True
            all_skills_mastered = True
            
            # Проверяем, не решал ли студент это задание уже много раз правильно
            if self._is_task_overlearned(task_id, task_attempts_stats):
                task_available = False
                continue
            
            # Проверяем каждый навык, который развивает это задание
            for skill_id in required_skills:
                skill_idx = skill_to_id.get(skill_id)
                if skill_idx is None:
                    continue
                    
                # Получаем уровень освоения навыка
                skill_mastery = bkt_params[skill_idx, 0].item()
                
                # Проверяем, что все prerequisite навыки освоены (рекурсивно)
                if not self._check_prerequisites_mastered(skill_id, bkt_params, skill_to_id, mastery_threshold=0.7):
                    task_available = False
                    break
                
                # Проверяем, что хотя бы один навык не полностью освоен
                # Повышаем порог для исключения полностью освоенных навыков
                if skill_mastery < 0.85:  # Если навык еще НЕ освоен
                    all_skills_mastered = False
                    
            # Исключаем задания, если ВСЕ развиваемые навыки уже освоены
            if all_skills_mastered:
                task_available = False
                    
            if task_available:
                # Добавляем индекс действия
                action_index = self.task_id_to_action[task_id]
                available_tasks.append(action_index)
                
        return available_tasks
    
    def _check_prerequisites_mastered(self, skill_id: int, bkt_params: torch.Tensor, 
                                    skill_to_id: Dict[int, int], mastery_threshold: float = 0.85) -> bool:
        """
        Рекурсивно проверяет, что все prerequisite навыки освоены
        
        Args:
            skill_id: ID проверяемого навыка
            bkt_params: BKT параметры
            skill_to_id: маппинг skill_db_id -> skill_idx
            mastery_threshold: порог освоения
            
        Returns:
            bool: True если все prerequisite освоены
        """
        # Получаем prerequisite для данного навыка
        prerequisites = self.skills_graph.get(skill_id, set())
        
        if not prerequisites:
            return True  # Нет prerequisite - навык доступен
        
        # Проверяем каждый prerequisite
        for prereq_id in prerequisites:
            skill_idx = skill_to_id.get(prereq_id)
            if skill_idx is None:
                continue
                
            # Получаем уровень освоения prerequisite навыка
            prereq_mastery = bkt_params[skill_idx, 0].item()
            
            # Если prerequisite не освоен - навык недоступен
            if prereq_mastery < mastery_threshold:
                return False
                
            # Рекурсивно проверяем prerequisite для prerequisite
            if not self._check_prerequisites_mastered(prereq_id, bkt_params, skill_to_id, mastery_threshold):
                return False
        
        return True
    
    def calculate_reward(self, task_id: int, success: bool, 
                        skill_improvements: Dict[int, float],
                        difficulty_match: float,
                        prerequisite_violated: bool = False) -> float:
        """
        Вычисляет награду за рекомендацию задания
        
        Args:
            task_id: ID рекомендованного задания
            success: успешно ли выполнено задание
            skill_improvements: словарь улучшений навыков {skill_id: improvement}
            difficulty_match: соответствие сложности уровню студента (0-1)
            prerequisite_violated: нарушены ли prerequisite ограничения
            
        Returns:
            reward: награда за действие
        """
        # Базовая награда за успех
        base_reward = 1.0 if success else -0.5
        
        # Бонус за улучшение навыков
        total_skill_improvement = sum(skill_improvements.values())
        skill_bonus = total_skill_improvement * 2.0
        
        # Бонус за подходящую сложность
        difficulty_bonus = difficulty_match * 0.5
        
        # Штраф за нарушение prerequisite
        prerequisite_penalty = -2.0 if prerequisite_violated else 0.0
          # Штраф за слишком легкие/сложные задания
        difficulty_penalty = 0.0
        if difficulty_match < 0.3:
            difficulty_penalty = -0.3
            
        total_reward = (base_reward + skill_bonus + difficulty_bonus + 
                       prerequisite_penalty + difficulty_penalty)
        
        return total_reward
    
    def is_done(self) -> bool:
        """Проверяет, завершена ли сессия"""
        return self.current_session_length >= self.max_session_length
    
    def reset(self):
        """Сброс среды для новой сессии"""
        self.current_session_length = 0
    
    def _get_task_attempts_stats(self) -> Dict[int, Dict[str, int]]:
        """
        Получает статистику попыток студента по заданиям
        
        Returns:
            Dict[task_id, {'total': int, 'correct': int, 'recent_correct': int}]
        """
        from mlmodels.models import TaskAttempt
        from datetime import datetime, timedelta
        
        stats = {}
        
        # Получаем все попытки студента за последние 30 дней
        cutoff_date = datetime.now() - timedelta(days=30)
        
        attempts = TaskAttempt.objects.filter(
            student=self.student_profile,
            started_at__gte=cutoff_date
        ).order_by('-started_at')
        
        for attempt in attempts:
            task_id = attempt.task.id
            if task_id not in stats:
                stats[task_id] = {'total': 0, 'correct': 0, 'recent_correct': 0}
            
            stats[task_id]['total'] += 1
            if attempt.is_correct:
                stats[task_id]['correct'] += 1
                
                # Считаем последовательные правильные попытки (последние 5)
                recent_attempts = TaskAttempt.objects.filter(
                    student=self.student_profile,
                    task=attempt.task
                ).order_by('-started_at')[:5]
                
                recent_correct_streak = 0
                for recent_attempt in recent_attempts:
                    if recent_attempt.is_correct:
                        recent_correct_streak += 1
                    else:
                        break
                
                stats[task_id]['recent_correct'] = recent_correct_streak
        
        return stats
    
    def _is_task_overlearned(self, task_id: int, attempts_stats: Dict[int, Dict[str, int]]) -> bool:
        """
        Проверяет, не переизучено ли задание студентом
        
        Args:
            task_id: ID задания
            attempts_stats: статистика попыток
            
        Returns:
            bool: True если задание переизучено
        """
        if task_id not in attempts_stats:
            return False
        
        stats = attempts_stats[task_id]
        
        # Исключаем задания, которые студент решил правильно 3+ раза подряд
        if stats['recent_correct'] >= 3:
            return True
              # Исключаем задания с очень высоким процентом успеха (>90%) и много попыток (>5)
        if stats['total'] >= 5 and (stats['correct'] / stats['total']) > 0.9:
            return True
            
        return False


class DQNDataProcessor:
    """Обработчик данных для DQN с поддержкой графа навыков"""
    def __init__(self, max_history_length: int = 50):
        self.max_history_length = max_history_length
        self.skill_to_id = {}
        self.task_to_id = {}
        self.id_to_skill = {}
        self.id_to_task = {}
        self.task_to_skills = {}  # Добавляем маппинг заданий на навыки
        
        # Маппинги для типов заданий и сложности
        self.difficulty_map = {
            'beginner': 0,
            'intermediate': 1, 
            'advanced': 2
        }
        
        self.type_map = {
            'single_choice': 0,
            'multiple_choice': 1,
            'true_false': 2
        }
        
        self._build_mappings()
    def _build_mappings(self):
        """Создает маппинги между объектами и ID"""
        # Навыки
        skills = list(Skill.objects.all().order_by('id'))
        for i, skill in enumerate(skills):
            self.skill_to_id[skill.id] = i
            self.id_to_skill[i] = skill.id
              
        # Задания
        tasks = list(Task.objects.all().order_by('id'))
        for i, task in enumerate(tasks):
            self.task_to_id[task.id] = i
            self.id_to_task[i] = task.id
            
        # Маппинг заданий на навыки
        for task in Task.objects.all():
            skills = set()
            for skill in task.skills.all():
                skills.add(skill.id)
            self.task_to_skills[task.id] = skills

    def get_student_state(self, student_id: int) -> Dict:
        """
        Получает полное состояние студента для DQN
        
        Args:
            student_id: ID студента
            
        Returns:
            Dict с состоянием студента, включая:
            - bkt_params: BKT параметры для всех навыков
            - history: история попыток
            - mastered_skills: множество освоенных навыков
            - available_actions: доступные задания
        """
        user = User.objects.get(id=student_id)
        student_profile, created = StudentProfile.objects.get_or_create(user=user)
        
        # BKT параметры для всех навыков
        bkt_params = self._get_all_bkt_parameters(student_profile)
          # История попыток студента
        history = self._get_student_history(student_profile)
        
        # Создаём среду для определения доступных действий
        env = DQNEnvironment(student_id)
        available_actions = env.get_available_actions(bkt_params, self.skill_to_id)
        
        # Добавляем информацию о графе навыков
        skills_graph_matrix = self._build_skills_graph_matrix()
        
        return {
            'bkt_params': bkt_params,
            'history': history,
            'available_actions': available_actions,
            'skills_graph': skills_graph_matrix,
            'environment': env
        }
    
    def _get_all_bkt_parameters(self, student_profile: StudentProfile) -> torch.Tensor:
        """
        Получает BKT параметры для всех навыков из базы данных
        
        Returns:
            torch.Tensor: [num_skills, 1] - только вероятность знания (mastery probability)
        """
        num_skills = len(self.skill_to_id)
        bkt_params = torch.zeros(num_skills, 1)  # Только вероятность знания
          # Получаем все записи StudentSkillMastery для студента
        masteries = StudentSkillMastery.objects.filter(student=student_profile)
        
        # Создаем словарь для быстрого поиска
        mastery_dict = {mastery.skill_id: mastery for mastery in masteries}
        
        for skill_db_id, skill_idx in self.skill_to_id.items():
            try:
                # Ищем запись для данного навыка
                mastery = mastery_dict.get(skill_db_id)
                
                if mastery:
                    # Извлекаем только вероятность знания
                    bkt_params[skill_idx] = torch.tensor([
                        mastery.current_mastery_prob  # P(know) - текущая вероятность знания
                    ])
                else:
                    # Значение по умолчанию если записи нет
                    bkt_params[skill_idx] = torch.tensor([0.1])
                    
            except Exception:
                # Значение по умолчанию при ошибке
                bkt_params[skill_idx] = torch.tensor([0.1])
        
        return bkt_params
    
    def _get_student_history(self, student_profile: StudentProfile) -> torch.Tensor:
        """
        Получает историю попыток студента
        
        Returns:
            torch.Tensor: [seq_len, 7] - история попыток
        """
        # Получаем последние попытки
        attempts = TaskAttempt.objects.filter(
            student=student_profile
        ).order_by('-started_at')[:self.max_history_length]
        
        history_data = []
        processed_count = 0
        error_count = 0
        
        for attempt in reversed(attempts):  # Реверсируем для хронологического порядка
            try:
                task = attempt.task
                if not task:
                    error_count += 1
                    continue
                
                # Подготавливаем данные попытки
                task_id_encoded = self.task_to_id.get(task.id, 0)
                success = 1.0 if attempt.is_correct else 0.0
                
                # Проверяем и маппим сложность
                difficulty = 1  # По умолчанию средняя сложность
                if hasattr(task, 'difficulty') and task.difficulty:
                    difficulty = self.difficulty_map.get(task.difficulty, 1)
                
                # Проверяем и маппим тип задания
                task_type = 0  # По умолчанию single_choice
                if hasattr(task, 'task_type') and task.task_type:
                    task_type = self.type_map.get(task.task_type, 0)
                
                # Создаем среду для получения навыков задания
                env = DQNEnvironment(student_profile.user.id)
                task_skills = env.task_to_skills.get(task.id, set())
                primary_skill_id = min(task_skills) if task_skills else 0
                  # Получаем уровень освоения основного навыка
                skill_level = 0.1  # Значение по умолчанию
                if primary_skill_id:
                    try:
                        skill_mastery = StudentSkillMastery.objects.get(
                            student=student_profile, 
                            skill_id=primary_skill_id
                        )
                        skill_level = skill_mastery.current_mastery_prob
                    except StudentSkillMastery.DoesNotExist:
                        skill_level = 0.1
                  # Дополнительные метрики
                time_spent = min(getattr(attempt, 'time_spent', 60) / 300.0, 1.0)
                
                # Подсчёт streak
                streak = self._calculate_streak(student_profile, attempt.started_at)
                
                history_entry = [
                    task_id_encoded, success, difficulty, task_type,
                    skill_level, time_spent, streak
                ]
                
                history_data.append(history_entry)
                processed_count += 1
                
            except Exception as e:
                error_count += 1
                continue
        
        if not history_data:
            return torch.zeros(1, 7)
        
        return torch.tensor(history_data, dtype=torch.float32)
    def _calculate_streak(self, student_profile: StudentProfile, current_time: datetime) -> float:
        """Вычисляет серию последних успехов"""
        recent_attempts = TaskAttempt.objects.filter(
            student=student_profile,
            started_at__lte=current_time  # Используем started_at вместо timestamp
        ).order_by('-started_at')[:10]
        
        streak = 0
        for attempt in recent_attempts:
            if attempt.is_correct:
                streak += 1
            else:
                break
                
        return min(streak / 10.0, 1.0)  # Нормализуем
    def _get_mastered_skills(self, student_profile: StudentProfile, 
                           bkt_params: torch.Tensor, mastery_threshold: float = 0.7) -> Set[int]:
        """
        Определяет освоенные навыки на основе BKT параметров
        
        Args:
            student_profile: профиль студента
            bkt_params: BKT параметры [num_skills, 1]
            mastery_threshold: порог освоения навыка
            
        Returns:
            Set[int]: множество ID освоенных навыков
        """
        mastered_skills = set()
        
        for skill_idx, (skill_db_id, _) in enumerate(self.id_to_skill.items()):
            know_prob = bkt_params[skill_idx, 0].item()  # Вероятность знания навыка
            
            if know_prob >= mastery_threshold:
                mastered_skills.add(skill_db_id)
                
        return mastered_skills
    
    def get_task_data(self, task_id: int) -> Dict:
        """
        Получает данные о задании
          Args:
            task_id: ID задания
            
        Returns:
            Dict с данными задания
        """
        try:
            task = Task.objects.get(id=task_id)
            
            return {
                'task_id': task_id,
                'difficulty': self.difficulty_map.get(task.difficulty, 1),
                'task_type': self.type_map.get(task.task_type, 0),
                'skills': [skill.id for skill in task.skills.all()],
                'estimated_time': getattr(task, 'estimated_time', 300),  # Секунды
            }
            
        except Task.DoesNotExist:
            return {
                'task_id': task_id,
                'difficulty': 1,
                'task_type': 0,
                'skills': [],
                'estimated_time': 300
            }
    
    def prepare_training_batch(self, experiences: List[Dict]) -> Dict[str, torch.Tensor]:
        """
        Подготавливает батч данных для обучения DQN
        
        Args:
            experiences: список опыта обучения
            
        Returns:
            Dict с тензорами для обучения
        """
        batch_states = []
        batch_actions = []
        batch_rewards = []
        batch_next_states = []
        batch_dones = []
        
        for exp in experiences:
            batch_states.append(exp['state'])
            batch_actions.append(exp['action'])
            batch_rewards.append(exp['reward'])
            batch_next_states.append(exp['next_state'])
            batch_dones.append(exp['done'])
        
        return {
            'states': torch.stack(batch_states),
            'actions': torch.tensor(batch_actions, dtype=torch.long),
            'rewards': torch.tensor(batch_rewards, dtype=torch.float),
            'next_states': torch.stack(batch_next_states),
            'dones': torch.tensor(batch_dones, dtype=torch.bool)
        }
    
    def get_num_skills(self) -> int:
        """Возвращает количество навыков"""
        return len(self.skill_to_id)
    
    def get_num_tasks(self) -> int:
        """Возвращает количество заданий"""
        return len(self.task_to_id)
    
    def _build_skills_graph_matrix(self) -> torch.Tensor:
        """
        Строит матрицу смежности графа навыков для Q-функции
        
        Returns:
            torch.Tensor: [num_skills, num_skills] - матрица prerequisite связей
        """
        num_skills = self.get_num_skills()
        graph_matrix = torch.zeros(num_skills, num_skills)
        
        # Получаем все навыки и создаем маппинг ID -> индекс
        skills = list(Skill.objects.all().values_list('id', flat=True))
        skill_to_idx = {skill_id: idx for idx, skill_id in enumerate(sorted(skills))}
        
        # Заполняем матрицу prerequisite связей
        for skill in Skill.objects.all():
            skill_idx = skill_to_idx[skill.id]
            for prereq in skill.prerequisites.all():
                prereq_idx = skill_to_idx[prereq.id]
                graph_matrix[skill_idx, prereq_idx] = 1.0  # prereq -> skill
                
        return graph_matrix
    
    def get_recommended_actions(self, student_id: int, top_k: int = 5) -> List[Tuple[int, float]]:
        """
        Получает рекомендованные задания с учетом уровня освоения навыков
        
        Args:
            student_id: ID студента
            top_k: количество рекомендаций
            
        Returns:
            List[Tuple[int, float]]: список (action_index, priority_score)
        """
        state_data = self.get_student_state(student_id)
        bkt_params = state_data['bkt_params']
        available_actions = state_data['available_actions']
        env = state_data['environment']
        
        recommendations = []
        
        for action_idx in available_actions:
            task_id = env.action_to_task_id[action_idx]
            task = Task.objects.get(id=task_id)
            
            # Получаем навыки, которые развивает задание
            task_skills = env.task_to_skills.get(task_id, set())
            
            if not task_skills:
                continue
                  # Вычисляем приоритет на основе уровня освоения навыков
            skill_priorities = []
            for skill_id in task_skills:
                skill_idx = self.skill_to_id.get(skill_id)  # Используем правильный маппинг
                if skill_idx is not None and skill_idx < len(bkt_params):
                    mastery_level = bkt_params[skill_idx, 0].item()  # current_mastery_prob
                    
                    # Определяем подходящую сложность для этого уровня освоения
                    if mastery_level < 0.5:
                        # Слабый навык - нужны простые задания
                        preferred_difficulty = 0  # Низкая сложность
                        preferred_type = 0  # true_false
                    elif mastery_level < 0.8:
                        # Средний навык - средние задания
                        preferred_difficulty = 1  # Средняя сложность
                        preferred_type = 1  # single
                    else:
                        # Сильный навык - сложные задания
                        preferred_difficulty = 2  # Высокая сложность
                        preferred_type = 2  # multiple
                    
                    # Вычисляем соответствие задания предпочтениям
                    task_difficulty_int = self.difficulty_map.get(task.difficulty, 1)
                    difficulty_match = 1.0 - abs(task_difficulty_int - preferred_difficulty) / 2.0
                    type_match = 1.0 if task.task_type == preferred_type else 0.7
                    
                    # Приоритет на основе потребности в развитии навыка
                    development_need = 1.0 - mastery_level  # Чем слабее навык, тем выше приоритет
                    
                    priority = difficulty_match * type_match * development_need
                    skill_priorities.append(priority)
            
            # Общий приоритет задания
            overall_priority = max(skill_priorities) if skill_priorities else 0.0
            recommendations.append((action_idx, overall_priority))
        
        # Сортируем по приоритету и возвращаем топ-k
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:top_k]
