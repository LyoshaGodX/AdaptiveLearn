from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q, Count
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .decorators import methodist_required
from skills.models import Skill, Course
from .models import Task
import json


@login_required
@methodist_required
def courses_list(request):
    """
    Список всех курсов с возможностью фильтрации и поиска
    """
    search_query = request.GET.get('search', '')
    
    # Базовая выборка курсов с аннотациями для подсчета связанных объектов
    courses = Course.objects.annotate(
        skills_count=Count('skills', distinct=True),
        tasks_count=Count('tasks', distinct=True)
    ).order_by('name')
    
    # Применяем фильтр поиска
    if search_query:
        courses = courses.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    context = {
        'courses': courses,
        'search_query': search_query,
        'total_courses': courses.count(),
    }
    
    return render(request, 'methodist/courses_list.html', context)


@login_required
@methodist_required
def course_create(request):
    """
    Создание нового курса
    """
    if request.method == 'POST':
        return _handle_course_form(request)
    
    # GET запрос - показываем форму
    all_skills = Skill.objects.all().order_by('name')
    all_tasks = Task.objects.filter(is_active=True).order_by('title')
    
    context = {
        'course': None,
        'all_skills': all_skills,
        'all_tasks': all_tasks,
        'is_editing': False,
    }
    
    return render(request, 'methodist/course_form.html', context)


@login_required
@methodist_required
def course_edit(request, course_id):
    """
    Редактирование существующего курса
    """
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        return _handle_course_form(request, course)
    
    # GET запрос - показываем форму с данными курса
    all_skills = Skill.objects.all().order_by('name')
    all_tasks = Task.objects.filter(is_active=True).order_by('title')
    
    # Получаем текущие связи
    current_skills = course.skills.all()
    current_tasks = course.tasks.all()
    
    context = {
        'course': course,
        'all_skills': all_skills,
        'all_tasks': all_tasks,
        'current_skills': current_skills,
        'current_tasks': current_tasks,
        'is_editing': True,
    }
    
    return render(request, 'methodist/course_form.html', context)


@require_POST
@login_required
@methodist_required
def course_delete(request, course_id):
    """
    Удаление курса
    """
    course = get_object_or_404(Course, id=course_id)
    course_name = course.name
    
    # Проверяем, есть ли связанные навыки или задания
    skills_count = course.skills.count()
    tasks_count = course.tasks.count()
    
    if skills_count > 0 or tasks_count > 0:
        messages.warning(
            request, 
            f'Курс "{course_name}" содержит {skills_count} навыков и {tasks_count} заданий. '
            'Сначала удалите все связи или переместите содержимое в другой курс.'
        )
        return redirect('methodist_courses')
    
    course.delete()
    messages.success(request, f'Курс "{course_name}" успешно удален')
    return redirect('methodist_courses')


def _handle_course_form(request, course=None):
    """
    Обработка формы создания/редактирования курса
    """
    try:
        # Получаем данные из формы
        course_id = request.POST.get('course_id', '').strip().upper()
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        duration_hours = request.POST.get('duration_hours', '').strip()
        skill_ids = request.POST.getlist('skills')
        task_ids = request.POST.getlist('tasks')
        
        # Валидация обязательных полей
        if not name:
            messages.error(request, 'Название курса обязательно')
            return redirect(request.path)
            
        if not description:
            messages.error(request, 'Описание курса обязательно')
            return redirect(request.path)
        
        # Валидация ID курса для новых курсов
        if course is None:
            if not course_id:
                messages.error(request, 'ID курса обязателен')
                return redirect(request.path)
                
            # Проверяем формат ID (должен быть C + цифры)
            import re
            if not re.match(r'^C\d+$', course_id):
                messages.error(request, 'ID курса должен иметь формат C + число (например, C4, C5)')
                return redirect(request.path)
                
            # Проверяем уникальность ID
            if Course.objects.filter(id=course_id).exists():
                messages.error(request, f'Курс с ID "{course_id}" уже существует')
                return redirect(request.path)
        
        # Обработка длительности
        try:
            duration_hours = int(duration_hours) if duration_hours else None
        except ValueError:
            messages.error(request, 'Длительность должна быть числом')
            return redirect(request.path)
        
        # Создаем или обновляем курс
        if course is None:
            course = Course.objects.create(
                id=course_id,
                name=name,
                description=description,
                duration_hours=duration_hours
            )
            action = 'создан'
        else:
            course.name = name
            course.description = description
            course.duration_hours = duration_hours
            course.save()
            action = 'обновлен'
        
        # Устанавливаем связи с навыками
        if skill_ids:
            skills = Skill.objects.filter(id__in=skill_ids)
            course.skills.set(skills)
        else:
            course.skills.clear()
        
        # Устанавливаем связи с заданиями
        if task_ids:
            tasks = Task.objects.filter(id__in=task_ids)
            course.tasks.set(tasks)
        else:
            course.tasks.clear()
        
        messages.success(request, f'Курс "{name}" успешно {action}')
        return redirect('methodist_courses')
        
    except Exception as e:
        messages.error(request, f'Ошибка при сохранении курса: {str(e)}')
        return redirect(request.path)


