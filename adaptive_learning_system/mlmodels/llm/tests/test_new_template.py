"""
Тест нового расширенного алгоритмического шаблона
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


def test_new_template():
    """Тест нового расширенного шаблона"""
    print("=== ТЕСТ НОВОГО РАСШИРЕННОГО ШАБЛОНА ===\n")
    
    # Создаем генератор с Gemma для быстрого тестирования
    generator = ExplanationGenerator(model_key='gemma-2b', device='auto')
    
    # Инициализируем модель
    print("🔄 Инициализация Gemma-2B...")
    success = generator.initialize(use_quantization=True)
    
    if not success:
        print("❌ Не удалось инициализировать модель")
        return False
    
    print("✅ Модель инициализирована")
    
    # Тестовые данные для демонстрации нового шаблона
    test_data = {
        'student_name': 'Мария',
        'task_title': 'Циклы for и while в Python',
        'task_difficulty': 'intermediate',
        'task_type': 'multiple',
        'target_skill_info': [{
            'skill_name': 'Циклы',
            'current_mastery_probability': 0.45
        }],
        'prerequisite_skills_snapshot': [
            {'skill_name': 'Основы Python', 'mastery_probability': 0.85},
            {'skill_name': 'Переменные', 'mastery_probability': 0.75}
        ],
        'dependent_skills_snapshot': [
            {'skill_name': 'Функции'},
            {'skill_name': 'Работа со списками'},
            {'skill_name': 'Обработка данных'}
        ],
        'student_progress_context': {
            'total_success_rate': 0.62
        }
    }
    
    print(f"\n📊 ТЕСТОВЫЕ ДАННЫЕ:")
    print(f"   Студент: {test_data['student_name']}")
    print(f"   Задание: {test_data['task_title']}")
    print(f"   Тип: {test_data['task_type']} | Сложность: {test_data['task_difficulty']}")
    print(f"   Навык: {test_data['target_skill_info'][0]['skill_name']} (освоен на {test_data['target_skill_info'][0]['current_mastery_probability']:.0%})")
    print(f"   Общий успех: {test_data['student_progress_context']['total_success_rate']:.0%}")
    
    print(f"\n🚀 Генерация с новым шаблоном...")
    
    try:
        explanation = generator.generate_recommendation_explanation(test_data)
        
        print(f"\n🎯 РЕЗУЛЬТАТ НОВОГО ШАБЛОНА:")
        print("=" * 80)
        print(f"{explanation}")
        print("=" * 80)
        print(f"\nДлина: {len(explanation)} символов")
        print(f"Слов: {len(explanation.split()) if explanation else 0}")
        
        # Проверяем качество ответа
        if explanation and len(explanation.strip()) > 200:
            print("🎉 Новый шаблон генерирует развернутые объяснения!")
            return True
        else:
            print("⚠️ Объяснение недостаточно подробное")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при генерации: {e}")
        return False


if __name__ == '__main__':
    test_new_template()
