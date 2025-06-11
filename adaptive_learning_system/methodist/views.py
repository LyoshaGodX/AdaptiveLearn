from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib import messages
from django.db.models import Prefetch, Q
from django.views.decorators.http import require_POST
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth.decorators import login_required
from .decorators import methodist_required
from skills.models import Skill, Course
from .models import Task, TaskAnswer, TaskType, DifficultyLevel
import json
import datetime

# Функция для генерации данных для графа навыков
def generate_cytoscape_data(skills_queryset=None, selected_skill_id=None):
    """
    Генерирует данные для интерактивного графа Cytoscape.js
    skills_queryset: если передан, строит граф только по этим навыкам
    selected_skill_id: если передан, включает навык и его зависимости в граф
    """
    try:
        if skills_queryset is None:
            skills = Skill.objects.all().only('id', 'name', 'is_base').prefetch_related('prerequisites')
        else:
            skills = skills_queryset
    
        # Проверяем, передан ли выбранный навык
        selected_skill = None
        if selected_skill_id:
            try:
                selected_skill = Skill.objects.get(id=selected_skill_id)
            except Skill.DoesNotExist:
                print(f"Ошибка: Навык с ID {selected_skill_id} не найден")
                selected_skill_id = None
        
        # Определяем по переданному набору данных, была ли применена фильтрация по курсу
        if skills_queryset is not None and hasattr(skills_queryset, 'model') and skills_queryset.model == Skill:
            # Проверяем, это полный набор навыков или отфильтрованный по курсу
            total_skills_count = Skill.objects.count()
            current_skills_count = skills_queryset.count()
            filter_by_course = current_skills_count < total_skills_count
        else:
            filter_by_course = False
        
        # Если выбран конкретный навык, строим граф с ним и его непосредственными связями
        nodes = []
        edges = []
        skill_ids_in_graph = set()
        
        if selected_skill and selected_skill_id:
            # Добавляем выбранный навык
            nodes.append({
                'data': {
                    'id': f'skill_{selected_skill.id}',
                    'name': selected_skill.name,
                    'is_base': selected_skill.is_base,
                    'skill_id': selected_skill.id
                },
                'classes': "base-skill" if selected_skill.is_base else "regular-skill"
            })
            skill_ids_in_graph.add(selected_skill.id)
            
            # Определяем связи в зависимости от применения фильтра по курсу
            if filter_by_course:
                selected_course_skills = set(s.id for s in skills)
                # Получаем только непосредственные предпосылки, фильтруя по курсу
                prereqs = [prereq for prereq in selected_skill.prerequisites.all() 
                          if prereq.id in selected_course_skills]
                # Получаем только непосредственно зависимые навыки, фильтруя по курсу
                dependents = [dep for dep in selected_skill.dependent_skills.all() 
                            if dep.id in selected_course_skills]
            else:
                # Если нет фильтра по курсу, добавляем все непосредственные связи
                prereqs = list(selected_skill.prerequisites.all())
                dependents = list(selected_skill.dependent_skills.all())
            
            # Добавляем предпосылки
            for prereq in prereqs:
                if prereq.id not in skill_ids_in_graph:
                    nodes.append({
                        'data': {
                            'id': f'skill_{prereq.id}',
                            'name': prereq.name,
                            'is_base': prereq.is_base,
                            'skill_id': prereq.id
                        },
                        'classes': "base-skill" if prereq.is_base else "regular-skill"
                    })
                    skill_ids_in_graph.add(prereq.id)
            
            # Добавляем зависимые навыки
            for dependent in dependents:
                if dependent.id not in skill_ids_in_graph:
                    nodes.append({
                        'data': {
                            'id': f'skill_{dependent.id}',
                            'name': dependent.name,
                            'is_base': dependent.is_base,
                            'skill_id': dependent.id
                        },
                        'classes': "base-skill" if dependent.is_base else "regular-skill"
                    })
                    skill_ids_in_graph.add(dependent.id)
            
            # Добавляем ребра для связей выбранного навыка
            for prereq in prereqs:
                if prereq.id in skill_ids_in_graph:
                    edges.append({
                        'data': {
                            'id': f'edge_{prereq.id}_{selected_skill.id}',
                            'source': f'skill_{prereq.id}',
                            'target': f'skill_{selected_skill.id}'
                        }
                    })
            
            for dependent in dependents:
                if dependent.id in skill_ids_in_graph:
                    edges.append({
                        'data': {
                            'id': f'edge_{selected_skill.id}_{dependent.id}',
                            'source': f'skill_{selected_skill.id}',
                            'target': f'skill_{dependent.id}'
                        }
                    })
        else:
            # Если не выбран конкретный навык, отображаем все навыки и связи
            for skill in skills:
                nodes.append({
                    'data': {
                        'id': f'skill_{skill.id}',
                        'name': skill.name,
                        'is_base': skill.is_base,
                        'skill_id': skill.id
                    },
                    'classes': "base-skill" if skill.is_base else "regular-skill"
                })
                skill_ids_in_graph.add(skill.id)
                
                # Добавляем ребра для всех предпосылок
                for prereq in skill.prerequisites.all():
                    # Проверка, что предпосылка входит в текущий набор навыков (если применен фильтр)
                    if filter_by_course and prereq.id not in set(s.id for s in skills):
                        continue
                        
                    edges.append({
                        'data': {
                            'id': f'edge_{prereq.id}_{skill.id}',
                            'source': f'skill_{prereq.id}',
                            'target': f'skill_{skill.id}'
                        }
                    })
        
        result = {
            'nodes': nodes,
            'edges': edges,
            'meta': {
                'timestamp': str(datetime.datetime.now()),
                'selected_skill_id': selected_skill_id
            }
        }
        
        return json.dumps(result)
    except Exception as e:
        print(f"Ошибка при создании данных для Cytoscape: {e}")
        import traceback
        traceback.print_exc()
        
        # Возвращаем пустой граф в случае ошибки
        empty_graph = {
            'nodes': [],
            'edges': [],
            'meta': {
                'error': 'Ошибка при формировании графа',
                'timestamp': str(datetime.datetime.now())
            }
        }
        return json.dumps(empty_graph)


