#!/usr/bin/env python
import os
import sys
import django

# Добавляем путь к проекту
sys.path.append('c:/Users/AKlem/Documents/Python projects/AdaptiveLearn/adaptive_learning_system')

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

# Импортируем модели
from methodist.models import Skill, Course
from skills.models import Skill as SkillsSkill, Course as SkillsCourse

def main():
    print('=== ПРОВЕРКА ДАННЫХ В БАЗЕ ===')
    
    # Проверка данных в приложении skills
    print('\n--- Данные в приложении SKILLS ---')
    skills_courses = SkillsCourse.objects.all()
    skills_skills = SkillsSkill.objects.all()
    
    print(f'Курсов в skills: {skills_courses.count()}')
    for course in skills_courses:
        print(f'  - Курс: {course.id} - {course.name}')
    
    print(f'Навыков в skills: {skills_skills.count()}')
    for skill in skills_skills[:10]:  # Показываем первые 10
        prereqs = skill.prerequisites.all()
        courses = skill.courses.all()
        print(f'  - Навык: {skill.id} - {skill.name} (базовый: {skill.is_base})')
        if prereqs.exists():
            print(f'    Предпосылки: {[p.name for p in prereqs]}')
        if courses.exists():
            print(f'    Курсы: {[c.name for c in courses]}')
    
    if skills_skills.count() > 10:
        print(f'  ... и еще {skills_skills.count() - 10} навыков')
    
    # Проверка данных в приложении methodist
    print('\n--- Данные в приложении METHODIST ---')
    methodist_courses = Course.objects.all()
    methodist_skills = Skill.objects.all()
    
    print(f'Курсов в methodist: {methodist_courses.count()}')
    for course in methodist_courses:
        print(f'  - Курс: {course.id} - {course.name}')
    
    print(f'Навыков в methodist: {methodist_skills.count()}')
    for skill in methodist_skills[:10]:  # Показываем первые 10
        prereqs = skill.prerequisites.all()
        courses = skill.courses.all()
        print(f'  - Навык: {skill.id} - {skill.name} (базовый: {skill.is_base})')
        if prereqs.exists():
            print(f'    Предпосылки: {[p.name for p in prereqs]}')
        if courses.exists():
            print(f'    Курсы: {[c.name for c in courses]}')
    
    if methodist_skills.count() > 10:
        print(f'  ... и еще {methodist_skills.count() - 10} навыков')
    
    # Проверка связей
    print('\n--- ПРОВЕРКА СВЯЗЕЙ ---')
    total_prereq_relations_skills = sum(skill.prerequisites.count() for skill in skills_skills)
    total_prereq_relations_methodist = sum(skill.prerequisites.count() for skill in methodist_skills)
    
    print(f'Связей предпосылок в skills: {total_prereq_relations_skills}')
    print(f'Связей предпосылок в methodist: {total_prereq_relations_methodist}')
    
    total_course_relations_skills = sum(skill.courses.count() for skill in skills_skills)
    total_course_relations_methodist = sum(skill.courses.count() for skill in methodist_skills)
    
    print(f'Связей навык-курс в skills: {total_course_relations_skills}')
    print(f'Связей навык-курс в methodist: {total_course_relations_methodist}')
    
    # Сравнение данных
    print('\n--- СРАВНЕНИЕ ---')
    if skills_courses.count() == methodist_courses.count():
        print('✓ Количество курсов совпадает')
    else:
        print('✗ Количество курсов НЕ совпадает')
    
    if skills_skills.count() == methodist_skills.count():
        print('✓ Количество навыков совпадает')
    else:
        print('✗ Количество навыков НЕ совпадает')
    
    if total_prereq_relations_skills == total_prereq_relations_methodist:
        print('✓ Количество связей предпосылок совпадает')
    else:
        print('✗ Количество связей предпосылок НЕ совпадает')
    
    if total_course_relations_skills == total_course_relations_methodist:
        print('✓ Количество связей навык-курс совпадает')
    else:
        print('✗ Количество связей навык-курс НЕ совпадает')
    
    # Проверка импорта данных
    print('\n--- РЕКОМЕНДАЦИИ ---')
    if methodist_skills.count() == 0:
        print('⚠ В приложении methodist нет навыков!')
        print('Попробуйте импортировать данные командой:')
        print('python manage.py import_skills_dot')
    elif methodist_skills.count() < skills_skills.count():
        print('⚠ В приложении methodist меньше навыков, чем в skills!')
        print('Возможно, миграция данных прошла не полностью.')
    else:
        print('✓ Данные в приложении methodist присутствуют')
    
    print('\n=== ПРОВЕРКА ЗАВЕРШЕНА ===')

if __name__ == '__main__':
    main()
