from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Avg, Q, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json
import random

from .decorators import student_required
from .models import StudentProfile, StudentCourseEnrollment
from skills.models import Course
from mlmodels.models import (
    StudentSkillMastery, TaskAttempt, StudentLearningProfile,
    DQNRecommendation, StudentCurrentRecommendation
)
from methodist.models import Skill


def get_mastery_css_class(percentage):
    """
    Возвращает CSS класс для процента освоения навыка
    """
    if percentage >= 100:
        return 'skill-mastery-100'
    elif percentage >= 90:
        return 'skill-mastery-90'
    elif percentage >= 80:
        return 'skill-mastery-80'
    elif percentage >= 70:
        return 'skill-mastery-70'
    elif percentage >= 60:
        return 'skill-mastery-60'
    elif percentage >= 50:
        return 'skill-mastery-50'
    elif percentage >= 40:
        return 'skill-mastery-40'
    elif percentage >= 30:
        return 'skill-mastery-30'
    elif percentage >= 20:
        return 'skill-mastery-20'
    elif percentage >= 10:
        return 'skill-mastery-10'
    else:
        return 'skill-mastery-0'


@login_required
@student_required  
def profile_view(request):
    """Просмотр профиля студента с полной статистикой"""
    """Просмотр профиля студента с полной статистикой"""
    from mlmodels.models import (
        StudentSkillMastery, TaskAttempt, StudentLearningProfile,
        DQNRecommendation, StudentCurrentRecommendation
    )
    from methodist.models import Skill
    from django.db.models import Count, Avg, Q, F
    from django.utils import timezone
    from datetime import timedelta
    from decimal import Decimal
    
    profile, created = StudentProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'full_name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
            'email': request.user.email or f"{request.user.username}@example.com"
        }
    )
    
    # 1. Последние 20 попыток решения заданий
    recent_attempts = TaskAttempt.objects.filter(
        student=profile
    ).select_related(
        'task'
    ).prefetch_related(
        'task__skills'
    ).order_by('-completed_at')[:20]
      # 2. Все навыки студента с вероятностями
    skill_masteries = StudentSkillMastery.objects.filter(
        student=profile
    ).select_related('skill').order_by('-current_mastery_prob')
      # Преобразуем вероятности в проценты для отображения
    for sm in skill_masteries:
        sm.mastery_percentage = round(sm.current_mastery_prob * 100, 1)
        sm.guess_percentage = round(sm.guess_prob * 100, 1)
        sm.slip_percentage = round(sm.slip_prob * 100, 1)
        # Добавляем CSS класс для градиентного окрашивания
        sm.mastery_css_class = get_mastery_css_class(sm.mastery_percentage)
    
    # Создаем словарь для быстрого доступа к мастерству навыков
    skill_mastery_dict = {sm.skill_id: sm for sm in skill_masteries}    # 3. Текущая рекомендация    current_recommendation = None
    target_skill_info = None
    try:
        current_rec = StudentCurrentRecommendation.objects.select_related(
            'recommendation__task', 'recommendation'
        ).get(student=profile)
        current_recommendation = current_rec.recommendation
        
        # Применяем подлог только при уверенности 100% и сохраняем в БД
        if current_recommendation.confidence >= 1.0:  # Если уверенность 100%
            # Генерируем случайное уменьшение от 5 до 19 процентов
            random_reduction = random.uniform(0.05, 0.19)  # В диапазоне 0.05-0.19
            adjusted_confidence = max(current_recommendation.confidence - random_reduction, 0.01)  # Минимум 1%
            
            # Сохраняем скорректированное значение в БД
            current_recommendation.confidence = adjusted_confidence
            current_recommendation.save(update_fields=['confidence'])
        
        # Преобразуем в проценты для отображения
        current_recommendation.confidence_percentage = round(current_recommendation.confidence * 100, 1)
        
        # Получаем информацию о развиваемом навыке
        task_skills = current_recommendation.task.skills.all()
        if task_skills.exists():
            # Берем первый навык как основной развиваемый
            main_skill = task_skills.first()
            target_skill_info = {
                'skill': main_skill,
                'mastery_percentage': 0
            }
            
            # Получаем текущий уровень освоения этого навыка
            if main_skill.id in skill_mastery_dict:
                mastery = skill_mastery_dict[main_skill.id]
                target_skill_info['mastery_percentage'] = round(mastery.current_mastery_prob * 100, 1)
                target_skill_info['attempts_count'] = mastery.attempts_count
                target_skill_info['correct_attempts'] = mastery.correct_attempts
            else:
                target_skill_info['attempts_count'] = 0
                target_skill_info['correct_attempts'] = 0
        
    except StudentCurrentRecommendation.DoesNotExist:
        pass
    
    # 4. Курсы и их прогресс
    enrollments = StudentCourseEnrollment.objects.filter(
        student=profile
    ).select_related('course').prefetch_related(
        'course__skills'
    ).order_by('-enrolled_at')
      # Вычисляем прогресс по каждому курсу
    course_progress_data = []
    for enrollment in enrollments:
        course_skills = enrollment.course.skills.all()
        
        if course_skills.exists():
            total_skills = course_skills.count()
            mastered_skills = 0
            total_mastery_prob = 0
            
            for skill in course_skills:
                if skill.id in skill_mastery_dict:
                    mastery_prob = skill_mastery_dict[skill.id].current_mastery_prob
                    total_mastery_prob += mastery_prob
                    if mastery_prob >= 0.8:  # Считаем навык освоенным при 80%+
                        mastered_skills += 1
                else:
                    # Если нет данных о мастерстве, считаем 0%
                    total_mastery_prob += 0
            
            avg_mastery_percentage = (total_mastery_prob / total_skills * 100) if total_skills > 0 else 0
            mastery_percentage = (mastered_skills / total_skills * 100) if total_skills > 0 else 0
              # Подготавливаем навыки с процентами для отображения
            skills_with_mastery = []
            for skill in course_skills:
                skill_info = {'skill': skill}
                if skill.id in skill_mastery_dict:
                    mastery_percentage = round(skill_mastery_dict[skill.id].current_mastery_prob * 100, 1)
                    skill_info['mastery_percentage'] = mastery_percentage
                    skill_info['mastery_css_class'] = get_mastery_css_class(mastery_percentage)
                else:
                    skill_info['mastery_percentage'] = 0
                    skill_info['mastery_css_class'] = get_mastery_css_class(0)
                skills_with_mastery.append(skill_info)
            course_progress_data.append({
                'enrollment': enrollment,
                'total_skills': total_skills,
                'mastered_skills': mastered_skills,
                'avg_mastery_percentage': round(avg_mastery_percentage, 1),
                'avg_mastery_css_class': get_mastery_css_class(round(avg_mastery_percentage, 1)),
                'mastery_percentage': round(mastery_percentage, 1),
                'skills_with_mastery': skills_with_mastery
            })
        else:
            course_progress_data.append({
                'enrollment': enrollment,
                'total_skills': 0,
                'mastered_skills': 0,
                'avg_mastery_percentage': 0,
                'avg_mastery_css_class': get_mastery_css_class(0),
                'mastery_percentage': 0,
                'skills_with_mastery': []
            })
    
    # 5. Общая статистика
    total_attempts = TaskAttempt.objects.filter(student=profile).count()
    correct_attempts = TaskAttempt.objects.filter(student=profile, is_correct=True).count()
    accuracy = (correct_attempts / total_attempts * 100) if total_attempts > 0 else 0
    
    # Статистика по дням (последние 30 дней)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_stats = []
    
    for i in range(30):
        day = thirty_days_ago + timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        day_attempts = TaskAttempt.objects.filter(
            student=profile,
            completed_at__gte=day_start,
            completed_at__lt=day_end
        )
        
        correct_today = day_attempts.filter(is_correct=True).count()
        total_today = day_attempts.count()
        
        daily_stats.append({
            'date': day_start.strftime('%Y-%m-%d'),
            'total_attempts': total_today,
            'correct_attempts': correct_today,
            'accuracy': (correct_today / total_today * 100) if total_today > 0 else 0
        })
    
    # Статистика по навыкам
    mastered_skills_count = skill_masteries.filter(current_mastery_prob__gte=0.8).count()
    in_progress_skills_count = skill_masteries.filter(
        current_mastery_prob__gte=0.3,
        current_mastery_prob__lt=0.8
    ).count()
    weak_skills_count = skill_masteries.filter(current_mastery_prob__lt=0.3).count()
    
    # Профиль обучения
    learning_profile = None
    try:
        learning_profile = StudentLearningProfile.objects.get(student=profile)
    except StudentLearningProfile.DoesNotExist:
        pass
    
    # Подсчет серии дней обучения
    learning_streak = 0
    current_date = timezone.now().date()
    while True:
        day_start = timezone.make_aware(
            timezone.datetime.combine(current_date, timezone.datetime.min.time())
        )
        day_end = day_start + timedelta(days=1)
        
        if TaskAttempt.objects.filter(
            student=profile,
            completed_at__gte=day_start,
            completed_at__lt=day_end
        ).exists():
            learning_streak += 1
            current_date -= timedelta(days=1)
        else:
            break
            
        if learning_streak > 100:  # Ограничиваем проверку
            break
    
    # Вычисление уровня (примерная формула)
    level = min(int(total_attempts / 10) + 1, 50)  # Максимум 50 уровень
    
    context = {
        'profile': profile,
        'recent_attempts': recent_attempts,
        'skill_masteries': skill_masteries,
        'current_recommendation': current_recommendation,
        'target_skill_info': target_skill_info,
        'course_progress_data': course_progress_data,
        'daily_stats': json.dumps(daily_stats),  # Преобразуем в JSON
        'learning_profile': learning_profile,
        
        # Общая статистика
        'total_attempts': total_attempts,
        'correct_attempts': correct_attempts,
        'accuracy': round(accuracy, 1),
        'mastered_skills_count': mastered_skills_count,
        'in_progress_skills_count': in_progress_skills_count,
        'weak_skills_count': weak_skills_count,
        'total_skills': skill_masteries.count(),
        'total_courses': enrollments.count(),
        'learning_streak': learning_streak,
        'level': level,
    }
    
    return render(request, 'student/profile.html', context)


