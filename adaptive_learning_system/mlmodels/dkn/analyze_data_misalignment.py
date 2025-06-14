#!/usr/bin/env python3
"""
Анализ несоответствий между синтетическими и реальными данными для DKN

Выявление проблем и предложения по оптимизации обучающего датасета
"""

import os
import sys
import django
from pathlib import Path
import torch
import numpy as np
import pandas as pd
from typing import Dict, List, Any
import json

# Настройка Django
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

from django.contrib.auth.models import User
from skills.models import Skill
from methodist.models import Task
from mlmodels.models import TaskAttempt, StudentSkillMastery
from student.models import StudentProfile
from data_processor import DKNDataProcessor


def analyze_data_misalignment():
    """Анализ несоответствий между синтетическими и реальными данными"""
    print("🔍 АНАЛИЗ НЕСООТВЕТСТВИЙ ДАННЫХ")
    print("=" * 60)
    
    # 1. Загружаем синтетические данные
    synthetic_path = Path("dataset/enhanced_synthetic_dataset.csv")
    if not synthetic_path.exists():
        print("❌ Синтетические данные не найдены!")
        return
    
    df_synthetic = pd.read_csv(synthetic_path)
    print(f"📊 Синтетических записей: {len(df_synthetic)}")
    
    # 2. Анализируем реальные данные
    real_students = User.objects.filter(student_profile__isnull=False)
    real_attempts = TaskAttempt.objects.all()
    real_masteries = StudentSkillMastery.objects.all()
    
    print(f"📊 Реальных студентов: {real_students.count()}")
    print(f"📊 Реальных попыток: {real_attempts.count()}")
    print(f"📊 Реальных освоений навыков: {real_masteries.count()}")
    
    return df_synthetic, real_students, real_attempts, real_masteries


