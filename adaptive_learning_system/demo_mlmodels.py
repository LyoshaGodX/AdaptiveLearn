#!/usr/bin/env python3
"""
Основной скрипт для демонстрации функциональности MLModels приложения.

Включает:
1. Работу с интерфейсами данных
2. Создание графа навыков  
3. Генерацию синтетических данных
4. Обучение BKT модели
5. Рекомендации для студентов

Использование:
    python demo_mlmodels.py
"""

import os
import sys
import django
from pathlib import Path

# Настройка Django
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

# Настройка Django
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

import mlmodels
import pandas as pd
import json
from datetime import datetime

# Получаем необходимые классы
BKTModel, BKTParameters, BKTTrainer = mlmodels.get_bkt_models()
DatabaseInterface, SkillsGraph = mlmodels.get_data_interfaces()
SyntheticDataGenerator, SyntheticStudent, SyntheticAttempt = mlmodels.get_synthetic_data()
(StudentStrategy, StudentStrategyFactory, BeginnerStrategy,
 IntermediateStrategy, AdvancedStrategy, GiftedStrategy, StruggleStrategy) = mlmodels.get_student_strategies()

# Импортируем классы напрямую для использования в демо
from mlmodels.data_interfaces.database_interface import (
    CourseDataInterface, SkillDataInterface, TaskDataInterface, StudentDataInterface
)
from mlmodels.data_interfaces.skills_graph import SkillsGraphInterface


def demo_data_interfaces():
    """Демонстрация работы с интерфейсами данных"""
    print("=" * 60)
    print("ДЕМОНСТРАЦИЯ ИНТЕРФЕЙСОВ ДАННЫХ")
    print("=" * 60)
    
    # Получаем все курсы
    courses = CourseDataInterface.get_all_courses()
    print(f"\nВсего курсов в системе: {courses.count()}")
    
    if courses.exists():
        course = courses.first()
        print(f"Пример курса: {course.name} (ID: {course.id})")
        
        # Статистика курса
        stats = CourseDataInterface.get_course_statistics(course.id)
        print(f"Статистика курса {course.name}:")
        print(f"  - Навыков: {stats['skills_count']}")
        print(f"  - Заданий: {stats['tasks_count']}")
        print(f"  - Студентов: {stats['students_count']}")
        
        # Навыки курса
        skills = CourseDataInterface.get_course_skills(course.id)
        print(f"\nПервые 5 навыков курса:")
        for skill in skills[:5]:
            print(f"  - {skill.name} (базовый: {skill.is_base})")
    
    # Все навыки
    all_skills = SkillDataInterface.get_all_skills()
    print(f"\nВсего навыков в системе: {all_skills.count()}")
    
    # Базовые навыки
    base_skills = SkillDataInterface.get_base_skills()
    print(f"Базовых навыков: {base_skills.count()}")


