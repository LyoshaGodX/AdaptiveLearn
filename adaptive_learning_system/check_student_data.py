#!/usr/bin/env python3
"""
Скрипт для проверки данных студента ID=15 (alex_klementev)
"""

import os
import sys
import django
from pathlib import Path

# Настройка Django
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

from django.contrib.auth.models import User
from student.models import StudentProfile
from skills.models import Skill
from methodist.models import Task
from mlmodels.models import StudentSkillMastery, TaskAttempt, DQNRecommendation
from mlmodels.dqn.data_processor import DQNDataProcessor


def check_student_data():
    """Проверяет данные студента с ID=15"""
    
    print("🔍 ПРОВЕРКА ДАННЫХ СТУДЕНТА ID=15 (alex_klementev)")
    print("="*80)
    
    try:
        # Получаем пользователя
        user = User.objects.get(id=15)
        print(f"✅ Пользователь найден: {user.username} (ID: {user.id})")
        
        # Получаем профиль студента
        try:
            student_profile = StudentProfile.objects.get(user=user)
            print(f"✅ Профиль студента найден (ID: {student_profile.id})")
        except StudentProfile.DoesNotExist:
            print("❌ Профиль студента не найден")
            return
        
        print("\n📊 АНАЛИЗ ПОПЫТОК")
        print("-" * 40)
        
        # Проверяем попытки
        attempts = TaskAttempt.objects.filter(student=student_profile)
        print(f"✅ Всего попыток: {attempts.count()}")
        
        if attempts.exists():
            recent_attempts = attempts.order_by('-started_at')[:5]
            print("🕒 Последние 5 попыток:")
            for attempt in recent_attempts:
                status = "✅ Правильно" if attempt.is_correct else "❌ Неправильно"
                print(f"  - Задание {attempt.task.id}: {status} ({attempt.started_at.strftime('%Y-%m-%d %H:%M')})")
        
        print("\n📊 АНАЛИЗ BKT ОЦЕНОК")
        print("-" * 40)
          # Проверяем BKT оценки
        bkt_records = StudentSkillMastery.objects.filter(student=student_profile)
        print(f"✅ Всего BKT записей: {bkt_records.count()}")
        
        if bkt_records.exists():
            print("🎯 BKT по навыкам:")
            for bkt in bkt_records.order_by('-current_mastery_prob')[:10]:
                status = "🔥 ОСВОЕН" if bkt.current_mastery_prob >= 0.85 else "🔶 ИЗУЧАЕТСЯ" if bkt.current_mastery_prob >= 0.5 else "🔴 НИЗКИЙ"
                print(f"  - {bkt.skill.name}: {bkt.current_mastery_prob:.4f} {status}")
        
        print("\n📋 АНАЛИЗ РЕКОМЕНДАЦИЙ")
        print("-" * 40)
          # Проверяем рекомендации
        recommendations = DQNRecommendation.objects.filter(student_id=user.id)
        print(f"✅ Всего рекомендаций: {recommendations.count()}")
        
        if recommendations.exists():
            current_rec = recommendations.filter(is_current=True).first()
            if current_rec:
                print(f"📌 Текущая рекомендация: Задание {current_rec.task.id} (ID рек: {current_rec.id})")
                print(f"   Q-value: {current_rec.q_value:.4f}, Уверенность: {current_rec.confidence:.4f}")
            else:
                print("⚠️  Нет текущей рекомендации")
            
            recent_recs = recommendations.order_by('-created_at')[:5]
            print("🕒 Последние 5 рекомендаций:")
            for rec in recent_recs:
                current = "📌 ТЕКУЩАЯ" if rec.is_current else ""
                print(f"  - Рек {rec.id}: Задание {rec.task.id} {current} ({rec.created_at.strftime('%Y-%m-%d %H:%M')})")
        
        print("\n🧠 ТЕСТ DQN DATA PROCESSOR")
        print("-" * 40)
        
        # Тестируем DQNDataProcessor
        try:
            processor = DQNDataProcessor()
            state = processor.get_student_state(user.id)
            print(f"✅ DQN состояние получено: размер {state.shape}")
            
            # Получаем доступные действия
            available_actions = processor.get_available_actions(user.id)
            print(f"✅ Доступных действий: {len(available_actions)}")
            
            if available_actions:
                print("🎯 Первые 5 доступных заданий:")
                for i, task_id in enumerate(available_actions[:5]):
                    try:
                        task = Task.objects.get(id=task_id)
                        print(f"  - Задание {task_id}: {task.title[:50]}...")
                    except Task.DoesNotExist:
                        print(f"  - Задание {task_id}: [задание не найдено]")
            
        except Exception as e:
            print(f"❌ Ошибка DQN Data Processor: {e}")
        
        print("\n✅ ПРОВЕРКА ЗАВЕРШЕНА")
        print("="*80)
        
    except User.DoesNotExist:
        print("❌ Пользователь с ID=15 не найден")
    except Exception as e:
        print(f"❌ Ошибка при проверке: {e}")


if __name__ == "__main__":
    check_student_data()