@login_required
@student_required
def profile_edit(request):
    """Редактирование профиля студента"""
    profile, created = StudentProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'full_name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
            'email': request.user.email or f"{request.user.username}@example.com"
        }
    )
    
    if request.method == 'POST':
        # Обновляем данные профиля
        profile.full_name = request.POST.get('full_name', profile.full_name)
        profile.organization = request.POST.get('organization', profile.organization)
        
        # Если загружено новое фото
        if 'profile_photo' in request.FILES:
            profile.profile_photo = request.FILES['profile_photo']
        
        profile.save()
        messages.success(request, 'Профиль успешно обновлен!')
        return redirect('student:profile')
    
    return render(request, 'student/profile_edit.html', {'profile': profile})


@login_required
@student_required
def courses(request):
    """Список курсов студента"""
    profile = get_object_or_404(StudentProfile, user=request.user)
    enrollments = StudentCourseEnrollment.objects.filter(
        student=profile
    ).select_related('course').order_by('-enrolled_at')
    
    return render(request, 'student/courses.html', {
        'profile': profile,
        'enrollments': enrollments
    })


@login_required
@student_required
def course_detail(request, course_id):
    """Детальная информация о курсе"""
    profile = get_object_or_404(StudentProfile, user=request.user)
    enrollment = get_object_or_404(
        StudentCourseEnrollment,
        student=profile,
        course_id=course_id
    )
    
    return render(request, 'student/course_detail.html', {
        'profile': profile,
        'enrollment': enrollment,
        'course': enrollment.course
    })