def demo_skills_graph():
    """Демонстрация работы с графом навыков"""
    print("\n" + "=" * 60)
    print("ДЕМОНСТРАЦИЯ ГРАФА НАВЫКОВ")
    print("=" * 60)
    
    # Создаем граф навыков
    graph_interface = SkillsGraphInterface()
    graph = graph_interface.build_graph_from_database()
    
    print(f"\nГраф навыков построен:")
    print(f"  - Узлов (навыков): {graph.number_of_nodes()}")
    print(f"  - Рёбер (зависимостей): {graph.number_of_edges()}")
    
    # Статистика графа
    stats = graph_interface.get_graph_statistics()
    print(f"\nСтатистика графа:")
    print(f"  - Базовых навыков: {stats['node_types']['base_skills']}")
    print(f"  - Конечных навыков: {stats['node_types']['leaf_skills']}")
    print(f"  - Плотность графа: {stats['basic_stats']['density']:.3f}")
    print(f"  - Ациклический граф: {stats['basic_stats']['is_dag']}")
    
    # Валидация графа
    validation = graph_interface.validate_graph()
    print(f"\nВалидация графа:")
    print(f"  - Граф валидный: {validation['is_valid']}")
    if validation['issues']:
        print(f"  - Найдено проблем: {len(validation['issues'])}")
        for issue in validation['issues']:
            print(f"    * {issue['description']}")
    
    # Экспорт графа
    output_dir = Path("temp_dir")
    output_dir.mkdir(exist_ok=True)
    
    # Экспорт в DOT формат
    dot_file = output_dir / "skills_graph.dot"
    if graph_interface.export_to_dot(str(dot_file)):
        print(f"\nГраф экспортирован в DOT формат: {dot_file}")    
    # Экспорт в JSON
    json_file = output_dir / "skills_graph.json"
    if graph_interface.export_to_json(str(json_file)):
        print(f"Граф экспортирован в JSON формат: {json_file}")
    
    # Демонстрация рекомендуемого порядка изучения
    if graph.number_of_nodes() > 0:
        try:
            learning_order = graph_interface.get_topological_order()
            print(f"\nРекомендуемый порядок изучения навыков (первые 10):")
            for i, skill_id in enumerate(learning_order[:10]):
                skill_name = graph.nodes[skill_id].get('name', f'Skill {skill_id}')
                print(f"  {i+1}. {skill_name}")
        except Exception as e:
            print(f"\n[ВНИМАНИЕ] Не удалось определить порядок изучения: граф содержит циклы")
            print("Это означает, что есть циклические зависимости между навыками в данных")


def demo_student_strategies():
    """Демонстрация стратегий студентов"""
    print("\n" + "=" * 60)
    print("ДЕМОНСТРАЦИЯ СТРАТЕГИЙ СТУДЕНТОВ")
    print("=" * 60)    
    # Создаем разные типы студентов
    strategy_types = ['beginner', 'intermediate', 'advanced', 'gifted', 'struggle']
    
    print("\nСоздание стратегий студентов:")
    strategies = []
    for strategy_type in strategy_types:
        strategy = StudentStrategyFactory.create_strategy(strategy_type)
        strategies.append(strategy)
        print(f"  - {strategy.get_strategy_name()}: "
              f"Скорость обучения = {strategy.characteristics.learning_speed.value:.2f}, "
              f"P(T) = {strategy.characteristics.base_transition_prob:.2f}")
    
    # Создаем популяцию студентов
    print(f"\nСоздание смешанной популяции из 20 студентов:")
    population = StudentStrategyFactory.create_mixed_population(20)
    
    strategy_counts = {}
    for student in population:
        strategy_name = student.get_strategy_name()
        strategy_counts[strategy_name] = strategy_counts.get(strategy_name, 0) + 1
    
    for strategy_name, count in strategy_counts.items():
        percentage = (count / len(population)) * 100
        print(f"  - {strategy_name}: {count} студентов ({percentage:.1f}%)")


def demo_synthetic_data_generation():
    """Демонстрация генерации синтетических данных"""
    print("\n" + "=" * 60)
    print("ДЕМОНСТРАЦИЯ ГЕНЕРАЦИИ СИНТЕТИЧЕСКИХ ДАННЫХ")
    print("=" * 60)
    
    # Получаем курсы для генерации данных
    courses = CourseDataInterface.get_all_courses()
    if not courses.exists():
        print("Нет доступных курсов для генерации данных")
        return
    
    course_ids = [course.id for course in courses[:2]]  # Берем первые 2 курса
    print(f"Генерируем данные для курсов: {course_ids}")
    
    # Создаем генератор
    generator = SyntheticDataGenerator(course_ids)
    
    # Генерируем небольшой датасет
    print(f"\nГенерация датасета для 10 студентов...")
    dataset = generator.generate_dataset(
        num_students=10,
        sessions_per_student=(5, 15),
        output_format='pandas'
    )
    
    print(f"\nСгенерированный датасет:")
    print(f"  - Строк (попыток): {len(dataset)}")
    print(f"  - Уникальных студентов: {dataset['student_id'].nunique()}")
    print(f"  - Уникальных заданий: {dataset['task_id'].nunique()}")
    print(f"  - Уникальных навыков: {dataset['skill_id'].nunique()}")
    
    # Статистика по результатам
    success_rate = dataset['is_correct'].mean()
    avg_time = dataset['time_spent_minutes'].mean()
    print(f"  - Общий процент успеха: {success_rate:.1%}")
    print(f"  - Среднее время на задание: {avg_time:.1f} минут")
    
    # Статистика по стратегиям
    print(f"\nСтатистика по стратегиям студентов:")
    strategy_stats = dataset.groupby('student_strategy')['is_correct'].agg(['count', 'mean'])
    for strategy, stats in strategy_stats.iterrows():
        print(f"  - {strategy}: {stats['count']} попыток, успех {stats['mean']:.1%}")
    
    # Сохраняем датасет
    output_dir = Path("temp_dir")
    output_dir.mkdir(exist_ok=True)
    
    dataset_file = output_dir / "synthetic_dataset.csv"
    dataset.to_csv(dataset_file, index=False)
    print(f"\nДатасет сохранен в: {dataset_file}")
    
    return dataset


