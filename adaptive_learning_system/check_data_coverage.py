#!/usr/bin/env python
"""
Временный скрипт для анализа покрытия навыков и заданий в системе
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

import json
from collections import defaultdict
from skills.models import Skill
from methodist.models import Task

def analyze_system_data():
    """Анализ данных в системе"""
    print('🔍 АНАЛИЗ ДАННЫХ В СИСТЕМЕ')
    print('='*50)
    
    # Проверяем навыки
    skills = Skill.objects.all()
    print(f'Всего навыков в системе: {skills.count()}')
    
    # Проверяем задания  
    tasks = Task.objects.all().prefetch_related('skills')
    print(f'Всего заданий в системе: {tasks.count()}')
    
    # Проверяем распределение заданий по навыкам
    skills_with_tasks = set()
    tasks_by_skill_count = defaultdict(int)
    tasks_by_skill_list = defaultdict(list)
    
    for task in tasks:
        task_skills = task.skills.all()
        for skill in task_skills:
            skills_with_tasks.add(skill.id)
            tasks_by_skill_count[skill.id] += 1
            tasks_by_skill_list[skill.id].append(task.id)
    
    print(f'Навыков с заданиями: {len(skills_with_tasks)}')
    print(f'Навыков без заданий: {skills.count() - len(skills_with_tasks)}')
    
    # Показываем статистику заданий по навыкам
    print('\n📊 Распределение заданий по навыкам:')
    for skill in skills.order_by('name'):
        count = tasks_by_skill_count.get(skill.id, 0)
        status = "✅" if count > 0 else "❌"
        print(f'  {status} {skill.name} (ID: {skill.id}): {count} заданий')
    
    # Навыки без заданий
    skills_without_tasks = []
    for skill in skills:
        if skill.id not in skills_with_tasks:
            skills_without_tasks.append((skill.id, skill.name))
    
    if skills_without_tasks:
        print(f'\n❌ Навыки без заданий ({len(skills_without_tasks)}):')
        for skill_id, skill_name in skills_without_tasks:
            print(f'   - {skill_name} (ID: {skill_id})')
    
    return {
        'total_skills': skills.count(),
        'total_tasks': tasks.count(),
        'skills_with_tasks': len(skills_with_tasks),
        'skills_without_tasks': skills_without_tasks,
        'tasks_by_skill': dict(tasks_by_skill_list)
    }

def analyze_synthetic_spec():
    """Анализ спецификации синтетических данных"""
    print('\n🔍 АНАЛИЗ СПЕЦИФИКАЦИИ СИНТЕТИЧЕСКИХ ДАННЫХ')
    print('='*50)
    
    try:
        with open('temp_dir/synthetic_data_spec.json', 'r', encoding='utf-8') as f:
            spec = json.load(f)
        
        skills_in_spec = len(spec['skills_graph']['skills_info'])
        skills_with_deps = len(spec['skills_graph']['dependencies'])
        
        print(f'Навыков в спецификации: {skills_in_spec}')
        print(f'Навыков с зависимостями: {skills_with_deps}')
        
        # Проверяем, какие навыки есть в спецификации
        spec_skill_ids = set(int(k) for k in spec['skills_graph']['skills_info'].keys())
        all_skill_ids = set(Skill.objects.values_list('id', flat=True))
        
        missing_in_spec = all_skill_ids - spec_skill_ids
        extra_in_spec = spec_skill_ids - all_skill_ids
        
        if missing_in_spec:
            print(f'\n❌ Навыки отсутствующие в спецификации ({len(missing_in_spec)}):')
            for skill_id in sorted(missing_in_spec):
                skill_name = Skill.objects.get(id=skill_id).name
                print(f'   - {skill_name} (ID: {skill_id})')
        
        if extra_in_spec:
            print(f'\n⚠️ Лишние навыки в спецификации ({len(extra_in_spec)}):')
            for skill_id in sorted(extra_in_spec):
                print(f'   - ID: {skill_id}')
        
        return {
            'skills_in_spec': skills_in_spec,
            'missing_in_spec': missing_in_spec,
            'extra_in_spec': extra_in_spec
        }
        
    except FileNotFoundError:
        print('❌ Файл спецификации не найден!')
        return None

def check_generation_coverage():
    """Проверяем, что генератор охватывает все навыки"""
    print('\n🔍 ПРОВЕРКА ПОКРЫТИЯ ГЕНЕРАТОРА')
    print('='*50)
    
    try:
        # Проверяем последние результаты генерации
        print('Проверяем статистику последней генерации...')
        
        # Загружаем спецификацию
        with open('temp_dir/synthetic_data_spec.json', 'r', encoding='utf-8') as f:
            spec = json.load(f)
        
        # Проверяем доступность заданий для каждого навыка
        skills_with_no_tasks = []
        
        for skill_id_str in spec['skills_graph']['skills_info'].keys():
            skill_id = int(skill_id_str)
            
            # Проверяем, есть ли задания для этого навыка
            tasks_for_skill = Task.objects.filter(skills__id=skill_id).count()
            if tasks_for_skill == 0:
                try:
                    skill_name = Skill.objects.get(id=skill_id).name
                    skills_with_no_tasks.append((skill_id, skill_name))
                except Skill.DoesNotExist:
                    skills_with_no_tasks.append((skill_id, f'Навык не найден'))
        
        if skills_with_no_tasks:
            print(f'❌ Навыки без заданий (не могут быть сгенерированы):')
            for skill_id, skill_name in skills_with_no_tasks:
                print(f'   - {skill_name} (ID: {skill_id})')
        else:
            print('✅ Все навыки в спецификации имеют задания!')
        
        return len(skills_with_no_tasks) == 0
        
    except Exception as e:
        print(f'❌ Ошибка при проверке: {e}')
        return False

def main():
    """Основная функция"""
    
    # Анализируем данные системы
    system_data = analyze_system_data()
    
    # Анализируем спецификацию
    spec_data = analyze_synthetic_spec()
    
    # Проверяем покрытие генератора
    coverage_ok = check_generation_coverage()
    
    print('\n🎯 РЕКОМЕНДАЦИИ')
    print('='*50)
    
    if system_data['skills_without_tasks']:
        print('1. ❌ Есть навыки без заданий. Рекомендуется:')
        print('   - Создать задания для этих навыков')
        print('   - Или исключить их из спецификации генерации')
    
    if spec_data and spec_data['missing_in_spec']:
        print('2. ❌ Не все навыки включены в спецификацию. Нужно:')
        print('   - Пересоздать спецификацию с помощью analyze_dkn_data_requirements.py')
    
    if not coverage_ok:
        print('3. ❌ Генератор не может охватить все навыки из-за отсутствия заданий')
        print('   - Нужно создать задания или обновить спецификацию')
    else:
        print('3. ✅ Генератор может охватить все навыки из спецификации')
    
    print('\n🚀 Готовность к генерации:', '✅ ДА' if coverage_ok else '❌ НЕТ')

if __name__ == "__main__":
    main()
