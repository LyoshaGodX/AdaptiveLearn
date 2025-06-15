"""
Быстрый тест LLM генерации после исправления ошибки кэша
"""
import os
import sys
from pathlib import Path

# Настройка Django
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')

import django
django.setup()

from mlmodels.llm.explanation_generator import ExplanationGenerator


def quick_test():
    """Быстрый тест генерации объяснения"""
    print("=== БЫСТРЫЙ ТЕСТ LLM ГЕНЕРАЦИИ ===\n")
    
    # Создаем генератор
    generator = ExplanationGenerator(model_key='phi3.5-mini', device='auto')
    
    # Инициализируем модель
    print("🔄 Инициализация LLM...")
    success = generator.initialize(use_quantization=True)
    
    if not success:
        print("❌ Не удалось инициализировать LLM")
        return False
    
    print("✅ LLM инициализирована успешно")
    
    # Тестовые данные
    test_data = {
        'student_name': 'Тест',
        'task_title': 'Переменные в Python',
        'task_difficulty': 'beginner',
        'task_type': 'true_false',
        'target_skill_info': [{
            'skill_name': 'Основы Python',
            'current_mastery_probability': 0.2
        }],
        'prerequisite_skills_snapshot': [],
        'dependent_skills_snapshot': [
            {'skill_name': 'Условные операторы'},
            {'skill_name': 'Циклы'}
        ],
        'student_progress_context': {
            'total_success_rate': 0.3
        }
    }
    
    print("\n🚀 Генерация объяснения...")
    
    try:
        explanation = generator.generate_recommendation_explanation(test_data)
        
        print(f"\n✅ РЕЗУЛЬТАТ:")
        print(f"'{explanation}'")
        print(f"\nДлина: {len(explanation)} символов")
        print(f"Слов: {len(explanation.split()) if explanation else 0}")
        
        if explanation and len(explanation.strip()) > 50:
            print("🎉 LLM генерирует полные объяснения!")
            return True
        else:
            print("⚠️ LLM генерирует короткие fallback объяснения")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при генерации: {e}")
        return False


if __name__ == '__main__':
    quick_test()
