#!/usr/bin/env python3
"""
Тест сравнения различных LLM моделей

Сравнивает качество генерации объяснений между:
- Qwen2.5-0.5B-Instruct
- Phi-3.5-mini-instruct  
- saiga_mistral_7b (если доступна)
"""

import os
import sys
from pathlib import Path
import time
from typing import Dict, List

# Добавляем путь к Django проекту
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')

import django
django.setup()

from mlmodels.llm.explanation_generator import ExplanationGenerator
from mlmodels.llm.model_manager import LLMModelManager


def print_separator(title: str, char="=", length=80):
    """Красивый разделитель"""
    print(f"\n{char * length}")
    print(f"{title.center(length)}")  
    print(f"{char * length}")


def test_model_comparison():
    """Сравнение разных LLM моделей"""
    print_separator("🏆 СРАВНЕНИЕ LLM МОДЕЛЕЙ", "🔥")
    
    # Получаем список поддерживаемых моделей
    supported_models = LLMModelManager.list_supported_models()
    
    print("📋 ДОСТУПНЫЕ МОДЕЛИ:")
    for key, info in supported_models.items():
        print(f"   🤖 {key}:")
        print(f"      Название: {info['model_name']}")
        print(f"      Размер: {info['size_gb']} GB")
        print(f"      Описание: {info['description']}")
    
    # Тестовые данные
    test_data = {
        'student_name': 'Елена',
        'task_title': 'Обработка исключений в Python',
        'task_difficulty': 'intermediate',
        'target_skill_info': [{
            'skill_name': 'Обработка ошибок',
            'current_mastery_probability': 0.3
        }],
        'prerequisite_skills_snapshot': [
            {'skill_name': 'Основы Python', 'mastery_probability': 0.8},
            {'skill_name': 'Условные операторы', 'mastery_probability': 0.7}
        ],
        'student_progress_context': {
            'total_success_rate': 0.6
        }
    }
    
    print(f"\n📝 ТЕСТОВЫЕ ДАННЫЕ:")
    print(f"   Студент: {test_data['student_name']}")
    print(f"   Задание: {test_data['task_title']}")
    print(f"   Сложность: {test_data['task_difficulty']}")
    print(f"   Целевой навык: {test_data['target_skill_info'][0]['skill_name']}")
    print(f"   Освоенность: {test_data['target_skill_info'][0]['current_mastery_probability']:.1%}")
    
    # Модели для тестирования (начинаем с самой быстрой)
    models_to_test = ['qwen2.5-0.5b']  # Добавьте другие по желанию
    
    results = {}
    
    for model_key in models_to_test:
        print_separator(f"ТЕСТ МОДЕЛИ: {model_key.upper()}", "🚀")
        
        try:
            print(f"🔄 Инициализация {model_key}...")
            start_time = time.time()
            
            generator = ExplanationGenerator(model_key=model_key, device='auto')
            
            if not generator.is_initialized:
                print("⏳ Загружаем модель...")
                success = generator.initialize(use_quantization=True)
                
                if not success:
                    print(f"❌ Не удалось загрузить модель {model_key}")
                    continue
            
            init_time = time.time() - start_time
            print(f"✅ Модель загружена за {init_time:.1f} секунд")
            
            # Генерация объяснения
            print("🤖 Генерация объяснения...")
            gen_start = time.time()
            
            explanation = generator.generate_recommendation_explanation(test_data)
            
            gen_time = time.time() - gen_start
            
            print(f"\n📝 РЕЗУЛЬТАТ ({model_key}):")
            print("┌" + "─" * 78 + "┐")
            if explanation:
                words = explanation.split()
                current_line = ""
                for word in words:
                    if len(current_line + " " + word) <= 76:
                        current_line += (" " + word if current_line else word)
                    else:
                        print(f"│ {current_line:<76} │")
                        current_line = word
                if current_line:
                    print(f"│ {current_line:<76} │")
            else:
                print("│ [ОШИБКА ИЛИ ПУСТОЙ ОТВЕТ]                                           │")
            print("└" + "─" * 78 + "┘")
            
            # Сохраняем результаты
            results[model_key] = {
                'explanation': explanation,
                'init_time': init_time,
                'generation_time': gen_time,
                'length': len(explanation) if explanation else 0,
                'word_count': len(explanation.split()) if explanation else 0,
                'success': bool(explanation and len(explanation.strip()) > 10)
            }
            
            print(f"\n📊 МЕТРИКИ:")
            print(f"   Время инициализации: {init_time:.1f} сек")
            print(f"   Время генерации: {gen_time:.2f} сек")
            print(f"   Длина: {results[model_key]['length']} символов")
            print(f"   Слов: {results[model_key]['word_count']}")
            print(f"   Качество: {'✅' if results[model_key]['success'] else '❌'}")
            
        except Exception as e:
            print(f"💥 ОШИБКА при тестировании {model_key}: {e}")
            results[model_key] = {
                'explanation': None,
                'init_time': 0,
                'generation_time': 0,
                'length': 0,
                'word_count': 0,
                'success': False,
                'error': str(e)
            }
    
    # Итоговое сравнение
    if len(results) > 1:
        print_separator("📊 ИТОГОВОЕ СРАВНЕНИЕ", "🏆")
        
        print("┌─────────────────┬──────────┬──────────┬─────────┬───────┬─────────┐")
        print("│ Модель          │ Инициал. │ Генерац. │ Длина   │ Слова │ Успех   │")
        print("├─────────────────┼──────────┼──────────┼─────────┼───────┼─────────┤")
        
        for model_key, result in results.items():
            name = model_key[:15]
            init_time = f"{result['init_time']:.1f}с" if result['success'] else "ОШИБКА"
            gen_time = f"{result['generation_time']:.2f}с" if result['success'] else "N/A"
            length = str(result['length'])
            words = str(result['word_count'])
            success = "✅" if result['success'] else "❌"
            
            print(f"│ {name:<15} │ {init_time:>8} │ {gen_time:>8} │ {length:>7} │ {words:>5} │ {success:>7} │")
        
        print("└─────────────────┴──────────┴──────────┴─────────┴───────┴─────────┘")
        
        # Рекомендации
        fastest_init = min((k for k, v in results.items() if v['success']), 
                          key=lambda k: results[k]['init_time'], default=None)
        fastest_gen = min((k for k, v in results.items() if v['success']), 
                         key=lambda k: results[k]['generation_time'], default=None)
        
        print(f"\n🏆 РЕКОМЕНДАЦИИ:")
        if fastest_init:
            print(f"   🚀 Быстрейшая инициализация: {fastest_init}")
        if fastest_gen:
            print(f"   ⚡ Быстрейшая генерация: {fastest_gen}")
        
        successful_models = [k for k, v in results.items() if v['success']]
        if successful_models:
            best_quality = max(successful_models, 
                             key=lambda k: results[k]['length'] if 150 <= results[k]['length'] <= 250 else 0)
            print(f"   ⭐ Лучшее качество (по длине): {best_quality}")


def main():
    """Главная функция"""
    print_separator("🧪 СРАВНИТЕЛЬНЫЙ ТЕСТ LLM МОДЕЛЕЙ", "🔬")
    
    print("📝 ОПИСАНИЕ:")
    print("   Этот тест сравнивает производительность и качество")
    print("   различных LLM моделей для генерации объяснений.")
    print("   ")
    print("⚠️  ВНИМАНИЕ:")
    print("   - Загрузка моделей может занять время")
    print("   - Требуется достаточно свободной памяти")
    print("   - Некоторые модели могут быть недоступны")
    
    try:
        input("\n👆 Нажмите Enter для продолжения или Ctrl+C для отмены...")
        test_model_comparison()
        
        print_separator("✅ СРАВНИТЕЛЬНЫЙ ТЕСТ ЗАВЕРШЕН", "🎉")
        
    except KeyboardInterrupt:
        print("\n\n❌ Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n\n💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