def identify_feature_mismatches(df_synthetic):
    """Выявляет конкретные несоответствия в признаках"""
    print(f"\n🎯 ВЫЯВЛЕНИЕ НЕСООТВЕТСТВИЙ ПРИЗНАКОВ")
    print("=" * 60)
    
    print("❌ КРИТИЧЕСКИЕ НЕСООТВЕТСТВИЯ:")
    print("-" * 40)
    
    # 1. BKT параметры
    print("1. 🧠 BKT ПАРАМЕТРЫ:")
    
    # Реальные BKT из базы
    real_bkt_stats = {}
    masteries = StudentSkillMastery.objects.all()
    if masteries.exists():
        p_l_values = [m.current_mastery_prob for m in masteries]
        p_t_values = [m.transition_prob for m in masteries]
        p_g_values = [m.guess_prob for m in masteries]
        p_s_values = [m.slip_prob for m in masteries]
        
        real_bkt_stats = {
            'P_L': {'mean': np.mean(p_l_values), 'std': np.std(p_l_values), 'min': np.min(p_l_values), 'max': np.max(p_l_values)},
            'P_T': {'mean': np.mean(p_t_values), 'std': np.std(p_t_values), 'min': np.min(p_t_values), 'max': np.max(p_t_values)},
            'P_G': {'mean': np.mean(p_g_values), 'std': np.std(p_g_values), 'min': np.min(p_g_values), 'max': np.max(p_g_values)},
            'P_S': {'mean': np.mean(p_s_values), 'std': np.std(p_s_values), 'min': np.min(p_s_values), 'max': np.max(p_s_values)}
        }
        
        print("   📊 Реальные BKT распределения:")
        for param, stats in real_bkt_stats.items():
            print(f"     {param}: {stats['mean']:.3f} ± {stats['std']:.3f} (диапазон: {stats['min']:.3f}-{stats['max']:.3f})")
    
    # Синтетические BKT
    print("   📊 Синтетические BKT:")
    skill_learned_cols = [col for col in df_synthetic.columns if 'skill_' in col and '_learned' in col]
    skill_transit_cols = [col for col in df_synthetic.columns if 'skill_' in col and '_transit' in col]
    
    if skill_learned_cols:
        synthetic_p_l = df_synthetic[skill_learned_cols[0]].values
        print(f"     P_L: {np.mean(synthetic_p_l):.3f} ± {np.std(synthetic_p_l):.3f}")
    
    if skill_transit_cols:
        synthetic_p_t = df_synthetic[skill_transit_cols[0]].values
        print(f"     P_T: {np.mean(synthetic_p_t):.3f} ± {np.std(synthetic_p_t):.3f}")
    
    # 2. История попыток
    print(f"\n2. 📚 ИСТОРИЯ ПОПЫТОК:")
    
    # Реальная история
    processor = DKNDataProcessor(max_history_length=10)
    student_with_data = User.objects.get(id=7)  # Студент с данными
    student_profile = StudentProfile.objects.get(user=student_with_data)
    
    real_attempts_user = TaskAttempt.objects.filter(student=student_profile)
    if real_attempts_user.exists():
        real_success_rate = real_attempts_user.filter(is_correct=True).count() / real_attempts_user.count()
        real_times = [a.time_spent for a in real_attempts_user if a.time_spent]
        real_avg_time = np.mean(real_times) if real_times else 0
        
        print(f"   📊 Реальные попытки:")
        print(f"     Успешность: {real_success_rate:.1%}")
        print(f"     Среднее время: {real_avg_time:.1f}с")
        print(f"     Всего попыток: {real_attempts_user.count()}")
    
    # Синтетическая история
    synthetic_success = df_synthetic['target'].mean()
    hist_time_cols = [col for col in df_synthetic.columns if 'hist_' in col and '_time' in col]
    if hist_time_cols:
        synthetic_times = df_synthetic[hist_time_cols].values.flatten()
        synthetic_times = synthetic_times[synthetic_times > 0]  # Убираем нули
        synthetic_avg_time = np.mean(synthetic_times) if len(synthetic_times) > 0 else 0
        
        print(f"   📊 Синтетические попытки:")
        print(f"     Успешность: {synthetic_success:.1%}")
        print(f"     Среднее время: {synthetic_avg_time:.1f}с")
    
    # 3. Сложность и типы заданий
    print(f"\n3. 📝 ЗАДАНИЯ:")
    
    # Реальные задания
    real_tasks = Task.objects.all()
    real_difficulties = [task.difficulty for task in real_tasks]
    real_types = [task.task_type for task in real_tasks]
    
    difficulty_counts = {}
    type_counts = {}
    
    for diff in real_difficulties:
        difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1
    
    for t_type in real_types:
        type_counts[t_type] = type_counts.get(t_type, 0) + 1
    
    print(f"   📊 Реальные задания:")
    print(f"     Сложности: {difficulty_counts}")
    print(f"     Типы: {type_counts}")
      # Синтетические задания
    synthetic_difficulties = df_synthetic['task_difficulty'].value_counts().to_dict()
    synthetic_types = df_synthetic['task_type'].value_counts().to_dict()
    
    print(f"   📊 Синтетические задания:")
    print(f"     Сложности: {synthetic_difficulties}")
    print(f"     Типы: {synthetic_types}")
    
    return real_bkt_stats, {
        'real_success_rate': real_success_rate if real_attempts_user.exists() else 0,
        'synthetic_success_rate': synthetic_success,
        'real_difficulty_dist': difficulty_counts,
        'synthetic_difficulty_dist': synthetic_difficulties,
        'real_type_dist': type_counts,
        'synthetic_type_dist': synthetic_types
    }


