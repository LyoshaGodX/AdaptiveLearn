"""
Система рекомендаций на основе DKN модели

Этот модуль использует обученную DKN модель для рекомендации 
оптимальных заданий студентам на основе их текущих навыков и истории.
"""

import torch
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

# Django imports
from django.contrib.auth.models import User
from skills.models import Skill
from methodist.models import Task
from mlmodels.models import TaskAttempt, StudentSkillMastery
from student.models import StudentProfile

# Local imports
from .model import DKNModel, DKNConfig
from .data_processor import DKNDataProcessor

logger = logging.getLogger(__name__)


@dataclass
class RecommendationResult:
    """Результат рекомендации задания"""
    task_id: int
    task_title: str
    predicted_success_prob: float
    confidence: float
    reasoning: str
    required_skills: List[str]
    difficulty: str
    estimated_time: int  # минуты


class DKNRecommender:
    """Система рекомендаций на основе DKN"""
    
    def __init__(self, model_path: str, config: Optional[DKNConfig] = None):
        """
        Args:
            model_path: Путь к сохраненной модели
            config: Конфигурация модели (если None, будет загружена из checkpoint)
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.processor = DKNDataProcessor()
        
        # Загружаем модель
        if config is None:
            config = DKNConfig()
        
        self.model = DKNModel(
            num_skills=len(self.processor.skill_to_id),
            num_tasks=len(self.processor.task_to_id),
            config=config
        )
        
        try:
            checkpoint = torch.load(model_path, map_location=self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.model.eval()
            logger.info(f"Модель загружена из {model_path}")
        except FileNotFoundError:
            logger.warning(f"Файл модели {model_path} не найден. Используется необученная модель.")
    
    def get_recommendations(self, student_id: int, 
                          num_recommendations: int = 5,
                          difficulty_preference: Optional[str] = None,
                          skill_focus: Optional[List[str]] = None,
                          exclude_completed: bool = True) -> List[RecommendationResult]:
        """
        Получает рекомендации заданий для студента
        
        Args:
            student_id: ID студента
            num_recommendations: Количество рекомендаций
            difficulty_preference: Предпочтительная сложность ('beginner', 'intermediate', 'advanced')
            skill_focus: Список навыков для фокусировки (по названию)
            exclude_completed: Исключать уже выполненные задания
            
        Returns:
            Список рекомендаций, отсортированный по релевантности
        """
        try:
            student = User.objects.get(id=student_id)
            
            # Получаем кандидатов заданий
            candidate_tasks = self._get_candidate_tasks(
                student, difficulty_preference, skill_focus, exclude_completed
            )
            
            if not candidate_tasks:
                logger.warning(f"Нет доступных заданий для студента {student_id}")
                return []
            
            # Получаем предсказания для всех кандидатов
            predictions = self._predict_success_batch(student_id, candidate_tasks)
            
            # Создаем рекомендации
            recommendations = []
            for task, pred_data in zip(candidate_tasks, predictions):
                recommendation = RecommendationResult(
                    task_id=task.id,
                    task_title=task.title,
                    predicted_success_prob=pred_data['success_prob'],
                    confidence=pred_data['confidence'],
                    reasoning=pred_data['reasoning'],
                    required_skills=[skill.name for skill in task.required_skills.all()],
                    difficulty=task.difficulty,
                    estimated_time=task.estimated_time or 30
                )
                recommendations.append(recommendation)
            
            # Сортируем по оптимальности (зона ближайшего развития)
            recommendations = self._rank_recommendations(recommendations, student_id)
            
            return recommendations[:num_recommendations]
            
        except Exception as e:
            logger.error(f"Ошибка при получении рекомендаций для студента {student_id}: {e}")
            return []
    
    def _get_candidate_tasks(self, student: User, 
                           difficulty_preference: Optional[str],
                           skill_focus: Optional[List[str]],
                           exclude_completed: bool) -> List[Task]:
        """Получает кандидатов заданий для рекомендации"""
        
        # Базовый запрос
        tasks_query = Task.objects.all()
        
        # Фильтр по сложности
        if difficulty_preference:
            tasks_query = tasks_query.filter(difficulty=difficulty_preference)
        
        # Фильтр по навыкам
        if skill_focus:
            skills = Skill.objects.filter(name__in=skill_focus)
            tasks_query = tasks_query.filter(required_skills__in=skills).distinct()
        
        # Исключаем уже выполненные задания
        if exclude_completed:
            completed_task_ids = TaskAttempt.objects.filter(
                student__user=student,
                is_correct=True
            ).values_list('task_id', flat=True)
            
            tasks_query = tasks_query.exclude(id__in=completed_task_ids)
        
        return list(tasks_query[:50])  # Ограничиваем количество кандидатов
    
    def _predict_success_batch(self, student_id: int, tasks: List[Task]) -> List[Dict]:
        """Предсказывает успех для батча заданий"""
        predictions = []
        
        # Подготавливаем данные для всех заданий
        batch_data = []
        for task in tasks:
            student_data = self.processor.get_student_data(student_id, task.id)
            batch_data.append(student_data)
        
        # Подготавливаем батч для модели
        model_batch = self.processor.prepare_batch(batch_data)
        
        # Переводим на устройство
        model_batch = {k: v.to(self.device) if isinstance(v, torch.Tensor) else v 
                      for k, v in model_batch.items()}
        
        # Получаем предсказания
        with torch.no_grad():
            success_probs = self.model(model_batch).cpu().numpy()
        
        # Анализируем результаты
        for i, (task, prob) in enumerate(zip(tasks, success_probs)):
            confidence = self._calculate_confidence(prob)
            reasoning = self._generate_reasoning(task, prob, batch_data[i])
            
            predictions.append({
                'success_prob': float(prob),
                'confidence': confidence,
                'reasoning': reasoning
            })
        
        return predictions
    
    def _calculate_confidence(self, prob: float) -> float:
        """Вычисляет уверенность предсказания"""
        # Уверенность выше, когда вероятность близка к 0 или 1
        return float(2 * abs(prob - 0.5))
    
    def _generate_reasoning(self, task: Task, prob: float, student_data: Dict) -> str:
        """Генерирует объяснение рекомендации"""
        reasoning_parts = []
        
        # Анализ вероятности успеха
        if prob > 0.8:
            reasoning_parts.append("Высокая вероятность успешного выполнения")
        elif prob > 0.6:
            reasoning_parts.append("Умеренная вероятность успеха")
        elif prob > 0.4:
            reasoning_parts.append("Задание может быть сложным, но выполнимым")
        else:
            reasoning_parts.append("Задание может быть слишком сложным")
        
        # Анализ навыков
        required_skills = list(task.required_skills.all())
        if required_skills:
            skill_names = [skill.name for skill in required_skills]
            reasoning_parts.append(f"Требует навыки: {', '.join(skill_names)}")
        
        # Анализ сложности
        difficulty_desc = {
            'beginner': 'начальный уровень',
            'intermediate': 'средний уровень', 
            'advanced': 'продвинутый уровень'
        }
        
        if task.difficulty in difficulty_desc:
            reasoning_parts.append(f"Сложность: {difficulty_desc[task.difficulty]}")
        
        return ". ".join(reasoning_parts)
    
    def _rank_recommendations(self, recommendations: List[RecommendationResult], 
                            student_id: int) -> List[RecommendationResult]:
        """
        Ранжирует рекомендации по оптимальности
        
        Использует концепцию зоны ближайшего развития:
        - Оптимальные задания имеют вероятность успеха 0.6-0.8
        - Слишком легкие (>0.8) менее приоритетны
        - Слишком сложные (<0.4) менее приоритетны
        """
        
        def calculate_optimality_score(rec: RecommendationResult) -> float:
            prob = rec.predicted_success_prob
            
            # Оптимальная зона: 0.6-0.8
            if 0.6 <= prob <= 0.8:
                # Максимальный балл в середине зоны (0.7)
                return 1.0 - abs(prob - 0.7) * 2
            elif prob > 0.8:
                # Слишком легко, но лучше чем слишком сложно
                return 0.3 + (1.0 - prob) * 0.5
            else:
                # Слишком сложно
                return prob * 0.5
        
        # Добавляем оценку оптимальности
        for rec in recommendations:
            rec.optimality_score = calculate_optimality_score(rec)
        
        # Сортируем по оптимальности, затем по уверенности
        recommendations.sort(
            key=lambda x: (x.optimality_score, x.confidence), 
            reverse=True
        )
        
        return recommendations
    
    def explain_recommendation(self, student_id: int, task_id: int) -> Dict:
        """
        Объясняет, почему конкретное задание рекомендовано студенту
        
        Returns:
            Подробное объяснение с анализом навыков и предсказанием
        """
        try:
            # Получаем данные
            student_data = self.processor.get_student_data(student_id, task_id)
            task = Task.objects.get(id=task_id)
            
            # Получаем предсказание
            model_batch = self.processor.prepare_batch([student_data])
            model_batch = {k: v.to(self.device) if isinstance(v, torch.Tensor) else v 
                          for k, v in model_batch.items()}
            
            with torch.no_grad():
                success_prob = float(self.model(model_batch)[0])
            
            # Анализируем навыки студента
            skill_analysis = self._analyze_student_skills(student_id, task)
            
            return {
                'task_title': task.title,
                'predicted_success': success_prob,
                'difficulty': task.difficulty,
                'required_skills': [s.name for s in task.required_skills.all()],
                'skill_analysis': skill_analysis,
                'recommendation_type': self._get_recommendation_type(success_prob),
                'learning_benefit': self._estimate_learning_benefit(success_prob)
            }
            
        except Exception as e:
            logger.error(f"Ошибка при объяснении рекомендации: {e}")
            return {'error': str(e)}
    
    def _analyze_student_skills(self, student_id: int, task: Task) -> Dict:
        """Анализирует навыки студента относительно задания"""
        try:
            student = User.objects.get(id=student_id)
            student_profile = StudentProfile.objects.get(user=student)
            
            skill_analysis = {}
            
            for skill in task.required_skills.all():
                try:
                    mastery = StudentSkillMastery.objects.get(
                        student=student_profile, 
                        skill=skill
                    )
                    skill_analysis[skill.name] = {
                        'mastery_level': mastery.mastery_probability,
                        'status': 'developing' if mastery.mastery_probability < 0.7 else 'mastered'
                    }
                except StudentSkillMastery.DoesNotExist:
                    skill_analysis[skill.name] = {
                        'mastery_level': 0.1,
                        'status': 'not_started'
                    }
            
            return skill_analysis
            
        except Exception as e:
            logger.error(f"Ошибка анализа навыков: {e}")
            return {}
    
    def _get_recommendation_type(self, prob: float) -> str:
        """Определяет тип рекомендации на основе вероятности"""
        if prob > 0.8:
            return 'practice'  # Для закрепления
        elif prob > 0.6:
            return 'challenge'  # Оптимальная сложность  
        elif prob > 0.4:
            return 'stretch'  # Сложное, но достижимое
        else:
            return 'preparation_needed'  # Нужна подготовка
    
    def _estimate_learning_benefit(self, prob: float) -> str:
        """Оценивает пользу для обучения"""
        if 0.6 <= prob <= 0.8:
            return 'high'  # Зона ближайшего развития
        elif prob > 0.8:
            return 'low'   # Слишком легко
        elif prob > 0.4:
            return 'medium'  # Может быть полезно с поддержкой
        else:
            return 'low'   # Слишком сложно


def get_next_task_recommendation(student_id: int, 
                               course_id: Optional[int] = None,
                               model_path: str = 'models/dkn_model.pth') -> Optional[RecommendationResult]:
    """
    Быстрая функция для получения одной рекомендации задания
    
    Args:
        student_id: ID студента
        course_id: ID курса (опционально, для фильтрации заданий)
        model_path: Путь к модели DKN
        
    Returns:
        Одна лучшая рекомендация или None
    """
    try:
        recommender = DKNRecommender(model_path)
        recommendations = recommender.get_recommendations(student_id, num_recommendations=1)
        
        return recommendations[0] if recommendations else None
        
    except Exception as e:
        logger.error(f"Ошибка при получении рекомендации: {e}")
        return None
