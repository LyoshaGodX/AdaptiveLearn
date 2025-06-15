#!/usr/bin/env python3
"""
Детальный тест LLM модуля с выводом промптов и ответов

Этот тест:
1. Загружает LLM модель 
2. Показывает весь входной промпт
3. Выводит полный ответ LLM
4. Тестирует различные сценарии объяснений
5. Работает с реальными данными из БД
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

from mlmodels.llm.explanation_generator import ExplanationGenerator
from mlmodels.llm.prompt_templates import PromptTemplates
from mlmodels.models import DQNRecommendation


def print_separator(title: str, char="=", length=80):
    """Красивый разделитель"""
    print(f"\n{char * length}")
    print(f"{title.center(length)}")
    print(f"{char * length}")


def print_subsection(title: str):
    """Подсекция"""
    print(f"\n{'─' * 60}")
    print(f"📝 {title}")
    print(f"{'─' * 60}")


def test_prompt_generation():
    """Тест генерации промптов без LLM"""
    print_separator("ТЕСТ ГЕНЕРАЦИИ ПРОМПТОВ", "🧪")
    
    templates = PromptTemplates()
      # Тестовые данные для разных сценариев
    test_scenarios = [
        {
            'name': 'Начинающий студент - простое задание True/False',
            'data': {
                'student_name': 'Алексей',
                'task_title': 'Переменные в Python',
                'task_difficulty': 'beginner',
                'task_type': 'true_false',
                'target_skill': 'Основы Python',
                'target_skill_mastery': 0.1,
                'prerequisite_skills': [],
                'dependent_skills': [
                    {'skill_name': 'Условные операторы'},
                    {'skill_name': 'Циклы'}
                ],
                'student_progress': {'total_success_rate': 0.2}
            }
        },
        {
            'name': 'Средний студент - задание множественного выбора',
            'data': {
                'student_name': 'Мария',
                'task_title': 'Рекурсивные функции',
                'task_difficulty': 'intermediate',
                'task_type': 'multiple',
                'target_skill': 'Функции',
                'target_skill_mastery': 0.4,
                'prerequisite_skills': [
                    {'skill_name': 'Основы Python', 'mastery_probability': 0.9},
                    {'skill_name': 'Циклы', 'mastery_probability': 0.6}
                ],
                'dependent_skills': [
                    {'skill_name': 'Алгоритмы'},
                    {'skill_name': 'Структуры данных'}
                ],
                'student_progress': {'total_success_rate': 0.65}
            }
        },
        {
            'name': 'Продвинутый студент - задание одиночного выбора',
            'data': {
                'student_name': 'Дмитрий',
                'task_title': 'Оптимизация алгоритмов',
                'task_difficulty': 'advanced',
                'task_type': 'single',
                'target_skill': 'Алгоритмы',
                'target_skill_mastery': 0.8,
                'prerequisite_skills': [
                    {'skill_name': 'Структуры данных', 'mastery_probability': 0.9},
                    {'skill_name': 'Сложность алгоритмов', 'mastery_probability': 0.7},
                    {'skill_name': 'Математика', 'mastery_probability': 0.8}
                ],
                'dependent_skills': [
                    {'skill_name': 'Машинное обучение'},
                    {'skill_name': 'Высокопроизводительные вычисления'}
                ],
                'student_progress': {'total_success_rate': 0.85}
            }
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print_subsection(f"СЦЕНАРИЙ {i}: {scenario['name']}")
        
        data = scenario['data']
        prompt = templates.recommendation_explanation_prompt(
            student_name=data['student_name'],
            task_title=data['task_title'],
            task_difficulty=data['task_difficulty'],
            task_type=data['task_type'],
            target_skill=data['target_skill'],
            target_skill_mastery=data['target_skill_mastery'],
            prerequisite_skills=data['prerequisite_skills'],
            dependent_skills=data['dependent_skills'],
            student_progress=data['student_progress']        )
        
        print("📋 ВХОДНЫЕ ДАННЫЕ:")
        for key, value in data.items():
            if isinstance(value, list) and value:
                print(f"   {key}: {len(value)} элементов")
                for item in value:
                    print(f"      - {item}")
            else:
                print(f"   {key}: {value}")
        
        print(f"\n🤖 ПРОМПТ ДЛЯ LLM:")
        print(prompt)
        
        print(f"\n📏 СТАТИСТИКА ПРОМПТА:")
        print(f"   Длина: {len(prompt)} символов")
        print(f"   Строк: {len(prompt.split('n'))}")


def test_llm_with_detailed_output():
    """Тест с реальной LLM и детальным выводом"""
    print_separator("ТЕСТ РЕАЛЬНОЙ LLM С ДЕТАЛЬНЫМ ВЫВОДОМ", "🚀")
      # Инициализируем LLM
    print("🔄 Инициализация LLM...")
    generator = ExplanationGenerator(model_key='phi3.5-mini', device='auto')
    
    print("📊 Информация о модели:")
    model_info = generator.model_manager.get_model_info()
    for key, value in model_info.items():
        print(f"   {key}: {value}")
    
    if not generator.is_initialized:
        print("\n🚀 Загружаем LLM модель (это может занять время)...")
        success = generator.initialize(use_quantization=True)
        
        if not success:
            print("❌ Не удалось загрузить LLM модель")
            return False
        
        print("✅ LLM модель успешно загружена!")
      # Тестовые сценарии для генерации (5 примеров)
    test_cases = [
        {
            'name': 'Новичок - первые шаги в программировании',
            'data': {
                'student_name': 'Анна',
                'task_title': 'Что такое переменная?',
                'task_difficulty': 'beginner',
                'task_type': 'true_false',
                'target_skill_info': [{
                    'skill_name': 'Основы Python',
                    'current_mastery_probability': 0.05
                }],
                'prerequisite_skills_snapshot': [],
                'dependent_skills_snapshot': [
                    {'skill_name': 'Условные операторы'},
                    {'skill_name': 'Циклы'}
                ],
                'student_progress_context': {
                    'total_success_rate': 0.1
                }
            }
        },
        {
            'name': 'Средний уровень - изучение циклов',
            'data': {
                'student_name': 'Михаил',
                'task_title': 'Цикл for в Python',
                'task_difficulty': 'intermediate',
                'task_type': 'single',
                'target_skill_info': [{
                    'skill_name': 'Циклы',
                    'current_mastery_probability': 0.35
                }],
                'prerequisite_skills_snapshot': [
                    {'skill_name': 'Основы Python', 'mastery_probability': 0.8},
                    {'skill_name': 'Условные операторы', 'mastery_probability': 0.6}
                ],
                'dependent_skills_snapshot': [
                    {'skill_name': 'Функции'},
                    {'skill_name': 'Работа со списками'}
                ],
                'student_progress_context': {
                    'total_success_rate': 0.5
                }
            }
        },
        {
            'name': 'Продвинутый - сложные функции',
            'data': {
                'student_name': 'Елена',
                'task_title': 'Рекурсивные алгоритмы',
                'task_difficulty': 'advanced',
                'task_type': 'multiple',
                'target_skill_info': [{
                    'skill_name': 'Рекурсия',
                    'current_mastery_probability': 0.6
                }],
                'prerequisite_skills_snapshot': [
                    {'skill_name': 'Функции', 'mastery_probability': 0.9},
                    {'skill_name': 'Алгоритмы', 'mastery_probability': 0.7},
                    {'skill_name': 'Математические основы', 'mastery_probability': 0.8}
                ],
                'dependent_skills_snapshot': [
                    {'skill_name': 'Динамическое программирование'},
                    {'skill_name': 'Структуры данных'}
                ],
                'student_progress_context': {
                    'total_success_rate': 0.75
                }
            }
        },
        {
            'name': 'Освоение ООП - классы и объекты',
            'data': {
                'student_name': 'Дмитрий',
                'task_title': 'Наследование в Python',
                'task_difficulty': 'intermediate',
                'task_type': 'single',
                'target_skill_info': [{
                    'skill_name': 'ООП',
                    'current_mastery_probability': 0.45
                }],
                'prerequisite_skills_snapshot': [
                    {'skill_name': 'Классы и объекты', 'mastery_probability': 0.7},
                    {'skill_name': 'Функции', 'mastery_probability': 0.85}
                ],
                'dependent_skills_snapshot': [
                    {'skill_name': 'Полиморфизм'},
                    {'skill_name': 'Паттерны проектирования'}
                ],
                'student_progress_context': {
                    'total_success_rate': 0.62
                }
            }
        },
        {
            'name': 'Работа с данными - структуры данных',
            'data': {
                'student_name': 'София',
                'task_title': 'Реализация стека',
                'task_difficulty': 'advanced',
                'task_type': 'multiple',
                'target_skill_info': [{
                    'skill_name': 'Структуры данных',
                    'current_mastery_probability': 0.55
                }],
                'prerequisite_skills_snapshot': [
                    {'skill_name': 'ООП', 'mastery_probability': 0.8},
                    {'skill_name': 'Алгоритмы', 'mastery_probability': 0.75},
                    {'skill_name': 'Списки и словари', 'mastery_probability': 0.9}
                ],
                'dependent_skills_snapshot': [
                    {'skill_name': 'Алгоритмы сортировки'},
                    {'skill_name': 'Графы и деревья'}
                ],
                'student_progress_context': {
                    'total_success_rate': 0.68
                }
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print_subsection(f"ГЕНЕРАЦИЯ {i}: {test_case['name']}")
        
        data = test_case['data']
        
        print("📋 ВХОДНЫЕ ДАННЫЕ:")
        print(f"   Студент: {data['student_name']}")
        print(f"   Задание: {data['task_title']}")
        print(f"   Сложность: {data['task_difficulty']}")
        
        if data['target_skill_info']:
            skill = data['target_skill_info'][0]
            print(f"   Целевой навык: {skill['skill_name']}")
            print(f"   Освоенность: {skill['current_mastery_probability']:.1%}")
        
        prereq_count = len(data.get('prerequisite_skills_snapshot', []))
        print(f"   Prerequisite навыков: {prereq_count}")
        
        progress = data.get('student_progress_context', {})
        if progress:
            print(f"   Общий успех: {progress.get('total_success_rate', 0):.1%}")
          # Создаем промпт
        templates = PromptTemplates()
        target_skill = data['target_skill_info'][0]['skill_name'] if data['target_skill_info'] else 'Programming'
        target_mastery = data['target_skill_info'][0]['current_mastery_probability'] if data['target_skill_info'] else 0.1
        
        prompt = templates.recommendation_explanation_prompt(
            student_name=data['student_name'],
            task_title=data['task_title'],
            task_difficulty=data['task_difficulty'],
            task_type=data.get('task_type', 'single'),  # Добавляем тип задания
            target_skill=target_skill,
            target_skill_mastery=target_mastery,
            prerequisite_skills=data.get('prerequisite_skills_snapshot', []),            dependent_skills=data.get('dependent_skills_snapshot', []),  # Добавляем зависимые навыки
            student_progress=data.get('student_progress_context', {})
        )
        
        print(f"\n🤖 ПОЛНЫЙ ПРОМПТ ДЛЯ LLM:")
        print(prompt)
        
        print(f"\n⚙️ ГЕНЕРАЦИЯ...")
        
        # Генерируем объяснение
        explanation = generator.generate_recommendation_explanation(data)
        
        print(f"\n✨ РЕЗУЛЬТАТ LLM:")
        if explanation:
            print(explanation)
        else:            print("[ПУСТОЙ ОТВЕТ ИЛИ ОШИБКА]")
        
        print(f"\n📊 СТАТИСТИКА:")
        print(f"   Длина объяснения: {len(explanation)} символов")
        print(f"   Слов: {len(explanation.split()) if explanation else 0}")


def main():
    """Главная функция теста"""
    print_separator("🧪 ДЕТАЛЬНЫЙ ТЕСТ LLM МОДУЛЯ", "🚀")
    
    try:
        # 1. Тест генерации промптов (без LLM)
        test_prompt_generation()
        
        # 2. Тест реальной LLM с 5 примерами
        print("\n" + "=" * 80)
        user_input = input("🤖 Загрузить LLM модель для тестирования? (y/N): ").strip().lower()
        
        if user_input in ['y', 'yes', 'д', 'да']:
            test_llm_with_detailed_output()
        else:
            print("⏭️ Пропускаем тест реальной LLM")
        
        print_separator("✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ", "🎉")
        
    except KeyboardInterrupt:
        print("\n\n❌ Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n\n💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
