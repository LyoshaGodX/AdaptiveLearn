#!/usr/bin/env python3
"""
Тест исправленного менеджера рекомендаций
"""

import os
import sys
sys.path.append('.')

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')

import django
django.setup()

def test_fixed_manager():
    """Тестируем исправленный менеджер"""
    try:
        print("=== Тест исправленного менеджера рекомендаций ===")
        
        # Тестируем функцию поиска модели
        print("\n1. Тестируем функцию поиска модели...")
        from mlmodels.dqn.recommendation_manager_fixed import find_latest_dqn_model
        
        latest_model = find_latest_dqn_model()
        print(f"Найденная модель: {latest_model}")
        
        # Тестируем создание менеджера
        print("\n2. Тестируем создание менеджера...")
        from mlmodels.dqn.recommendation_manager_fixed import DQNRecommendationManagerFixed
        
        manager = DQNRecommendationManagerFixed()
        print(f"✅ Менеджер создан успешно: {type(manager)}")
        
        # Проверяем, что рекомендатор инициализирован
        print(f"Рекомендатор: {type(manager.recommender)}")
        
        print("\n✅ Все тесты прошли успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_fixed_manager()
