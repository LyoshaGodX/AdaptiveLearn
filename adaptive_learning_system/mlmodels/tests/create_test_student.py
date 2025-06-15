#!/usr/bin/env python3
"""
Скрипт для создания тестового студента с реальными попытками

Создает студента alex_klementev и симулирует его обучение:
- Создает попытки решения заданий  
- BKT параметры обновляются автоматически через TaskAttempt.save()
- Следует логике обучения: от простых навыков к сложным
- Учитывает prerequisite навыков

Использование:
    python mlmodels/tests/create_test_student.py
    или
    python mlmodels/tests/create_test_student.py --recreate
"""

import os
import sys
import django
from pathlib import Path
import random
from datetime import datetime, timedelta
from django.utils import timezone

# Настройка Django
def setup_django():
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
    django.setup()

setup_django()

from django.contrib.auth.models import User
from django.db import transaction
from student.models import StudentProfile, StudentCourseEnrollment
from skills.models import Skill, Course
from methodist.models import Task
from mlmodels.models import TaskAttempt, StudentSkillMastery


class TestStudentCreator:
    """Создатель тестового студента с реалистичной симуляцией обучения"""
    
    def __init__(self):
        self.username = "alex_klementev"
        self.student_profile = None
        self.created_attempts = []
        
        # Базовые навыки (без prerequisite)
        self.basic_skills = [
            "Переменные и типы данных",
            "Введение в ООП", 
            "Основы алгоритмов",
            "Работа с вводом/выводом данных"
        ]
        
        # Продвинутые навыки (требуют базовые)
        self.advanced_skills = [
            "Операторы и выражения",
            "Логические операторы", 
            "Контейнеры данных (tuple, set)",
            "Сложность алгоритмов",
            "Объектно-ориентированное программирование"
        ]
    
    def create_or_recreate_student(self, recreate=False):
        """Создает или пересоздает студента"""
        if recreate:
            print("🗑️ Удаление существующих данных студента...")
            try:
                user = User.objects.get(username=self.username)
                # Удаляем связанные попытки и BKT данные
                TaskAttempt.objects.filter(student__user=user).delete()
                StudentSkillMastery.objects.filter(student__user=user).delete()
                user.delete()
                print("✅ Старые данные удалены")
            except User.DoesNotExist:
                pass
        
        print(f"👨‍🎓 Создание студента {self.username}...")
        
        # Создаем пользователя
        user, created = User.objects.get_or_create(
            username=self.username,
            defaults={
                'first_name': "Алексей",
                'last_name': "Клементьев", 
                'email': "alex.klementev@example.com",
                'is_active': True
            }
        )
        
        if not created and not recreate:
            print(f"⚠️ Студент {self.username} уже существует")
            self.student_profile = user.student_profile
            return self.student_profile
        
        # Создаем профиль студента
        student_profile, _ = StudentProfile.objects.get_or_create(
            user=user,
            defaults={
                'full_name': "Клементьев Алексей Александрович",
                'email': "alex.klementev@example.com",
                'organization': "РГПУ им. Герцена",
                'is_active': True
            }
        )
        
        # Записываем на все курсы
        for course in Course.objects.all():
            StudentCourseEnrollment.objects.get_or_create(
                student=student_profile,
                course=course,
                defaults={
                    'enrolled_at': timezone.now(),
                    'status': 'enrolled'
                }
            )
        
        self.student_profile = student_profile
        print(f"✅ Студент создан (ID: {user.id})")
        return student_profile
    
    def simulate_skill_learning(self, skill_name: str, success_rate: float, num_attempts: int):
        """Симулирует изучение конкретного навыка"""
        print(f"  📚 Изучение навыка: {skill_name}")
        
        try:
            skill = Skill.objects.get(name=skill_name)
        except Skill.DoesNotExist:
            print(f"    ❌ Навык '{skill_name}' не найден")
            return []
        
        # Получаем задания для этого навыка
        tasks = list(Task.objects.filter(skills=skill))
        if not tasks:
            print(f"    ❌ Нет заданий для навыка '{skill_name}'")
            return []
        
        print(f"    📋 Найдено заданий: {len(tasks)}")
        
        attempts = []
        current_time = timezone.now() - timedelta(days=30)  # Начинаем месяц назад
        
        for i in range(num_attempts):
            # Выбираем случайное задание
            task = random.choice(tasks)
            
            # Определяем правильность ответа
            is_correct = random.random() < success_rate
            
            # Время решения (30 сек - 10 минут)
            time_spent = random.randint(30, 600)
            
            # Создаем попытку
            attempt = TaskAttempt.objects.create(
                student=self.student_profile,
                task=task,
                is_correct=is_correct,
                given_answer=f"Ответ на задание {task.id}" if is_correct else "Неправильный ответ",
                correct_answer=f"Правильный ответ на {task.title}",
                started_at=current_time,
                completed_at=current_time + timedelta(seconds=time_spent),
                time_spent=time_spent,
                metadata={
                    'skill': skill_name,
                    'attempt_number': i + 1,
                    'total_attempts': num_attempts,
                    'simulated': True,
                    'success_rate_target': success_rate
                }
            )
            
            attempts.append(attempt)
            self.created_attempts.append(attempt)
            
            # Увеличиваем время для следующей попытки
            current_time += timedelta(minutes=random.randint(15, 120))
        
        success_count = sum(1 for a in attempts if a.is_correct)
        actual_rate = success_count / len(attempts) if attempts else 0
        print(f"    ✅ Создано попыток: {len(attempts)} (успешных: {success_count}, {actual_rate:.1%})")
        
        return attempts
    
    def simulate_learning_progression(self):
        """Симулирует реалистичную прогрессию обучения"""
        print("\n🎯 Симуляция обучения студента...")
        
        # Этап 1: Изучение базовых навыков (высокий успех)
        print("\n📘 ЭТАП 1: Базовые навыки")
        for skill_name in self.basic_skills:
            success_rate = random.uniform(0.8, 0.95)  # 80-95% успех
            num_attempts = random.randint(8, 15)
            self.simulate_skill_learning(skill_name, success_rate, num_attempts)
        
        # Этап 2: Изучение продвинутых навыков (средний успех)
        print("\n📙 ЭТАП 2: Продвинутые навыки")
        for skill_name in self.advanced_skills:
            success_rate = random.uniform(0.4, 0.8)  # 40-80% успех
            num_attempts = random.randint(5, 12)
            self.simulate_skill_learning(skill_name, success_rate, num_attempts)
    
    def analyze_results(self):
        """Анализирует результаты обучения"""
        print("\n📊 АНАЛИЗ РЕЗУЛЬТАТОВ")
        print("="*60)
        
        # Статистика попыток
        total_attempts = len(self.created_attempts)
        correct_attempts = sum(1 for a in self.created_attempts if a.is_correct)
        success_rate = correct_attempts / total_attempts if total_attempts > 0 else 0
        
        print(f"📈 Общая статистика:")
        print(f"  • Всего попыток: {total_attempts}")
        print(f"  • Правильных: {correct_attempts}")
        print(f"  • Успешность: {success_rate:.1%}")
        
        # BKT данные (должны создаться автоматически)
        bkt_records = StudentSkillMastery.objects.filter(student=self.student_profile)
        print(f"\n🧠 BKT записи (автоматически созданы): {bkt_records.count()}")
        
        for bkt in bkt_records.order_by('-current_mastery_prob'):
            prob = bkt.current_mastery_prob
            status = "🔥" if prob >= 0.85 else "🔶" if prob >= 0.5 else "🔴"
            print(f"  {status} {bkt.skill.name}: P = {prob:.4f}")
        
        print("\n✨ СИМУЛЯЦИЯ ЗАВЕРШЕНА!")
        return {
            'total_attempts': total_attempts,
            'correct_attempts': correct_attempts,
            'success_rate': success_rate,
            'bkt_records': bkt_records.count(),
            'student_id': self.student_profile.user.id
        }


def main():
    """Основная функция"""
    recreate = '--recreate' in sys.argv
    
    print("🚀 СОЗДАНИЕ ТЕСТОВОГО СТУДЕНТА С СИМУЛЯЦИЕЙ ОБУЧЕНИЯ")
    print("="*80)
    
    creator = TestStudentCreator()
    
    try:
        with transaction.atomic():
            # Создаем студента
            creator.create_or_recreate_student(recreate=recreate)
            
            # Симулируем обучение
            creator.simulate_learning_progression()
            
            # Анализируем результаты
            results = creator.analyze_results()
            
            print(f"\n🎉 УСПЕХ! Студент создан с ID: {results['student_id']}")
            
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
