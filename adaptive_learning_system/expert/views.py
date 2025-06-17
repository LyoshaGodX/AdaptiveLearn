from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Prefetch, Max
from django.utils import timezone
from datetime import timedelta
import json

from .decorators import expert_required
from mlmodels.models import (
    DQNRecommendation, TaskAttempt, ExpertFeedback, 
    StudentSkillMastery, StudentCurrentRecommendation
)
from student.models import StudentProfile
from skills.models import Skill
from methodist.models import Task


@login_required
@expert_required
def index(request):
    """Главная страница эксперта - перенаправляем на управление DQN"""
    return dqn_management(request)


@login_required
@expert_required
def dqn_management(request):
    """Главная страница управления DQN"""
    # Получаем статистику
    total_recommendations = DQNRecommendation.objects.count()
    active_students = StudentProfile.objects.filter(
        task_attempts__completed_at__gte=timezone.now() - timedelta(days=7)
    ).distinct().count()
    
    # Получаем студентов с последними попытками, отсортированных по времени последней попытки
    students_with_attempts = StudentProfile.objects.annotate(
        last_attempt_time=Max('task_attempts__completed_at'),
        attempts_count=Count('task_attempts'),
        recommendations_count=Count('dqn_recommendations')
    ).filter(
        last_attempt_time__isnull=False
    ).order_by('-last_attempt_time')[:50]  # Показываем топ 50
    
    context = {
        'total_recommendations': total_recommendations,
        'active_students': active_students,
        'students_with_attempts': students_with_attempts,
        'feedback_count': ExpertFeedback.objects.count(),
        'unused_feedback_count': ExpertFeedback.objects.filter(is_used_for_training=False).count(),
    }
    
    return render(request, 'expert/dqn_management.html', context)


@login_required
@expert_required
def dqn_student_detail(request, student_id):
    """Детальная страница студента с рекомендациями и попытками"""
    student = get_object_or_404(StudentProfile, id=student_id)
    
    # Получаем скользящее окно из 20 связок рекомендация-попытка
    recommendations_with_attempts = DQNRecommendation.objects.filter(
        student=student,
        attempt__isnull=False  # Только те рекомендации, по которым была попытка
    ).select_related(
        'task', 'attempt', 'attempt__task'
    ).prefetch_related(
        'task__skills',
        'expert_feedback'
    ).order_by('-created_at')[:20]
    
    # Подготавливаем данные для каждой связки
    recommendation_pairs = []
    for rec in recommendations_with_attempts:        # Получаем информацию о навыках
        prerequisite_skills = []
        dependent_skills = []
        
        if rec.prerequisite_skills_snapshot:
            for skill_data in rec.prerequisite_skills_snapshot:
                try:
                    skill = Skill.objects.get(id=skill_data['skill_id'])
                    prerequisite_skills.append({
                        'skill': skill,
                        'mastery_level': skill_data.get('mastery_probability', 0.0)
                    })
                except Skill.DoesNotExist:
                    pass
        
        if rec.dependent_skills_snapshot:
            for skill_data in rec.dependent_skills_snapshot:
                try:
                    skill = Skill.objects.get(id=skill_data['skill_id'])
                    dependent_skills.append({
                        'skill': skill,
                        'mastery_level': skill_data.get('mastery_probability', 0.0)
                    })
                except Skill.DoesNotExist:
                    pass
        
        # Проверяем, есть ли уже фидбек от текущего эксперта
        existing_feedback = rec.expert_feedback.filter(expert=request.user).first()
        
        recommendation_pairs.append({
            'recommendation': rec,
            'attempt': rec.attempt,
            'prerequisite_skills': prerequisite_skills,
            'dependent_skills': dependent_skills,
            'target_skill': rec.task.skills.first() if rec.task.skills.exists() else None,
            'existing_feedback': existing_feedback,
            'has_feedback': existing_feedback is not None
        })
    
    context = {
        'student': student,
        'recommendation_pairs': recommendation_pairs,
        'total_pairs': len(recommendation_pairs),
    }
    
    return render(request, 'expert/dqn_student_detail.html', context)


@login_required
@expert_required
@require_POST
def save_expert_feedback(request):
    """Сохраняет экспертную разметку"""
    try:
        data = json.loads(request.body)
        recommendation_id = data.get('recommendation_id')
        feedback_type = data.get('feedback_type')  # 'positive' or 'negative'
        strength = data.get('strength')  # 'low', 'medium', 'high'
        comment = data.get('comment', '')
        
        recommendation = get_object_or_404(DQNRecommendation, id=recommendation_id)
        
        # Создаем или обновляем фидбек
        feedback, created = ExpertFeedback.objects.update_or_create(
            recommendation=recommendation,
            expert=request.user,
            defaults={
                'feedback_type': feedback_type,
                'strength': strength,
                'comment': comment,
                'is_used_for_training': False  # Сбрасываем флаг при обновлении
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Разметка сохранена успешно',
            'feedback_id': feedback.id,
            'reward_value': feedback.reward_value
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Ошибка сохранения: {str(e)}'
        }, status=400)


@login_required
@expert_required
def view_feedback_dataset(request):
    """Просмотр размеченного датасета для fine-tune"""
    feedbacks = ExpertFeedback.objects.select_related(
        'recommendation__student__user',
        'recommendation__task',
        'recommendation__attempt',
        'expert'
    ).prefetch_related(
        'recommendation__task__skills'
    ).order_by('-created_at')
    
    # Статистика датасета
    total_feedback = feedbacks.count()
    positive_feedback = feedbacks.filter(feedback_type='positive').count()
    negative_feedback = feedbacks.filter(feedback_type='negative').count()
    unused_feedback = feedbacks.filter(is_used_for_training=False).count()
    
    # Группировка по силе
    strength_stats = feedbacks.values('strength', 'feedback_type').annotate(
        count=Count('id')
    ).order_by('strength', 'feedback_type')
    
    context = {
        'feedbacks': feedbacks[:100],  # Показываем последние 100 записей
        'total_feedback': total_feedback,
        'positive_feedback': positive_feedback,
        'negative_feedback': negative_feedback,
        'unused_feedback': unused_feedback,
        'strength_stats': strength_stats,
    }
    
    return render(request, 'expert/dqn_feedback_dataset.html', context)


# Заглушки для BKT и LLM (будут реализованы позже)
@login_required
@expert_required
def bkt_management(request):
    """Заглушка для управления BKT"""
    return render(request, 'expert/bkt_management.html', {
        'page_title': 'Управление BKT',
        'message': 'Страница управления BKT будет реализована позже.'
    })


@login_required
@expert_required
def llm_management(request):
    """Заглушка для управления LLM"""
    return render(request, 'expert/llm_management.html', {
        'page_title': 'Управление LLM',
        'message': 'Страница управления LLM будет реализована позже.'
    })
