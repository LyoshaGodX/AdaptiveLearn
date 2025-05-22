from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Prefetch, Q
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers.json import DjangoJSONEncoder
from .models import Skill, Course
import json
import datetime

def skills_list(request):
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
            # Проверяем существование навыка перед созданием графа
            selected_skill = Skill.objects.get(id=selected_skill_id)
            
            # Используем все навыки, так как при выборе конкретного навыка 
            # нам всегда нужно показать его зависимости независимо от курса
            all_skills = Skill.objects.all().prefetch_related('prerequisites')
            
            # Если выбран курс, проверяем принадлежит ли навык курсу
            if course_id and course_id != '':
                # Если навык принадлежит курсу, используем данные курса с выбранным навыком
                if course_skills.filter(id=selected_skill.id).exists():
                    # Передаем выбранный навык для отображения только его и прямых зависимостей
                    cytoscape_data = generate_cytoscape_data(course_skills, selected_skill_id)
                # Если навык не принадлежит курсу, но выбран курс - показываем только курс
                else:
                    # Показываем обычный граф курса без выбранного навыка
                    cytoscape_data = generate_cytoscape_data(course_skills)
            # Если курс не выбран, отображаем выбранный навык с его прямыми зависимостями
            else:
                # Генерируем данные для графа с выбранным навыком
                cytoscape_data = generate_cytoscape_data(all_skills, selected_skill_id)
                
        except Skill.DoesNotExist:
            # Если навык не найден, показываем обычный граф
            print(f"Ошибка: Навык с ID {selected_skill_id} не найден")
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
            # Проверяем, принадлежит ли навык выбранному курсу
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
    return render(request, 'skills/skills_list.html', context)

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
            
            # Добавляем ребра только для прямых связей выбранного навыка
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
            # Обычный режим: добавляем все навыки и их связи
            for skill in skills:
                node_class = "base-skill" if skill.is_base else "regular-skill"
                nodes.append({
                    'data': {
                        'id': f'skill_{skill.id}',
                        'name': skill.name,
                        'is_base': skill.is_base,
                        'skill_id': skill.id
                    },
                    'classes': node_class
                })
                skill_ids_in_graph.add(skill.id)
            
            # Добавляем все связи между навыками
            added_edges = set()
            for skill in skills:
                for prereq in skill.prerequisites.all():
                    # Проверяем, что оба навыка есть в графе
                    if prereq.id in skill_ids_in_graph and skill.id in skill_ids_in_graph:
                        edge_id = f'edge_{prereq.id}_{skill.id}'
                        if edge_id not in added_edges:
                            edges.append({
                                'data': {
                                    'id': edge_id,
                                    'source': f'skill_{prereq.id}',
                                    'target': f'skill_{skill.id}'
                                }
                            })
                            added_edges.add(edge_id)
        
        # Формируем результат
        cytoscape_data = {
            'nodes': nodes,
            'edges': edges
        }
        
        # Проверяем результат
        if not nodes:
            print("Предупреждение: Пустой список узлов в графе")
        
        # Сериализуем данные
        return json.dumps(cytoscape_data)
        
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
    
    
def skills_edit(request):
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
            pass
    
    # Выбранный навык
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

    return render(request, 'skills/skills_edit.html', context)


@require_POST
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
        return redirect('skills_edit')
    
    # Обновляем существующий или создаем новый навык
    if skill_id:
        skill = get_object_or_404(Skill, id=skill_id)
        skill.name = name
        skill.is_base = is_base
        skill.save()
        messages.success(request, f'Навык "{name}" успешно обновлен')
        
        # ИЗМЕНЕНИЕ: При редактировании навыка НЕ обновляем связи с курсами,
        # только если явно переданы курсы (например, из модального окна "Присвоить курсу")
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
    
    return redirect(f'/edit/?skill={skill.id}')


@require_POST
def delete_skill(request):
    """
    Удаление навыка
    """
    skill_id = request.POST.get('skill_id')
    
    if not skill_id:
        messages.error(request, 'Не указан навык для удаления')
        return redirect('skills_edit')
    
    skill = get_object_or_404(Skill, id=skill_id)
    skill_name = skill.name
    skill.delete()
    
    messages.success(request, f'Навык "{skill_name}" успешно удален')
    return redirect('/edit/')


@require_POST
def update_skill_courses(request):
    """
    Обновление списка курсов, к которым относится навык
    """
    skill_id = request.POST.get('skill_id')
    courses_ids = request.POST.getlist('courses')
    
    if not skill_id:
        messages.error(request, 'Не указан ID навыка')
        return redirect('skills_edit')
    
    try:
        skill = Skill.objects.get(id=skill_id)
        
        # Обновляем курсы
        if courses_ids:
            courses = Course.objects.filter(id__in=courses_ids)
            skill.courses.set(courses)
        else:
            skill.courses.clear()
            
        messages.success(request, f'Курсы навыка "{skill.name}" успешно обновлены')
        return redirect(f'/edit/?skill={skill.id}')
        
    except Skill.DoesNotExist:
        messages.error(request, 'Навык не найден')
        return redirect('skills_edit')
    

def api_skill_courses(request, skill_id):
    """
    API для получения курсов, к которым относится навык
    """
    try:
        try:
            skill = Skill.objects.get(id=skill_id)
            courses = skill.courses.all().values('id', 'name')
            
            return JsonResponse({
                'skill_id': skill_id,
                'skill_name': skill.name,
                'courses': list(courses.values_list('id', flat=True))
            })
        except Skill.DoesNotExist:
            return JsonResponse({'error': f'Навык с ID {skill_id} не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Ошибка при получении курсов: {str(e)}'}, status=500)


def api_skill_details(request, skill_id):
    """
    API для получения подробной информации о навыке
    """
    try:
        # Сначала проверяем существование навыка
        try:
            skill = Skill.objects.get(id=skill_id)
        except Skill.DoesNotExist:
            return JsonResponse({'error': f'Навык с ID {skill_id} не найден'}, status=404)
        
        # Получаем количество зависимостей
        prerequisites_count = skill.prerequisites.count()
        
        # Получаем количество зависимых навыков
        # Используем более надежный способ без прямого доступа к related_name
        dependents_count = Skill.objects.filter(prerequisites=skill).count()
        
        # Получаем курсы
        courses = list(skill.courses.values_list('id', flat=True))
        course_names = list(skill.courses.values_list('name', flat=True))
        
        # Формируем и возвращаем ответ
        return JsonResponse({
            'skill_id': skill.id,
            'name': skill.name,
            'is_base': skill.is_base,
            'prerequisites_count': prerequisites_count,
            'dependents_count': dependents_count,
            'courses': courses,
            'course_names': course_names
        })
        
    except Exception as e:
        # Логируем ошибку для отладки
        import traceback
        print(f"Ошибка в api_skill_details: {e}")
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
def api_add_prerequisite(request):
    skill_id = request.POST.get('skill_id')
    prereq_id = request.POST.get('prereq_id')
    if not skill_id or not prereq_id:
        return JsonResponse({'error': 'Не переданы параметры'}, status=400)
    try:
        skill = Skill.objects.get(id=skill_id)
        prereq = Skill.objects.get(id=prereq_id)
        skill.prerequisites.add(prereq)
        return JsonResponse({'success': True})
    except Skill.DoesNotExist:
        return JsonResponse({'error': 'Навык не найден'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
def api_remove_prerequisite(request):
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
