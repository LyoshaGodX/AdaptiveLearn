"""
Среда обучения для DQN агента

Реализует среду Reinforcement Learning для обучения DQN агента
рекомендации заданий с учётом:
- Графа навыков и prerequisite ограничений
- Обратной связи от студента (успех/неудача)
- Динамического обновления BKT параметров
- Формирования наград за улучшение обучения
"""

import torch
import numpy as np
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime, timedelta
import random

from .data_processor import DQNDataProcessor, DQNEnvironment
from .model import DQNConfig
from methodist.models import Task
from mlmodels.models import TaskAttempt
from student.models import StudentProfile
from django.contrib.auth.models import User


class DQNTrainingEnvironment:
    """Среда для обучения DQN агента"""
    
    def __init__(self, config: DQNConfig):
        self.config = config
        self.data_processor = DQNDataProcessor(config.max_history_length)
        
        # Статистика обучения
        self.total_episodes = 0
        self.total_rewards = []
        self.episode_lengths = []
        
    def create_training_episode(self, student_id: int, num_steps: int = 10) -> List[Dict]:
        """
        Создаёт эпизод обучения для студента
        
        Args:
            student_id: ID студента
            num_steps: количество шагов в эпизоде
            
        Returns:
            List[Dict]: список опыта (state, action, reward, next_state, done)
        """
        episode_data = []
        
        # Получаем начальное состояние студента
        current_state_data = self.data_processor.get_student_state(student_id)
        current_state = self._encode_state(current_state_data)
        
        env = current_state_data['environment']
        
        for step in range(num_steps):
            # Получаем доступные действия
            available_actions = current_state_data['available_actions']
            
            if not available_actions:
                # Если нет доступных заданий, завершаем эпизод
                break
            
            # Выбираем действие (задание)
            action = self._select_training_action(available_actions)
            
            # Симулируем выполнение задания
            success, skill_improvements, difficulty_match = self._simulate_task_execution(
                student_id, action, current_state_data
            )
            
            # Вычисляем награду
            reward = env.calculate_reward(
                task_id=action,
                success=success,
                skill_improvements=skill_improvements,
                difficulty_match=difficulty_match
            )
            
            # Обновляем состояние студента после выполнения задания
            next_state_data = self._update_student_state(
                student_id, action, success, skill_improvements
            )
            next_state = self._encode_state(next_state_data)
            
            # Проверяем, завершён ли эпизод
            done = (step == num_steps - 1) or env.is_done()
            
            # Сохраняем опыт
            episode_data.append({
                'state': current_state,
                'action': action,
                'reward': reward,
                'next_state': next_state,
                'done': done,
                'available_actions': available_actions
            })
            
            # Переходим к следующему состоянию
            current_state = next_state
            current_state_data = next_state_data
            
            if done:
                break
        
        return episode_data
    
    def _encode_state(self, state_data: Dict) -> torch.Tensor:
        """Кодирует состояние студента в тензор"""
        bkt_params = state_data['bkt_params'].unsqueeze(0)  # [1, num_skills, 4]
        history = state_data['history'].unsqueeze(0)        # [1, seq_len, 8]
        
        # Используем временный энкодер для получения состояния
        from .model import StudentStateEncoder
        encoder = StudentStateEncoder(self.config, num_skills=bkt_params.size(1))
        
        with torch.no_grad():
            state = encoder(bkt_params, history)  # [1, state_dim]
            
        return state.squeeze(0)  # [state_dim]
    
    def _select_training_action(self, available_actions: List[int]) -> int:
        """Выбирает действие для обучения (случайно из доступных)"""
        return random.choice(available_actions)
    
    def _simulate_task_execution(self, student_id: int, task_id: int, 
                                state_data: Dict) -> Tuple[bool, Dict[int, float], float]:
        """
        Симулирует выполнение задания студентом
        
        Returns:
            success: успешно ли выполнено задание
            skill_improvements: улучшения навыков {skill_id: improvement}
            difficulty_match: соответствие сложности (0-1)
        """
        # Получаем данные задания
        task_data = self.data_processor.get_task_data(task_id)
        task_skills = task_data['skills']
        
        # Вычисляем вероятность успеха на основе BKT
        bkt_params = state_data['bkt_params']
        success_prob = self._calculate_success_probability(task_skills, bkt_params)
        
        # Симулируем результат
        success = np.random.random() < success_prob
        
        # Вычисляем улучшения навыков
        skill_improvements = {}
        if success:
            for skill_id in task_skills:
                skill_idx = self.data_processor.skill_to_id.get(skill_id, 0)
                # Улучшение пропорционально текущему незнанию навыка
                current_know = bkt_params[skill_idx, 0].item()
                improvement = (1 - current_know) * 0.1  # 10% от незнания
                skill_improvements[skill_id] = improvement
        else:
            # При неудаче улучшения минимальны
            for skill_id in task_skills:
                skill_improvements[skill_id] = 0.02
          # Вычисляем соответствие сложности
        difficulty_match = self._calculate_difficulty_match(task_data, success_prob)
        
        return success, skill_improvements, difficulty_match
    
    def _calculate_success_probability(self, task_skills: List[int], 
                                     bkt_params: torch.Tensor) -> float:
        """Вычисляет вероятность успеха на основе BKT параметров"""
        if not task_skills:
            return 0.1
        
        # Берём среднюю вероятность знания по всем навыкам задания
        total_prob = 0.0
        for skill_id in task_skills:
            skill_idx = self.data_processor.skill_to_id.get(skill_id, 0)
            know_prob = bkt_params[skill_idx, 0].item()
            guess_prob = bkt_params[skill_idx, 2].item()
            slip_prob = bkt_params[skill_idx, 3].item()
            
            # P(correct) = P(know) * (1 - P(slip)) + (1 - P(know)) * P(guess)
            correct_prob = know_prob * (1 - slip_prob) + (1 - know_prob) * guess_prob
            total_prob += correct_prob
        
        return total_prob / len(task_skills)
    
    def _calculate_difficulty_match(self, task_data: Dict, success_prob: float) -> float:
        """Вычисляет, насколько сложность задания соответствует уровню студента"""
        # Оптимальная вероятность успеха ~ 0.7 (зона ближайшего развития)
        optimal_prob = 0.7
        diff = abs(success_prob - optimal_prob)
        
        # Чем ближе к оптимальной, тем лучше соответствие
        match = max(0.0, 1.0 - diff * 2)
        return match
    
    def _update_student_state(self, student_id: int, task_id: int, success: bool, 
                            skill_improvements: Dict[int, float]) -> Dict:
        """
        Обновляет состояние студента после выполнения задания
        
        Returns:
            Dict: новое состояние студента
        """
        # В реальной системе здесь бы обновлялись BKT параметры
        # Для симуляции мы просто получаем текущее состояние и немного модифицируем
        
        current_state = self.data_processor.get_student_state(student_id)
        
        # Обновляем BKT параметры на основе результата
        updated_bkt = current_state['bkt_params'].clone()
        
        for skill_id, improvement in skill_improvements.items():
            skill_idx = self.data_processor.skill_to_id.get(skill_id, 0)
            
            if success:
                # Увеличиваем вероятность знания при успехе
                updated_bkt[skill_idx, 0] = torch.clamp(
                    updated_bkt[skill_idx, 0] + improvement, 0.0, 1.0
                )
            else:
                # Немного уменьшаем при неудаче
                updated_bkt[skill_idx, 0] = torch.clamp(
                    updated_bkt[skill_idx, 0] - 0.01, 0.0, 1.0
                )
        
        # Создаём новое состояние
        new_state = current_state.copy()
        new_state['bkt_params'] = updated_bkt
        
        # Пересчитываем освоенные навыки и доступные действия
        new_state['mastered_skills'] = self.data_processor._get_mastered_skills(
            new_state['environment'].student_profile, updated_bkt
        )
        new_state['available_actions'] = new_state['environment'].get_available_actions(
            new_state['mastered_skills']
        )
        
        return new_state
    
    def generate_synthetic_episodes(self, num_students: int = 100, 
                                  episodes_per_student: int = 5) -> List[List[Dict]]:
        """
        Генерирует синтетические эпизоды для обучения
        
        Args:
            num_students: количество синтетических студентов
            episodes_per_student: количество эпизодов на студента
            
        Returns:
            List[List[Dict]]: список эпизодов
        """
        all_episodes = []
        
        # Получаем существующих студентов или создаём синтетических
        existing_students = list(User.objects.filter(
            studentprofile__isnull=False
        ).values_list('id', flat=True))
        
        if len(existing_students) < num_students:
            print(f"Недостаточно студентов в базе ({len(existing_students)}), "
                  f"используем существующих")
            student_ids = existing_students
        else:
            student_ids = existing_students[:num_students]
        
        for student_id in student_ids:
            try:
                for episode_num in range(episodes_per_student):
                    episode = self.create_training_episode(
                        student_id, num_steps=random.randint(5, 15)
                    )
                    
                    if episode:  # Добавляем только непустые эпизоды
                        all_episodes.append(episode)
                        
            except Exception as e:
                continue
        
        return all_episodes
    
    def evaluate_agent_performance(self, agent, num_episodes: int = 10) -> Dict:
        """
        Оценивает производительность обученного агента
        
        Args:
            agent: обученный DQN агент
            num_episodes: количество эпизодов для оценки
            
        Returns:
            Dict: метрики производительности
        """
        total_rewards = []
        episode_lengths = []
        success_rates = []
        
        # Получаем тестовых студентов
        test_students = list(User.objects.filter(
            studentprofile__isnull=False
        ).values_list('id', flat=True))[:10]
        
        for student_id in test_students:
            try:
                state_data = self.data_processor.get_student_state(student_id)
                state = self._encode_state(state_data)
                
                episode_reward = 0
                episode_length = 0
                successes = 0
                
                for step in range(20):  # Максимум 20 шагов
                    available_actions = state_data['available_actions']
                    
                    if not available_actions:
                        break
                    
                    # Агент выбирает действие
                    action = agent.select_action(state, available_actions)
                    
                    # Симулируем выполнение
                    success, skill_improvements, difficulty_match = self._simulate_task_execution(
                        student_id, action, state_data
                    )
                    
                    if success:
                        successes += 1
                    
                    # Вычисляем награду
                    reward = state_data['environment'].calculate_reward(
                        action, success, skill_improvements, difficulty_match
                    )
                    
                    episode_reward += reward
                    episode_length += 1
                    
                    # Обновляем состояние
                    state_data = self._update_student_state(
                        student_id, action, success, skill_improvements
                    )
                    state = self._encode_state(state_data)
                
                total_rewards.append(episode_reward)
                episode_lengths.append(episode_length)
                success_rates.append(successes / max(episode_length, 1))
                
            except Exception as e:
                continue
        
        return {
            'mean_reward': np.mean(total_rewards) if total_rewards else 0,
            'std_reward': np.std(total_rewards) if total_rewards else 0,
            'mean_episode_length': np.mean(episode_lengths) if episode_lengths else 0,
            'mean_success_rate': np.mean(success_rates) if success_rates else 0,
            'num_episodes': len(total_rewards)
        }
