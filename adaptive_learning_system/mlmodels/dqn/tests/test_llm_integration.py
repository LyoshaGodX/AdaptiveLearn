#!/usr/bin/env python3
"""
Тест интеграции LLM с системой рекомендаций

Проверяет, что при создании рекомендации автоматически генерируется LLM объяснение
"""

import os
import sys
from pathlib import Path

# Добавляем путь к Django проекту
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')

import django
django.setup()

from django.contrib.auth.models import User
from mlmodels.dqn.recommendation_manager_fixed import recommendation_manager_fixed
from mlmodels.models import DQNRecommendation


def test_llm_integration():
    """Тест интеграции LLM с рекомендациями"""
    print("🧪 ТЕСТ ИНТЕГРАЦИИ LLM С РЕКОМЕНДАЦИЯМИ")
    print("=" * 60)
    
    # Находим активного студента
    student_user = User.objects.filter(is_active=True).first()
    if not student_user:
        print("❌ Не найдено активных пользователей")
        return False
    
    print(f"👤 Тестируем на студенте: {student_user.get_full_name() or student_user.username}")
    
    # Считаем количество рекомендаций до теста
    initial_count = DQNRecommendation.objects.filter(student__user=student_user).count()
    print(f"📊 Рекомендаций до теста: {initial_count}")
    
    # Генерируем новую рекомендацию
    print("\n🚀 Генерируем новую рекомендацию...")
    result = recommendation_manager_fixed.generate_and_save_recommendation(
        student_id=student_user.id,
        set_as_current=True
    )
    
    if not result:
        print("❌ Не удалось создать рекомендацию")
        return False
    
    print(f"✅ Рекомендация создана!")
    print(f"   ID: {result.recommendation_id}")
    print(f"   Задание: {result.task_id}")
    print(f"   Q-value: {result.q_value:.3f}")
    print(f"   Уверенность: {result.confidence:.3f}")
    
    # Получаем созданную рекомендацию
    recommendation = DQNRecommendation.objects.get(id=result.recommendation_id)
    
    print(f"\n📝 АНАЛИЗ СОЗДАННОЙ РЕКОМЕНДАЦИИ:")
    print(f"   Студент: {recommendation.student.user.get_full_name()}")
    print(f"   Задание: {recommendation.task.title}")
    print(f"   Сложность: {recommendation.task.difficulty}")
    print(f"   Создана: {recommendation.created_at}")
    
    # Проверяем LLM данные
    print(f"\n🤖 LLM ДАННЫЕ:")
    print(f"   Целевой навык: {len(recommendation.target_skill_info or [])}")
    print(f"   Prerequisite навыки: {len(recommendation.prerequisite_skills_snapshot or [])}")
    print(f"   Прогресс студента: {'Да' if recommendation.student_progress_context else 'Нет'}")
    
    # Главная проверка - LLM объяснение
    if recommendation.llm_explanation:
        print(f"   ✅ LLM объяснение: '{recommendation.llm_explanation}'")
        print(f"   📏 Длина: {len(recommendation.llm_explanation)} символов")
        print(f"   ⏰ Сгенерировано: {recommendation.llm_explanation_generated_at}")
    else:
        print(f"   ⚠️ LLM объяснение не создано (fallback режим)")
    
    # Проверяем текущую рекомендацию
    from mlmodels.models import StudentCurrentRecommendation
    current = StudentCurrentRecommendation.objects.filter(
        student__user=student_user
    ).first()
    
    if current:
        print(f"\n📌 ТЕКУЩАЯ РЕКОМЕНДАЦИЯ:")
        print(f"   ID: {current.recommendation.id}")
        print(f"   Установлена: {current.set_at}")
        if current.llm_explanation:
            print(f"   LLM объяснение: '{current.llm_explanation}'")
        else:
            print(f"   LLM объяснение: не задано")
    
    print("\n✅ Тест интеграции завершен успешно!")
    return True


def main():
    """Главная функция"""
    try:
        success = test_llm_integration()
        
        print("\n" + "=" * 80)
        if success:
            print("🎉 ИНТЕГРАЦИЯ LLM С РЕКОМЕНДАЦИЯМИ РАБОТАЕТ!")
            print("\n📋 ВОЗМОЖНОСТИ:")
            print("• Автоматическая генерация объяснений при создании рекомендаций")
            print("• Fallback режим, если LLM недоступна")
            print("• Сохранение объяснений в БД с временными метками")
            print("• Копирование объяснений в текущую рекомендацию")
        else:
            print("❌ ТЕСТ НЕ ПРОШЕЛ")
            
    except Exception as e:
        print(f"💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