def demo_bkt_training(dataset):
    """Демонстрация обучения BKT модели"""
    print("\n" + "=" * 60)
    print("ДЕМОНСТРАЦИЯ ОБУЧЕНИЯ BKT МОДЕЛИ")
    print("=" * 60)
    
    if dataset is None or len(dataset) == 0:
        print("Нет данных для обучения BKT модели")
        return None
    
    # Создаем модель и тренер
    model = BKTModel()
    trainer = BKTTrainer(model)
    
    # Подготавливаем данные для обучения
    print(f"Подготовка данных для обучения...")
    training_data = trainer.prepare_training_data(dataset)
    print(f"Подготовлено {len(training_data)} примеров для обучения")
    
    # Разделяем на тренировочные и тестовые данные
    split_idx = int(len(training_data) * 0.8)
    train_data = training_data[:split_idx]
    test_data = training_data[split_idx:]
    
    print(f"Тренировочных примеров: {len(train_data)}")
    print(f"Тестовых примеров: {len(test_data)}")
    
    # Обучаем модель методом EM
    print(f"\nОбучение модели методом EM...")
    training_results = trainer.train_with_em(
        train_data, 
        max_iterations=50,
        verbose=True
    )
    
    print(f"\nРезультаты обучения:")
    for skill_id, results in training_results.items():
        print(f"  Навык {skill_id}:")
        print(f"    - Итераций: {results['iterations']}")
        print(f"    - Точность: {results['accuracy']:.3f}")
        print(f"    - Log-likelihood: {results['log_likelihood']:.3f}")
        params = results['parameters']
        print(f"    - P(L0)={params['P_L0']:.3f}, P(T)={params['P_T']:.3f}, "
              f"P(G)={params['P_G']:.3f}, P(S)={params['P_S']:.3f}")
    
    # Оценка на тестовых данных
    if test_data:
        print(f"\nОценка модели на тестовых данных...")
        evaluation = trainer.evaluate_model(test_data)
        
        overall = evaluation['overall_metrics']
        print(f"Общие метрики:")
        print(f"  - Точность: {overall['overall_accuracy']:.3f}")
        print(f"  - Log-likelihood: {overall['overall_log_likelihood']:.3f}")
        print(f"  - Оценено навыков: {evaluation['evaluated_skills']}")
    
    # Сохраняем модель
    output_dir = Path("temp_dir")
    model_file = output_dir / "bkt_model.json"
    model.save_model(str(model_file))
    print(f"\nМодель сохранена в: {model_file}")
    
    return model


