#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

from methodist.models import Skill, Course
from skills.models import Skill as SkillsSkill, Course as SkillsCourse

def check_data():
    print("=== ПРОВЕРКА ДАННЫХ В БАЗЕ ===")
    
    print("\n1. Данные в приложении 'skills':")
    skills_courses = SkillsCourse.objects.all()
    skills_skills = SkillsSkill.objects.all()
    
    print(f"   Курсов в skills: {skills_courses.count()}")
    for course in skills_courses:
        print(f"     - {course.id}: {course.name}")
    
    print(f"   Навыков в skills: {skills_skills.count()}")
    for skill in skills_skills[:5]:  # Показываем первые 5
        print(f"     - {skill.id}: {skill.name} (базовый: {skill.is_base})")
    if skills_skills.count() > 5:
        print(f"     ... и еще {skills_skills.count() - 5} навыков")
    
    print("\n2. Данные в приложении 'methodist':")
    methodist_courses = Course.objects.all()
    methodist_skills = Skill.objects.all()
    
    print(f"   Курсов в methodist: {methodist_courses.count()}")
    for course in methodist_courses:
        print(f"     - {course.id}: {course.name}")
    
    print(f"   Навыков в methodist: {methodist_skills.count()}")
    for skill in methodist_skills[:5]:  # Показываем первые 5
        print(f"     - {skill.id}: {skill.name} (базовый: {skill.is_base})")
    if methodist_skills.count() > 5:
        print(f"     ... и еще {methodist_skills.count() - 5} навыков")
    
    print("\n3. Проверка связей:")
    if methodist_skills.exists():
        first_skill = methodist_skills.first()
        print(f"   Первый навык: {first_skill.name}")
        print(f"   Курсы этого навыка: {list(first_skill.courses.values_list('name', flat=True))}")
        print(f"   Предпосылки: {list(first_skill.prerequisites.values_list('name', flat=True))}")
        print(f"   Зависимые навыки: {list(first_skill.dependent_skills.values_list('name', flat=True))}")
    
    print("\n=== ЗАКЛЮЧЕНИЕ ===")
    if methodist_skills.count() == 0:
        print("❌ Данные в приложении methodist отсутствуют!")
        if skills_skills.count() > 0:
            print("⚠️  Но данные есть в приложении skills - нужно выполнить перенос")
        else:
            print("⚠️  Данных нет ни в одном приложении - нужно импортировать из DOT файла")
    else:
        print("✅ Данные в приложении methodist найдены!")

if __name__ == "__main__":
    check_data()
