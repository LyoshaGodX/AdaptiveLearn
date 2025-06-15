#!/usr/bin/env python3
"""
Простой тест выполнения рекомендации

Этот тест просто:
1. Берет текущую рекомендацию студента
2. Показывает информацию о рекомендации
3. Показывает информацию о задании
4. Симулирует выполнение попытки студентом
5. Записывает попытку в базу данных
6. НЕ вмешивается в работу DQN системы

Цель: проверить, работает ли автоматическое создание новых рекомендаций
"""

import os
import sys
from pathlib import Path
import random
from datetime import datetime, timedelta

# Добавляем путь к Django проекту
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')

import django
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Count

from skills.models import Skill
from methodist.models import Task
from mlmodels.models import TaskAttempt, DQNRecommendation, StudentCurrentRecommendation
from student.models import StudentProfile


def get_current_recommendation(student_id):
    """Получает текущую рекомендацию студента"""
    try:
        current = StudentCurrentRecommendation.objects.select_related(
            'recommendation__task'
        ).get(student__user_id=student_id)
        
        recommendation = current.recommendation
        
        return {
            'recommendation_id': recommendation.id,
            'task_id': recommendation.task.id,
            'task': recommendation.task,
            'q_value': recommendation.q_value,
            'confidence': recommendation.confidence,
            'reason': recommendation.reason,
            'llm_explanation': recommendation.llm_explanation,
            'created_at': recommendation.created_at,
            'set_as_current_at': current.set_at,
            'current_llm_explanation': current.llm_explanation
        }
    except StudentCurrentRecommendation.DoesNotExist:
        return None


def analyze_recommendation(rec_data):
    """Анализирует информацию о рекомендации"""
    print("\n🤖 ИНФОРМАЦИЯ О ТЕКУЩЕЙ РЕКОМЕНДАЦИИ")
    print("-" * 50)
    
    print(f"🆔 ID рекомендации: {rec_data['recommendation_id']}")
    print(f"📅 Создана: {rec_data['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Установлена как текущая: {rec_data['set_as_current_at'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Q-value: {rec_data['q_value']:.6f}")
    print(f"📈 Уверенность: {rec_data['confidence']:.6f}")
    print(f"💡 Причина: {rec_data['reason']}")
    
    # Проверяем LLM объяснения
    print(f"\n🤖 LLM ОБЪЯСНЕНИЯ:")
    print(f"  📝 В рекомендации: {'✅ Есть' if rec_data['llm_explanation'] else '❌ Пустое'}")
    if rec_data['llm_explanation']:
        explanation_preview = rec_data['llm_explanation'][:200] + "..." if len(rec_data['llm_explanation']) > 200 else rec_data['llm_explanation']
        print(f"     {explanation_preview}")
    
    print(f"  📄 В текущей записи: {'✅ Есть' if rec_data['current_llm_explanation'] else '❌ Пустое'}")
    if rec_data['current_llm_explanation']:
        current_preview = rec_data['current_llm_explanation'][:200] + "..." if len(rec_data['current_llm_explanation']) > 200 else rec_data['current_llm_explanation']
        print(f"     {current_preview}")