@login_required
def skill_graph(request):
    """
    Отображает список всех навыков с группировкой по курсам, поддерживает фильтрацию графа по курсу
    """
    course_id = request.GET.get('course')
    selected_skill_id = request.GET.get('skill')
    courses = Course.objects.all().prefetch_related('skills')
    base_skills = Skill.objects.filter(is_base=True)
    
    # Проверяем, не является ли значение course строкой "None"
    if course_id == 'None':
        course_id = None
        
    # Для фильтрации графа по курсу
    if course_id and course_id != '':
        try:
            course = Course.objects.get(id=course_id)
            course_skills = course.skills.all().prefetch_related('prerequisites')
        except Course.DoesNotExist:
            course_skills = Skill.objects.none()
    else:
        course_skills = Skill.objects.all().prefetch_related('prerequisites')
    
    # Если выбран конкретный навык, убедимся, что данные для графа содержат его и его прямые зависимости
    if selected_skill_id and selected_skill_id.isdigit():
        try:
            selected_skill = Skill.objects.get(id=selected_skill_id)
            all_skills = Skill.objects.all().prefetch_related('prerequisites')
            
            # Если выбран курс, проверяем принадлежит ли навык курсу
            if course_id and course_id != '':
                # Если навык принадлежит курсу, используем данные курса с выбранным навыком
                if course_skills.filter(id=selected_skill.id).exists():
                    cytoscape_data = generate_cytoscape_data(course_skills, selected_skill_id)
                # Если навык не принадлежит курсу, но выбран курс - показываем только курс
                else:
                    cytoscape_data = generate_cytoscape_data(course_skills)
            # Если курс не выбран, отображаем выбранный навык с его прямыми зависимостями
            else:
                cytoscape_data = generate_cytoscape_data(all_skills, selected_skill_id)
                
        except Skill.DoesNotExist:
            cytoscape_data = generate_cytoscape_data(course_skills)
    else:
        # Если навык не выбран, отображаем обычный граф с фильтрацией по курсу
        cytoscape_data = generate_cytoscape_data(course_skills)

    # Для отображения зависимостей в списке
    all_skills = Skill.objects.prefetch_related('prerequisites').all()
    
    # Проверка, относится ли выбранный навык к курсу
    skill_in_course = False
    if selected_skill_id and course_id:
        try:
            skill_in_course = Skill.objects.filter(
                id=selected_skill_id,
                courses__id=course_id
            ).exists()
        except Exception as e:
            print(f"Ошибка при проверке принадлежности навыка курсу: {e}")
    
    context = {
        'courses': courses,
        'base_skills': base_skills,
        'cytoscape_data': cytoscape_data,
        'selected_course_id': course_id,
        'all_skills': all_skills,
        'selected_skill_id': selected_skill_id,
        'skill_in_course': skill_in_course
    }
    return render(request, 'methodist/skills_list.html', context)


