#!/usr/bin/env python3
"""
Скрипт для создания одной тестовой попытки студента

Создает попытку решения задания по навыку "Объектно-ориентированное программирование"
с неудачным результатом для студента ID=15.

Это должно запустить цепочку автоматических процессов:
1. Сохранение попытки в БД
2. Автоматический пересчет BKT параметров
3. Автоматическое создание рекомендации
4. Установка текущей рекомендации для студента
"""

import os
import sys
import django
from pathlib import Path
import random
from django.utils import timezone

# Настройка Django
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

from django.contrib.auth.models import User
from student.models import StudentProfile
from skills.models import Skill
from methodist.models import Task
from mlmodels.models import TaskAttempt, StudentSkillMastery, DQNRecommendation, StudentCurrentRecommendation


def create_test_attempt():
    """Создает тестовую попытку для студента ID=15"""
    
    print("🧪 СОЗДАНИЕ ТЕСТОВОЙ ПОПЫТКИ")
    print("="*60)
    
    # 1. Получаем студента
    try:
        user = User.objects.get(id=15)
        student_profile, _ = StudentProfile.objects.get_or_create(user=user)
        print(f"✅ Студент найден: {user.username} (ID: {user.id})")
    except User.DoesNotExist:
        print("❌ Студент с ID=15 не найден")
        return False
    
    # 2. Получаем навык "Объектно-ориентированное программирование"
    try:
        skill = Skill.objects.get(name="Объектно-ориентированное программирование")
        print(f"✅ Навык найден: {skill.name} (ID: {skill.id})")
    except Skill.DoesNotExist:
        print("❌ Навык 'Объектно-ориентированное программирование' не найден")
        return False
    
    # 3. Получаем задания по этому навыку
    tasks = Task.objects.filter(skills=skill, is_active=True)
    if not tasks.exists():
        print("❌ Нет активных заданий по этому навыку")
        return False
    
    # Выбираем случайное задание
    task = random.choice(tasks)
    print(f"✅ Выбрано задание: {task.title} (ID: {task.id})")
    print(f"   Сложность: {task.difficulty}")
    print(f"   Тип: {task.task_type}")
    
    # 4. Показываем текущее состояние BKT для этого навыка
    try:
        current_bkt = StudentSkillMastery.objects.get(
            student=student_profile,
            skill=skill
        )
        print(f"\n📊 ТЕКУЩЕЕ СОСТОЯНИЕ BKT:")
        print(f"   P(знание) = {current_bkt.current_mastery_prob:.4f}")
        print(f"   Попыток: {current_bkt.attempts_count}")
        print(f"   Правильных: {current_bkt.correct_attempts}")
    except StudentSkillMastery.DoesNotExist:
        print(f"\n📊 BKT данные для навыка отсутствуют (будут созданы)")
    
    # 5. Показываем текущие рекомендации
    current_recommendations = DQNRecommendation.objects.filter(student_id=user.id).count()
    current_rec = StudentCurrentRecommendation.objects.filter(student=student_profile).first()
    
    print(f"\n📋 ТЕКУЩИЕ РЕКОМЕНДАЦИИ:")
    print(f"   Всего рекомендаций: {current_recommendations}")
    if current_rec:
        print(f"   Текущая рекомендация: Задание #{current_rec.recommendation.task.id}")
    else:
        print(f"   Текущая рекомендация: Нет")
    
    # 6. Создаем неудачную попытку
    print(f"\n🎯 СОЗДАНИЕ ПОПЫТКИ...")
    print(f"   Результат: ❌ Неправильно")
    
    try:
        # Создаем попытку с неудачным результатом
        attempt = TaskAttempt.objects.create(
            student=student_profile,
            task=task,
            is_correct=False,  # Неудачный результат
            given_answer="Неправильный ответ студента",
            correct_answer=f"Правильный ответ на задание {task.id}",
            started_at=timezone.now(),
            time_spent=random.randint(60, 300),  # от 1 до 5 минут
            metadata={
                'test_attempt': True,
                'skill': skill.name,
                'auto_generated': True
            }
        )
        
        print(f"✅ Попытка создана с ID: {attempt.id}")
        print(f"   Время выполнения: {attempt.completed_at}")
        print(f"   Потрачено времени: {attempt.time_spent} сек")
        
        # 7. Проверяем автоматические изменения
        print(f"\n🔄 ПРОВЕРКА АВТОМАТИЧЕСКИХ ИЗМЕНЕНИЙ...")
        
        # Проверяем обновление BKT
        try:
            updated_bkt = StudentSkillMastery.objects.get(
                student=student_profile,
                skill=skill
            )
            print(f"✅ BKT обновлен:")
            print(f"   P(знание) = {updated_bkt.current_mastery_prob:.4f}")
            print(f"   Попыток: {updated_bkt.attempts_count}")
            print(f"   Правильных: {updated_bkt.correct_attempts}")
        except StudentSkillMastery.DoesNotExist:
            print(f"⚠️ BKT данные не найдены после создания попытки")
        
        # Проверяем создание рекомендаций
        new_recommendations_count = DQNRecommendation.objects.filter(student_id=user.id).count()
        new_current_rec = StudentCurrentRecommendation.objects.filter(student=student_profile).first()
        
        print(f"\n📋 РЕКОМЕНДАЦИИ ПОСЛЕ ПОПЫТКИ:")
        print(f"   Всего рекомендаций: {new_recommendations_count}")
        
        if new_recommendations_count > current_recommendations:
            print(f"   ✅ Создано новых рекомендаций: {new_recommendations_count - current_recommendations}")
            
            # Показываем последнюю рекомендацию
            latest_rec = DQNRecommendation.objects.filter(student_id=user.id).order_by('-created_at').first()
            if latest_rec:
                print(f"   📋 Последняя рекомендация:")
                print(f"      ID: {latest_rec.id}")
                print(f"      Задание: {latest_rec.task.title}")
                print(f"      Q-value: {latest_rec.q_value:.4f}")
                print(f"      Уверенность: {latest_rec.confidence:.4f}")
        else:
            print(f"   ⚠️ Новые рекомендации не созданы")
        
        if new_current_rec:
            if not current_rec or new_current_rec.recommendation.id != current_rec.recommendation.id:
                print(f"   ✅ Текущая рекомендация обновлена:")
                print(f"      Задание: {new_current_rec.recommendation.task.title}")
                print(f"      Установлена: {new_current_rec.set_at}")
            else:
                print(f"   📌 Текущая рекомендация не изменилась")
        else:
            print(f"   ⚠️ Текущая рекомендация не установлена")
        
        print(f"\n🎉 ПОПЫТКА УСПЕШНО СОЗДАНА!")
        print(f"   Попытка ID: {attempt.id}")
        print(f"   Студент: {user.username} (ID: {user.id})")
        print(f"   Задание: {task.title} (ID: {task.id})")
        print(f"   Навык: {skill.name}")
        print(f"   Результат: ❌ Неправильно")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при создании попытки: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = create_test_attempt()
        if success:
            print(f"\n✅ Скрипт выполнен успешно!")
            print(f"💡 Теперь можно запустить другие тесты для проверки:")
            print(f"   python mlmodels\\dqn\\tests\\test_student_analysis.py")
            print(f"   python mlmodels\\dqn\\tests\\test_recommendation_execution.py")
        else:
            print(f"\n❌ Скрипт завершился с ошибками")
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
