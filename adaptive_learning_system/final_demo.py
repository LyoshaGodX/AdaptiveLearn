#!/usr/bin/env python3
"""
Финальная демонстрация системы адаптивного обучения MLModels
с полной поддержкой типов заданий и уровней сложности.

Этот скрипт демонстрирует:
1. Интеграцию всех компонентов системы
2. Работу с типами заданий (true_false, single, multiple)
3. Адаптацию под уровни сложности (beginner, intermediate, advanced)
4. Генерацию синтетических данных с учетом новых параметров
5. Обучение и предсказания BKT модели
6. Рекомендации адаптивной системы
"""

import os
import sys
import django
from datetime import datetime
from typing import Dict, List, Any

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

# Импорты модулей системы
import mlmodels
from mlmodels.bkt.base_model import BKTModel, BKTParameters, TaskCharacteristics
from mlmodels.student_strategies.strategies import StudentStrategyFactory
from mlmodels.synthetic_data.generator import SyntheticDataGenerator

def main():
    print("🚀 ФИНАЛЬНАЯ ДЕМОНСТРАЦИЯ СИСТЕМЫ MLMODELS")
    print("Адаптивное обучение с поддержкой типов заданий и сложности")
    print(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
      # 1. Инициализация системы
    print("\n📋 ЭТАП 1: ИНИЦИАЛИЗАЦИЯ СИСТЕМЫ")
    print("-" * 50)
    
    # Получаем интерфейсы
    database_interface = mlmodels.get_database_interface()
    skills_graph = mlmodels.get_skills_graph()
    
    # Загружаем данные
    courses = database_interface.get_all_courses()
    print(f"✅ Загружено курсов: {len(courses)}")
    
    skills = database_interface.get_all_skills()
    print(f"✅ Загружено навыков: {len(skills)}")
    
    tasks = database_interface.get_all_tasks()
    print(f"✅ Загружено заданий: {len(tasks)}")
      # Анализируем типы заданий
    task_types = {}
    difficulty_levels = {}
    
    for task in tasks:
        task_type = getattr(task, 'task_type', 'single')
        difficulty = getattr(task, 'difficulty', 'intermediate')
        
        task_types[task_type] = task_types.get(task_type, 0) + 1
        difficulty_levels[difficulty] = difficulty_levels.get(difficulty, 0) + 1
    
    print(f"📊 Распределение по типам заданий: {task_types}")
    print(f"📊 Распределение по уровням сложности: {difficulty_levels}")
    
    # 2. Демонстрация адаптации BKT параметров
    print("\n🧠 ЭТАП 2: АДАПТАЦИЯ BKT ПОД ТИПЫ ЗАДАНИЙ")
    print("-" * 50)
    
    # Создаем BKT модель
    bkt_model = BKTModel()
    
    # Базовые параметры
    base_params = BKTParameters(P_L0=0.1, P_T=0.3, P_G=0.2, P_S=0.1)
    
    # Тестируем адаптацию для разных типов заданий
    test_cases = [
        ('true_false', 'beginner'),
        ('single', 'intermediate'), 
        ('multiple', 'advanced')
    ]
    
    print(f"🔧 Базовые параметры: P(L0)={base_params.P_L0}, P(T)={base_params.P_T}, P(G)={base_params.P_G}, P(S)={base_params.P_S}")
    print("\nАдаптация параметров под разные типы заданий:")
    
    for task_type, difficulty in test_cases:
        characteristics = TaskCharacteristics(task_type=task_type, difficulty=difficulty)
        adapted_params = bkt_model._adjust_parameters_for_task(base_params, characteristics)
        
        print(f\"\
📝 {task_type.upper()} ({difficulty}):\")
        print(f\"   P(G): {base_params.P_G:.3f} → {adapted_params.P_G:.3f}\")
        print(f\"   P(S): {base_params.P_S:.3f} → {adapted_params.P_S:.3f}\")
        print(f\"   P(T): {base_params.P_T:.3f} → {adapted_params.P_T:.3f}\")
        
        # Предсказываем вероятность успеха для нового студента
        bkt_model.set_skill_parameters(1, base_params)
        prob = bkt_model.predict_performance(1, 1, characteristics)
        print(f\"   🎯 Предсказанная вероятность успеха: {prob:.3f}\")
    
    # 3. Демонстрация стратегий студентов с типами заданий
    print(\"\
👥 ЭТАП 3: СТРАТЕГИИ СТУДЕНТОВ И ТИПЫ ЗАДАНИЙ\")
    print(\"-\" * 50)
    
    strategies = ['beginner', 'intermediate', 'advanced', 'gifted', 'struggle']
    task_types_list = ['true_false', 'single', 'multiple']
    
    print(\"Предпочтения студентов по типам заданий:\")
    for strategy_name in strategies:
        strategy = StudentStrategyFactory.create_strategy(strategy_name)
        print(f\"\
🎓 {strategy_name.upper()}:\")
        
        for task_type in task_types_list:
            preference = strategy.get_task_type_preference(task_type)
            if preference > 1.2:
                emoji = \"💚\"
                desc = \"сильно предпочитает\"
            elif preference > 1.0:
                emoji = \"✅\"
                desc = \"предпочитает\"
            elif preference > 0.8:
                emoji = \"⚪\"
                desc = \"нейтрально\"
            else:
                emoji = \"❌\"
                desc = \"избегает\"
            
            print(f\"   {task_type:12} {emoji} {preference:.2f} ({desc})\")
    
    # 4. Генерация синтетических данных с учетом типов заданий
    print(\"\
🔬 ЭТАП 4: ГЕНЕРАЦИЯ СИНТЕТИЧЕСКИХ ДАННЫХ\")
    print(\"-\" * 50)
    
    generator = SyntheticDataGenerator()
    generator.load_course_data(['C1'])  # Используем один курс для демонстрации
    
    # Создаем студентов с разными стратегиями
    students = generator.generate_students(
        count=5,
        strategy_distribution={
            'beginner': 0.2,
            'intermediate': 0.3,
            'advanced': 0.3,
            'gifted': 0.1,
            'struggle': 0.1
        }
    )
    
    print(f\"✅ Создано студентов: {len(students)}\")
    
    # Генерируем попытки с учетом типов заданий
    attempts = generator.generate_attempts(
        students=students,
        attempts_per_student=50,
        time_period_days=30
    )
    
    print(f\"✅ Сгенерировано попыток: {len(attempts)}\")
    
    # Анализируем сгенерированные данные
    type_stats = {}
    difficulty_stats = {}
    success_by_type = {}
    
    for attempt in attempts:
        task_type = attempt.task_type
        difficulty = attempt.difficulty
        
        # Статистика по типам
        if task_type not in type_stats:
            type_stats[task_type] = {'total': 0, 'correct': 0}
        type_stats[task_type]['total'] += 1
        if attempt.is_correct:
            type_stats[task_type]['correct'] += 1
        
        # Статистика по сложности
        if difficulty not in difficulty_stats:
            difficulty_stats[difficulty] = {'total': 0, 'correct': 0}
        difficulty_stats[difficulty]['total'] += 1
        if attempt.is_correct:
            difficulty_stats[difficulty]['correct'] += 1
    
    print(\"\
📊 Статистика по типам заданий:\")
    for task_type, stats in type_stats.items():
        success_rate = stats['correct'] / stats['total'] * 100
        print(f\"   {task_type:12}: {stats['total']:3d} попыток, успех {success_rate:.1f}%\")
    
    print(\"\
📊 Статистика по уровням сложности:\")
    for difficulty, stats in difficulty_stats.items():
        success_rate = stats['correct'] / stats['total'] * 100
        print(f\"   {difficulty:12}: {stats['total']:3d} попыток, успех {success_rate:.1f}%\")
    
    # 5. Обучение BKT модели с учетом типов заданий
    print(\"\
🎯 ЭТАП 5: ОБУЧЕНИЕ BKT МОДЕЛИ\")
    print(\"-\" * 50)
    
    # Подготавливаем данные для обучения
    training_data = []
    for attempt in attempts[:300]:  # Берем первые 300 для обучения
        training_data.append({
            'student_id': attempt.student_id,
            'skill_id': attempt.skill_id,
            'is_correct': attempt.is_correct,
            'task_type': attempt.task_type,
            'difficulty': attempt.difficulty
        })
    
    print(f\"📚 Подготовлено примеров для обучения: {len(training_data)}\")
    
    # Обучаем модель
    trainer = mlmodels.get_bkt_trainer()
    trainer.fit(bkt_model, training_data)
    
    print(\"✅ Модель обучена\")
    
    # 6. Демонстрация предсказаний с учетом типов заданий
    print(\"\
🔮 ЭТАП 6: ПРЕДСКАЗАНИЯ С УЧЕТОМ ТИПОВ ЗАДАНИЙ\")
    print(\"-\" * 50)
    
    # Тестируем предсказания для разных типов заданий
    test_student_id = 1
    test_skill_id = 1
    
    print(f\"Предсказания для студента {test_student_id}, навык {test_skill_id}:\")
    
    for task_type in task_types_list:
        for difficulty in ['beginner', 'intermediate', 'advanced']:
            characteristics = TaskCharacteristics(task_type=task_type, difficulty=difficulty)
            prob = bkt_model.predict_performance(test_student_id, test_skill_id, characteristics)
            print(f\"   {task_type:12} ({difficulty:12}): {prob:.3f}\")
    
    # 7. Рекомендации системы
    print(\"\
💡 ЭТАП 7: АДАПТИВНЫЕ РЕКОМЕНДАЦИИ\")
    print(\"-\" * 50)
    
    # Получаем рекомендации для студента
    available_skills = list(range(1, 11))  # Первые 10 навыков
    recommendations = bkt_model.get_skill_recommendations(
        student_id=test_student_id,
        available_skills=available_skills,
        mastery_threshold=0.7
    )
    
    print(f\"🎓 Рекомендации для студента {test_student_id}:\")
    if recommendations:
        for i, skill_id in enumerate(recommendations[:5], 1):
            skill_name = f\"Навык {skill_id}\"  # В реальной системе загружали бы название
            mastery = bkt_model.get_student_mastery_summary(test_student_id).get(skill_id, 0.0)
            print(f\"   {i}. {skill_name} (текущее освоение: {mastery:.2f})\")
    else:
        print(\"   Нет доступных рекомендаций\")
    
    # 8. Сохранение результатов
    print(\"\
💾 ЭТАП 8: СОХРАНЕНИЕ РЕЗУЛЬТАТОВ\")
    print(\"-\" * 50)
    
    # Создаем папку для результатов если нет
    os.makedirs('temp_dir', exist_ok=True)
    
    # Сохраняем модель
    model_path = 'temp_dir/final_bkt_model.json'
    bkt_model.save_model(model_path)
    print(f\"✅ BKT модель сохранена: {model_path}\")
    
    # Сохраняем датасет
    dataset_path = 'temp_dir/final_synthetic_dataset.csv'
    generator.save_dataset(attempts, students, dataset_path, 'csv')
    print(f\"✅ Синтетический датасет сохранен: {dataset_path}\")
    
    # Сохраняем статистику
    stats_path = 'temp_dir/final_statistics.json'
    import json
    
    final_stats = {
        'timestamp': datetime.now().isoformat(),
        'courses_count': len(courses),
        'skills_count': len(skills),
        'tasks_count': len(tasks),
        'task_types_distribution': task_types,
        'difficulty_distribution': difficulty_levels,
        'generated_students': len(students),
        'generated_attempts': len(attempts),
        'training_examples': len(training_data),
        'type_success_stats': {
            task_type: {
                'total': stats['total'],
                'success_rate': stats['correct'] / stats['total']
            }
            for task_type, stats in type_stats.items()
        },
        'difficulty_success_stats': {
            difficulty: {
                'total': stats['total'],
                'success_rate': stats['correct'] / stats['total']
            }
            for difficulty, stats in difficulty_stats.items()
        }
    }
    
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(final_stats, f, ensure_ascii=False, indent=2)
    
    print(f\"✅ Финальная статистика сохранена: {stats_path}\")
    
    # Финальный отчет
    print(\"\
🎉 ФИНАЛЬНЫЙ ОТЧЕТ\")
    print(\"=\" * 80)
    print(\"✅ Система адаптивного обучения MLModels успешно продемонстрирована!\")
    print(\"\
🔧 Реализованные возможности:\")
    print(\"   ✓ Поддержка типов заданий (true_false, single, multiple)\")
    print(\"   ✓ Адаптация под уровни сложности (beginner, intermediate, advanced)\")
    print(\"   ✓ BKT модель с динамической адаптацией параметров\")
    print(\"   ✓ Стратегии студентов с предпочтениями по типам заданий\")
    print(\"   ✓ Генерация синтетических данных с учетом новых параметров\")
    print(\"   ✓ Обучение и предсказания модели\")
    print(\"   ✓ Адаптивные рекомендации системы\")
    print(\"   ✓ Полная интеграция с Django\")
    
    print(\"\
📁 Созданные файлы:\")
    print(f\"   • {model_path}\")
    print(f\"   • {dataset_path}\")
    print(f\"   • {stats_path}\")
    
    print(\"\
🚀 Система готова к использованию в продакшене!\")
    print(\"=\" * 80)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f\"\
❌ ОШИБКА: {e}\")
        import traceback
        traceback.print_exc()
        sys.exit(1)
