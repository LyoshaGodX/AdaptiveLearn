"""
Django views для работы с интерфейсом оценки студентов
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.decorators import login_required
import json
from datetime import datetime
import logging

from mlmodels.services.student_assessment_service import (
    student_assessment_service,
    assess_student,
    process_attempt,
    get_progress_summary,
    get_recommendations
)

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class StudentAssessmentView(View):
    """View для работы с оценкой студентов"""
    
    def get(self, request, student_id):
        """Получить оценку студента"""
        try:
            # Параметры запроса
            reset_state = request.GET.get('reset', 'false').lower() == 'true'
            days_back = request.GET.get('days_back')
            if days_back:
                days_back = int(days_back)
            
            # Получаем оценку
            result = student_assessment_service.assess_student_from_attempts_history(
                student_id=int(student_id),
                reset_state=reset_state,
                days_back=days_back
            )
            
            return JsonResponse(result, safe=False)
            
        except ValueError as e:
            return JsonResponse({'error': f'Неверные параметры: {e}'}, status=400)
        except Exception as e:
            logger.error(f"Ошибка получения оценки студента {student_id}: {e}")
            return JsonResponse({'error': 'Внутренняя ошибка сервера'}, status=500)
    
    def post(self, request, student_id):
        """Обработать новую попытку студента"""
        try:
            data = json.loads(request.body)
            
            # Обязательные параметры
            task_id = data['task_id']
            is_correct = data['is_correct']
            
            # Опциональные параметры
            answer_score = data.get('answer_score')
            timestamp = data.get('timestamp')
            if timestamp:
                timestamp = datetime.fromisoformat(timestamp)
            
            # Обрабатываем попытку
            result = student_assessment_service.process_new_attempt(
                student_id=int(student_id),
                task_id=int(task_id),
                is_correct=bool(is_correct),
                answer_score=answer_score,
                timestamp=timestamp
            )
            
            return JsonResponse(result)
            
        except KeyError as e:
            return JsonResponse({'error': f'Отсутствует обязательный параметр: {e}'}, status=400)
        except ValueError as e:
            return JsonResponse({'error': f'Неверные параметры: {e}'}, status=400)
        except Exception as e:
            logger.error(f"Ошибка обработки попытки студента {student_id}: {e}")
            return JsonResponse({'error': 'Внутренняя ошибка сервера'}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class StudentProgressView(View):
    """View для получения прогресса студента"""
    
    def get(self, request, student_id):
        """Получить сводку прогресса студента"""
        try:
            result = student_assessment_service.get_student_progress_summary(int(student_id))
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"Ошибка получения прогресса студента {student_id}: {e}")
            return JsonResponse({'error': 'Внутренняя ошибка сервера'}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class SkillProgressView(View):
    """View для получения прогресса по навыку"""
    
    def get(self, request, student_id, skill_id):
        """Получить детали прогресса по навыку"""
        try:
            result = student_assessment_service.get_skill_progress_details(
                int(student_id), int(skill_id)
            )
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"Ошибка получения прогресса по навыку {skill_id} студента {student_id}: {e}")
            return JsonResponse({'error': 'Внутренняя ошибка сервера'}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class CourseProgressView(View):
    """View для получения прогресса по курсу"""
    
    def get(self, request, student_id, course_id):
        """Получить детали прогресса по курсу"""
        try:
            result = student_assessment_service.get_course_progress_details(
                int(student_id), int(course_id)
            )
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"Ошибка получения прогресса по курсу {course_id} студента {student_id}: {e}")
            return JsonResponse({'error': 'Внутренняя ошибка сервера'}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class LearningRecommendationsView(View):
    """View для получения рекомендаций по обучению"""
    
    def get(self, request, student_id):
        """Получить рекомендации по обучению"""
        try:
            result = student_assessment_service.get_learning_recommendations(int(student_id))
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"Ошибка получения рекомендаций для студента {student_id}: {e}")
            return JsonResponse({'error': 'Внутренняя ошибка сервера'}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class BulkStudentAssessmentView(View):
    """View для массовой оценки студентов"""
    
    def post(self, request):
        """Массовая оценка группы студентов"""
        try:
            data = json.loads(request.body)
            student_ids = data['student_ids']
            
            if not isinstance(student_ids, list):
                return JsonResponse({'error': 'student_ids должен быть списком'}, status=400)
            
            result = student_assessment_service.bulk_assess_students(student_ids)
            return JsonResponse(result)
            
        except KeyError:
            return JsonResponse({'error': 'Отсутствует параметр student_ids'}, status=400)
        except Exception as e:
            logger.error(f"Ошибка массовой оценки студентов: {e}")
            return JsonResponse({'error': 'Внутренняя ошибка сервера'}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class ClassAnalyticsView(View):
    """View для аналитики по группе студентов"""
    
    def post(self, request):
        """Получить аналитику по группе студентов"""
        try:
            data = json.loads(request.body)
            student_ids = data['student_ids']
            
            if not isinstance(student_ids, list):
                return JsonResponse({'error': 'student_ids должен быть списком'}, status=400)
            
            result = student_assessment_service.get_class_analytics(student_ids)
            return JsonResponse(result)
            
        except KeyError:
            return JsonResponse({'error': 'Отсутствует параметр student_ids'}, status=400)
        except Exception as e:
            logger.error(f"Ошибка получения аналитики группы: {e}")
            return JsonResponse({'error': 'Внутренняя ошибка сервера'}, status=500)

# Функциональные views для упрощения использования
@csrf_exempt
@require_http_methods(["GET"])
@login_required
def quick_assessment(request, student_id):
    """Быстрая оценка студента"""
    try:
        reset = request.GET.get('reset', 'false').lower() == 'true'
        result = assess_student(int(student_id), reset_state=reset)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def quick_attempt_process(request):
    """Быстрая обработка попытки"""
    try:
        data = json.loads(request.body)
        result = process_attempt(
            student_id=int(data['student_id']),
            task_id=int(data['task_id']),
            is_correct=bool(data['is_correct']),
            answer_score=data.get('answer_score')
        )
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
@login_required
def quick_progress(request, student_id):
    """Быстрое получение прогресса"""
    try:
        result = get_progress_summary(int(student_id))
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
@login_required
def quick_recommendations(request, student_id):
    """Быстрое получение рекомендаций"""
    try:
        result = get_recommendations(int(student_id))
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
