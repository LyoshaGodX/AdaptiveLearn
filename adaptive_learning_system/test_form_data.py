#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

from skills.models import Skill, Course
from methodist.models import Task, TaskType, DifficultyLevel

# Проверим, что данные загружаются правильно для формы
print("=== ДАННЫЕ ДЛЯ ФОРМЫ СОЗДАНИЯ ЗАДАНИЯ ===")

print(f"\nНавыки: {Skill.objects.count()}")
skills = Skill.objects.prefetch_related('courses').all()[:5]
for skill in skills:
    courses = [c.name for c in skill.courses.all()]
    print(f"  - {skill.name} (курсы: {courses if courses else 'без курса'})")

print(f"\nКурсы: {Course.objects.count()}")
for course in Course.objects.all():
    print(f"  - {course.name}")

print(f"\nТипы заданий:")
for value, label in TaskType.choices:
    print(f"  - {value}: {label}")

print(f"\nУровни сложности:")
for value, label in DifficultyLevel.choices:
    print(f"  - {value}: {label}")

print(f"\nСуществующие задания: {Task.objects.count()}")
