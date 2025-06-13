"""
Django сервис для интеграции BKT-интерфейса оценки студен            # Конвертируем в AttemptData
            attempt_data_list = []
            for attempt in attempts_query:
                try:
                    attempt_data = create_attempt_data_from_django(
                        student_profile=student_profile,
                        task=attempt.task,
                        is_correct=attempt.is_correct,
                        answer_score=1.0 if attempt.is_correct else 0.0,
                        timestamp=attempt.completed_at,
                        attempt_number=1
                    )
                    attempt_data_list.append(attempt_data)
                except ValueError as e:
                    logger.warning(f"Пропущена попытка {attempt.id}: {e}")
                    continueадаптивного обучения
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from django.db import transaction
from django.core.cache import cache
from django.conf import settings
import logging

# Local imports
from mlmodels.interfaces.student_assessment_interface import (
    StudentAssessmentInterface, AttemptData, SkillAssessment, 
    CourseAssessment, StudentCharacteristics, create_attempt_data_from_django
)
from mlmodels.models import TaskAttempt
from student.models import StudentProfile
from methodist.models import Task, Course
from skills.models import Skill

logger = logging.getLogger(__name__)

class StudentAssessmentService:
    """Django сервис для работы с оценкой характеристик студентов"""
    
    def __init__(self):
        """Инициализация сервиса"""
        self.assessment_interface = StudentAssessmentInterface()
        
    def assess_student_from_attempts_history(
        self, 
        student_id: int, 
        reset_state: bool = False,
        days_back: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Оценить студента на основе истории попыток из базы данных
        
        Args:
            student_id: ID студента
            reset_state: Сбросить предыдущее состояние
            days_back: Количество дней назад для анализа (None = вся история)
            
        Returns:
            Dict: Результаты оценки
        """
        try:            # Получаем профиль студента
            student_profile = StudentProfile.objects.get(id=student_id)              # Получаем попытки из базы данных
            attempts_query = TaskAttempt.objects.filter(
                student=student_profile
            ).select_related('task').prefetch_related('task__skills', 'task__courses')
            
            # Фильтруем по времени если нужно
            if days_back:
                cutoff_date = datetime.now() - timedelta(days=days_back)
                attempts_query = attempts_query.filter(completed_at__gte=cutoff_date)
            
            attempts_query = attempts_query.order_by('completed_at')
            
            # Конвертируем в AttemptData
            attempt_data_list = []
            for attempt in attempts_query:
                try:
                    attempt_data = create_attempt_data_from_django(
                        student_profile=student_profile,
                        task=attempt.task,
                        is_correct=attempt.is_correct,
                        answer_score=1.0 if attempt.is_correct else 0.0,
                        timestamp=attempt.completed_at,
                        attempt_number=1
                    )
                    attempt_data_list.append(attempt_data)
                except ValueError as e:
                    logger.warning(f"Пропущена попытка {attempt.id}: {e}")
                    continue
            
            if not attempt_data_list:
                return {
                    'error': 'Нет данных о попытках для анализа',
                    'student_id': student_id
                }
            
            # Выполняем оценку
            results = self.assessment_interface.process_attempt_history(
                student_id=student_id,
                attempts=attempt_data_list,
                reset_state=reset_state
            )
              # Сохраняем результаты в базу данных
            self._save_assessment_results(student_id, results)
            
            return results
            
        except StudentProfile.DoesNotExist:
            return {
                'error': f'Студент с ID {student_id} не найден',
                'student_id': student_id
            }
        except Exception as e:
            logger.error(f"Ошибка оценки студента {student_id}: {e}")
            return {
                'error': str(e),
                'student_id': student_id
            }
    
    def process_new_attempt(
        self, 
        student_id: int, 
        task_id: int, 
        is_correct: bool,
        answer_score: Optional[float] = None,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Обработать новую попытку студента и обновить оценки
        
        Args:
            student_id: ID студента
            task_id: ID задания
            is_correct: Правильность ответа
            answer_score: Оценка ответа (если None, то 1.0/0.0 на основе is_correct)
            timestamp: Время попытки (если None, то текущее время)
            
        Returns:
            Dict: Обновленные оценки
        """
        try:
            if answer_score is None:
                answer_score = 1.0 if is_correct else 0.0
                
            if timestamp is None:
                timestamp = datetime.now()
            
            # Получаем объекты из базы данных
            student_profile = StudentProfile.objects.get(user_id=student_id)
            task = Task.objects.get(id=task_id)
            
            # Создаем данные попытки
            attempt_data = create_attempt_data_from_django(
                student_profile=student_profile,
                task=task,
                is_correct=is_correct,
                answer_score=answer_score,
                timestamp=timestamp
            )
            
            # Обновляем оценку навыка
            skill_assessment = self.assessment_interface.update_single_attempt(
                student_id=student_id,
                attempt=attempt_data
            )
            
            # Обновляем кэшированные результаты
            cached_assessment = self.assessment_interface.get_student_assessment(student_id)
            if cached_assessment:
                cached_assessment['skills'][attempt_data.skill_id] = skill_assessment
                cached_assessment['last_updated'] = datetime.now()
                self.assessment_interface._cache_assessment_results(student_id, cached_assessment)
            
            return {
                'success': True,
                'student_id': student_id,
                'skill_assessment': skill_assessment,
                'updated_mastery': skill_assessment.current_mastery
            }
            
        except (StudentProfile.DoesNotExist, Task.DoesNotExist) as e:
            return {
                'error': f'Объект не найден: {e}',
                'student_id': student_id
            }
        except Exception as e:
            logger.error(f"Ошибка обработки попытки: {e}")
            return {
                'error': str(e),
                'student_id': student_id
            }
    
    def get_student_progress_summary(self, student_id: int) -> Dict[str, Any]:
        """
        Получить сводку прогресса студента
        
        Args:
            student_id: ID студента
            
        Returns:
            Dict: Сводка прогресса
        """
        assessment = self.assessment_interface.get_student_assessment(student_id)
        
        if not assessment:
            # Попытаемся сгенерировать оценку
            assessment = self.assess_student_from_attempts_history(student_id)
            if 'error' in assessment:
                return assessment
        
        # Формируем краткую сводку
        skills = assessment.get('skills', {})
        courses = assessment.get('courses', {})
        characteristics = assessment.get('characteristics')
        
        summary = {
            'student_id': student_id,
            'last_updated': assessment.get('last_updated'),
            'overall_performance': characteristics.overall_performance if characteristics else 0.0,
            'learning_rate': characteristics.learning_rate if characteristics else 0.5,
            'total_skills': len(skills),
            'mastered_skills': len([s for s in skills.values() if s.current_mastery >= 0.8]),
            'skills_in_progress': len([s for s in skills.values() if 0.3 <= s.current_mastery < 0.8]),
            'struggling_skills': len([s for s in skills.values() if s.current_mastery < 0.3]),
            'enrolled_courses': len(courses),
            'completed_courses': len([c for c in courses.values() if c.progress_percentage >= 95]),
            'recommended_difficulty': characteristics.recommended_difficulty if characteristics else 'medium',
            'study_time_estimate': characteristics.study_time_estimate if characteristics else 5
        }
        
        return summary
    
    def get_skill_progress_details(self, student_id: int, skill_id: int) -> Dict[str, Any]:
        """
        Получить детали прогресса по конкретному навыку
        
        Args:
            student_id: ID студента
            skill_id: ID навыка
            
        Returns:
            Dict: Детали прогресса по навыку
        """
        assessment = self.assessment_interface.get_student_assessment(student_id)
        
        if not assessment or skill_id not in assessment.get('skills', {}):
            return {
                'error': f'Нет данных по навыку {skill_id} для студента {student_id}',
                'student_id': student_id,
                'skill_id': skill_id
            }
        
        skill_assessment = assessment['skills'][skill_id]
        
        # Получаем прогноз улучшения
        predictions = self.assessment_interface.predict_skill_mastery(
            student_id=student_id,
            skill_id=skill_id,
            future_attempts=10
        )
        
        return {
            'student_id': student_id,
            'skill_id': skill_id,
            'skill_name': skill_assessment.skill_name,
            'current_mastery': skill_assessment.current_mastery,
            'attempts_count': skill_assessment.attempts_count,
            'accuracy': skill_assessment.accuracy,
            'confidence_level': skill_assessment.confidence_level,
            'last_updated': skill_assessment.last_updated,
            'mastery_predictions': predictions,
            'recommendations': self._get_skill_recommendations(skill_assessment)
        }
    
    def get_course_progress_details(self, student_id: int, course_id: int) -> Dict[str, Any]:
        """
        Получить детали прогресса по курсу
        
        Args:
            student_id: ID студента
            course_id: ID курса
            
        Returns:
            Dict: Детали прогресса по курсу
        """
        assessment = self.assessment_interface.get_student_assessment(student_id)
        
        if not assessment or course_id not in assessment.get('courses', {}):
            return {
                'error': f'Нет данных по курсу {course_id} для студента {student_id}',
                'student_id': student_id,
                'course_id': course_id
            }
        
        course_assessment = assessment['courses'][course_id]
        
        # Детализируем прогресс по навыкам курса
        skills_details = []
        for skill_id, mastery in course_assessment.skills_mastery.items():
            skill_info = assessment['skills'].get(skill_id)
            skills_details.append({
                'skill_id': skill_id,
                'skill_name': skill_info.skill_name if skill_info else f'Навык {skill_id}',
                'mastery': mastery,
                'status': 'mastered' if mastery >= 0.8 else 'in_progress' if mastery >= 0.3 else 'struggling'
            })
        
        skills_details.sort(key=lambda x: x['mastery'], reverse=True)
        
        return {
            'student_id': student_id,
            'course_id': course_id,
            'course_name': course_assessment.course_name,
            'overall_mastery': course_assessment.overall_mastery,
            'progress_percentage': course_assessment.progress_percentage,
            'completed_skills': course_assessment.completed_skills,
            'total_skills': course_assessment.total_skills,
            'difficulty_trend': course_assessment.difficulty_trend,
            'estimated_completion': course_assessment.estimated_completion,
            'skills_details': skills_details
        }
    
    def get_learning_recommendations(self, student_id: int) -> Dict[str, Any]:
        """
        Получить рекомендации по обучению для студента
        
        Args:
            student_id: ID студента
            
        Returns:
            Dict: Рекомендации по обучению
        """
        return self.assessment_interface.get_learning_recommendations(student_id)
    
    def bulk_assess_students(self, student_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """
        Массовая оценка группы студентов
        
        Args:
            student_ids: Список ID студентов
            
        Returns:
            Dict: Результаты оценки для каждого студента
        """
        results = {}
        
        for student_id in student_ids:
            try:
                results[student_id] = self.assess_student_from_attempts_history(student_id)
            except Exception as e:
                results[student_id] = {
                    'error': str(e),
                    'student_id': student_id
                }
                logger.error(f"Ошибка оценки студента {student_id}: {e}")
        
        return results
    
    def get_class_analytics(self, student_ids: List[int]) -> Dict[str, Any]:
        """
        Получить аналитику по группе студентов
        
        Args:
            student_ids: Список ID студентов
            
        Returns:
            Dict: Аналитика по группе
        """
        assessments = []
        
        for student_id in student_ids:
            assessment = self.assessment_interface.get_student_assessment(student_id)
            if assessment and 'characteristics' in assessment:
                assessments.append(assessment)
        
        if not assessments:
            return {'error': 'Нет данных для анализа группы'}
        
        # Вычисляем статистики группы
        performance_scores = [a['characteristics'].overall_performance for a in assessments]
        learning_rates = [a['characteristics'].learning_rate for a in assessments]
        
        avg_performance = sum(performance_scores) / len(performance_scores)
        avg_learning_rate = sum(learning_rates) / len(learning_rates)
        
        # Находим лучших и отстающих студентов
        student_performances = [
            (a['student_id'], a['characteristics'].overall_performance) 
            for a in assessments
        ]
        student_performances.sort(key=lambda x: x[1], reverse=True)
        
        top_students = student_performances[:3]
        struggling_students = student_performances[-3:]
        
        return {
            'total_students': len(assessments),
            'average_performance': avg_performance,
            'average_learning_rate': avg_learning_rate,
            'top_students': [{'student_id': sid, 'performance': perf} for sid, perf in top_students],
            'struggling_students': [{'student_id': sid, 'performance': perf} for sid, perf in struggling_students],
            'performance_distribution': {
                'excellent': len([p for p in performance_scores if p >= 0.8]),
                'good': len([p for p in performance_scores if 0.6 <= p < 0.8]),
                'average': len([p for p in performance_scores if 0.4 <= p < 0.6]),
                'needs_help': len([p for p in performance_scores if p < 0.4])
            }
        }
    
    def _save_assessment_results(self, student_id: int, results: Dict[str, Any]):
        """Сохранить результаты оценки в базу данных (опционально)"""
        # Здесь можно реализовать сохранение результатов в специальные таблицы
        # Пока используем только кэширование
        pass
    
    def _get_skill_recommendations(self, skill_assessment: SkillAssessment) -> List[str]:
        """Получить рекомендации по улучшению навыка"""
        recommendations = []
        
        if skill_assessment.current_mastery < 0.3:
            recommendations.append("Начните с базовых упражнений")
            recommendations.append("Изучите теоретический материал")
        elif skill_assessment.current_mastery < 0.6:
            recommendations.append("Выполните дополнительные практические задания")
            recommendations.append("Обратитесь за помощью к преподавателю")
        elif skill_assessment.current_mastery < 0.8:
            recommendations.append("Попробуйте более сложные задания")
            recommendations.append("Изучите продвинутые аспекты темы")
        else:
            recommendations.append("Помогите другим студентам")
            recommendations.append("Изучите связанные продвинутые темы")
        
        if skill_assessment.confidence_level == 'low':
            recommendations.append("Решите больше заданий для повышения уверенности")
        
        return recommendations


# Глобальный экземпляр сервиса
student_assessment_service = StudentAssessmentService()


# Функции-shortcuts для упрощения использования
def assess_student(student_id: int, reset_state: bool = False) -> Dict[str, Any]:
    """Быстрая оценка студента"""
    return student_assessment_service.assess_student_from_attempts_history(
        student_id=student_id, 
        reset_state=reset_state
    )

def process_attempt(student_id: int, task_id: int, is_correct: bool, answer_score: Optional[float] = None) -> Dict[str, Any]:
    """Быстрая обработка попытки"""
    return student_assessment_service.process_new_attempt(
        student_id=student_id,
        task_id=task_id,
        is_correct=is_correct,
        answer_score=answer_score
    )

def get_progress_summary(student_id: int) -> Dict[str, Any]:
    """Быстрое получение сводки прогресса"""
    return student_assessment_service.get_student_progress_summary(student_id)

def get_recommendations(student_id: int) -> Dict[str, Any]:
    """Быстрое получение рекомендаций"""
    return student_assessment_service.get_learning_recommendations(student_id)