def calculate_distribution_divergence(real_bkt_stats, comparison_stats):
    """Вычисляет расхождение между распределениями"""
    print(f"\n📊 РАСЧЕТ РАСХОЖДЕНИЙ РАСПРЕДЕЛЕНИЙ")
    print("=" * 60)
    
    divergences = {}
    
    # 1. Успешность
    success_diff = abs(comparison_stats['real_success_rate'] - comparison_stats['synthetic_success_rate'])
    divergences['success_rate'] = success_diff
    print(f"🎯 Расхождение успешности: {success_diff:.1%}")
    
    # 2. Сложности заданий
    real_diff_dist = comparison_stats['real_difficulty_dist']
    synthetic_diff_dist = comparison_stats['synthetic_difficulty_dist']
    
    # Нормализуем для сравнения
    real_total = sum(real_diff_dist.values())
    synthetic_total = sum(synthetic_diff_dist.values())
    
    difficulty_divergence = 0
    all_difficulties = set(list(real_diff_dist.keys()) + list(synthetic_diff_dist.keys()))
    
    for diff in all_difficulties:
        real_prob = real_diff_dist.get(diff, 0) / real_total
        synthetic_prob = synthetic_diff_dist.get(diff, 0) / synthetic_total
        difficulty_divergence += abs(real_prob - synthetic_prob)
    
    divergences['difficulty'] = difficulty_divergence
    print(f"📝 Расхождение сложности: {difficulty_divergence:.3f}")
      # 3. Типы заданий
    real_type_dist = comparison_stats['real_type_dist']
    synthetic_type_dist = comparison_stats['synthetic_type_dist']
    
    real_type_total = sum(real_type_dist.values())
    synthetic_type_total = sum(synthetic_type_dist.values())
    
    type_divergence = 0
    all_types = set(list(real_type_dist.keys()) + list(synthetic_type_dist.keys()))
    
    for t_type in all_types:
        real_prob = real_type_dist.get(t_type, 0) / real_type_total
        synthetic_prob = synthetic_type_dist.get(t_type, 0) / synthetic_type_total
        type_divergence += abs(real_prob - synthetic_prob)
    
    divergences['task_type'] = type_divergence
    print(f"📋 Расхождение типов: {type_divergence:.3f}")
    
    return divergences


def identify_redundant_features(df_synthetic):
    """Выявляет избыточные/нерелевантные признаки"""
    print(f"\n🔍 ВЫЯВЛЕНИЕ ИЗБЫТОЧНЫХ ПРИЗНАКОВ")
    print("=" * 60)
    
    # 1. Анализ корреляций
    numeric_cols = df_synthetic.select_dtypes(include=[np.number]).columns
    correlation_matrix = df_synthetic[numeric_cols].corr()
    
    # Находим высококоррелированные пары
    high_corr_pairs = []
    for i in range(len(correlation_matrix.columns)):
        for j in range(i+1, len(correlation_matrix.columns)):
            corr_val = abs(correlation_matrix.iloc[i, j])
            if corr_val > 0.95:  # Очень высокая корреляция
                high_corr_pairs.append((
                    correlation_matrix.columns[i],
                    correlation_matrix.columns[j],
                    corr_val
                ))
    
    print(f"🔄 Высококоррелированные признаки (r > 0.95):")
    for col1, col2, corr in high_corr_pairs:
        print(f"   {col1} ↔ {col2}: {corr:.3f}")
    
    # 2. Анализ важности для целевой переменной
    target_correlations = correlation_matrix['target'].abs().sort_values(ascending=False)
    
    print(f"\n📈 Корреляция с целевой переменной (топ-10):")
    for feature, corr in target_correlations.head(10).items():
        if feature != 'target':
            print(f"   {feature}: {corr:.3f}")
    
    print(f"\n📉 Слабо коррелированные с целью (< 0.1):")
    weak_features = target_correlations[target_correlations < 0.1]
    for feature, corr in weak_features.items():
        if feature != 'target':
            print(f"   {feature}: {corr:.3f}")
    
    # 3. Постоянные значения
    constant_features = []
    for col in numeric_cols:
        if df_synthetic[col].nunique() == 1:
            constant_features.append(col)
    
    if constant_features:
        print(f"\n🚫 Константные признаки:")
        for feature in constant_features:
            print(f"   {feature}: {df_synthetic[feature].iloc[0]}")
    
    return high_corr_pairs, weak_features.index.tolist(), constant_features


