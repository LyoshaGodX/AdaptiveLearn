#!/usr/bin/env python
"""
Тестовый скрипт для проверки данных BKT и профиля студента
"""

import os
import sys
import django

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

from student.models import StudentProfile
from mlmodels.models import StudentSkillMastery, TaskAttempt, StudentCurrentRecommendation
from methodist.models import Task
from skills.models import Skill
from django.contrib.auth.models import User

def test_bkt_data():
    """Тестируем данные BKT"""
    print("=== ТЕСТ ДАННЫХ BKT ===")
    
    # Находим всех студентов
    students = StudentProfile.objects.all()
    print(f"Всего студентов: {students.count()}")
    
    if not students.exists():
        print("❌ Нет студентов в базе данных")
        return
    
    # Берем первого студента
    student = students.first()
    print(f"\n📋 Тестируем студента: {student.full_name} (ID: {student.id})")
    
    # Проверяем навыки студента
    skill_masteries = StudentSkillMastery.objects.filter(student=student)
    print(f"Навыков у студента: {skill_masteries.count()}")
    
    if not skill_masteries.exists():
        print("❌ У студента нет записей о навыках")
        return
        
    print("\n🧠 НАВЫКИ СТУДЕНТА:")
    print("-" * 80)
    print(f"{'Навык':<30} {'Текущая P(L)':<15} {'Попыток':<10} {'Правильных':<12} {'P(G)':<8} {'P(S)':<8}")
    print("-" * 80)
    
    for sm in skill_masteries[:10]:  # Первые 10 навыков
        print(f"{sm.skill.name[:29]:<30} "
              f"{sm.current_mastery_prob:<15.4f} "
              f"{sm.attempts_count:<10} "
              f"{sm.correct_attempts:<12} "
              f"{sm.guess_prob:<8.3f} "
              f"{sm.slip_prob:<8.3f}")
    
    # Проверяем попытки решения заданий
    attempts = TaskAttempt.objects.filter(student=student)
    print(f"\n📝 ПОПЫТКИ РЕШЕНИЯ ЗАДАНИЙ:")
    print(f"Всего попыток: {attempts.count()}")
    print(f"Правильных: {attempts.filter(is_correct=True).count()}")
    print(f"Неправильных: {attempts.filter(is_correct=False).count()}")
    
    if attempts.exists():
        print("\n📊 ПОСЛЕДНИЕ 5 ПОПЫТОК:")
        print("-" * 60)
        print(f"{'Задание':<25} {'Результат':<10} {'Время':<20}")
        print("-" * 60)
        
        for attempt in attempts.order_by('-completed_at')[:5]:
            result = "✅ Верно" if attempt.is_correct else "❌ Неверно"
            print(f"{attempt.task.title[:24]:<25} "
                  f"{result:<10} "
                  f"{attempt.completed_at.strftime('%d.%m %H:%M'):<20}")
    
    # Проверяем текущую рекомендацию
    try:
        current_rec = StudentCurrentRecommendation.objects.select_related(
            'recommendation__task'
        ).get(student=student)
        print(f"\n🎯 ТЕКУЩАЯ РЕКОМЕНДАЦИЯ:")
        print(f"Задание: {current_rec.recommendation.task.title}")
        print(f"Уверенность: {current_rec.recommendation.confidence:.2f}")
        print(f"Q-value: {current_rec.recommendation.q_value:.4f}")
        if current_rec.recommendation.llm_explanation:
            print(f"Объяснение: {current_rec.recommendation.llm_explanation[:100]}...")
    except StudentCurrentRecommendation.DoesNotExist:
        print("\n❌ У студента нет текущей рекомендации")

def test_skills_data():
    """Тестируем данные навыков"""
    print("\n\n=== ТЕСТ ДАННЫХ НАВЫКОВ ===")
    
    skills = Skill.objects.all()
    print(f"Всего навыков в системе: {skills.count()}")
    
    if not skills.exists():
        print("❌ Нет навыков в базе данных")
        return
    
    print("\n🎯 СПИСОК НАВЫКОВ:")
    print("-" * 50)
    
    for skill in skills[:15]:  # Первые 15 навыков
        masteries_count = StudentSkillMastery.objects.filter(skill=skill).count()
        print(f"ID: {skill.id:<3} | {skill.name:<35} | Студентов: {masteries_count}")

def test_tasks_data():
    """Тестируем данные заданий"""
    print("\n\n=== ТЕСТ ДАННЫХ ЗАДАНИЙ ===")
    
    tasks = Task.objects.all()
    print(f"Всего заданий: {tasks.count()}")
    
    if not tasks.exists():
        print("❌ Нет заданий в базе данных")
        return
    
    print("\n📚 СПИСОК ЗАДАНИЙ:")
    print("-" * 80)
    print(f"{'ID':<5} {'Название':<40} {'Тип':<15} {'Сложность':<15}")
    print("-" * 80)
    
    for task in tasks[:10]:  # Первые 10 заданий
        attempts_count = TaskAttempt.objects.filter(task=task).count()
        print(f"{task.id:<5} "
              f"{task.title[:39]:<40} "
              f"{task.task_type:<15} "
              f"{task.difficulty:<15}")

def check_bkt_calculations():
    """Проверяем правильность вычислений BKT"""
    print("\n\n=== ПРОВЕРКА ВЫЧИСЛЕНИЙ BKT ===")
    
    # Находим навыки с попытками
    skill_masteries = StudentSkillMastery.objects.filter(
        attempts_count__gt=0
    ).select_related('skill', 'student')[:5]
    
    if not skill_masteries.exists():
        print("❌ Нет навыков с попытками")
        return
    
    print("\n🔍 ДЕТАЛЬНЫЙ АНАЛИЗ BKT:")
    print("-" * 100)
    
    for sm in skill_masteries:
        print(f"\n👤 Студент: {sm.student.full_name}")
        print(f"🎯 Навык: {sm.skill.name}")
        print(f"📊 Попыток: {sm.attempts_count}, Правильных: {sm.correct_attempts}")
        
        accuracy = sm.correct_attempts / sm.attempts_count if sm.attempts_count > 0 else 0
        print(f"📈 Точность: {accuracy:.2%}")
        
        print(f"🧮 P(L0): {sm.initial_mastery_prob:.4f}")
        print(f"🧮 P(Lt): {sm.current_mastery_prob:.4f}")
        print(f"🧮 P(T): {sm.transition_prob:.4f}")
        print(f"🧮 P(G): {sm.guess_prob:.4f}")
        print(f"🧮 P(S): {sm.slip_prob:.4f}")
        
        # Проверяем логику
        print(f"✅ Процент освоения для отображения: {sm.current_mastery_prob * 100:.1f}%")

def main():
    """Главная функция"""
    print("🚀 ЗАПУСК ДИАГНОСТИКИ СИСТЕМЫ АДАПТИВНОГО ОБУЧЕНИЯ")
    print("=" * 60)
    
    try:
        test_bkt_data()
        test_skills_data() 
        test_tasks_data()
        check_bkt_calculations()
        
        print("\n\n✅ ДИАГНОСТИКА ЗАВЕРШЕНА")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
