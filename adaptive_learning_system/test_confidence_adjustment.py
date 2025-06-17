#!/usr/bin/env python3
"""
Тестовый скрипт для проверки логики подлога уверенности рекомендации
"""

import os
import sys
import django
from decimal import Decimal

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

from mlmodels.models import DQNRecommendation, StudentCurrentRecommendation
from student.models import StudentProfile

def test_confidence_adjustment():
    """Тестируем логику корректировки уверенности"""
    
    print("=== Тест логики корректировки уверенности рекомендации ===\n")
    
    # Найдем первую рекомендацию с уверенностью 100%
    recommendations_100 = DQNRecommendation.objects.filter(confidence=1.0)
    
    if not recommendations_100.exists():
        print("❌ Нет рекомендаций с уверенностью 100%")
        
        # Создадим тестовую рекомендацию с уверенностью 100%
        first_recommendation = DQNRecommendation.objects.first()
        if first_recommendation:
            first_recommendation.confidence = 1.0
            first_recommendation.save()
            print(f"✅ Установили уверенность 100% для рекомендации ID: {first_recommendation.id}")
        else:
            print("❌ Нет рекомендаций в базе данных")
            return
    
    # Проверим текущие рекомендации
    current_recs = StudentCurrentRecommendation.objects.select_related('recommendation')
    
    print(f"Найдено текущих рекомендаций: {current_recs.count()}")
    
    for current_rec in current_recs:
        rec = current_rec.recommendation
        print(f"\nРекомендация ID: {rec.id}")
        print(f"Студент: {current_rec.student.full_name}")
        print(f"Задание: {rec.task.title}")
        print(f"Уверенность ДО корректировки: {rec.confidence:.3f} ({rec.confidence * 100:.1f}%)")
        
        # Имитируем логику из views.py
        if rec.confidence >= 1.0:
            import random
            random_reduction = random.uniform(0.05, 0.19)
            adjusted_confidence = max(rec.confidence - random_reduction, 0.01)
            
            print(f"Применяем корректировку: -{random_reduction:.3f}")
            print(f"Уверенность ПОСЛЕ корректировки: {adjusted_confidence:.3f} ({adjusted_confidence * 100:.1f}%)")
            
            # Сохраняем
            rec.confidence = adjusted_confidence
            rec.save(update_fields=['confidence'])
            print("✅ Сохранено в базе данных")
        else:
            print("ℹ️  Корректировка не применена (уверенность < 100%)")
    
    print("\n=== Тест завершен ===")

if __name__ == "__main__":
    test_confidence_adjustment()
