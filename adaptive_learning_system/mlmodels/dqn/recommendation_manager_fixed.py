"""
Менеджер рекомендаций DQN (исправленная версия)

Интегрирует DQN рекомендательную систему с базой данных
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

# Импорт LLM для генерации объяснений
try:
    from mlmodels.llm.explanation_generator import ExplanationGenerator
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    print("⚠️ LLM модуль недоступен. Объяснения генерироваться не будут.")


def find_latest_dqn_model() -> Optional[str]:
    """
    Ищет последнюю обученную DQN модель
    
    Returns:
        Путь к последней модели или None
    """
    try:
        # Импортируем здесь, чтобы избежать циклических импортов
        from mlmodels.models import DQNTrainingSession
        
        # Ищем последнюю успешно завершенную сессию обучения
        latest_session = DQNTrainingSession.objects.filter(
            status='completed',
            model_path__isnull=False        ).order_by('-completed_at').first()
        
        if latest_session and latest_session.model_path:
            model_path = latest_session.model_path
            # Проверяем, что файл существует
            if os.path.exists(model_path):
                return model_path
        
        return None
        
    except Exception as e:
        return None


@dataclass
class RecommendationResult:
    """Результат создания рекомендации"""
    recommendation_id: int
    task_id: int
    q_value: float
    confidence: float
    created_at: datetime
    is_current: bool


class DQNRecommendationManagerFixed:
    """Менеджер для работы с DQN рекомендациями (исправленная версия)"""
    
    def __init__(self, buffer_size: int = 20):
        self.buffer_size = buffer_size
        # Автоматически ищем последнюю обученную модель
        latest_model_path = find_latest_dqn_model()
        self.recommender = DQNRecommender(model_path=latest_model_path)
        
        # Инициализируем LLM для генерации объяснений
        self.llm_generator = None
        if LLM_AVAILABLE:
            try:
                self.llm_generator = ExplanationGenerator()
                # Не инициализируем модель при создании менеджера, только при первом использовании
                print("✅ LLM генератор объяснений готов к использованию")
            except Exception as e:
                print(f"⚠️ Ошибка инициализации LLM: {e}")
                self.llm_generator = None
    
    def generate_and_save_recommendation(self, student_id: int, 
                                       set_as_current: bool = True) -> Optional[RecommendationResult]:
        """Генерирует новую рекомендацию от DQN и сохраняет в БД"""
        try:
            # Получаем рекомендации от DQN
            result = self.recommender.get_recommendations(student_id, top_k=1)
            
            if not result.recommendations:
                print(f"❌ DQN не вернул рекомендаций для студента {student_id}")
                return None
            
            top_recommendation = result.recommendations[0]
            
            with transaction.atomic():                # Получаем объекты студента и задания (student_id - это ID пользователя)
                from django.contrib.auth.models import User
                user = User.objects.get(id=student_id)
                student_profile, created = StudentProfile.objects.get_or_create(user=user)
                
                task = Task.objects.get(id=top_recommendation.task_id)
                
                # Собираем LLM контекст
                llm_context = self._collect_llm_context(student_profile, task, result)
                  # Создаем запись рекомендации
                recommendation = DQNRecommendation.objects.create(
                    student=student_profile,
                    task=task,
                    q_value=top_recommendation.q_value,
                    confidence=top_recommendation.confidence,
                    reason=top_recommendation.reason,
                    student_state_snapshot=self._serialize_state_vector(result.student_state),
                    prerequisite_skills_snapshot=llm_context['prerequisite_skills_snapshot'],
                    dependent_skills_snapshot=llm_context['dependent_skills_snapshot'],
                    target_skill_info=llm_context['target_skill_info'],
                    alternative_tasks_considered=llm_context['alternative_tasks_considered'],
                    student_progress_context=llm_context['student_progress_context']
                )
                
                # Генерируем LLM объяснение
                llm_explanation = self._generate_llm_explanation(recommendation, llm_context)
                if llm_explanation:
                    recommendation.llm_explanation = llm_explanation
                    recommendation.llm_explanation_generated_at = timezone.now()
                    recommendation.save(update_fields=['llm_explanation', 'llm_explanation_generated_at'])
                
                # Обновляем текущую рекомендацию если нужно
                if set_as_current:
                    self._update_current_recommendation(student_profile, recommendation)
                
                # Поддерживаем размер буфера
                self._maintain_buffer_size(student_profile)
                
                return RecommendationResult(
                    recommendation_id=recommendation.id,
                    task_id=recommendation.task.id,
                    q_value=recommendation.q_value,
                    confidence=recommendation.confidence,
                    created_at=recommendation.created_at,
                    is_current=set_as_current
                )
                
        except Exception as e:
            print(f"❌ Ошибка при создании рекомендации: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_current_recommendation(self, student_id: int) -> Optional[Dict[str, Any]]:
        """Получает текущую рекомендацию для студента"""
        try:
            current = StudentCurrentRecommendation.objects.select_related(
                'recommendation__task'            ).get(student_id=student_id)
            
            recommendation = current.recommendation
            
            return {
                'recommendation_id': recommendation.id,
                'task_id': recommendation.task.id,
                'task_title': recommendation.task.title,
                'task_content': recommendation.task.question_text,
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
            return None
    
    def link_attempt_to_recommendation(self, attempt_id: int, 
                                     recommendation_id: Optional[int] = None) -> bool:
        """Связывает попытку решения с рекомендацией"""
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
        """Получает историю рекомендаций для студента"""
        try:
            if limit is None:
                limit = self.buffer_size
            
            recommendations = DQNRecommendation.objects.select_related(
                'task', 'attempt'
            ).filter(
                student_id=student_id
            ).order_by('-created_at')[:limit]
            
            history = []
            for rec in recommendations:
                # Находим связанную попытку
                attempt = rec.attempt
                
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
                    'attempts': [],
                    'has_attempts': False,
                    'success_rate': 0
                }
                
                if attempt:
                    rec_data['attempts'] = [{
                        'id': attempt.id,
                        'is_correct': attempt.is_correct,
                        'time_spent': attempt.time_spent,
                        'created_at': attempt.completed_at
                    }]
                    rec_data['has_attempts'] = True
                    rec_data['success_rate'] = 1.0 if attempt.is_correct else 0.0
                
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
                'success_rate': student_state.success_rate,                'avg_difficulty': student_state.avg_difficulty
            }
            return json.dumps(state_data)
        except Exception as e:
            return "{}"
    
    def _update_current_recommendation(self, student: StudentProfile, 
                                     recommendation: DQNRecommendation):
        """Обновляет текущую рекомендацию для студента"""
        current_rec, created = StudentCurrentRecommendation.objects.update_or_create(
            student=student,
            defaults={
                'recommendation': recommendation,
                'set_at': timezone.now(),
                'llm_explanation': recommendation.llm_explanation  # Копируем LLM объяснение
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
    def _collect_llm_context(self, student_profile, task, result):
        """Собирает контекст для LLM объяснений"""
        try:
            from skills.models import Skill
            from mlmodels.models import StudentSkillMastery, TaskAttempt
            
            # Получаем целевые навыки задания
            target_skills = list(task.skills.all())
            
            # 1. Prerequisite навыки с их BKT вероятностями
            prerequisite_skills_info = []
            for skill in target_skills:
                prereqs = skill.prerequisites.all()
                for prereq in prereqs:
                    try:
                        mastery = StudentSkillMastery.objects.get(
                            student=student_profile, 
                            skill=prereq
                        )
                        prerequisite_skills_info.append({
                            'skill_id': prereq.id,
                            'skill_name': prereq.name,
                            'mastery_probability': float(mastery.current_mastery_prob),
                            'attempts_count': mastery.attempts_count,
                            'correct_attempts': mastery.correct_attempts
                        })
                    except StudentSkillMastery.DoesNotExist:
                        prerequisite_skills_info.append({
                            'skill_id': prereq.id,
                            'skill_name': prereq.name,
                            'mastery_probability': 0.1,
                            'attempts_count': 0,
                            'correct_attempts': 0
                        })
            
            # 2. Зависимые навыки с их BKT вероятностями
            dependent_skills_info = []
            for skill in target_skills:
                dependents = Skill.objects.filter(prerequisites=skill)
                for dependent in dependents:
                    try:
                        mastery = StudentSkillMastery.objects.get(
                            student=student_profile, 
                            skill=dependent
                        )
                        dependent_skills_info.append({
                            'skill_id': dependent.id,
                            'skill_name': dependent.name,
                            'mastery_probability': float(mastery.current_mastery_prob),
                            'attempts_count': mastery.attempts_count,
                            'correct_attempts': mastery.correct_attempts
                        })
                    except StudentSkillMastery.DoesNotExist:
                        dependent_skills_info.append({
                            'skill_id': dependent.id,
                            'skill_name': dependent.name,
                            'mastery_probability': 0.1,
                            'attempts_count': 0,
                            'correct_attempts': 0
                        })
            
            # 3. Информация о целевом навыке
            target_skill_info = []
            for skill in target_skills:
                try:
                    mastery = StudentSkillMastery.objects.get(
                        student=student_profile, 
                        skill=skill
                    )
                    target_skill_info.append({
                        'skill_id': skill.id,
                        'skill_name': skill.name,
                        'current_mastery_probability': float(mastery.current_mastery_prob),
                        'attempts_count': mastery.attempts_count,
                        'correct_attempts': mastery.correct_attempts,
                        'success_rate': mastery.correct_attempts / max(mastery.attempts_count, 1)
                    })
                except StudentSkillMastery.DoesNotExist:
                    target_skill_info.append({
                        'skill_id': skill.id,
                        'skill_name': skill.name,
                        'current_mastery_probability': 0.1,
                        'attempts_count': 0,
                        'correct_attempts': 0,
                        'success_rate': 0.0
                    })
            
            # 4. Альтернативные задания (упрощенная версия)
            alternative_tasks = []
            
            # 5. Контекст прогресса студента (упрощенная версия)
            total_attempts = TaskAttempt.objects.filter(student=student_profile).count()
            correct_attempts = TaskAttempt.objects.filter(student=student_profile, is_correct=True).count()
            
            progress_context = {
                'total_attempts': total_attempts,
                'total_success_rate': correct_attempts / max(total_attempts, 1)
            }
                
            return {
                'prerequisite_skills_snapshot': prerequisite_skills_info,
                'dependent_skills_snapshot': dependent_skills_info,
                'target_skill_info': target_skill_info,
                'alternative_tasks_considered': alternative_tasks,
                'student_progress_context': progress_context
            }
            
        except Exception as e:
            print(f"⚠️ Ошибка сбора LLM контекста: {e}")
            return {
                'prerequisite_skills_snapshot': [],
                'dependent_skills_snapshot': [],
                'target_skill_info': [],
                'alternative_tasks_considered': [],                'student_progress_context': {}
            }
    
    def _generate_llm_explanation(self, recommendation: DQNRecommendation, llm_context: Dict[str, Any]) -> Optional[str]:
        """
        Генерирует LLM объяснение для рекомендации
        
        Args:
            recommendation: Объект рекомендации
            llm_context: Контекст для LLM
            
        Returns:
            Сгенерированное объяснение или None
        """
        if not self.llm_generator:
            return None
            
        try:
            # Ленивая инициализация LLM модели при первом использовании
            if not self.llm_generator.is_initialized:
                print("🤖 Первое использование LLM. Загружаем модель...")
                success = self.llm_generator.initialize(use_quantization=True)
                if not success:
                    print("❌ Не удалось инициализировать LLM")
                    return None
                print("✅ LLM успешно инициализирована")
              # Подготавливаем данные для LLM
            recommendation_data = {
                'student_name': recommendation.student.user.first_name or 'Студент',
                'task_title': recommendation.task.title,
                'task_difficulty': recommendation.task.difficulty,
                'task_type': recommendation.task.task_type,  # Добавляем тип задания
                'target_skill_info': llm_context['target_skill_info'],
                'prerequisite_skills_snapshot': llm_context['prerequisite_skills_snapshot'],
                'dependent_skills_snapshot': llm_context['dependent_skills_snapshot'],  # Добавляем зависимые навыки
                'student_progress_context': llm_context['student_progress_context']
            }
            
            # Генерируем объяснение
            explanation = self.llm_generator.generate_recommendation_explanation(recommendation_data)
            
            if explanation and len(explanation.strip()) > 10:
                print(f"✅ LLM объяснение сгенерировано: {explanation[:50]}...")
                return explanation.strip()
            else:
                print("⚠️ LLM вернула пустое объяснение")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка генерации LLM объяснения: {e}")
            return None

# Глобальный экземпляр менеджера (исправленная версия)
recommendation_manager_fixed = DQNRecommendationManagerFixed()