def suggest_data_optimization(divergences, redundant_features):
    """Предлагает оптимизацию данных"""
    print(f"\n💡 ПРЕДЛОЖЕНИЯ ПО ОПТИМИЗАЦИИ ДАННЫХ")
    print("=" * 60)
    
    print("🎯 КРИТИЧЕСКИЕ ПРОБЛЕМЫ:")
    print("-" * 40)
    
    critical_issues = []
    
    # 1. Проверяем расхождения
    if divergences.get('success_rate', 0) > 0.2:  # Более 20% разница
        critical_issues.append("Большое расхождение в успешности")
        print("❌ Успешность в синтетических данных сильно отличается от реальной")
    
    if divergences.get('difficulty', 0) > 0.5:
        critical_issues.append("Несоответствие распределения сложности")
        print("❌ Распределение сложности заданий не соответствует реальному")
    
    if divergences.get('task_type', 0) > 0.5:
        critical_issues.append("Несоответствие типов заданий")
        print("❌ Распределение типов заданий не соответствует реальному")
    
    # 2. Избыточные признаки
    high_corr_pairs, weak_features, constant_features = redundant_features
    
    if high_corr_pairs:
        critical_issues.append("Мультиколлинеарность")
        print(f"❌ Обнаружено {len(high_corr_pairs)} пар высококоррелированных признаков")
    
    if len(weak_features) > 5:
        critical_issues.append("Много нерелевантных признаков")
        print(f"❌ {len(weak_features)} признаков слабо коррелируют с целью")
    
    if constant_features:
        critical_issues.append("Константные признаки")
        print(f"❌ {len(constant_features)} константных признаков")
    
    print(f"\n✅ РЕКОМЕНДАЦИИ ПО УЛУЧШЕНИЮ:")
    print("-" * 40)
    
    recommendations = []
    
    # 1. Исправление распределений
    if divergences.get('success_rate', 0) > 0.1:
        recommendations.append("Скорректировать целевую переменную")
        print("1. 🎯 Пересбалансировать целевую переменную:")
        print("   - Изменить архетипы студентов для более реалистичной успешности")
        print("   - Добавить больше неуспешных попыток")
    
    if divergences.get('difficulty', 0) > 0.3:
        recommendations.append("Исправить распределение сложности")
        print("2. 📝 Исправить распределение сложности заданий:")
        print("   - Сгенерировать больше заданий соответствующих сложностей")
        print("   - Убрать избыточные уровни сложности")
    
    # 2. Удаление избыточных признаков
    if high_corr_pairs:
        recommendations.append("Устранить мультиколлинеарность")
        print("3. 🔄 Устранить мультиколлинеарность:")
        for col1, col2, corr in high_corr_pairs[:3]:  # Показываем первые 3
            print(f"   - Удалить один из: {col1} или {col2}")
    
    if len(weak_features) > 5:
        recommendations.append("Удалить нерелевантные признаки")
        print("4. 🗑️ Удалить нерелевантные признаки:")
        print(f"   - Удалить {len(weak_features)} слабо коррелированных признаков")
        print(f"   - Например: {', '.join(weak_features[:5])}")
    
    if constant_features:
        recommendations.append("Удалить константы")
        print("5. 🚫 Удалить константные признаки:")
        for feature in constant_features[:3]:
            print(f"   - Удалить: {feature}")
    
    # 3. Дополнительные рекомендации
    print(f"\n🚀 ДОПОЛНИТЕЛЬНЫЕ УЛУЧШЕНИЯ:")
    print("-" * 40)
    print("6. 📊 Согласование с реальными данными:")
    print("   - Использовать реальные BKT параметры как базовые")
    print("   - Сгенерировать историю на основе реальных паттернов")
    print("   - Добавить шум для реалистичности")
    
    print("7. 🎯 Фокус на важных признаках:")
    print("   - Увеличить вариативность важных BKT параметров")
    print("   - Улучшить моделирование истории попыток")
    print("   - Добавить сезонность и временные паттерны")
    
    return {
        'critical_issues': critical_issues,
        'recommendations': recommendations,
        'features_to_remove': list(set(weak_features + constant_features + [pair[1] for pair in high_corr_pairs]))
    }


