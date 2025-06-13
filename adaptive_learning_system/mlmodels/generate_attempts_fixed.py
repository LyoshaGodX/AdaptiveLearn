#!/usr/bin/env python
"""
Скрипт для генерации тестовых попыток для студента ID: 2 (Анна Козлова)
ИСПРАВЛЕННАЯ ВЕРСИЯ с правильным timezone

Алгоритм:
1. Находит курсы, на которые подписан студент
2. Собирает все задания из этих курсов  
3. Выбирает до 30 случайных заданий с ограничением: не более 2 заданий на развитие одного навыка
4. Создает по 2 попытки на каждое задание
5. Записывает попытки в базу данных с правильным timezone
"""

import os
import sys
import django
import random
from datetime import timedelta

# Настройка Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth.models import User
from student.models import StudentProfile, StudentCourseEnrollment
from methodist.models import Task
from mlmodels.models import TaskAttempt
from skills.models import Course, Skill


def main():
    print("=" * 60)
    print("🎯 ГЕНЕРАТОР ТЕСТОВЫХ ПОПЫТОК (БЕЗ TIMEZONE ОШИБОК)")
    print("=" * 60)
    
    # Находим тестового студента
    try:
        student_profile = StudentProfile.objects.get(id=2)
        print(f"👨‍🎓 Студент: {student_profile.full_name}")
        print(f"📧 Email: {student_profile.user.email}")
    except StudentProfile.DoesNotExist:
        print("❌ Студент с ID=2 не найден!")
        return
    
    print("\n" + "─" * 60)
    print("📚 АНАЛИЗ ПОДПИСОК НА КУРСЫ")
    print("─" * 60)
    
    # Находим курсы студента
    enrollments = StudentCourseEnrollment.objects.filter(
        student=student_profile,
        status__in=['enrolled', 'in_progress', 'completed']
    ).select_related('course')
    
    if not enrollments.exists():
        print("❌ Студент не подписан ни на один курс!")
        return
    
    courses = [enrollment.course for enrollment in enrollments]
    print(f"📖 Найдено курсов: {len(courses)}")
    for i, course in enumerate(courses, 1):
        print(f"  {i}. {course.name} (ID: {course.id})")
    
    print("\n" + "─" * 60)
    print("📝 СБОР ЗАДАНИЙ ИЗ КУРСОВ")
    print("─" * 60)
    
    # Собираем все задания из курсов студента
    all_tasks = Task.objects.filter(
        courses__in=courses,
        is_active=True
    ).prefetch_related('skills').distinct()
    
    print(f"📋 Найдено активных заданий: {all_tasks.count()}")
    
    if all_tasks.count() == 0:
        print("❌ В курсах студента нет активных заданий!")
        return
    
    print("\n" + "─" * 60)
    print("🎲 ВЫБОР СЛУЧАЙНЫХ ЗАДАНИЙ (до 30 шт)")
    print("─" * 60)
    
    # Выбираем до 30 заданий с ограничением: не более 2 заданий на навык
    selected_tasks = []
    skill_task_count = {}
    
    # Перемешиваем задания для случайного выбора
    tasks_list = list(all_tasks)
    random.shuffle(tasks_list)
    
    print("🔍 Анализируем задания по навыкам...")
    
    for task in tasks_list:
        if len(selected_tasks) >= 30:
            break
            
        task_skills = list(task.skills.all())
        
        # Проверяем, можно ли добавить это задание
        can_add = True
        for skill in task_skills:
            if skill_task_count.get(skill.id, 0) >= 2:
                can_add = False
                break
        
        if can_add:
            selected_tasks.append(task)
            # Увеличиваем счетчик для всех навыков этого задания
            for skill in task_skills:
                skill_task_count[skill.id] = skill_task_count.get(skill.id, 0) + 1
    
    print(f"🎯 Выбрано заданий: {len(selected_tasks)}")
    
    # Показываем статистику по навыкам
    all_selected_skills = set()
    for i, task in enumerate(selected_tasks, 1):
        skills_names = [skill.name for skill in task.skills.all()]
        all_selected_skills.update(task.skills.all())
        print(f"  {i}. {task.title}")
        print(f"     Навыки: {', '.join(skills_names)}")
        print(f"     Сложность: {task.get_difficulty_display()}")
    
    print(f"\n📊 Статистика распределения по навыкам:")
    for skill_id, count in skill_task_count.items():
        skill_name = next((skill.name for skill in all_selected_skills if skill.id == skill_id), f"ID:{skill_id}")
        print(f"  • {skill_name}: {count} заданий")
    
    print("\n" + "─" * 60)
    print("💾 СОЗДАНИЕ ПОПЫТОК")
    print("─" * 60)
    
    # Проверяем, есть ли уже попытки для этих заданий
    existing_attempts = TaskAttempt.objects.filter(
        student=student_profile,
        task__in=selected_tasks
    ).count()
    
    if existing_attempts > 0:
        print(f"⚠️  Найдено {existing_attempts} существующих попыток для выбранных заданий")
        choice = input("Продолжить создание новых попыток? (y/n): ").lower()
        if choice != 'y':
            print("❌ Отменено пользователем")
            return
    
    attempts_created = 0
    base_time = timezone.now() - timedelta(days=7)  # Начинаем с недели назад
    
    for i, task in enumerate(selected_tasks):
        print(f"\n📝 Создание попыток для задания: {task.title}")
        
        # Создаем 2 попытки для каждого задания
        for attempt_num in range(2):
            # Случайно определяем правильность ответа (70% правильных)
            is_correct = random.random() < 0.7
            
            # Случайное время начала и завершения (timezone-aware)
            start_time = base_time + timedelta(
                days=i,
                hours=random.randint(9, 18),
                minutes=random.randint(0, 59)
            )
            
            # Время решения от 30 секунд до 10 минут
            solve_duration = random.randint(30, 600)
            end_time = start_time + timedelta(seconds=solve_duration)
            
            # Создаем попытку с timezone-aware datetime
            attempt = TaskAttempt.objects.create(
                student=student_profile,
                task=task,
                is_correct=is_correct,
                metadata={'generated': True, 'attempt': attempt_num + 1, 'timezone_fixed': True},
                started_at=start_time,
                time_spent=solve_duration
            )
            
            # Обновляем completed_at
            attempt.completed_at = end_time
            attempt.save()
            
            attempts_created += 1
            result = "✅ Правильно" if is_correct else "❌ Неправильно"
            print(f"  Попытка {attempt_num + 1}: {result} ({solve_duration}s) - ✨ Без timezone ошибок!")
    
    print("\n" + "─" * 60)
    print("📊 ИТОГИ")
    print("─" * 60)
    print(f"✅ Создано попыток: {attempts_created}")
    print(f"📝 Заданий обработано: {len(selected_tasks)}")
    print(f"🧠 Уникальных навыков: {len(all_selected_skills)}")
    print(f"🕐 Все timestamp созданы с правильным timezone!")
    
    # Проверим, что BKT обновился автоматически
    print(f"\n🔄 Проверяем автоматическое обновление BKT...")
    from mlmodels.models import StudentSkillMastery
    
    skill_masteries = StudentSkillMastery.objects.filter(
        student=student_profile,
        skill__in=all_selected_skills
    )
    
    print(f"📈 Найдено записей о навыках: {skill_masteries.count()}")
    
    if skill_masteries.exists():
        print("\n🎯 Топ-5 навыков по вероятности освоения:")
        top_skills = skill_masteries.order_by('-current_mastery_prob')[:5]
        for skill_mastery in top_skills:
            print(f"  • {skill_mastery.skill.name}: "
                  f"{skill_mastery.current_mastery_prob:.2%}")
    
    print("\n" + "=" * 60)
    print("🎉 ГЕНЕРАЦИЯ ЗАВЕРШЕНА УСПЕШНО! БЕЗ ОШИБОК!")
    print("=" * 60)


if __name__ == '__main__':
    main()
