"""
Менеджер экспертной обратной связи для DQN

Управляет:
- Сбором обратной связи от экспертов
- Подготовкой данных для обучения с подкреплением
- Обучением модели на размеченных данных
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

# Добавляем путь к Django проекту
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')

import django
django.setup()

import torch
import numpy as np
from django.db import transaction
from django.utils import timezone

from mlmodels.models import ExpertFeedback, DQNRecommendation, DQNTrainingSession
from student.models import StudentProfile
from .data_processor import DQNDataProcessor
from .trainer import DQNTrainer
from .model import DQNAgent


@dataclass
class FeedbackStats:
    """Статистика обратной связи"""
    total_feedback: int
    positive_feedback: int
    negative_feedback: int
    avg_reward: float
    by_strength: Dict[str, int]
    by_expert: Dict[int, int]


class ExpertFeedbackManager:
    """Менеджер для работы с экспертной обратной связью"""
    
    # Маппинг силы подкрепления в числовые значения
    REWARD_MAPPING = {
        'low': {'positive': 0.3, 'negative': -0.3},
        'medium': {'positive': 0.6, 'negative': -0.6},
        'strong': {'positive': 1.0, 'negative': -1.0}    }
    
    def __init__(self):
        self.data_processor = DQNDataProcessor()
        # Инициализируем data_processor
        try:
            _ = self.data_processor.get_student_state(10)  # Инициализация на тестовом студенте
        except Exception as e:
            pass

    def add_feedback(self, recommendation_id: int, expert_id: int,
                    feedback_type: str, strength: str, 
                    comment: str = "") -> bool:
        """
        Добавляет обратную связь эксперта
        
        Args:
            recommendation_id: ID рекомендации
            expert_id: ID эксперта
            feedback_type: 'positive' или 'negative'
            strength: 'low', 'medium', 'strong'
            comment: Комментарий эксперта
            
        Returns:
            True если обратная связь добавлена успешно
        """
        try:
            # Проверяем валидность параметров
            if feedback_type not in ['positive', 'negative']:
                raise ValueError(f"Некорректный тип обратной связи: {feedback_type}")
            
            if strength not in ['low', 'medium', 'strong']:
                raise ValueError(f"Некорректная сила подкрепления: {strength}")
            
            # Вычисляем награду
            reward = self.REWARD_MAPPING[strength][feedback_type]
            
            with transaction.atomic():
                # Получаем рекомендацию
                recommendation = DQNRecommendation.objects.get(id=recommendation_id)
                
                # Создаем или обновляем обратную связь
                feedback, created = ExpertFeedback.objects.update_or_create(
                    recommendation=recommendation,
                    expert_id=expert_id,
                    defaults={
                        'feedback_type': feedback_type,
                        'strength': strength,
                        'reward_value': reward,
                        'comment': comment,
                        'created_at': timezone.now()
                    }
                )
                
                action = "создана" if created else "обновлена"
                
                return True
                
        except Exception as e:
            return False
    
    def get_feedback_stats(self, days: int = 30) -> FeedbackStats:
        """
        Получает статистику обратной связи за период
        
        Args:
            days: Количество дней для анализа
            
        Returns:
            Статистика обратной связи
        """
        try:
            # Фильтруем по дате
            since_date = timezone.now() - timedelta(days=days)
            feedbacks = ExpertFeedback.objects.filter(
                created_at__gte=since_date
            ).select_related('recommendation')
            
            total = feedbacks.count()
            if total == 0:
                return FeedbackStats(0, 0, 0, 0.0, {}, {})
            
            positive = feedbacks.filter(feedback_type='positive').count()
            negative = feedbacks.filter(feedback_type='negative').count()
              # Средняя награда
            rewards = [f.reward_value for f in feedbacks]
            avg_reward = float(np.mean(rewards)) if rewards else 0.0
            
            # По силе подкрепления
            by_strength = {}
            for strength in ['low', 'medium', 'strong']:
                by_strength[strength] = feedbacks.filter(strength=strength).count()
            
            # По экспертам
            by_expert = {}
            for feedback in feedbacks:
                expert_id = feedback.expert_id
                by_expert[expert_id] = by_expert.get(expert_id, 0) + 1
            
            return FeedbackStats(
                total_feedback=total,
                positive_feedback=positive,
                negative_feedback=negative,
                avg_reward=avg_reward,
                by_strength=by_strength,
                by_expert=by_expert
            )
            
        except Exception as e:
            return FeedbackStats(0, 0, 0, 0.0, {}, {})
    
    def prepare_training_data(self, min_feedback_count: int = 10) -> List[Dict[str, Any]]:
        """
        Подготавливает данные для обучения с подкреплением
        
        Args:
            min_feedback_count: Минимальное количество обратной связи для включения в обучение
            
        Returns:
            Список обучающих примеров
        """
        try:
            # Получаем все рекомендации с обратной связью
            feedbacks = ExpertFeedback.objects.select_related(
                'recommendation__student',
                'recommendation__task'
            ).all()
            
            if len(feedbacks) < min_feedback_count:
                return []
            
            training_examples = []
            
            for feedback in feedbacks:
                try:
                    recommendation = feedback.recommendation
                    student_id = recommendation.student.id
                    
                    # Получаем состояние студента на момент рекомендации
                    state = self.data_processor.get_student_state(student_id)
                    
                    # Получаем доступные действия через BKT параметры
                    bkt_params = state['bkt_params']
                    available_actions = self.data_processor.get_available_actions(
                        bkt_params, self.data_processor.skill_to_id
                    )
                    
                    # Находим индекс действия
                    try:
                        action_index = available_actions.index(recommendation.task.id)
                    except ValueError:
                        continue
                    
                    example = {
                        'student_id': student_id,
                        'state': {
                            'bkt_params': state['bkt_params'],
                            'history': state['history'],
                            'skills_graph': state['skills_graph']
                        },
                        'action': action_index,
                        'task_id': recommendation.task.id,
                        'reward': feedback.reward_value,
                        'feedback_type': feedback.feedback_type,
                        'strength': feedback.strength,
                        'q_value': recommendation.q_value,
                        'timestamp': feedback.created_at
                    }
                    
                    training_examples.append(example)
                    
                except Exception as e:
                    continue
            
            return training_examples
            
        except Exception as e:
            return []
    
    def train_model_with_feedback(self, training_examples: List[Dict[str, Any]],
                                learning_rate: float = 1e-4,
                                batch_size: int = 32,
                                epochs: int = 100) -> Optional[str]:
        """
        Обучает модель DQN на основе экспертной обратной связи
        
        Args:
            training_examples: Обучающие примеры
            learning_rate: Скорость обучения
            batch_size: Размер батча
            epochs: Количество эпох
            
        Returns:
            Путь к сохраненной модели или None при ошибке
        """
        try:
            if not training_examples:
                return None
            
            
            # Создаем сессию обучения
            session = DQNTrainingSession.objects.create(
                started_at=timezone.now(),
                training_examples_count=len(training_examples),
                learning_rate=learning_rate,
                batch_size=batch_size,
                epochs=epochs,
                status='running'
            )
            
            try:
                # Инициализируем тренер
                trainer = DQNTrainer(
                    state_dim=self.data_processor.get_state_dim(),
                    action_dim=self.data_processor.get_action_dim(),
                    learning_rate=learning_rate
                )
                
                # Конвертируем примеры в тензоры
                states, actions, rewards = self._convert_examples_to_tensors(training_examples)
                
                # Обучаем модель
                losses = []
                for epoch in range(epochs):
                    epoch_losses = []
                    
                    # Батчевое обучение
                    for i in range(0, len(states), batch_size):
                        batch_states = states[i:i+batch_size]
                        batch_actions = actions[i:i+batch_size]
                        batch_rewards = rewards[i:i+batch_size]
                        
                        loss = trainer.train_step(batch_states, batch_actions, batch_rewards)
                        epoch_losses.append(loss)
                    
                    avg_loss = np.mean(epoch_losses)
                    losses.append(avg_loss)
                
                # Сохраняем модель
                model_path = f"checkpoints/dqn_expert_feedback_{session.id}.pth"
                os.makedirs(os.path.dirname(model_path), exist_ok=True)
                trainer.save_model(model_path)
                
                # Обновляем сессию
                session.status = 'completed'
                session.completed_at = timezone.now()
                session.final_loss = losses[-1] if losses else 0.0
                session.model_path = model_path
                session.save()
                
                return model_path
                
            except Exception as training_error:
                # Обновляем статус сессии при ошибке
                session.status = 'failed'
                session.error_message = str(training_error)
                session.save()
                raise training_error
                
        except Exception as e:
            return None
    
    def get_training_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получает историю обучения модели
        
        Args:
            limit: Максимальное количество сессий
            
        Returns:
            Список сессий обучения
        """
        try:
            sessions = DQNTrainingSession.objects.order_by('-started_at')[:limit]
            
            history = []
            for session in sessions:
                session_data = {
                    'id': session.id,
                    'started_at': session.started_at,
                    'completed_at': session.completed_at,
                    'status': session.status,
                    'training_examples_count': session.training_examples_count,
                    'learning_rate': session.learning_rate,
                    'batch_size': session.batch_size,
                    'epochs': session.epochs,
                    'final_loss': session.final_loss,
                    'model_path': session.model_path,
                    'error_message': session.error_message
                }
                history.append(session_data)
            
            return history
            
        except Exception as e:
            return []
    
    def _convert_examples_to_tensors(self, examples: List[Dict[str, Any]]) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Конвертирует примеры в тензоры для обучения"""
        states = []
        actions = []
        rewards = []
        
        for example in examples:
            # Состояние: конкатенация BKT, истории и графа
            state = example['state']
            bkt = torch.tensor(state['bkt_params'], dtype=torch.float32)
            history = torch.tensor(state['history'], dtype=torch.float32)
            graph = torch.tensor(state['skills_graph'], dtype=torch.float32)
            
            # Объединяем в один вектор состояния
            combined_state = torch.cat([
                bkt.flatten(),
                history.flatten(),
                graph.flatten()
            ])
            
            states.append(combined_state)
            actions.append(example['action'])
            rewards.append(example['reward'])
        
        return (
            torch.stack(states),
            torch.tensor(actions, dtype=torch.long),
            torch.tensor(rewards, dtype=torch.float32)
        )


# Глобальный экземпляр менеджера
expert_feedback_manager = ExpertFeedbackManager()
