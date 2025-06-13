#!/usr/bin/env python
"""
Скрипт для полной очистки данных тестового студента ID: 2 (Анна Козлова)

Удаляет:
- Все попытки решения заданий (TaskAttempt)
- Все записи о навыках (StudentSkillMastery)
- Профиль обучения (StudentLearningProfile)
- Статистику и метрики

ВНИМАНИЕ: Операция необратима!
"""

import os
import sys
import django
from datetime import datetime

# Настройка Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

from django.contrib.auth.models import User
from student.models import StudentProfile
from mlmodels.models import TaskAttempt, StudentSkillMastery, StudentLearningProfile


def main():
    print("=" * 70)
    print("🗑️  ПОЛНАЯ ОЧИСТКА ДАННЫХ ТЕСТОВОГО СТУДЕНТА")
    print("=" * 70)
    
    # Находим тестового студента
    try:
        student_profile = StudentProfile.objects.get(id=2)
        print(f"👨‍🎓 Студент: {student_profile.full_name}")
        print(f"📧 Email: {student_profile.user.email}")
    except StudentProfile.DoesNotExist:
        print("❌ Студент с ID=2 не найден!")
        return
    
    print("\n" + "─" * 70)
    print("📊 АНАЛИЗ ТЕКУЩИХ ДАННЫХ")
    print("─" * 70)
    
    # Подсчитываем данные для удаления
    attempts_count = TaskAttempt.objects.filter(student=student_profile).count()
    skills_count = StudentSkillMastery.objects.filter(student=student_profile).count()
    
    try:
        learning_profile = StudentLearningProfile.objects.get(student=student_profile)
        has_learning_profile = True
    except StudentLearningProfile.DoesNotExist:
        has_learning_profile = False
    
    print(f"📝 Попыток решения заданий: {attempts_count}")
    print(f"🧠 Записей о навыках: {skills_count}")
    print(f"📈 Профиль обучения: {'Есть' if has_learning_profile else 'Нет'}")
    
    if attempts_count == 0 and skills_count == 0 and not has_learning_profile:
        print("\n✅ Данные студента уже очищены!")
        return
    
    print("\n" + "─" * 70)
    print("⚠️  ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ")
    print("─" * 70)
    print("ВНИМАНИЕ: Эта операция необратима!")
    print("Будут удалены:")
    if attempts_count > 0:
        print(f"  • {attempts_count} попыток решения заданий")
    if skills_count > 0:
        print(f"  • {skills_count} записей о навыках (BKT-данные)")
    if has_learning_profile:
        print(f"  • Профиль обучения студента")
    
    confirmation = input("\nВы уверены, что хотите удалить все данные? (yes/no): ").strip().lower()
    
    if confirmation not in ['yes', 'y', 'да', 'д']:
        print("❌ Операция отменена пользователем")
        return
    
    print("\n" + "─" * 70)
    print("🗑️  ВЫПОЛНЕНИЕ УДАЛЕНИЯ")
    print("─" * 70)
    
    deleted_total = 0
    
    # 1. Удаляем все попытки решения заданий
    if attempts_count > 0:
        print(f"🗑️  Удаляем {attempts_count} попыток решения заданий...")
        deleted_attempts = TaskAttempt.objects.filter(student=student_profile).delete()
        deleted_count = deleted_attempts[0] if deleted_attempts[0] else 0
        deleted_total += deleted_count
        print(f"   ✅ Удалено: {deleted_count} попыток")
    
    # 2. Удаляем все записи о навыках
    if skills_count > 0:
        print(f"🗑️  Удаляем {skills_count} записей о навыках...")
        deleted_skills = StudentSkillMastery.objects.filter(student=student_profile).delete()
        deleted_count = deleted_skills[0] if deleted_skills[0] else 0
        deleted_total += deleted_count
        print(f"   ✅ Удалено: {deleted_count} записей о навыках")
    
    # 3. Удаляем профиль обучения
    if has_learning_profile:
        print(f"🗑️  Удаляем профиль обучения...")
        deleted_profile = StudentLearningProfile.objects.filter(student=student_profile).delete()
        deleted_count = deleted_profile[0] if deleted_profile[0] else 0
        deleted_total += deleted_count
        print(f"   ✅ Удалено: {deleted_count} профиль обучения")
    
    print("\n" + "─" * 70)
    print("🔄 ПРОВЕРКА РЕЗУЛЬТАТА")
    print("─" * 70)
    
    # Проверяем, что все данные действительно удалены
    final_attempts = TaskAttempt.objects.filter(student=student_profile).count()
    final_skills = StudentSkillMastery.objects.filter(student=student_profile).count()
    final_profile = StudentLearningProfile.objects.filter(student=student_profile).count()
    
    print(f"📝 Попыток решения заданий: {final_attempts}")
    print(f"🧠 Записей о навыках: {final_skills}")
    print(f"📈 Профилей обучения: {final_profile}")
    
    if final_attempts == 0 and final_skills == 0 and final_profile == 0:
        print("\n✅ Все данные успешно удалены!")
    else:
        print("\n⚠️  Не все данные были удалены. Проверьте ограничения базы данных.")
    
    print("\n" + "─" * 70)
    print("📊 ИТОГО")
    print("─" * 70)
    print(f"🗑️  Общее количество удаленных записей: {deleted_total}")
    print(f"👤 Профиль студента: Сохранен (не удален)")
    print(f"🕐 Время выполнения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n" + "=" * 70)
    print("🎉 ОЧИСТКА ДАННЫХ ЗАВЕРШЕНА!")
    print("=" * 70)
    
    # Дополнительная информация
    print("\n💡 Что дальше:")
    print("   • Студент готов для новых тестов")
    print("   • Можно создать новые попытки с помощью generate_test_attempts.py")
    print("   • BKT-модель будет обучаться заново при новых попытках")


if __name__ == '__main__':
    main()