@login_required
@methodist_required
def edit_skills(request):
    """
    Страница для редактирования навыков и связей между ними
    """
    search_query = request.GET.get('search', '')
    course_id = request.GET.get('course')
    skill_id = request.GET.get('skill')
    
    # Загрузка всех курсов
    courses = Course.objects.all().prefetch_related('skills')
    
    # Фильтрация навыков
    filtered_skills = Skill.objects.all().prefetch_related('prerequisites')
    
    if search_query:
        filtered_skills = filtered_skills.filter(name__icontains=search_query)
    
    if course_id:
        try:
            course = Course.objects.get(id=course_id)
            filtered_skills = filtered_skills.filter(courses=course)
        except Course.DoesNotExist:
            pass    # Выбранный навык
    selected_skill = None
    dependent_skills = []
    
    if skill_id:
        try:
            selected_skill = Skill.objects.prefetch_related('prerequisites').get(id=skill_id)
            
            # Получаем навыки, которые зависят от выбранного
            dependent_skills = Skill.objects.filter(prerequisites=selected_skill)
            
            # Для визуализации графа: выбранный навык, его зависимости и зависящие от него навыки
            graph_skills = set([selected_skill])
            graph_skills.update(selected_skill.prerequisites.all())
            graph_skills.update(dependent_skills)
            
            cytoscape_data = generate_cytoscape_data(graph_skills)
                
        except Skill.DoesNotExist:
            cytoscape_data = json.dumps({'nodes': [], 'edges': []})
    else:
        cytoscape_data = json.dumps({'nodes': [], 'edges': []})
    
    # сериализация курсов
    courses_json = json.dumps(
        list(courses.values('id', 'name')),
        cls=DjangoJSONEncoder
    )
    # сериализация навыков
    skills_json = json.dumps([
        {
            'id': s.id,
            'name': s.name,
            'courses': list(s.courses.values_list('id', flat=True)),
            'prerequisites': list(s.prerequisites.values_list('id', flat=True)),
        } for s in filtered_skills
    ], cls=DjangoJSONEncoder)

    context = {
        'courses': courses,
        'filtered_skills': filtered_skills,
        'selected_skill': selected_skill,
        'dependent_skills': dependent_skills,
        'cytoscape_data': cytoscape_data,
        'search_query': search_query,
        'selected_course_id': course_id,
        'courses_json': courses_json,
        'skills_json': skills_json,
    }

    return render(request, 'methodist/skills_edit.html', context)


@require_POST
@login_required
@methodist_required
def edit_skill(request):
    """
    Создание или редактирование навыка
    """
    skill_id = request.POST.get('skill_id')
    name = request.POST.get('name')
    is_base = request.POST.get('is_base') == 'true'
    courses_ids = request.POST.getlist('courses')
    
    if not name:
        messages.error(request, 'Название навыка не может быть пустым')
        return redirect('methodist_edit')
    
    # Обновляем существующий или создаем новый навык
    if skill_id:
        skill = get_object_or_404(Skill, id=skill_id)
        skill.name = name
        skill.is_base = is_base
        skill.save()
        messages.success(request, f'Навык "{name}" успешно обновлен')
        
        # При редактировании навыка обновляем связи с курсами только если явно переданы курсы
        if 'update_courses' in request.POST:
            if courses_ids:
                courses = Course.objects.filter(id__in=courses_ids)
                skill.courses.set(courses)
            else:
                skill.courses.clear()
    else:
        # Для нового навыка создаем его и устанавливаем связи с курсами, если указаны
        skill = Skill.objects.create(name=name, is_base=is_base)
        messages.success(request, f'Навык "{name}" успешно создан')
        
        # Для нового навыка можно установить связи с курсами
        if courses_ids:
            courses = Course.objects.filter(id__in=courses_ids)
            skill.courses.set(courses)
    
    return redirect(f'/methodist/edit/?skill={skill.id}')


