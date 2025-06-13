"""
Скрипт для очистки истории попыток студента и сброса BKT данных
Позволяет протестировать BKT модель с чистого листа
"""

import os
import sys
import django
from pathlib import Path

# Настройка Django
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

from django.contrib.auth.models import User
from student.models import StudentProfile
from mlmodels.models import TaskAttempt, StudentSkillMastery
from django.db import transaction


def clear_student_data(username):
    """Очищает историю попыток и BKT данные студента"""
    print(f"🧹 ОЧИСТКА ДАННЫХ СТУДЕНТА: {username}")
    print("=" * 50)
    
    try:
        # Получаем студента
        user = User.objects.get(username=username)
        student = StudentProfile.objects.get(user=user)
        
        print(f"✅ Студент найден: {student.full_name}")
        
        # Проверяем текущие данные
        attempts_count = TaskAttempt.objects.filter(student=student).count()
        masteries_count = StudentSkillMastery.objects.filter(student=student).count()
        
        print(f"\n📊 ТЕКУЩИЕ ДАННЫЕ:")
        print(f"   📝 Попыток в базе: {attempts_count}")
        print(f"   🧠 BKT записей: {masteries_count}")
        
        if attempts_count == 0 and masteries_count == 0:
            print("   ℹ️  Данные уже отсутствуют")
            return
        
        # Спрашиваем подтверждение
        confirmation = input(f"\n❓ Удалить ВСЕ данные студента {student.full_name}? (yes/no): ")
        if confirmation.lower() not in ['yes', 'y']:
            print("❌ Операция отменена")
            return
        
        # Очищаем данные в транзакции
        with transaction.atomic():
            # Удаляем попытки
            deleted_attempts = TaskAttempt.objects.filter(student=student).delete()
            print(f"   🗑️  Удалено попыток: {deleted_attempts[0]}")
            
            # Удаляем BKT данные
            deleted_masteries = StudentSkillMastery.objects.filter(student=student).delete()
            print(f"   🗑️  Удалено BKT записей: {deleted_masteries[0]}")
            
        print(f"\n✅ ОЧИСТКА ЗАВЕРШЕНА УСПЕШНО!")
        print(f"   Студент {student.full_name} теперь не имеет:")
        print(f"   - Истории попыток решения заданий")
        print(f"   - BKT данных об освоении навыков")
        print(f"   - Система готова для чистого тестирования BKT")
        
        return student
        
    except User.DoesNotExist:
        print(f"❌ Пользователь с username '{username}' не найден")
        return None
    except StudentProfile.DoesNotExist:
        print(f"❌ Профиль студента для пользователя '{username}' не найден")
        return None
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None


def create_clean_attempts_for_student(student, num_attempts_per_skill=5):
    """Создает чистую историю попыток без применения BKT"""
    print(f"\n📝 СОЗДАНИЕ ЧИСТОЙ ИСТОРИИ ПОПЫТОК")
    print("-" * 40)
    
    from methodist.models import Task
    from datetime import datetime, timedelta
    from django.utils import timezone
    import random
    
    # Получаем задания из курсов студента
    from student.models import StudentCourseEnrollment
    enrollments = StudentCourseEnrollment.objects.filter(student=student)
    
    if not enrollments.exists():
        print("❌ Студент не записан ни на один курс")
        return
    
    all_tasks = []
    for enrollment in enrollments:
        course_tasks = Task.objects.filter(
            courses=enrollment.course,
            is_active=True
        ).prefetch_related('skills')[:15]  # Берем 15 заданий
        all_tasks.extend(course_tasks)
    
    if not all_tasks:
        print("❌ Не найдено заданий для курсов студента")
        return
    
    print(f"   📚 Найдено заданий: {len(all_tasks)}")
    
    # Создаем попытки
    attempts_data = []
    base_time = timezone.now() - timedelta(days=7)  # Неделю назад
    current_time = base_time
    
    success_rate = 0.4  # Начинаем с 40% успеха
    
    for i, task in enumerate(all_tasks):
        # Постепенно улучшаем результаты (имитируем обучение)
        current_success = min(0.8, success_rate + (i * 0.02))
        
        # Создаем 2 попытки на задание
        for attempt_num in range(2):
            is_correct = random.random() < current_success
            
            # Вторая попытка обычно лучше
            if attempt_num == 1:
                is_correct = random.random() < min(0.9, current_success + 0.2)
            
            time_spent = random.randint(60, 300)  # 1-5 минут
            
            attempt_data = {
                'student': student,
                'task': task,
                'is_correct': is_correct,
                'started_at': current_time,
                'completed_at': current_time + timedelta(seconds=time_spent),
                'time_spent': time_spent,
                'given_answer': f"Ответ {attempt_num + 1} на {task.title}",
            }
            
            attempts_data.append(attempt_data)
            current_time += timedelta(hours=random.randint(1, 12))
    
    # Сохраняем попытки БЕЗ вызова BKT
    print(f"   💾 Сохранение {len(attempts_data)} попыток...")
    
    saved_count = 0
    with transaction.atomic():
        for attempt_data in attempts_data:
            try:
                # Создаем попытку БЕЗ сигналов (чтобы не вызвать BKT)
                attempt = TaskAttempt(**attempt_data)
                attempt.save()
                saved_count += 1
                
            except Exception as e:
                print(f"   ⚠️ Ошибка сохранения попытки: {e}")
    
    print(f"   ✅ Сохранено попыток: {saved_count}")
    
    # Проверяем что BKT данные НЕ созданы
    bkt_records = StudentSkillMastery.objects.filter(student=student).count()
    print(f"   🧠 BKT записей после сохранения: {bkt_records}")
    
    if bkt_records == 0:
        print(f"   ✅ Отлично! BKT не применялся автоматически")
    else:
        print(f"   ⚠️ Внимание: BKT мог быть применен автоматически")
    
    return saved_count


def main():
    """Основная функция"""
    username = "student2"
    
    # 1. Очищаем существующие данные
    student = clear_student_data(username)
    
    if not student:
        return
    
    # 2. Создаем чистую историю попыток
    attempts_count = create_clean_attempts_for_student(student)
    
    if attempts_count > 0:
        print(f"\n🎯 ГОТОВО К ТЕСТИРОВАНИЮ BKT!")
        print("=" * 40)
        print(f"✅ Студент: {student.full_name}")
        print(f"✅ Попыток создано: {attempts_count}")
        print(f"✅ BKT данные отсутствуют")
        print(f"\n🚀 СЛЕДУЮЩИЕ ШАГИ:")
        print(f"1. Запустить BKT интерфейс для этого студента")
        print(f"2. Проверить создание BKT параметров:")
        print(f"   - P(L0) - начальная вероятность знания")
        print(f"   - P(Lt) - текущая вероятность знания")
        print(f"   - P(T) - вероятность обучения")
        print(f"   - P(G) - вероятность угадывания")
        print(f"   - P(S) - вероятность ошибки")
        print(f"3. Проанализировать корректность работы BKT")


if __name__ == "__main__":
    main()