def generate_optimization_script(optimization_plan):
    """Генерирует скрипт для оптимизации данных"""
    script_content = '''#!/usr/bin/env python3
"""
Скрипт оптимизации синтетических данных для DKN

Автоматически сгенерированный скрипт для исправления выявленных проблем
"""

import pandas as pd
import numpy as np
from pathlib import Path

def optimize_synthetic_data():
    """Оптимизирует синтетические данные"""
      # Загружаем данные
    df = pd.read_csv("dataset/enhanced_synthetic_dataset.csv")
    print(f"Исходных записей: {{len(df)}}")
    
    # Удаляем избыточные признаки
    features_to_remove = {features_to_remove}
    df_optimized = df.drop(columns=[col for col in features_to_remove if col in df.columns])
    print(f"Удалено признаков: {{len([col for col in features_to_remove if col in df.columns])}}")
    
    # Корректируем целевую переменную (если нужно)
    current_success_rate = df_optimized['target'].mean()
    target_success_rate = 0.75  # Целевая успешность на основе реальных данных
    
    if abs(current_success_rate - target_success_rate) > 0.1:
        print(f"Корректируем успешность: {{current_success_rate:.1%}} -> {{target_success_rate:.1%}}")
        
        # Простая коррекция через семплирование
        success_samples = df_optimized[df_optimized['target'] == 1]
        failure_samples = df_optimized[df_optimized['target'] == 0]
        
        target_success_count = int(len(df_optimized) * target_success_rate)
        target_failure_count = len(df_optimized) - target_success_count
        
        # Пересемплируем
        if len(success_samples) > target_success_count:
            success_samples = success_samples.sample(n=target_success_count, random_state=42)
        if len(failure_samples) > target_failure_count:
            failure_samples = failure_samples.sample(n=target_failure_count, random_state=42)
        
        df_optimized = pd.concat([success_samples, failure_samples]).sample(frac=1, random_state=42)
    
    # Сохраняем оптимизированные данные
    output_path = "dataset/optimized_synthetic_dataset.csv"
    df_optimized.to_csv(output_path, index=False)
    print(f"Оптимизированные данные сохранены: {{output_path}}")
    print(f"Финальных записей: {{len(df_optimized)}}")
    print(f"Финальных признаков: {{len(df_optimized.columns)}}")
    
    return df_optimized

if __name__ == "__main__":
    optimize_synthetic_data()
'''.format(features_to_remove=optimization_plan['features_to_remove'])
    
    # Сохраняем скрипт
    script_path = Path("optimize_synthetic_data.py")
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"\n📄 Сгенерирован скрипт оптимизации: {script_path}")
    return script_path


def main():
    """Основная функция анализа несоответствий"""
    print("🔍 ПОЛНЫЙ АНАЛИЗ НЕСООТВЕТСТВИЙ ДАННЫХ DKN")
    print("=" * 70)
    
    try:
        # 1. Загружаем и анализируем данные
        df_synthetic, real_students, real_attempts, real_masteries = analyze_data_misalignment()
        
        # 2. Выявляем несоответствия признаков
        real_bkt_stats, comparison_stats = identify_feature_mismatches(df_synthetic)
          # 3. Вычисляем расхождения
        divergences = calculate_distribution_divergence(real_bkt_stats, comparison_stats)
        
        # 4. Находим избыточные признаки
        redundant_features = identify_redundant_features(df_synthetic)
        
        # 5. Предлагаем оптимизацию
        optimization_plan = suggest_data_optimization(divergences, redundant_features)
        
        # 6. Генерируем скрипт оптимизации
        script_path = generate_optimization_script(optimization_plan)
        
        print(f"\n🎉 Анализ завершен! Запустите {script_path} для оптимизации данных.")
        
    except Exception as e:
        print(f"💥 Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