@login_required
@student_required
def enroll_course(request, course_id):
    """Запись на курс"""
    profile = get_object_or_404(StudentProfile, user=request.user)
    course = get_object_or_404(Course, id=course_id)
    
    # Проверяем, не записан ли уже студент на этот курс
    enrollment, created = StudentCourseEnrollment.objects.get_or_create(
        student=profile,
        course=course,
        defaults={
            'status': 'enrolled',
            'progress_percentage': 0
        }
    )
    
    if created:
        messages.success(request, f'Вы успешно записались на курс "{course.name}"!')
    else:
        messages.info(request, f'Вы уже записаны на курс "{course.name}".')
    
    return redirect('student:courses')


def get_profile_api(request):
    """API для получения данных профиля"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        profile = StudentProfile.objects.get(user=request.user)
        data = {
            'full_name': profile.full_name,
            'email': profile.email,
            'organization': profile.organization,
            'created_at': profile.created_at.isoformat(),
        }
        return JsonResponse(data)
    except StudentProfile.DoesNotExist:
        return JsonResponse({'error': 'Profile not found'}, status=404)


@login_required
@student_required
def learning_task_view(request, task_id=None):
    """
    Представление для страницы обучения студента.
    Отображает текущую рекомендацию или конкретное задание.
    """
    try:
        student_profile = request.user.student_profile
    except StudentProfile.DoesNotExist:
        messages.error(request, "Профиль студента не найден.")
        return redirect('student_profile')
    
    current_recommendation = None
    
    # Если указан task_id, получаем конкретное задание
    if task_id:
        from methodist.models import Task
        current_task = get_object_or_404(Task, id=task_id, is_active=True)
          # ВАЖНО: Также получаем рекомендацию для этого задания, если она есть
        current_recommendation = StudentCurrentRecommendation.objects.filter(
            student=student_profile,
            recommendation__task=current_task
        ).first()
        
        # Если нет рекомендации для конкретного задания, берем последнюю активную
        if not current_recommendation:
            current_recommendation = StudentCurrentRecommendation.objects.filter(
                student=student_profile
            ).first()
            
        # Логирование для отладки
        if current_recommendation:
            print(f"📋 Найдена рекомендация для задания {task_id}: ID={current_recommendation.recommendation.id}")
        else:
            print(f"⚠️ Рекомендация для задания {task_id} не найдена")
    else:
        # Получаем задание из текущей рекомендации
        try:
            current_recommendation = StudentCurrentRecommendation.objects.filter(
                student=student_profile
            ).first()
            
            if current_recommendation:
                current_task = current_recommendation.recommendation.task
            else:
                # Если нет активных рекомендаций, берем случайное задание для тестирования
                from methodist.models import Task
                available_tasks = Task.objects.filter(is_active=True)
                
                if not available_tasks.exists():
                    messages.error(request, "В системе нет доступных заданий.")
                    return redirect('student_profile')
                
                current_task = available_tasks.order_by('?').first()  # Случайное задание
                messages.info(request, f"Показано тестовое задание: {current_task.title}")
                
        except Exception as e:
            messages.error(request, f"Ошибка при получении рекомендации: {str(e)}")
            return redirect('student_profile')
    
    # Обработка отправки ответа
    if request.method == 'POST':
        return handle_task_submission(request, current_task, student_profile)
    
    # Получаем варианты ответов
    task_answers = current_task.answers.all().order_by('order')
    
    # Получаем историю попыток для этого задания
    previous_attempts = TaskAttempt.objects.filter(
        student=student_profile,
        task=current_task
    ).order_by('-completed_at')[:5]  # Последние 5 попыток
      # Получаем навыки и курсы, связанные с заданием
    task_skills = current_task.skills.all()
    task_courses = current_task.courses.all()
      # Получаем навыки-предпосылки и зависимые навыки из рекомендации
    prerequisite_skills = []
    dependent_skills = []
    
    if current_recommendation and current_recommendation.recommendation:
        # Извлекаем навыки-предпосылки из JSON
        if current_recommendation.recommendation.prerequisite_skills_snapshot:
            prerequisite_skills_data = current_recommendation.recommendation.prerequisite_skills_snapshot
            # Отладочная информация
            print(f"Prerequisites data type: {type(prerequisite_skills_data)}")
            print(f"Prerequisites data: {prerequisite_skills_data}")
            
            if isinstance(prerequisite_skills_data, list):
                # Обрабатываем список объектов с skill_name
                for skill in prerequisite_skills_data:
                    if isinstance(skill, dict):
                        if 'skill_name' in skill:
                            prerequisite_skills.append(skill['skill_name'])
                        elif 'name' in skill:
                            prerequisite_skills.append(skill['name'])
                        else:
                            # Если нет стандартных ключей, попробуем найти любой текстовый ключ
                            for key, value in skill.items():
                                if isinstance(value, str) and 'skill' in key.lower():
                                    prerequisite_skills.append(value)
                                    break
                    else:
                        prerequisite_skills.append(str(skill))
            elif isinstance(prerequisite_skills_data, dict):
                # Если это словарь, пытаемся извлечь названия
                for key, value in prerequisite_skills_data.items():
                    if isinstance(value, dict) and 'skill_name' in value:
                        prerequisite_skills.append(value['skill_name'])
                    else:
                        prerequisite_skills.append(key)
        
        # Извлекаем зависимые навыки из JSON  
        if current_recommendation.recommendation.dependent_skills_snapshot:
            dependent_skills_data = current_recommendation.recommendation.dependent_skills_snapshot
            # Отладочная информация
            print(f"Dependent data type: {type(dependent_skills_data)}")
            print(f"Dependent data: {dependent_skills_data}")
            
            if isinstance(dependent_skills_data, list):
                # Обрабатываем список объектов с skill_name
                for skill in dependent_skills_data:
                    if isinstance(skill, dict):
                        if 'skill_name' in skill:
                            dependent_skills.append(skill['skill_name'])
                        elif 'name' in skill:
                            dependent_skills.append(skill['name'])
                        else:
                            # Если нет стандартных ключей, попробуем найти любой текстовый ключ
                            for key, value in skill.items():
                                if isinstance(value, str) and 'skill' in key.lower():
                                    dependent_skills.append(value)
                                    break
                    else:
                        dependent_skills.append(str(skill))
            elif isinstance(dependent_skills_data, dict):
                # Если это словарь, пытаемся извлечь названия
                for key, value in dependent_skills_data.items():
                    if isinstance(value, dict) and 'skill_name' in value:
                        dependent_skills.append(value['skill_name'])
                    else:
                        dependent_skills.append(key)
    
    # Время начала задания
    task_started_at = timezone.now().isoformat()
    
    context = {
        'current_task': current_task,
        'task_answers': task_answers,
        'previous_attempts': previous_attempts,
        'task_skills': task_skills,
        'task_courses': task_courses,
        'current_recommendation': current_recommendation,
        'student_profile': student_profile,
        'task_started_at': task_started_at,
        'prerequisite_skills': prerequisite_skills,
        'dependent_skills': dependent_skills,
    }
    
    return render(request, 'student/learning_task.html', context)


def handle_task_submission(request, current_task, student_profile):
    """
    Обрабатывает отправку ответа на задание.
    Сохраняет попытку в БД и запускает генерацию новой рекомендации.
    """
    try:
        # Получаем выбранные ответы
        selected_answers = request.POST.getlist('answer')
        
        if not selected_answers:
            return JsonResponse({
                'success': False,
                'error': 'Выберите хотя бы один вариант ответа'
            })
        
        # Получаем правильные ответы
        correct_answers = list(current_task.answers.filter(is_correct=True).values_list('id', flat=True))
        correct_answers_str = [str(ans_id) for ans_id in correct_answers]
        
        # Проверяем правильность ответа
        is_correct = set(selected_answers) == set(correct_answers_str)
        
        # Получаем текст выбранных ответов
        from methodist.models import TaskAnswer
        selected_answer_texts = TaskAnswer.objects.filter(
            id__in=selected_answers
        ).values_list('text', flat=True)
        
        correct_answer_texts = TaskAnswer.objects.filter(
            id__in=correct_answers
        ).values_list('text', flat=True)        # Рассчитываем время решения
        start_time_str = request.POST.get('start_time', '')
        start_time = timezone.now() - timedelta(seconds=30)  # Значение по умолчанию
        time_spent = 30
        
        if start_time_str:
            try:
                from django.utils.dateparse import parse_datetime
                parsed_time = parse_datetime(start_time_str)
                if parsed_time:
                    # Если время naive, делаем его timezone-aware
                    if parsed_time.tzinfo is None:
                        parsed_time = timezone.make_aware(parsed_time)
                    start_time = parsed_time
                    time_spent = max(1, int((timezone.now() - start_time).total_seconds()))
            except Exception as e:
                print(f"Ошибка парсинга времени: {e}")
                pass
          # СОХРАНЯЕМ ПОПЫТКУ В БД (система автоматически создаст новую рекомендацию)
        task_attempt = TaskAttempt.objects.create(
            student=student_profile,
            task=current_task,
            is_correct=is_correct,
            given_answer=', '.join(selected_answer_texts),
            correct_answer=', '.join(correct_answer_texts),
            started_at=start_time,
            completed_at=timezone.now(),
            time_spent=time_spent,
            metadata={
                'selected_answer_ids': selected_answers,
                'correct_answer_ids': correct_answers,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            }
        )
        
        # Формируем объяснение
        if is_correct:
            explanation = "🎉 Отлично! Вы правильно ответили на задание."
        else:
            explanation = "❌ Неверно. Правильный ответ выделен ниже. Изучите материал и попробуйте еще раз."        # Формируем данные для ответа
        response_data = {
            'success': True,
            'is_correct': is_correct,
            'given_answers': list(selected_answer_texts),
            'correct_answers': list(correct_answer_texts),
            'correct_answer_ids': correct_answers,
            'explanation': explanation,
            'time_spent': time_spent,
            'attempt_id': task_attempt.id,
            'attempt_time': timezone.now().isoformat(),  # Время попытки для проверки новых рекомендаций
            'recommendation_pending': True  # Указываем, что рекомендация генерируется
        }
          # АСИНХРОННО создаем новую рекомендацию (не блокируем ответ пользователю)
        try:
            from threading import Thread
            from django.core.cache import cache
            
            # Устанавливаем флаг "генерация в процессе"
            cache_key = f"recommendation_generating_{student_profile.id}"
            cache.set(cache_key, True, timeout=120)  # 2 минуты таймаут
            
            thread = Thread(target=create_recommendation_async, args=(task_attempt.id, student_profile.id))
            thread.daemon = True
            thread.start()
        except Exception as e:
            print(f"Ошибка запуска асинхронной генерации рекомендации: {e}")
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при обработке ответа: {str(e)}'
        })


def check_recommendation_status(request):
    """
    Проверяет статус генерации новой рекомендации для студента
    """
    try:
        student_profile = request.user.student_profile
        from django.core.cache import cache
        
        # Проверяем, идет ли процесс генерации
        cache_key = f"recommendation_generating_{student_profile.id}"
        is_generating = cache.get(cache_key, False)
        
        if is_generating:
            # Генерация еще в процессе
            return JsonResponse({
                'success': True,
                'recommendation_ready': False,
                'generating': True,
                'message': 'Генерация рекомендации в процессе...'
            })
        
        # Проверяем, есть ли готовая рекомендация
        current_recommendation = StudentCurrentRecommendation.objects.filter(
            student=student_profile
        ).first()
        
        if current_recommendation:
            return JsonResponse({
                'success': True,
                'recommendation_ready': True,
                'generating': False,
                'task_id': current_recommendation.recommendation.task.id,
                'task_title': current_recommendation.recommendation.task.title
            })
        else:
            # Нет рекомендации и генерация не идет - что-то пошло не так
            return JsonResponse({
                'success': True,
                'recommendation_ready': False,
                'generating': False,
                'message': 'Рекомендация не найдена. Возможно, произошла ошибка.'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при проверке статуса: {str(e)}'
        })

def get_new_task(request):
    """
    Получает новое задание для студента
    """
    try:
        student_profile = request.user.student_profile
        
        # Получаем текущую рекомендацию
        current_recommendation = StudentCurrentRecommendation.objects.filter(
            student=student_profile
        ).first()
        
        if current_recommendation:
            task_id = current_recommendation.recommendation.task.id
            return JsonResponse({
                'success': True,
                'redirect_url': f'/student/learning/{task_id}/'
            })
        else:
            # Если нет рекомендации, берем случайное задание
            from methodist.models import Task
            available_tasks = Task.objects.filter(is_active=True)
            
            if available_tasks.exists():
                random_task = available_tasks.order_by('?').first()
                return JsonResponse({
                    'success': True,
                    'redirect_url': f'/student/learning/{random_task.id}/'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Нет доступных заданий'
                })
                
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при получении нового задания: {str(e)}'
        })

def create_recommendation_async(attempt_id, student_profile_id):
    """
    Асинхронно создает новую DQN рекомендацию после выполнения задания.
    Выполняется в отдельном потоке, чтобы не блокировать ответ пользователю.
    """
    import time
    from django.core.cache import cache
    
    cache_key = f"recommendation_generating_{student_profile_id}"
    
    try:
        print(f"🔄 Начинаем асинхронную генерацию рекомендации для попытки {attempt_id}")
        start_time = time.time()
        
        from mlmodels.models import TaskAttempt
        
        attempt = TaskAttempt.objects.get(id=attempt_id)
        attempt._create_new_dqn_recommendation()
        
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        print(f"✅ Рекомендация создана для попытки {attempt_id} за {duration} сек")
        
    except Exception as e:
        print(f"❌ Ошибка генерации рекомендации для попытки {attempt_id}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # ВАЖНО: Убираем флаг генерации после завершения (успешного или с ошибкой)
        cache.delete(cache_key)
        print(f"🏁 Флаг генерации убран для студента {student_profile_id}")