def demo_bkt_predictions(model, dataset):
    """Демонстрация предсказаний BKT модели"""
    print("\n" + "=" * 60)
    print("ДЕМОНСТРАЦИЯ ПРЕДСКАЗАНИЙ BKT МОДЕЛИ")
    print("=" * 60)
    
    if model is None or dataset is None:
        print("Нет обученной модели или данных для демонстрации")
        return
    
    # Берем первых студентов для демонстрации
    unique_students = dataset['student_id'].unique()[:3]
    
    print(f"Демонстрация предсказаний для {len(unique_students)} студентов:")
    
    for student_id in unique_students:
        print(f"\nСтудент {student_id}:")
        
        # Получаем профиль студента
        profile = model.get_student_profile(student_id)
        if not profile:
            print("  Нет данных о студенте")
            continue
        
        print(f"  Текущее освоение навыков:")
        for skill_id, state in profile.items():
            print(f"    Навык {skill_id}: {state.current_mastery:.3f} "
                  f"({state.attempts_count} попыток, точность {state.accuracy:.3f})")
        
        # Рекомендации навыков
        recommendations = model.recommend_skills_for_student(student_id, max_recommendations=3)
        if recommendations:
            print(f"  Рекомендуемые навыки:")
            for skill_id, mastery, reason in recommendations:
                print(f"    Навык {skill_id}: освоение {mastery:.3f} - {reason}")
        
        # Предсказания для случайного навыка
        if profile:
            skill_id = list(profile.keys())[0]
            prediction = model.predict_performance(student_id, skill_id)
            print(f"  Предсказание для навыка {skill_id}: {prediction:.3f} вероятность успеха")


def demo_skills_complexity():
    """Демонстрация анализа сложности навыков"""
    print("\n" + "=" * 60)
    print("ДЕМОНСТРАЦИЯ АНАЛИЗА СЛОЖНОСТИ НАВЫКОВ")
    print("=" * 60)
    
    # Создаем граф навыков
    graph_interface = SkillsGraphInterface()
    graph = graph_interface.build_graph_from_database()
    
    if graph.number_of_nodes() == 0:
        print("Нет данных о навыках")
        return
    
    # Анализ сложности навыков
    print(f"Анализ сложности навыков:")
    
    # Берем первые несколько навыков для анализа
    skill_nodes = list(graph.nodes())[:5]
    
    for skill_id in skill_nodes:
        complexity = graph_interface.get_skill_complexity(skill_id)
        skill_name = graph.nodes[skill_id].get('name', f'Skill {skill_id}')
        
        print(f"\nНавык: {skill_name}")
        print(f"  - Глубина зависимостей: {complexity['depth']}")
        print(f"  - Количество зависящих навыков: {complexity['breadth']}")
        print(f"  - Прямых пререквизитов: {complexity['direct_prerequisites']}")
        print(f"  - Оценка сложности: {complexity['complexity_score']:.3f}")
    
    # Предложение последовательности изучения
    if len(skill_nodes) >= 3:
        target_skills = skill_nodes[:3]
        sequence = graph_interface.suggest_learning_sequence(target_skills)
        
        print(f"\nРекомендуемая последовательность изучения для достижения навыков {target_skills}:")
        for step in sequence[:10]:  # Показываем первые 10 шагов
            status = "✓ готов" if step['is_ready'] else "⏳ ожидает"
            target_mark = " 🎯" if step['is_target'] else ""
            print(f"  {step['position']}. {step['skill_name']} ({status}){target_mark}")


def main():
    """Главная функция демонстрации"""
    print("ДЕМОНСТРАЦИЯ ВОЗМОЖНОСТЕЙ MLMODELS")
    print("Адаптивная система обучения с поддержкой BKT модели")
    print(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. Интерфейсы данных
        demo_data_interfaces()
        
        # 2. Граф навыков
        demo_skills_graph()
        
        # 3. Стратегии студентов
        demo_student_strategies()
        
        # 4. Генерация синтетических данных
        dataset = demo_synthetic_data_generation()
        
        # 5. Обучение BKT модели
        model = demo_bkt_training(dataset)
        
        # 6. Предсказания модели
        demo_bkt_predictions(model, dataset)
        
        # 7. Анализ сложности навыков
        demo_skills_complexity()
        
        print("\n" + "=" * 60)
        print("✅ ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА УСПЕШНО")
        print("=" * 60)
        print("\nСозданные файлы:")
        output_dir = Path("temp_dir")
        if output_dir.exists():
            for file_path in output_dir.glob("*"):
                print(f"  - {file_path}")
        
    except Exception as e:
        print(f"\n[ОШИБКА] ВО ВРЕМЯ ДЕМОНСТРАЦИИ: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
