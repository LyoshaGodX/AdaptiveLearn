"""
Менеджер рекомендаций DQN

Интегрирует DQN рекомендательную систему с базой данных:
- Генерирует и сохраняет рекомендации
-             return {
                'recommendation_id': recommendation.id,
                'task_id': recommendation.task.id,
                'task_title': recommendation.task.title,
                'task_content': recommendation.task.content,
                'task_type': recommendation.task.task_type,
                'difficulty': recommendation.task.difficulty,
                'q_value': recommendation.q_value,
                'confidence': recommendation.confidence,
                'reason': recommendation.reason,
                'created_at': recommendation.created_at,
                'set_as_current_at': current.set_at
            }
            
        except StudentCurrentRecommendation.DoesNotExist:
            return None
        except Exception as e:
            return None рекомендации для студентов
- Связывает попытки решения с рекомендациями
- Управляет буфером истории рекомендаций
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

# Добавляем путь к Django проекту
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')

import django
django.setup()

from django.db import transaction
from django.utils import timezone

from mlmodels.models import (
    DQNRecommendation, StudentCurrentRecommendation, 
    ExpertFeedback, TaskAttempt
)
from student.models import StudentProfile
from methodist.models import Task
from .recommender import DQNRecommender


@dataclass
class RecommendationResult:
    """Результат создания рекомендации"""
    recommendation_id: int
    task_id: int
    q_value: float
    confidence: float
    created_at: datetime
    is_current: bool


class DQNRecommendationManager:
    """Менеджер для работы с DQN рекомендациями"""
    
    def __init__(self, buffer_size: int = 20):
        """
        Args:
            buffer_size: Размер буфера истории рекомендаций для каждого студента
        """
        self.buffer_size = buffer_size
        self.recommender = DQNRecommender()
    
    def generate_and_save_recommendation(self, student_id: int, 
                                       set_as_current: bool = True) -> Optional[RecommendationResult]:
        """
        Генерирует новую рекомендацию от DQN и сохраняет в БД
        
        Args:
            student_id: ID студента
            set_as_current: Установить ли как текущую рекомендацию
            
        Returns:
            RecommendationResult или None при ошибке
        """
        try:
            # Получаем рекомендации от DQN
            result = self.recommender.get_recommendations(student_id, top_k=1)
            
            if not result.recommendations:
                return None
            
            top_recommendation = result.recommendations[0]
            
            with transaction.atomic():
                # Получаем объекты студента и задания
                student = StudentProfile.objects.get(id=student_id)
                task = Task.objects.get(id=top_recommendation.task_id)
                  # Создаем запись рекомендации
                recommendation = DQNRecommendation.objects.create(
                    student=student,
                    task=task,
                    q_value=top_recommendation.q_value,
                    confidence=top_recommendation.confidence,
                    reason=top_recommendation.reason,
                    student_state_snapshot=self._serialize_state_vector(result.student_state)
                )
                
                # Обновляем текущую рекомендацию если нужно
                if set_as_current:
                    self._update_current_recommendation(student, recommendation)
                
                # Поддерживаем размер буфера
                self._maintain_buffer_size(student)
                
                return RecommendationResult(
                    recommendation_id=recommendation.id,
                    task_id=recommendation.task.id,
                    q_value=recommendation.q_value,
                    confidence=recommendation.confidence,
                    created_at=recommendation.created_at,
                    is_current=set_as_current
                )
                
        except Exception as e:
            return None
    
    def get_current_recommendation(self, student_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает текущую рекомендацию для студента
        
        Args:
            student_id: ID студента
            
        Returns:
            Словарь с информацией о рекомендации или None
        """
        try:
            current = StudentCurrentRecommendation.objects.select_related(
                'recommendation__task'
            ).get(student_id=student_id)
            
            recommendation = current.recommendation
            
            return {
                'recommendation_id': recommendation.id,
                'task_id': recommendation.task.id,
                'task_title': recommendation.task.title,
                'task_content': recommendation.task.content,
                'task_type': recommendation.task.task_type,
                'difficulty': recommendation.task.difficulty,
                'q_value': recommendation.q_value,                'confidence': recommendation.confidence,
                'reason': recommendation.reason,
                'created_at': recommendation.created_at,
                'set_as_current_at': current.set_at
            }
        except StudentCurrentRecommendation.DoesNotExist:
            return None
        except Exception as e:
            return None
    
    def link_attempt_to_recommendation(self, attempt_id: int, 
                                     recommendation_id: Optional[int] = None) -> bool:
        """
        Связывает попытку решения с рекомендацией
        
        Args:
            attempt_id: ID попытки
            recommendation_id: ID рекомендации (если None, ищет по текущей рекомендации)
            
        Returns:
            True если связь создана успешно
        """
        try:
            attempt = TaskAttempt.objects.get(id=attempt_id)
            
            # Если recommendation_id не указан, ищем текущую рекомендацию
            if recommendation_id is None:
                current = self.get_current_recommendation(attempt.student.id)
                if not current:
                    return False
                recommendation_id = current['recommendation_id']
            
            # Проверяем, что рекомендация существует и для того же задания
            recommendation = DQNRecommendation.objects.get(id=recommendation_id)
            
            if recommendation.task_id != attempt.task.id:
                return False
            
            # Обновляем рекомендацию (связываем с попыткой)
            recommendation.attempt = attempt
            recommendation.save()
            
            return True
            
        except Exception as e:
            return False
    
    def get_recommendation_history(self, student_id: int, 
                                 limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Получает историю рекомендаций для студента
        
        Args:
            student_id: ID студента
            limit: Максимальное количество записей (по умолчанию buffer_size)
            
        Returns:
            Список рекомендаций с дополнительной информацией
        """
        try:
            if limit is None:
                limit = self.buffer_size
            
            recommendations = DQNRecommendation.objects.select_related(
                'task'
            ).prefetch_related(
                'taskattempt_set__student'
            ).filter(
                student_id=student_id
            ).order_by('-created_at')[:limit]
            
            history = []
            for rec in recommendations:
                # Находим связанные попытки
                attempts = rec.taskattempt_set.all()
                
                rec_data = {
                    'id': rec.id,
                    'task_id': rec.task.id,
                    'task_title': rec.task.title,
                    'task_type': rec.task.task_type,
                    'difficulty': rec.task.difficulty,
                    'q_value': rec.q_value,
                    'confidence': rec.confidence,
                    'reason': rec.reason,
                    'created_at': rec.created_at,
                    'attempts': [
                        {
                            'id': att.id,
                            'is_correct': att.is_correct,
                            'score': att.score,
                            'time_spent': att.time_spent,
                            'created_at': att.created_at
                        }
                        for att in attempts
                    ],
                    'has_attempts': len(attempts) > 0,
                    'success_rate': sum(1 for att in attempts if att.is_correct) / len(attempts) if attempts else 0
                }
                
                history.append(rec_data)
            
            return history
            
        except Exception as e:
            return []
    
    def _serialize_state_vector(self, student_state) -> str:
        """Сериализует вектор состояния для сохранения в БД"""
        import json
        import torch
        
        try:
            state_data = {
                'bkt_params': student_state.bkt_params.tolist(),
                'history_shape': list(student_state.history.shape),
                'graph_shape': list(student_state.skills_graph.shape),
                'total_skills': student_state.total_skills,
                'total_attempts': student_state.total_attempts,
                'success_rate': student_state.success_rate,
                'avg_difficulty': student_state.avg_difficulty
            }
            return json.dumps(state_data)
        except Exception as e:
            return "{}"
    
    def _update_current_recommendation(self, student: StudentProfile, 
                                     recommendation: DQNRecommendation):
        """Обновляет текущую рекомендацию для студента"""
        StudentCurrentRecommendation.objects.update_or_create(
            student=student,
            defaults={
                'recommendation': recommendation,
                'set_at': timezone.now()
            }
        )
    
    def _maintain_buffer_size(self, student: StudentProfile):
        """Поддерживает размер буфера рекомендаций"""
        # Получаем все рекомендации студента
        recommendations = DQNRecommendation.objects.filter(
            student=student
        ).order_by('-created_at')
        
        # Если превышен лимит, удаляем старые
        if recommendations.count() > self.buffer_size:
            old_recommendations = recommendations[self.buffer_size:]
            old_ids = [rec.id for rec in old_recommendations]
            DQNRecommendation.objects.filter(id__in=old_ids).delete()


# Глобальный экземпляр менеджера
recommendation_manager = DQNRecommendationManager()
