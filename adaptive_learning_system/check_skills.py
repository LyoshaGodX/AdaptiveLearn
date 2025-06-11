#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

# Попробуем импортировать из обеих моделей
try:
    from methodist.models import Skill as MethodistSkill, Course as MethodistCourse
    print("Модели из methodist загружены успешно")
    print(f"Навыки в methodist: {MethodistSkill.objects.count()}")
    print(f"Курсы в methodist: {MethodistCourse.objects.count()}")
except Exception as e:
    print(f"Ошибка при импорте из methodist: {e}")

try:
    from skills.models import Skill as SkillsSkill, Course as SkillsCourse
    print("Модели из skills загружены успешно")
    print(f"Навыки в skills: {SkillsSkill.objects.count()}")
    print(f"Курсы в skills: {SkillsCourse.objects.count()}")
    
    print("\nПервые 10 навыков из skills:")
    for skill in SkillsSkill.objects.prefetch_related('courses').all()[:10]:
        courses = [c.name for c in skill.courses.all()]
        print(f"- {skill.name} (курсы: {courses if courses else 'без курса'})")
        
    print("\nВсе курсы из skills:")
    for course in SkillsCourse.objects.all():
        print(f"- {course.name}")
except Exception as e:
    print(f"Ошибка при импорте из skills: {e}")
