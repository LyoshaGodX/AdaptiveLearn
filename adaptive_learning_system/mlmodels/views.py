from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
import json
from typing import Dict, List, Any, Optional

from student.models import StudentProfile, StudentTaskAttempt
from skills.models import Skill, Course
from methodist.models import Task
from .models import StudentSkillMastery, BKTModelState
from .bkt.base_model import BKTModel, BKTParameters, TaskCharacteristics


class MLModelsAPI:
    """
    Программный интерфейс для работы с BKT моделью и данными студентов
    """
    
    def __init__(self):
        self.bkt_model = BKTModel()
        self._load_optimized_parameters()
    
    def _load_optimized_parameters(self):
        """Загрузить оптимизированные параметры модели если они существуют"""
        try:
            import os
            optimized_model_path = os.path.join(
                os.path.dirname(__file__), 
                'bkt', 
                'optimized_bkt_model', 
                'bkt_model_optimized.json'
            )
            
            if os.path.exists(optimized_model_path):
                self.bkt_model.load_model(optimized_model_path)
                print(f"✅ Загружены оптимизированные параметры BKT модели")
            else:
                print("⚠️ Оптимизированные параметры не найдены, используются параметры по умолчанию")
                
        except Exception as e:
            print(f"❌ Ошибка загрузки оптимизированных параметров: {e}")
    
    def get_student_by_id(self, student_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить студента по ID из базы данных Django
        
        Args:
            student_id: ID студента
            
        Returns:
            Dict с информацией о студенте или None если не найден
        """
        try:
            student_profile = StudentProfile.objects.select_related('user').get(pk=student_id)
            
            return {
                'id': student_profile.id,
                'user_id': student_profile.user.id,
                'username': student_profile.user.username,
                'first_name': student_profile.user.first_name,
                'last_name': student_profile.user.last_name,
                'email': student_profile.user.email,
                'date_joined': student_profile.user.date_joined.isoformat(),
                'learning_style': student_profile.learning_style,
                'skill_level': student_profile.skill_level,
                'created_at': student_profile.created_at.isoformat(),
                'updated_at': student_profile.updated_at.isoformat()
            }
            
        except StudentProfile.DoesNotExist:
            return None
        except Exception as e:
            print(f"Ошибка получения студента {student_id}: {e}")
            return None
    
    def get_student_task_attempts(self, student_id: int) -> List[Dict[str, Any]]:
        """
        Получить все попытки прохождения заданий студентом
        
        Args:
            student_id: ID студента
            
        Returns:
            List попыток с подробной информацией
        """
        try:
            attempts = StudentTaskAttempt.objects.filter(
                student_id=student_id
            ).select_related(
                'task', 
                'task__skill', 
                'task__course'
            ).order_by('-attempted_at')
            
            attempts_data = []
            for attempt in attempts:
                # Определяем характеристики задания
                task_characteristics = TaskCharacteristics(
                    task_type=attempt.task.task_type,
                    difficulty=attempt.task.difficulty_level
                )
                
                attempt_data = {
                    'id': attempt.id,
                    'task_id': attempt.task.id,
                    'task_title': attempt.task.title,
                    'task_type': attempt.task.task_type,
                    'difficulty_level': attempt.task.difficulty_level,
                    'skill_id': attempt.task.skill.id if attempt.task.skill else None,
                    'skill_name': attempt.task.skill.name if attempt.task.skill else None,
                    'course_id': attempt.task.course.id if attempt.task.course else None,
                    'course_name': attempt.task.course.name if attempt.task.course else None,
                    'score': float(attempt.score),
                    'max_score': float(attempt.max_score),
                    'normalized_score': float(attempt.score / attempt.max_score) if attempt.max_score > 0 else 0.0,
                    'is_correct': attempt.is_correct,
                    'time_spent': attempt.time_spent,
                    'attempted_at': attempt.attempted_at.isoformat(),
                    'task_characteristics': {
                        'task_type': task_characteristics.task_type,
                        'difficulty': task_characteristics.difficulty,
                        'guess_probability': task_characteristics.get_guess_probability(),
                        'answer_weight': task_characteristics.get_answer_weight()
                    }
                }
                attempts_data.append(attempt_data)
            
            return attempts_data
            
        except Exception as e:
            print(f"Ошибка получения попыток студента {student_id}: {e}")
            return []
    
    def get_student_skill_masteries(self, student_id: int) -> Dict[int, Dict[str, Any]]:
        """
        Получить все характеристики освоения навыков студентом
        
        Args:
            student_id: ID студента
            
        Returns:
            Dict с информацией об освоении навыков {skill_id: mastery_info}
        """
        try:
            masteries = StudentSkillMastery.objects.filter(
                student_id=student_id
            ).select_related('skill')
            
            skill_masteries = {}
            
            for mastery in masteries:
                # Получаем дополнительную статистику из BKT модели
                bkt_mastery = self.bkt_model.get_student_mastery(student_id, mastery.skill.id)
                student_profile = self.bkt_model.get_student_profile(student_id)
                skill_state = student_profile.get(mastery.skill.id)
                
                mastery_info = {
                    'skill_id': mastery.skill.id,
                    'skill_name': mastery.skill.name,
                    'skill_description': mastery.skill.description,
                    'skill_category': mastery.skill.category,
                    
                    # Параметры из базы данных
                    'db_current_mastery_prob': float(mastery.current_mastery_prob),
                    'db_initial_mastery_prob': float(mastery.initial_mastery_prob),
                    'db_transition_prob': float(mastery.transition_prob),
                    'db_guess_prob': float(mastery.guess_prob),
                    'db_slip_prob': float(mastery.slip_prob),
                    
                    # Параметры из BKT модели
                    'bkt_current_mastery': float(bkt_mastery),
                    'bkt_skill_state': skill_state.to_dict() if skill_state else None,
                    
                    # Статистика
                    'attempts_count': mastery.attempts_count,
                    'correct_attempts': mastery.correct_attempts,
                    'accuracy': float(mastery.correct_attempts / mastery.attempts_count) if mastery.attempts_count > 0 else 0.0,
                    
                    # Временные метки
                    'first_attempt': mastery.first_attempt.isoformat() if mastery.first_attempt else None,
                    'last_attempt': mastery.last_attempt.isoformat() if mastery.last_attempt else None,
                    'created_at': mastery.created_at.isoformat(),
                    'updated_at': mastery.updated_at.isoformat()
                }
                
                skill_masteries[mastery.skill.id] = mastery_info
            
            return skill_masteries
            
        except Exception as e:
            print(f"Ошибка получения освоения навыков студента {student_id}: {e}")
            return {}
    
    def get_student_full_profile(self, student_id: int) -> Dict[str, Any]:
        """
        Получить полный профиль студента со всеми данными
        
        Args:
            student_id: ID студента
            
        Returns:
            Dict с полной информацией о студенте
        """
        student_info = self.get_student_by_id(student_id)
        if not student_info:
            return {'error': f'Студент с ID {student_id} не найден'}
        
        attempts = self.get_student_task_attempts(student_id)
        skill_masteries = self.get_student_skill_masteries(student_id)
        
        # Статистика
        total_attempts = len(attempts)
        correct_attempts = sum(1 for attempt in attempts if attempt['is_correct'])
        
        return {
            'student': student_info,
            'statistics': {
                'total_attempts': total_attempts,
                'correct_attempts': correct_attempts,
                'accuracy': correct_attempts / total_attempts if total_attempts > 0 else 0.0,
                'skills_learned': len(skill_masteries),
                'avg_mastery': sum(m['bkt_current_mastery'] for m in skill_masteries.values()) / len(skill_masteries) if skill_masteries else 0.0
            },
            'attempts': attempts,
            'skill_masteries': skill_masteries,
            'bkt_model_summary': self.bkt_model.get_model_summary()
        }
    
    def update_student_progress(self, student_id: int, task_id: int, score: float, max_score: float) -> Dict[str, Any]:
        """
        Обновить прогресс студента после выполнения задания
        
        Args:
            student_id: ID студента
            task_id: ID задания
            score: Полученный балл
            max_score: Максимальный балл
            
        Returns:
            Dict с результатами обновления
        """
        try:
            # Получаем задание
            task = Task.objects.select_related('skill').get(pk=task_id)
            if not task.skill:
                return {'error': 'Задание не связано с навыком'}
            
            skill_id = task.skill.id
            normalized_score = score / max_score if max_score > 0 else 0.0
            
            # Создаем характеристики задания
            task_characteristics = TaskCharacteristics(
                task_type=task.task_type,
                difficulty=task.difficulty_level
            )
            
            # Обновляем состояние в BKT модели
            updated_state = self.bkt_model.update_student_state(
                student_id=student_id,
                skill_id=skill_id,
                answer_score=normalized_score,
                task_characteristics=task_characteristics
            )
            
            # Обновляем базу данных
            mastery, created = StudentSkillMastery.objects.get_or_create(
                student_id=student_id,
                skill_id=skill_id,
                defaults={
                    'initial_mastery_prob': updated_state.current_mastery,
                    'current_mastery_prob': updated_state.current_mastery
                }
            )
            
            if not created:
                mastery.current_mastery_prob = updated_state.current_mastery
                mastery.attempts_count = updated_state.attempts_count
                mastery.correct_attempts = updated_state.correct_attempts
                mastery.save()
            
            return {
                'success': True,
                'student_id': student_id,
                'skill_id': skill_id,
                'updated_mastery': float(updated_state.current_mastery),
                'attempts_count': updated_state.attempts_count,
                'accuracy': updated_state.accuracy
            }
            
        except Task.DoesNotExist:
            return {'error': f'Задание с ID {task_id} не найдено'}
        except Exception as e:
            return {'error': f'Ошибка обновления прогресса: {str(e)}'}


# Создаем глобальный экземпляр API
ml_api = MLModelsAPI()


# Django Views для HTTP API
@require_http_methods(["GET"])
def get_student_profile(request, student_id):
    """API endpoint для получения профиля студента"""
    try:
        student_id = int(student_id)
        profile = ml_api.get_student_full_profile(student_id)
        return JsonResponse(profile, safe=False)
    except ValueError:
        return JsonResponse({'error': 'Неверный ID студента'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_student_attempts(request, student_id):
    """API endpoint для получения попыток студента"""
    try:
        student_id = int(student_id)
        attempts = ml_api.get_student_task_attempts(student_id)
        return JsonResponse({'attempts': attempts}, safe=False)
    except ValueError:
        return JsonResponse({'error': 'Неверный ID студента'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_student_masteries(request, student_id):
    """API endpoint для получения освоения навыков студентом"""
    try:
        student_id = int(student_id)
        masteries = ml_api.get_student_skill_masteries(student_id)
        return JsonResponse({'masteries': masteries}, safe=False)
    except ValueError:
        return JsonResponse({'error': 'Неверный ID студента'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def update_student_progress(request):
    """API endpoint для обновления прогресса студента"""
    try:
        data = json.loads(request.body)
        
        required_fields = ['student_id', 'task_id', 'score', 'max_score']
        for field in required_fields:
            if field not in data:
                return JsonResponse({'error': f'Отсутствует поле: {field}'}, status=400)
        
        result = ml_api.update_student_progress(
            student_id=int(data['student_id']),
            task_id=int(data['task_id']),
            score=float(data['score']),
            max_score=float(data['max_score'])
        )
        
        if 'error' in result:
            return JsonResponse(result, status=400)
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный JSON'}, status=400)
    except (ValueError, TypeError) as e:
        return JsonResponse({'error': f'Неверные типы данных: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
