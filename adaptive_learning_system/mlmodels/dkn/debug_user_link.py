#!/usr/bin/env python3
"""
Проверка связи между User и StudentProfile для студента ID=2
"""

import os
import sys
import django
from pathlib import Path

# Настройка Django
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

from django.contrib.auth.models import User
from mlmodels.models import TaskAttempt, StudentSkillMastery
from student.models import StudentProfile


def debug_user_profile_link():
    print("🔍 Отладка связи User <-> StudentProfile")
    print("=" * 50)
    
    # 1. Проверим User ID=2
    try:
        user2 = User.objects.get(id=2)
        print(f"✅ User ID=2: {user2.username} ({user2.email})")
    except User.DoesNotExist:
        print("❌ User ID=2 не найден!")
        return
    
    # 2. Проверим StudentProfile для этого User
    try:
        profile2 = StudentProfile.objects.get(user=user2)
        print(f"✅ StudentProfile ID={profile2.id}: {profile2.full_name}")
        print(f"   User связан: {profile2.user.username}")
    except StudentProfile.DoesNotExist:
        print("❌ StudentProfile для User ID=2 не найден!")
        return
    
    # 3. Проверим попытки через User ID
    attempts_by_user = TaskAttempt.objects.filter(student__user_id=2)
    print(f"📊 Попытки через student__user_id=2: {attempts_by_user.count()}")
    
    # 4. Проверим попытки через StudentProfile
    attempts_by_profile = TaskAttempt.objects.filter(student=profile2)
    print(f"📊 Попытки через student=profile2: {attempts_by_profile.count()}")
    
    # 5. Проверим попытки через student_id
    attempts_by_student_id = TaskAttempt.objects.filter(student_id=2)
    print(f"📊 Попытки через student_id=2: {attempts_by_student_id.count()}")
    
    # 6. Проверим все TaskAttempt и их student_id
    print("\n🔍 Все попытки в базе:")
    all_attempts = TaskAttempt.objects.all()
    print(f"Всего попыток: {all_attempts.count()}")
    
    for attempt in all_attempts[:5]:
        print(f"  TaskAttempt ID={attempt.id}:")
        print(f"    student_id={attempt.student_id}")
        print(f"    student.user.id={attempt.student.user.id}")
        print(f"    student.full_name={attempt.student.full_name}")
        print(f"    task_id={attempt.task_id}")
        print()
    
    # 7. Все StudentProfile и их User ID
    print("🔍 Все профили студентов:")
    profiles = StudentProfile.objects.all()
    for profile in profiles:
        attempts_count = TaskAttempt.objects.filter(student=profile).count()
        print(f"  StudentProfile ID={profile.id} (User ID={profile.user.id}): "
              f"{profile.full_name} - {attempts_count} попыток")


if __name__ == "__main__":    debug_user_profile_link()
