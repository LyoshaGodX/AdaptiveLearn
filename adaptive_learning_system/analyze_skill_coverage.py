#!/usr/bin/env python
"""
Анализ покрытия навыков в синтетических данных и курсах
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

import pandas as pd
from collections import defaultdict, Counter
from skills.models import Skill
from methodist.models import Task, Course

def analyze_course_structure():
    """Анализ структуры курсов"""
    print('🔍 АНАЛИЗ СТРУКТУРЫ КУРСОВ')
    print('='*50)
    
    courses = Course.objects.all()
    
    for course in courses:
        print(f'\n📚 Курс: {course.name}')
        course_skills = set()
        course_tasks = Task.objects.filter(courses=course)
        
        for task in course_tasks:
            for skill in task.skills.all():
                course_skills.add(skill.id)
        
        print(f'   Заданий: {course_tasks.count()}')
        print(f'   Навыков: {len(course_skills)}')
        print(f'   Навыки: {sorted(course_skills)}')

def analyze_synthetic_coverage():
    """Анализ покрытия навыков в синтетических данных"""
    print('\n🔍 АНАЛИЗ ПОКРЫТИЯ СИНТЕТИЧЕСКИХ ДАННЫХ')
    print('='*50)
    
    # Загружаем синтетические данные
    df = pd.read_csv('temp_dir/synthetic_dataset.csv')
    
    # Получаем все задания, которые встречаются в данных
    tasks_in_data = set(df['task_id'].unique())
    
    # Находим навыки для этих заданий
    skills_in_data = set()
    for task_id in tasks_in_data:
        try:
            task = Task.objects.get(id=task_id)
            for skill in task.skills.all():
                skills_in_data.add(skill.id)
        except Task.DoesNotExist:
            print(f'⚠️ Задание {task_id} не найдено в БД')
    
    # Все навыки в системе
    all_skills = set(Skill.objects.values_list('id', flat=True))
    missing_skills = all_skills - skills_in_data
    
    print(f'Всего навыков в системе: {len(all_skills)}')
    print(f'Навыков в синтетических данных: {len(skills_in_data)}')
    print(f'Отсутствующих навыков: {len(missing_skills)}')
    
    if missing_skills:
        print('\n❌ Отсутствующие навыки:')
        for skill_id in sorted(missing_skills):
            skill_name = Skill.objects.get(id=skill_id).name
            print(f'   - {skill_name} (ID: {skill_id})')
    
    return skills_in_data, missing_skills

def analyze_generation_paths():
    """Анализ путей генерации"""
    print('\n🔍 АНАЛИЗ ПУТЕЙ ГЕНЕРАЦИИ')
    print('='*50)
    
    # Загружаем спецификацию
    import json
    with open('temp_dir/synthetic_data_spec.json', 'r', encoding='utf-8') as f:
        spec = json.load(f)
    
    dependencies = {int(k): [int(x) for x in v] for k, v in spec['skills_graph']['dependencies'].items()}
    levels = {int(k): v for k, v in spec['skills_graph']['levels'].items()}
    
    # Находим базовые навыки (без пререквизитов)
    base_skills = [skill_id for skill_id, deps in dependencies.items() if not deps]
    
    print(f'Базовых навыков: {len(base_skills)}')
    print(f'Базовые навыки: {base_skills}')
    
    # Анализ уровней
    print('\nРаспределение по уровням:')
    level_counts = Counter(levels.values())
    for level in sorted(level_counts.keys()):
        skills_at_level = [skill_id for skill_id, skill_level in levels.items() if skill_level == level]
        print(f'   Уровень {level}: {level_counts[level]} навыков - {skills_at_level}')
    
    return base_skills, levels, dependencies

def identify_unreachable_skills(base_skills, levels, dependencies, max_attempts=50):
    """Определяем недостижимые навыки при ограниченном количестве попыток"""
    print(f'\n🔍 АНАЛИЗ ДОСТИЖИМОСТИ НАВЫКОВ (max_attempts={max_attempts})')
    print('='*50)
    
    # Симулируем путь студента
    reachable_in_attempts = set()
    
    # Начинаем с базовых навыков
    available_skills = set(base_skills)
    mastered_skills = set()
    attempts_used = 0
    
    # Средние попытки для освоения навыка (на основе сложности)
    attempts_per_skill = {
        0: 3,   # Базовые навыки
        1: 4,   # Первый уровень
        2: 5,   # Второй уровень
    }
    
    while attempts_used < max_attempts and available_skills:
        # Выбираем навык с минимальным уровнем
        current_skill = min(available_skills, key=lambda s: levels.get(s, 0))
        skill_level = levels.get(current_skill, 0)
          # Попытки для освоения навыка
        needed_attempts = attempts_per_skill.get(skill_level, skill_level + 3)
        if needed_attempts is None:
            needed_attempts = skill_level + 3
        
        if attempts_used + needed_attempts <= max_attempts:
            # Можем освоить этот навык
            mastered_skills.add(current_skill)
            reachable_in_attempts.add(current_skill)
            available_skills.remove(current_skill)
            attempts_used += needed_attempts
            
            # Добавляем новые доступные навыки
            for skill_id, prereqs in dependencies.items():
                if skill_id not in mastered_skills and skill_id not in available_skills:
                    if all(prereq in mastered_skills for prereq in prereqs):
                        available_skills.add(skill_id)
        else:
            # Не хватает попыток
            break
    
    all_skills = set(dependencies.keys())
    unreachable_skills = all_skills - reachable_in_attempts
    
    print(f'Достижимых навыков за {max_attempts} попыток: {len(reachable_in_attempts)}')
    print(f'Недостижимых навыков: {len(unreachable_skills)}')
    
    if unreachable_skills:
        print('\n❌ Недостижимые навыки:')
        for skill_id in sorted(unreachable_skills):
            skill_name = Skill.objects.get(id=skill_id).name
            skill_level = levels.get(skill_id, 0)
            print(f'   - {skill_name} (ID: {skill_id}, уровень: {skill_level})')
    
    return reachable_in_attempts, unreachable_skills

def suggest_improvements():
    """Предложения по улучшению покрытия"""
    print('\n💡 ПРЕДЛОЖЕНИЯ ПО УЛУЧШЕНИЮ')
    print('='*50)
    
    print('1. 📈 Увеличить количество попыток на студента:')
    print('   - Сейчас: ~43 попытки на студента')
    print('   - Рекомендуется: 80-120 попыток на студента')
    
    print('\n2. 👥 Создать специализированные архетипы студентов:')
    print('   - Студенты разных курсов (1-й, 2-й, 3-й)')
    print('   - Студенты с разным фокусом на навыки')
    
    print('\n3. 🎯 Улучшить алгоритм выбора навыков:')
    print('   - Обеспечить равномерное покрытие всех уровней')
    print('   - Добавить стохастичность в выбор следующего навыка')
    
    print('\n4. 📊 Создать балансированные данные:')
    print('   - Гарантировать минимальное количество примеров для каждого навыка')
    print('   - Добавить "продвинутых" студентов, которые доходят до высоких уровней')

def main():
    """Основная функция анализа"""
    
    # Анализ структуры курсов
    analyze_course_structure()
    
    # Анализ покрытия синтетических данных
    skills_in_data, missing_skills = analyze_synthetic_coverage()
    
    # Анализ путей генерации
    base_skills, levels, dependencies = analyze_generation_paths()
    
    # Анализ достижимости навыков
    reachable_43, unreachable_43 = identify_unreachable_skills(base_skills, levels, dependencies, max_attempts=43)
    reachable_80, unreachable_80 = identify_unreachable_skills(base_skills, levels, dependencies, max_attempts=80)
    reachable_120, unreachable_120 = identify_unreachable_skills(base_skills, levels, dependencies, max_attempts=120)
    
    # Предложения по улучшению
    suggest_improvements()
    
    print('\n🎯 ВЫВОД')
    print('='*50)
    print(f'Текущее покрытие навыков в синтетических данных: {len(skills_in_data)}/30')
    print(f'Теоретически достижимо за 43 попытки: {len(reachable_43)}/30')
    print(f'Теоретически достижимо за 80 попыток: {len(reachable_80)}/30')  
    print(f'Теоретически достижимо за 120 попыток: {len(reachable_120)}/30')
    
    if len(skills_in_data) < 25:  # Менее 25 из 30 навыков
        print('\n⚠️ КРИТИЧЕСКАЯ ПРОБЛЕМА: Недостаточное покрытие навыков!')
        print('   Необходимо изменить алгоритм генерации данных.')
    else:
        print('\n✅ Покрытие навыков приемлемое.')

if __name__ == "__main__":
    main()