@login_required
@methodist_required
def api_course_skills(request, course_id):
    """
    API для получения навыков курса
    """
    try:
        course = Course.objects.get(id=course_id)
        skills = list(course.skills.values('id', 'name', 'is_base'))
        return JsonResponse({'skills': skills})
    except Course.DoesNotExist:
        return JsonResponse({'error': 'Курс не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@methodist_required
def api_course_tasks(request, course_id):
    """
    API для получения заданий курса
    """
    try:
        course = Course.objects.get(id=course_id)
        tasks = list(course.tasks.values('id', 'title', 'task_type', 'difficulty'))
        return JsonResponse({'tasks': tasks})
    except Course.DoesNotExist:
        return JsonResponse({'error': 'Курс не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@login_required
@methodist_required
def api_update_course_skills(request):
    """
    API для обновления связей курса с навыками
    """
    try:
        course_id = request.POST.get('course_id')
        skill_ids = request.POST.getlist('skill_ids')
        
        if not course_id:
            return JsonResponse({'error': 'Не указан ID курса'}, status=400)
        
        course = Course.objects.get(id=course_id)
        
        if skill_ids:
            skills = Skill.objects.filter(id__in=skill_ids)
            course.skills.set(skills)
        else:
            course.skills.clear()
        
        return JsonResponse({
            'success': True,
            'message': f'Навыки курса "{course.name}" успешно обновлены'
        })
        
    except Course.DoesNotExist:
        return JsonResponse({'error': 'Курс не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@login_required
@methodist_required
def api_update_course_tasks(request):
    """
    API для обновления связей курса с заданиями
    """
    try:
        course_id = request.POST.get('course_id')
        task_ids = request.POST.getlist('task_ids')
        
        if not course_id:
            return JsonResponse({'error': 'Не указан ID курса'}, status=400)
        
        course = Course.objects.get(id=course_id)
        
        if task_ids:
            tasks = Task.objects.filter(id__in=task_ids)
            course.tasks.set(tasks)
        else:
            course.tasks.clear()
        
        return JsonResponse({
            'success': True,
            'message': f'Задания курса "{course.name}" успешно обновлены'
        })
        
    except Course.DoesNotExist:
        return JsonResponse({'error': 'Курс не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# === API ЭНДПОИНТЫ ===

@login_required
@methodist_required
def api_skills_list(request):
    """
    API для получения списка навыков
    """
    try:
        skills = Skill.objects.all().order_by('name')
        skills_data = []
        
        for skill in skills:
            skills_data.append({
                'id': skill.id,
                'name': skill.name,
                'is_base': skill.is_base,
                'description': skill.description or ''
            })
        
        return JsonResponse(skills_data, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@methodist_required
def api_tasks_list(request):
    """
    API для получения списка заданий
    """
    try:
        tasks = Task.objects.all().order_by('title')
        tasks_data = []
        
        for task in tasks:
            tasks_data.append({
                'id': task.id,
                'title': task.title,
                'difficulty': task.difficulty,
                'task_type': task.task_type,
                'question_text': task.question_text,
                'is_active': task.is_active,
                'created_at': task.created_at.isoformat() if task.created_at else None
            })
        
        return JsonResponse(tasks_data, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@methodist_required
def api_course_data(request, course_id):
    """
    API для получения данных курса со связанными навыками и заданиями
    """
    try:
        course = get_object_or_404(Course, id=course_id)
        
        # Получаем связанные навыки
        skills_data = []
        for skill in course.skills.all():
            skills_data.append({
                'id': skill.id,
                'name': skill.name,
                'is_base': skill.is_base
            })
          # Получаем связанные задания
        tasks_data = []
        for task in course.tasks.all():
            tasks_data.append({
                'id': task.id,
                'title': task.title,
                'difficulty': task.difficulty,
                'task_type': task.task_type
            })
        
        return JsonResponse({
            'id': course.id,
            'name': course.name,
            'description': course.description,
            'duration_hours': course.duration_hours,
            'skills': skills_data,
            'tasks': tasks_data
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# === ТЕСТОВЫЕ ЭНДПОИНТЫ (без аутентификации) ===

def test_skills_list(request):
    """
    Тестовый API для получения списка навыков (без аутентификации)
    """
    try:
        skills = Skill.objects.all().order_by('name')
        skills_data = []
        
        for skill in skills:
            skills_data.append({
                'id': skill.id,
                'name': skill.name,
                'is_base': skill.is_base,
                'description': skill.description or ''
            })
        
        return JsonResponse(skills_data, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def test_tasks_list(request):
    """
    Тестовый API для получения списка заданий (без аутентификации)
    """
    try:
        tasks = Task.objects.all().order_by('title')
        tasks_data = []
        
        for task in tasks:
            tasks_data.append({
                'id': task.id,
                'title': task.title,
                'difficulty': task.difficulty,
                'task_type': task.task_type,
                'question_text': task.question_text,
                'is_active': task.is_active,
                'created_at': task.created_at.isoformat() if task.created_at else None
            })
        
        return JsonResponse(tasks_data, safe=False)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def test_course_create(request):
    """
    Тестовое представление для создания курса (без аутентификации)
    """
    if request.method == 'POST':
        return _handle_course_form(request)
    
    # Получаем все навыки и задания для отображения
    skills = Skill.objects.all().order_by('name')
    tasks = Task.objects.all().order_by('title')
    
    context = {
        'is_editing': False,
        'available_skills': skills,
        'available_tasks': tasks,
        'current_skills': [],
        'current_tasks': [],
    }
    
    return render(request, 'methodist/course_form.html', context)


def test_course_form(request):
    """
    Тестовая страница формы курса без аутентификации
    """
    # Получаем все навыки
    all_skills = Skill.objects.all().order_by('name')
    
    # Получаем все задания
    all_tasks = Task.objects.all().order_by('title')
    
    context = {
        'is_editing': False,
        'course': None,
        'all_skills': all_skills,
        'all_tasks': all_tasks,
        'current_skills': [],
        'current_tasks': [],
    }
    
    return render(request, 'methodist/course_form.html', context)
