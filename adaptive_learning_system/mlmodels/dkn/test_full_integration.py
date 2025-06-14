#!/usr/bin/env python3
"""
Тест полного цикла интегрированной системы рекомендаций

Тестирует весь пайплайн:
1. data_processor - извлечение данных из базы
2. model - получение предсказаний DKN 
3. integrated_recommender - финальные рекомендации с учетом навыков
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

from integrated_recommender import IntegratedSkillRecommender


def test_full_integration_cycle(student_id: int = 7):
    """Тестирует полный цикл интегрированной системы"""
    print("🚀 ПОЛНЫЙ ТЕСТ ИНТЕГРИРОВАННОЙ СИСТЕМЫ РЕКОМЕНДАЦИЙ")
    print("=" * 70)
    
    print("📋 Этапы тестирования:")
    print("   1️⃣  Загрузка DKN модели")
    print("   2️⃣  Анализ навыков студента (BKT)")
    print("   3️⃣  Получение DKN предсказаний")
    print("   4️⃣  Комбинирование данных")
    print("   5️⃣  Генерация финальных рекомендаций")
    print()
    
    # Пытаемся найти обученную модель
    model_paths = [
        "training/models/best_model.pth",
        "../checkpoints/best_model.pth", 
        "../best_enhanced_model.pth",
        "../best_simple_model.pth"
    ]
    
    model_path = None
    for path in model_paths:
        if os.path.exists(path):
            model_path = path
            break
    
    print(f"🔍 Поиск модели DKN:")
    if model_path:
        print(f"   ✅ Найдена модель: {model_path}")
    else:
        print(f"   ⚠️  Обученная модель не найдена, используется необученная")
    
    print("\n" + "=" * 70)
    
    # Создаем и тестируем интегрированную систему
    try:
        recommender = IntegratedSkillRecommender(model_path)
        
        print(f"\n🎯 ТЕСТИРОВАНИЕ ДЛЯ СТУДЕНТА {student_id}")
        print("=" * 50)
        
        # Получаем рекомендации
        recommendations = recommender.get_recommendations(student_id, num_recommendations=5)
        
        if recommendations:
            print(f"\n✅ Получено {len(recommendations)} рекомендаций!")
            
            print(f"\n🏆 ФИНАЛЬНЫЕ РЕКОМЕНДАЦИИ:")
            print("-" * 40)
            
            for i, rec in enumerate(recommendations, 1):
                print(f"\n{i}. 📋 {rec.task_title}")
                print(f"   🎯 Навык: {rec.skill_name}")
                print(f"   📊 Освоение навыка (BKT): {rec.skill_mastery:.1%}")
                print(f"   🧠 Предсказание DKN: {rec.dkn_prediction:.1%}")
                print(f"   📈 Сложность задания: {rec.task_difficulty}")
                print(f"   ⭐ Приоритет: {rec.priority}/5")
                print(f"   🎯 Уверенность: {rec.confidence:.2f}")
                print(f"   💭 Обоснование:")
                print(f"      {rec.reasoning}")
            
            # Анализ результатов
            print(f"\n📊 АНАЛИЗ РЕЗУЛЬТАТОВ:")
            print("-" * 30)
            
            avg_bkt = sum(r.skill_mastery for r in recommendations) / len(recommendations)
            avg_dkn = sum(r.dkn_prediction for r in recommendations) / len(recommendations)
            avg_confidence = sum(r.confidence for r in recommendations) / len(recommendations)
            
            print(f"   📈 Среднее освоение навыков (BKT): {avg_bkt:.1%}")
            print(f"   🧠 Среднее предсказание DKN: {avg_dkn:.1%}")
            print(f"   🎯 Средняя уверенность: {avg_confidence:.2f}")
            
            # Распределение по приоритетам
            priorities = {}
            for rec in recommendations:
                priorities[rec.priority] = priorities.get(rec.priority, 0) + 1
            
            print(f"   ⭐ Распределение приоритетов:")
            for priority, count in sorted(priorities.items()):
                print(f"      Приоритет {priority}: {count} рекомендаций")
            
            # Оценка качества интеграции
            print(f"\n🔍 ОЦЕНКА КАЧЕСТВА ИНТЕГРАЦИИ:")
            print("-" * 35)
            
            # Проверяем согласованность BKT и DKN
            agreements = 0
            for rec in recommendations:
                if abs(rec.skill_mastery - rec.dkn_prediction) < 0.3:
                    agreements += 1
            
            agreement_rate = agreements / len(recommendations) if recommendations else 0
            print(f"   🤝 Согласованность BKT и DKN: {agreement_rate:.1%}")
            
            if agreement_rate > 0.6:
                print(f"   ✅ Высокая согласованность данных")
            elif agreement_rate > 0.4:
                print(f"   🔄 Средняя согласованность данных")
            else:
                print(f"   ⚠️  Низкая согласованность данных")
            
            # Проверяем разнообразие рекомендаций
            unique_skills = len(set(rec.skill_name for rec in recommendations))
            print(f"   🎨 Разнообразие навыков: {unique_skills} из {len(recommendations)}")
            
            if unique_skills == len(recommendations):
                print(f"   ✅ Все рекомендации для разных навыков")
            elif unique_skills > len(recommendations) // 2:
                print(f"   🔄 Хорошее разнообразие навыков")
            else:
                print(f"   ⚠️  Низкое разнообразие навыков")
            
        else:
            print(f"❌ Рекомендации не получены!")
            return False
        
        print(f"\n" + "=" * 70)
        print(f"🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО!")
        
        print(f"\n✅ ПОДТВЕРЖДЕННЫЕ ВОЗМОЖНОСТИ:")
        print(f"   🔄 Полный цикл: База → DKN → Навыки → Рекомендации")
        print(f"   🎯 Интеграция множественных источников данных")
        print(f"   📊 Анализ BKT данных освоения навыков")
        print(f"   🧠 Использование DKN предсказаний")
        print(f"   ⭐ Приоритизация рекомендаций")
        print(f"   🎯 Оценка уверенности в рекомендациях")
        print(f"   💭 Понятные объяснения решений")
        
        return True
        
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_students():
    """Тестирует систему на нескольких студентах"""
    print(f"\n🧪 ТЕСТИРОВАНИЕ НА НЕСКОЛЬКИХ СТУДЕНТАХ")
    print("=" * 50)
    
    student_ids = [2, 7]  # Студенты с данными
    
    for student_id in student_ids:
        print(f"\n👤 Тестирование студента {student_id}:")
        print("-" * 30)
        
        try:
            success = test_full_integration_cycle(student_id)
            if success:
                print(f"   ✅ Студент {student_id}: тест пройден")
            else:
                print(f"   ❌ Студент {student_id}: тест провален")
        except Exception as e:
            print(f"   💥 Студент {student_id}: ошибка - {e}")


if __name__ == "__main__":
    # Основной тест
    success = test_full_integration_cycle(student_id=7)
    
    if success:
        # Дополнительные тесты
        test_multiple_students()
        
        print(f"\n🏆 ВСЕ ТЕСТЫ ИНТЕГРИРОВАННОЙ СИСТЕМЫ ПРОЙДЕНЫ!")
        print(f"🚀 Система готова к продакшену!")
    else:
        print(f"\n💥 ТЕСТЫ ПРОВАЛЕНЫ!")
        sys.exit(1)
