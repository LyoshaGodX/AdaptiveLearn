#!/usr/bin/env python3
"""
Детальная проверка данных студента ID=2

Этот скрипт проверяет все возможные источники данных для студента:
- TaskAttempt (попытки решения задач)
- StudentSkillMastery (освоение навыков)
- StudentLearningProfile (профиль обучения)
- Любые другие связанные данные
"""

import os
import sys
import django
from pathlib import Path
from datetime import datetime

# Настройка Django
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

from django.contrib.auth.models import User
from django.db import models
from skills.models import Skill
from methodist.models import Task, Course
from mlmodels.models import TaskAttempt, StudentSkillMastery, StudentLearningProfile
from student.models import StudentProfile


def check_student_data(student_id: int = 2):
    """Детальная проверка всех данных студента"""
    print(f"🔍 Детальная проверка данных студента ID: {student_id}")
    print("=" * 70)
    
    # 1. Базовая информация о пользователе
    print("1. Базовая информация:")
    try:
        user = User.objects.get(id=student_id)
        print(f"   ✅ Пользователь: {user.username}")
        print(f"   📧 Email: {user.email}")
        print(f"   📅 Дата регистрации: {user.date_joined}")
        print(f"   👤 Имя: {user.first_name} {user.last_name}")
        print(f"   🏃 Активен: {user.is_active}")
        print(f"   👨‍💼 Персонал: {user.is_staff}")
        print(f"   🔑 Суперпользователь: {user.is_superuser}")
    except User.DoesNotExist:
        print(f"   ❌ Пользователь ID={student_id} не найден!")
        return
      # 2. Профиль студента
    print("\n2. Профиль студента:")
    try:
        student_profile = StudentProfile.objects.get(user=user)
        print(f"   ✅ Профиль найден")
        # Выведем все поля профиля
        for field in student_profile._meta.fields:
            if field.name not in ['id', 'user']:
                value = getattr(student_profile, field.name)
                if value:  # Показываем только непустые значения
                    print(f"   📋 {field.name}: {value}")
                else:
                    print(f"   📋 {field.name}: (пусто)")
    except StudentProfile.DoesNotExist:
        print(f"   ⚠️  Профиль студента не найден")
      # 3. Попытки решения задач (TaskAttempt)
    print("\n3. Попытки решения задач (TaskAttempt):")
    attempts = TaskAttempt.objects.filter(student_id=student_id)
    print(f"   📊 Всего попыток: {attempts.count()}")
    
    if attempts.exists():
        print("   📋 Детали попыток:")
        for i, attempt in enumerate(attempts.order_by('-started_at')[:10], 1):
            print(f"   {i:2d}. Задача: {attempt.task.title if attempt.task else 'Без названия'}")
            print(f"       🆔 Task ID: {attempt.task_id}")
            print(f"       ✅ Успех: {attempt.is_correct}")
            print(f"       📅 Начало: {attempt.started_at}")
            print(f"       ⏱️  Время: {attempt.time_spent}с")
            if hasattr(attempt, 'given_answer') and attempt.given_answer:
                print(f"       💭 Ответ: {str(attempt.given_answer)[:100]}...")
            print()
    else:
        print("   ❌ Попыток не найдено")
    
    # 4. Освоение навыков (StudentSkillMastery)
    print("4. Освоение навыков (StudentSkillMastery):")
    skill_masteries = StudentSkillMastery.objects.filter(student_id=student_id)
    print(f"   📊 Навыков отслеживается: {skill_masteries.count()}")    
    if skill_masteries.exists():
        print("   📋 Детали освоения навыков:")
        for mastery in skill_masteries.order_by('-current_mastery_prob')[:15]:
            print(f"   • {mastery.skill.name}: {mastery.current_mastery_prob:.3f}")
            print(f"     BKT: L={mastery.transition_prob:.3f}, G={mastery.guess_prob:.3f}, "
                  f"S={mastery.slip_prob:.3f}, P={mastery.initial_mastery_prob:.3f}")
            print(f"     Обновлено: {mastery.last_updated}")
            print()
    else:
        print("   ❌ Данных об освоении навыков не найдено")
    
    # 5. Профиль обучения (StudentLearningProfile)
    print("5. Профиль обучения (StudentLearningProfile):")
    learning_profiles = StudentLearningProfile.objects.filter(student_id=student_id)
    print(f"   📊 Профилей обучения: {learning_profiles.count()}")
    
    if learning_profiles.exists():
        print("   📋 Детали профилей:")
        for profile in learning_profiles:
            print(f"   • Тип: {profile.learning_style}")
            print(f"     Предпочтения: {profile.preferences}")
            print(f"     Метаданные: {profile.metadata}")
            print(f"     Создан: {profile.created_at}")
            print()
    else:
        print("   ❌ Профилей обучения не найдено")
    
    # 6. Проверим все модели, которые могут содержать данные студента
    print("6. Поиск в других моделях:")
    
    # Проверим все модели из mlmodels
    from mlmodels import models as ml_models
    model_classes = [getattr(ml_models, name) for name in dir(ml_models) 
                    if isinstance(getattr(ml_models, name), type) and 
                    issubclass(getattr(ml_models, name), django.db.models.Model)]
    
    for model_class in model_classes:
        if hasattr(model_class, 'student_id') or hasattr(model_class, 'student'):
            try:
                if hasattr(model_class, 'student_id'):
                    count = model_class.objects.filter(student_id=student_id).count()
                else:
                    count = model_class.objects.filter(student=user).count()
                
                if count > 0:
                    print(f"   ✅ {model_class.__name__}: {count} записей")
                    
                    # Покажем несколько примеров
                    if hasattr(model_class, 'student_id'):
                        samples = model_class.objects.filter(student_id=student_id)[:3]
                    else:
                        samples = model_class.objects.filter(student=user)[:3]
                    
                    for sample in samples:
                        print(f"      - {sample}")
                        
            except Exception as e:
                pass  # Игнорируем ошибки
    
    # 7. Статистика базы данных
    print("\n7. Общая статистика базы данных:")
    print(f"   👥 Всего пользователей: {User.objects.count()}")
    print(f"   🎓 Профилей студентов: {StudentProfile.objects.count()}")
    print(f"   📝 Всего попыток: {TaskAttempt.objects.count()}")
    print(f"   🧠 Записей освоения навыков: {StudentSkillMastery.objects.count()}")
    print(f"   📊 Профилей обучения: {StudentLearningProfile.objects.count()}")
    print(f"   📚 Навыков: {Skill.objects.count()}")
    print(f"   📋 Задач: {Task.objects.count()}")
    print(f"   🎯 Курсов: {Course.objects.count()}")
    
    # 8. Попытки для других студентов (для сравнения)
    print("\n8. Для сравнения - попытки других студентов:")
    other_attempts = TaskAttempt.objects.exclude(student_id=student_id).values('student_id').annotate(
        count=models.Count('id')
    ).order_by('-count')[:5]
    
    for attempt_stat in other_attempts:
        student_id_other = attempt_stat['student_id']
        count = attempt_stat['count']
        try:
            other_user = User.objects.get(id=student_id_other)
            print(f"   👤 Студент {other_user.username} (ID: {student_id_other}): {count} попыток")
        except User.DoesNotExist:
            print(f"   👤 Студент ID {student_id_other}: {count} попыток")


if __name__ == "__main__":
    check_student_data(2)
    print("\n" + "=" * 70)
    print("🔍 Детальная проверка завершена!")