@require_POST
@login_required
@methodist_required
def delete_skill(request):
    """
    Удаление навыка
    """
    skill_id = request.POST.get('skill_id')
    
    if not skill_id:
        messages.error(request, 'Не указан навык для удаления')
        return redirect('methodist_edit')
    
    skill = get_object_or_404(Skill, id=skill_id)
    skill_name = skill.name
    skill.delete()
    
    messages.success(request, f'Навык "{skill_name}" успешно удален')
    return redirect('methodist_edit')


@require_POST
@login_required
@methodist_required
def update_skill_courses(request):
    """
    Обновление связей навыка с курсами
    """
    skill_id = request.POST.get('skill_id')
    courses_ids = request.POST.getlist('courses')
    
    if not skill_id:
        messages.error(request, 'Не указан навык для обновления')
        return redirect('methodist_edit')
    
    skill = get_object_or_404(Skill, id=skill_id)
    
    if courses_ids:
        courses = Course.objects.filter(id__in=courses_ids)
        skill.courses.set(courses)
    else:
        skill.courses.clear()
    
    messages.success(request, f'Курсы для навыка "{skill.name}" успешно обновлены')
    return redirect(f'/methodist/edit/?skill={skill.id}')


@require_POST
@login_required
@methodist_required
def api_add_prerequisite(request):
    """
    API для добавления предварительного требования к навыку
    """
    skill_id = request.POST.get('skill_id')
    prereq_id = request.POST.get('prereq_id')
    
    print(f"DEBUG: Получены параметры - skill_id: {skill_id}, prereq_id: {prereq_id}")
    
    if not skill_id or not prereq_id:
        print("DEBUG: Ошибка - не переданы параметры")
        return JsonResponse({'error': 'Не переданы параметры'}, status=400)
        
    if skill_id == prereq_id:
        print("DEBUG: Ошибка - навык не может быть предпосылкой для самого себя")
        return JsonResponse({'error': 'Навык не может быть предпосылкой для самого себя'}, status=400)
    
    try:
        skill = Skill.objects.get(id=skill_id)
        prereq = Skill.objects.get(id=prereq_id)
        
        print(f"DEBUG: Найдены навыки - skill: {skill.name}, prereq: {prereq.name}")
        
        # Проверяем, не является ли уже предпосылкой
        if prereq in skill.prerequisites.all():
            print("DEBUG: Ошибка - навык уже является предпосылкой")
            return JsonResponse({'error': 'Этот навык уже является предпосылкой'}, status=400)
        
        # Проверяем на циклические зависимости
        def would_create_cycle(skill_obj, new_prereq):
            """
            Проверяет, создаст ли добавление new_prereq к skill циклическую зависимость
            """
            visited = set()
            
            def has_path_to_skill(current_skill, target_skill):
                if current_skill.id == target_skill.id:
                    return True
                if current_skill.id in visited:
                    return False
                visited.add(current_skill.id)
                
                # Проверяем все предпосылки текущего навыка
                for prereq in current_skill.prerequisites.all():
                    if has_path_to_skill(prereq, target_skill):
                        return True
                return False
              # Проверяем, есть ли путь от new_prereq к skill
            return has_path_to_skill(new_prereq, skill_obj)
        
        if would_create_cycle(skill, prereq):
            print(f"DEBUG: Ошибка - обнаружена циклическая зависимость")
            print(f"DEBUG: Попытка добавить {prereq.name} (ID: {prereq.id}) как предпосылку для {skill.name} (ID: {skill.id})")
            
            # Дополнительная диагностика - покажем цепочку зависимостей
            print(f"DEBUG: Предпосылки для {prereq.name}: {[p.name for p in prereq.prerequisites.all()]}")
            print(f"DEBUG: Зависимые от {skill.name}: {[d.name for d in Skill.objects.filter(prerequisites=skill)]}")
            
            return JsonResponse({
                'error': f'Добавление навыка "{prereq.name}" как предпосылки для "{skill.name}" создаст циклическую зависимость'
            }, status=400)
        
        # Добавляем предпосылку
        skill.prerequisites.add(prereq)
        print(f"DEBUG: Успешно добавлена предпосылка {prereq.name} для навыка {skill.name}")
        return JsonResponse({
            'success': True, 
            'message': f'Навык "{prereq.name}" успешно добавлен как предпосылка для "{skill.name}"'
        })
        
    except Skill.DoesNotExist:
        return JsonResponse({'error': 'Навык не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@login_required
@methodist_required
def api_remove_prerequisite(request):
    """
    API для удаления предварительного требования у навыка
    """
    skill_id = request.POST.get('skill_id')
    prereq_id = request.POST.get('prereq_id')
    if not skill_id or not prereq_id:
        return JsonResponse({'error': 'Не переданы параметры'}, status=400)
    try:
        skill = Skill.objects.get(id=skill_id)
        prereq = Skill.objects.get(id=prereq_id)
        skill.prerequisites.remove(prereq)
        return JsonResponse({'success': True})
    except Skill.DoesNotExist:
        return JsonResponse({'error': 'Навык не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@methodist_required
def api_skill_details(request, skill_id):
    """
    API для получения подробной информации о навыке
    """
    try:
        skill = Skill.objects.get(id=skill_id)
        prerequisites_count = skill.prerequisites.count()
        dependents_count = Skill.objects.filter(prerequisites=skill).count()
        
        # Получаем список курсов, к которым относится навык
        courses = list(skill.courses.values('id', 'name'))
        
        data = {
            'id': skill.id,
            'name': skill.name,
            'is_base': skill.is_base,
            'prerequisites_count': prerequisites_count,
            'dependents_count': dependents_count,
            'courses': courses
        }
        
        return JsonResponse(data)
    except Skill.DoesNotExist:
        return JsonResponse({'error': 'Навык не найден'}, status=404)
    except Exception as e:
        # Логируем ошибку для отладки
        import traceback
        print(f"Ошибка в api_skill_details: {e}")
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@methodist_required
def api_skill_courses(request, skill_id):
    """
    API для получения курсов, к которым относится навык
    """
    try:
        skill = Skill.objects.get(id=skill_id)
        courses = list(skill.courses.values('id', 'name'))
        return JsonResponse({'courses': courses})
    except Skill.DoesNotExist:
        return JsonResponse({'error': 'Навык не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@methodist_required
def api_remove_dependent(request):
    """
    API для удаления зависимого навыка (убирает связь dependent -> skill)
    """
    skill_id = request.POST.get('skill_id')
    dependent_id = request.POST.get('dependent_id')
    
    if not skill_id or not dependent_id:
        return JsonResponse({'error': 'Не переданы параметры'}, status=400)
    
    try:
        skill = Skill.objects.get(id=skill_id)
        dependent_skill = Skill.objects.get(id=dependent_id)
        
        # Убираем связь: dependent_skill больше не зависит от skill
        dependent_skill.prerequisites.remove(skill)
        
        return JsonResponse({'success': True})
    except Skill.DoesNotExist:
        return JsonResponse({'error': 'Навык не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ========== УПРАВЛЕНИЕ ЗАДАНИЯМИ ==========

@login_required
@methodist_required
def tasks_list(request):
    """
    Список всех заданий с фильтрацией
    """
    # Получаем параметры фильтрации
    course_id = request.GET.get('course')
    difficulty = request.GET.get('difficulty')
    skill_id = request.GET.get('skill')
    search_query = request.GET.get('search', '')
    
    # Базовая выборка заданий
    tasks = Task.objects.all().prefetch_related('skills', 'courses', 'answers')
    
    # Применяем фильтры
    if search_query:
        tasks = tasks.filter(
            Q(title__icontains=search_query) | 
            Q(question_text__icontains=search_query)
        )
    
    if course_id:
        tasks = tasks.filter(courses__id=course_id)
    
    if difficulty:
        tasks = tasks.filter(difficulty=difficulty)
    
    if skill_id:
        tasks = tasks.filter(skills__id=skill_id)
    
    # Получаем данные для фильтров
    courses = Course.objects.all()
    skills = Skill.objects.all()
    
    context = {
        'tasks': tasks,
        'courses': courses,
        'skills': skills,
        'difficulty_choices': DifficultyLevel.choices,
        'selected_course_id': course_id,
        'selected_difficulty': difficulty,
        'selected_skill_id': skill_id,
        'search_query': search_query,
    }
    
    return render(request, 'methodist/tasks_list.html', context)


@login_required
@methodist_required
def task_create(request):
    """
    Создание нового задания
    """
    if request.method == 'POST':
        return _handle_task_form(request)
    
    # GET запрос - показываем форму
    courses = Course.objects.all()
    skills = Skill.objects.prefetch_related('courses').all()
    
    context = {
        'task': None,
        'courses': courses,
        'skills': skills,
        'task_types': TaskType.choices,
        'difficulty_choices': DifficultyLevel.choices,
        'is_editing': False,
    }
    
    return render(request, 'methodist/task_form.html', context)


@login_required
@methodist_required
def task_edit(request, task_id):
    """
    Редактирование существующего задания
    """
    task = get_object_or_404(Task, id=task_id)
    
    if request.method == 'POST':
        return _handle_task_form(request, task)
    
    # GET запрос - показываем форму с данными задания
    courses = Course.objects.all()
    skills = Skill.objects.prefetch_related('courses').all()
    
    context = {
        'task': task,
        'courses': courses,
        'skills': skills,
        'task_types': TaskType.choices,
        'difficulty_choices': DifficultyLevel.choices,
        'is_editing': True,
    }
    
    return render(request, 'methodist/task_form.html', context)


@require_POST
@login_required
@methodist_required
def task_delete(request, task_id):
    """
    Удаление задания
    """
    task = get_object_or_404(Task, id=task_id)
    task_title = task.title
    task.delete()
    
    messages.success(request, f'Задание "{task_title}" успешно удалено')
    return redirect('methodist_tasks')


def _handle_task_form(request, task=None):
    """
    Обработка формы создания/редактирования задания
    """
    print(f"DEBUG: Starting _handle_task_form, task={task}")
    try:
        # Получаем данные из формы
        title = request.POST.get('title', '').strip()
        task_type = request.POST.get('task_type')
        difficulty = request.POST.get('difficulty')
        question_text = request.POST.get('question_text', '').strip()
        correct_answer = request.POST.get('correct_answer', '').strip()
        explanation = request.POST.get('explanation', '').strip()
        skill_ids = request.POST.getlist('skills')
        course_id = request.POST.get('course', '').strip()  # Теперь это одиночное значение
        
        # Отладочная информация
        print(f"DEBUG: Raw POST data = {dict(request.POST)}")
        print(f"DEBUG: skill_ids = {skill_ids}")
        print(f"DEBUG: skill_ids types = {[type(sid) for sid in skill_ids]}")
        print(f"DEBUG: course_id = {course_id}")
        
        # Проверяем, что skill_ids содержат числа, а не названия
        numeric_skill_ids = []
        for sid in skill_ids:
            try:
                numeric_skill_ids.append(int(sid))
            except (ValueError, TypeError):
                print(f"DEBUG: Invalid skill_id: {sid} (type: {type(sid)})")
                messages.error(request, f'Неверный идентификатор навыка: {sid}')
                return redirect(request.path)
        
        print(f"DEBUG: numeric_skill_ids = {numeric_skill_ids}")
        
        # Валидация обязательных полей
        if not title:
            messages.error(request, 'Название задания обязательно')
            return redirect(request.path)
        
        if not question_text:
            messages.error(request, 'Формулировка задачи обязательна')
            return redirect(request.path)
        
        if not numeric_skill_ids:
            messages.error(request, 'Необходимо выбрать хотя бы один навык')
            return redirect(request.path)
            
        if not course_id:
            messages.error(request, 'Необходимо выбрать курс для задания')
            return redirect(request.path)
        
        # Создаем или обновляем задание
        if task is None:
            task = Task.objects.create(
                title=title,
                task_type=task_type,
                difficulty=difficulty,
                question_text=question_text,
                correct_answer=correct_answer,
                explanation=explanation
            )
            action = 'создано'
        else:
            task.title = title
            task.task_type = task_type
            task.difficulty = difficulty
            task.question_text = question_text
            task.correct_answer = correct_answer
            task.explanation = explanation
            task.save()
            action = 'обновлено'
          # Устанавливаем связи с навыками
        if numeric_skill_ids:
            print(f"DEBUG: numeric_skill_ids before filtering = {numeric_skill_ids}")
            skills = Skill.objects.filter(id__in=numeric_skill_ids)
            print(f"DEBUG: Found skills = {skills}")
            print(f"DEBUG: Skills list = {list(skills)}")
            print(f"DEBUG: Skills IDs = {[skill.id for skill in skills]}")
            print(f"DEBUG: About to call task.skills.set()")
            try:
                task.skills.set(skills)
                print(f"DEBUG: Successfully set skills")
            except Exception as e:
                print(f"DEBUG: Error in task.skills.set(): {e}")
                print(f"DEBUG: Error type: {type(e)}")
                raise
          # Устанавливаем связи с курсами
        task.courses.clear()  # Сначала очищаем все связи
        print(f"DEBUG: About to find course with id: {course_id}")
        try:
            course = Course.objects.get(id=course_id)
            print(f"DEBUG: Found course: {course} (id: {course.id})")
            print(f"DEBUG: About to add course to task")
            task.courses.add(course)
            print(f"DEBUG: Successfully added course")
        except Course.DoesNotExist:
            print(f"DEBUG: Course with id {course_id} not found")
            messages.error(request, 'Выбранный курс не найден')
            return redirect(request.path)
        except Exception as e:
            print(f"DEBUG: Error with course: {e}")
            print(f"DEBUG: Error type: {type(e)}")
            raise
          # Обрабатываем варианты ответов для заданий с выбором
        if task_type in ['single', 'multiple', 'true_false']:
            # Удаляем старые варианты ответов
            task.answers.all().delete()
            
            if task_type == 'true_false':
                # Для типа "верно/неверно" обрабатываем радио-кнопки
                true_false_answer = request.POST.get('true_false_answer')
                print(f"DEBUG: true_false_answer = {true_false_answer}")
                print(f"DEBUG: true_false_answer type = {type(true_false_answer)}")
                
                # Создаем варианты "Верно" и "Неверно"
                TaskAnswer.objects.create(
                    task=task,
                    text='Верно',
                    is_correct=(true_false_answer == 'true'),
                    order=0
                )
                print(f"DEBUG: Created 'Верно' answer with is_correct={true_false_answer == 'true'}")
                
                TaskAnswer.objects.create(
                    task=task,
                    text='Неверно',
                    is_correct=(true_false_answer == 'false'),
                    order=1
                )
                print(f"DEBUG: Created 'Неверно' answer with is_correct={true_false_answer == 'false'}")
            else:
                # Для типов "single" и "multiple" обрабатываем обычные варианты
                answer_texts = request.POST.getlist('answer_text')
                
                if task_type == 'single':
                    correct_answer_index = request.POST.get('correct_answer_single')
                    
                    for i, answer_text in enumerate(answer_texts):
                        if answer_text.strip():
                            is_correct = (str(i) == correct_answer_index)
                            TaskAnswer.objects.create(
                                task=task,
                                text=answer_text.strip(),
                                is_correct=is_correct,
                                order=i
                            )
                            
                elif task_type == 'multiple':
                    correct_answers = request.POST.getlist('correct_answers_multiple')
                    
                    for i, answer_text in enumerate(answer_texts):
                        if answer_text.strip():
                            is_correct = str(i) in correct_answers
                            TaskAnswer.objects.create(
                                task=task,
                                text=answer_text.strip(),
                                is_correct=is_correct,
                                order=i                            )
        
        messages.success(request, f'Задание "{title}" успешно {action}')
        print(f"DEBUG: About to redirect to 'methodist_tasks'")
        return redirect('methodist_tasks')
        
    except Exception as e:
        print(f"DEBUG: Exception caught in _handle_task_form: {e}")
        print(f"DEBUG: Exception type: {type(e)}")
        import traceback
        print(f"DEBUG: Full traceback:")
        traceback.print_exc()
        messages.error(request, f'Ошибка при сохранении задания: {str(e)}')
        return redirect(request.path)