def analyze_task(task):
    """Анализирует информацию о задании"""
    print("\n📋 ИНФОРМАЦИЯ О РЕКОМЕНДОВАННОМ ЗАДАНИИ")
    print("-" * 50)
    
    print(f"🆔 ID задания: {task.id}")
    print(f"📝 Название: {task.title}")
    print(f"🔤 Тип: {task.task_type}")
    print(f"⚡ Сложность: {task.difficulty}")
    print(f"✅ Активное: {'Да' if task.is_active else 'Нет'}")
    print(f"📅 Создано: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Содержание задания
    print(f"\n📖 СОДЕРЖАНИЕ ЗАДАНИЯ:")
    content = task.question_text or "Содержание не указано"
    print(f"  {content[:300]}{'...' if len(content) > 300 else ''}")
    
    # Навыки, которые развивает задание
    skills = task.skills.all()
    print(f"\n🎯 РАЗВИВАЕМЫЕ НАВЫКИ ({skills.count()}):")
    for skill in skills:
        print(f"  • {skill.name}")
    
    # Статистика задания
    attempts_count = TaskAttempt.objects.filter(task=task).count()
    if attempts_count > 0:
        success_count = TaskAttempt.objects.filter(task=task, is_correct=True).count()
        success_rate = (success_count / attempts_count * 100)
        print(f"\n📊 СТАТИСТИКА ЗАДАНИЯ:")
        print(f"  📈 Всего попыток: {attempts_count}")
        print(f"  ✅ Успешных: {success_count}")
        print(f"  📊 Процент успеха: {success_rate:.1f}%")
    else:
        print(f"\n📊 СТАТИСТИКА: Задание ещё никто не решал")


def simulate_attempt(student_profile, task):
    """Симулирует выполнение попытки студентом"""
    print("\n🎮 СИМУЛЯЦИЯ ВЫПОЛНЕНИЯ ПОПЫТКИ")
    print("-" * 50)
    
    # Генерируем случайный результат
    is_correct = random.choice([True, False, True])  # небольшой уклон в сторону успеха
    
    # Генерируем случайный ответ
    answer_options = [
        f"Ответ студента на задание {task.id}",
        f"Решение: вариант {random.randint(1, 4)}",
        "42",
        f"Попытка решения #{random.randint(1000, 9999)}",
        "Мой ответ"
    ]
    given_answer = random.choice(answer_options)
    
    print(f"🎯 Задание: {task.title}")
    print(f"💭 Ответ студента: {given_answer}")
    print(f"🎲 Результат: {'✅ Правильно' if is_correct else '❌ Неправильно'}")
    
    # Создаем попытку в базе данных
    try:
        attempt = TaskAttempt.objects.create(
            student=student_profile,
            task=task,
            is_correct=is_correct,
            given_answer=given_answer,
            started_at=timezone.now() - timedelta(minutes=random.randint(1, 5)),
            time_spent=random.randint(30, 180)  # от 30 секунд до 3 минут
        )
        
        print(f"💾 Попытка сохранена в БД с ID: {attempt.id}")
        print(f"📅 Время выполнения: {attempt.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return attempt
        
    except Exception as e:
        print(f"❌ Ошибка при сохранении попытки: {e}")
        return None


def main():
    """Главная функция теста"""
    print("🧪 ПРОСТОЙ ТЕСТ ВЫПОЛНЕНИЯ РЕКОМЕНДАЦИИ")
    print("=" * 80)
    
    # Найдем студента с текущей рекомендацией
    students_with_current_rec = StudentCurrentRecommendation.objects.values('student__user_id').distinct()
    
    if not students_with_current_rec:
        print("⚠️ Студенты с текущими рекомендациями не найдены")
        return False
    
    # Берем первого студента с текущей рекомендацией
    student_id = students_with_current_rec[0]['student__user_id']
    user = User.objects.get(id=student_id)
    profile, _ = StudentProfile.objects.get_or_create(user=user)
    
    print(f"👤 Выбран студент: {user.username} (ID: {student_id})")
    
    # 1. Получаем текущую рекомендацию
    print("\n🔍 ПОЛУЧЕНИЕ ТЕКУЩЕЙ РЕКОМЕНДАЦИИ...")
    current_rec = get_current_recommendation(student_id)
    
    if not current_rec:
        print("❌ У студента нет текущей рекомендации")
        return False
    
    print(f"✅ Найдена текущая рекомендация #{current_rec['recommendation_id']}")
    
    # 2. Анализируем рекомендацию
    analyze_recommendation(current_rec)
    
    # 3. Анализируем задание
    analyze_task(current_rec['task'])
    
    # 4. Симулируем выполнение попытки
    attempt = simulate_attempt(profile, current_rec['task'])
    
    if attempt:
        print(f"\n✅ Попытка успешно записана!")
        print(f"🔄 Теперь система должна автоматически:")
        print(f"   • Связать попытку с рекомендацией")
        print(f"   • Создать новую рекомендацию")
        print(f"   • Обновить текущую рекомендацию студента")
        
        print(f"\n💡 Запустите test_student_analysis.py для студента {student_id},")
        print(f"   чтобы проверить, что система работает автоматически!")
        
        return True
    else:
        print(f"\n❌ Не удалось записать попытку")
        return False


if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 Тест успешно выполнен!")
        else:
            print("\n❌ Тест завершился с ошибками")
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
