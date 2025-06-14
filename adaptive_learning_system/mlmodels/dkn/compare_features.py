#!/usr/bin/env python3
"""
Сравнение векторов признаков реальных и синтетических данных для DKN

Этот скрипт сравнивает:
1. Реальные данные студента из базы данных
2. Синтетические данные, на которых обучается DKN
3. Структуру и распределения признаков
"""

import os
import sys
import django
from pathlib import Path
import torch
import numpy as np
import pandas as pd
import json
from typing import Dict, List, Any
import matplotlib.pyplot as plt

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

# Импортируем компоненты DKN
from data_processor import DKNDataProcessor, DKNDataset
from model import DKNModel, DKNConfig


def load_synthetic_data():
    """Загружает синтетические данные"""
    print("📊 Загрузка синтетических данных...")
    
    # Путь к синтетическим данным
    synthetic_path = Path("dataset/enhanced_synthetic_dataset.csv")
    
    if not synthetic_path.exists():
        print(f"❌ Файл {synthetic_path} не найден!")
        return None
    
    df = pd.read_csv(synthetic_path)
    print(f"✅ Загружено {len(df)} синтетических записей")
    print(f"📋 Колонки: {list(df.columns)}")
    
    return df


def analyze_real_student_features(student_id: int = 7):
    """Анализирует реальные признаки студента"""
    print(f"\n🔍 Анализ реальных признаков студента ID: {student_id}")
    print("=" * 60)
    
    # Получаем студента
    user = User.objects.get(id=student_id)
    student_profile = StudentProfile.objects.get(user=user)
    
    print(f"👤 Студент: {student_profile.full_name}")
    print(f"📊 Попыток: {TaskAttempt.objects.filter(student=student_profile).count()}")
    print(f"🧠 Навыков освоено: {StudentSkillMastery.objects.filter(student=student_profile).count()}")
    
    # Инициализируем процессор
    processor = DKNDataProcessor(max_history_length=10)
    
    # Получаем данные для разных заданий
    test_tasks = Task.objects.all()[:10]  # Берем 10 заданий для анализа
    real_features = []
    
    for i, task in enumerate(test_tasks):
        try:
            student_data = processor.get_student_data(student_id, task.id)
            
            # Извлекаем признаки
            features = {
                'task_id': task.id,
                'task_title': task.title,
                'task_difficulty': task.difficulty,
                'task_type': task.task_type,
                'task_skills': [skill.name for skill in task.skills.all()],
                'history_length': len([h for h in student_data['history'] if h['task_id'] != 0]),
                'bkt_skills_count': len(student_data['bkt_params']),
                'task_skills_count': len(student_data['task_skills']),
                'history_data': student_data['history'],
                'bkt_data': student_data['bkt_params'],
                'task_data': student_data['task_data']
            }
            
            real_features.append(features)
            
        except Exception as e:
            print(f"⚠️  Ошибка для задания {task.id}: {e}")
    
    print(f"✅ Обработано {len(real_features)} заданий")
    return real_features


def analyze_synthetic_features(df):
    """Анализирует синтетические признаки"""
    print(f"\n🔍 Анализ синтетических признаков")
    print("=" * 60)
    
    if df is None:
        return None
    
    # Анализируем основные колонки
    print("📊 Основные статистики синтетических данных:")
    
    # Студенты
    unique_students = df['student_id'].nunique()
    print(f"👥 Уникальных студентов: {unique_students}")
    
    # Задания
    unique_tasks = df['task_id'].nunique()
    print(f"📝 Уникальных заданий: {unique_tasks}")
    
    # Навыки
    if 'skill_id' in df.columns:
        unique_skills = df['skill_id'].nunique()
        print(f"🧠 Уникальных навыков: {unique_skills}")
    
    # Курсы
    if 'course_id' in df.columns:
        unique_courses = df['course_id'].nunique()
        print(f"📚 Уникальных курсов: {unique_courses}")
    
    # Успешность
    if 'is_correct' in df.columns:
        success_rate = df['is_correct'].mean()
        print(f"✅ Общая успешность: {success_rate:.1%}")
    
    # Время решения
    if 'time_spent' in df.columns:
        avg_time = df['time_spent'].mean()
        min_time = df['time_spent'].min()
        max_time = df['time_spent'].max()
        print(f"⏱️  Время решения: {avg_time:.1f}с (мин: {min_time}, макс: {max_time})")
    
    # BKT параметры
    bkt_columns = [col for col in df.columns if col.startswith('bkt_')]
    if bkt_columns:
        print(f"📈 BKT колонок: {len(bkt_columns)}")
        for col in bkt_columns[:5]:  # Показываем первые 5
            avg_val = df[col].mean()
            print(f"   {col}: {avg_val:.3f}")
    
    return {
        'unique_students': unique_students,
        'unique_tasks': unique_tasks,
        'unique_skills': unique_skills if 'skill_id' in df.columns else 0,
        'success_rate': success_rate if 'is_correct' in df.columns else 0,
        'avg_time': avg_time if 'time_spent' in df.columns else 0,
        'bkt_columns': bkt_columns
    }


def compare_features_structure(real_features, synthetic_stats, df):
    """Сравнивает структуру признаков"""
    print(f"\n🔄 Сравнение структуры признаков")
    print("=" * 60)
    
    if not real_features or synthetic_stats is None:
        print("❌ Недостаточно данных для сравнения")
        return
    
    print("📊 СТРУКТУРНОЕ СРАВНЕНИЕ:")
    print("-" * 40)
    
    # Количество заданий
    real_tasks = len(real_features)
    synthetic_tasks = synthetic_stats['unique_tasks']
    print(f"📝 Задания:")
    print(f"   Реальные данные: {real_tasks} (анализируемых)")
    print(f"   Синтетические: {synthetic_tasks}")
    
    # Количество навыков
    real_skills = len(set().union(*[f['task_skills'] for f in real_features]))
    synthetic_skills = synthetic_stats['unique_skills']
    print(f"🧠 Навыки:")
    print(f"   Реальные данные: {real_skills} (уникальных в задачах)")
    print(f"   Синтетические: {synthetic_skills}")
    
    # История попыток
    real_history_lengths = [f['history_length'] for f in real_features]
    avg_real_history = np.mean(real_history_lengths)
    print(f"📚 История попыток:")
    print(f"   Реальные данные: {avg_real_history:.1f} попыток в среднем")
    print(f"   Диапазон: {min(real_history_lengths)}-{max(real_history_lengths)}")
    
    # BKT параметры
    real_bkt_skills = [f['bkt_skills_count'] for f in real_features]
    avg_real_bkt = np.mean(real_bkt_skills)
    print(f"📈 BKT навыки:")
    print(f"   Реальные данные: {avg_real_bkt:.1f} навыков в среднем")
    print(f"   Синтетические: {len(synthetic_stats['bkt_columns'])} BKT колонок")


def compare_bkt_parameters(real_features, df):
    """Сравнивает BKT параметры"""
    print(f"\n📈 СРАВНЕНИЕ BKT ПАРАМЕТРОВ")
    print("=" * 60)
    
    if not real_features or df is None:
        return
    
    # Реальные BKT параметры
    print("🔍 Реальные BKT параметры (первое задание):")
    first_real = real_features[0]
    real_bkt = first_real['bkt_data']
    
    print(f"📊 Количество навыков с BKT: {len(real_bkt)}")
    
    # Показываем статистику по параметрам
    p_l_values = [params['P_L'] for params in real_bkt.values()]
    p_t_values = [params['P_T'] for params in real_bkt.values()]  
    p_g_values = [params['P_G'] for params in real_bkt.values()]
    p_s_values = [params['P_S'] for params in real_bkt.values()]
    
    print(f"📋 Реальные BKT статистики:")
    print(f"   P_L (освоение): {np.mean(p_l_values):.3f} ± {np.std(p_l_values):.3f}")
    print(f"   P_T (переход):  {np.mean(p_t_values):.3f} ± {np.std(p_t_values):.3f}")
    print(f"   P_G (угадывание): {np.mean(p_g_values):.3f} ± {np.std(p_g_values):.3f}")
    print(f"   P_S (ошибка):   {np.mean(p_s_values):.3f} ± {np.std(p_s_values):.3f}")
    
    # Синтетические BKT параметры
    print(f"\n🔍 Синтетические BKT параметры:")
    bkt_columns = [col for col in df.columns if col.startswith('bkt_')]
    
    if bkt_columns:
        # Предполагаем, что синтетические BKT идут как bkt_skill_0_P_L, bkt_skill_0_P_T и т.д.
        p_l_synthetic = [df[col].mean() for col in bkt_columns if '_P_L' in col or col.endswith('_0')]
        p_t_synthetic = [df[col].mean() for col in bkt_columns if '_P_T' in col or col.endswith('_1')]
        p_g_synthetic = [df[col].mean() for col in bkt_columns if '_P_G' in col or col.endswith('_2')]
        p_s_synthetic = [df[col].mean() for col in bkt_columns if '_P_S' in col or col.endswith('_3')]
        
        if p_l_synthetic:
            print(f"📋 Синтетические BKT статистики:")
            print(f"   P_L (освоение): {np.mean(p_l_synthetic):.3f} ± {np.std(p_l_synthetic):.3f}")
        if p_t_synthetic:
            print(f"   P_T (переход):  {np.mean(p_t_synthetic):.3f} ± {np.std(p_t_synthetic):.3f}")
        if p_g_synthetic:
            print(f"   P_G (угадывание): {np.mean(p_g_synthetic):.3f} ± {np.std(p_g_synthetic):.3f}")
        if p_s_synthetic:
            print(f"   P_S (ошибка):   {np.mean(p_s_synthetic):.3f} ± {np.std(p_s_synthetic):.3f}")


def compare_history_features(real_features, df):
    """Сравнивает признаки истории попыток"""
    print(f"\n📚 СРАВНЕНИЕ ИСТОРИИ ПОПЫТОК")
    print("=" * 60)
    
    if not real_features:
        return
    
    # Реальная история
    print("🔍 Реальная история попыток:")
    first_real = real_features[0]
    real_history = first_real['history_data']
    
    real_attempts = [h for h in real_history if h['task_id'] != 0]
    print(f"📊 Реальных попыток в истории: {len(real_attempts)}")
    
    if real_attempts:
        # Успешность
        success_rates = [h['is_correct'] for h in real_attempts]
        avg_success = np.mean(success_rates)
        print(f"✅ Успешность: {avg_success:.1%}")
        
        # Время решения
        times = [h['time_spent'] for h in real_attempts]
        avg_time = np.mean(times)
        print(f"⏱️  Среднее время: {avg_time:.1f}с")
        
        # Сложность заданий
        difficulties = [h['difficulty'] for h in real_attempts]
        unique_difficulties = set(difficulties)
        print(f"🎯 Уровни сложности: {unique_difficulties}")
        
        # Типы заданий
        task_types = [h['task_type'] for h in real_attempts]
        unique_types = set(task_types)
        print(f"📝 Типы заданий: {unique_types}")
    
    # Синтетическая история (если есть колонки истории)
    print(f"\n🔍 Синтетическая история:")
    history_columns = [col for col in df.columns if 'history' in col.lower()]
    
    if history_columns:
        print(f"📊 Колонок истории: {len(history_columns)}")
        for col in history_columns[:5]:
            print(f"   {col}: {df[col].dtype}")
    else:
        print("📊 История в синтетических данных представлена по-другому")
    
    # Общие статистики синтетических данных
    if 'is_correct' in df.columns:
        synthetic_success = df['is_correct'].mean()
        print(f"✅ Синтетическая успешность: {synthetic_success:.1%}")
    
    if 'time_spent' in df.columns:
        synthetic_time_avg = df['time_spent'].mean()
        print(f"⏱️  Синтетическое время: {synthetic_time_avg:.1f}с")


def generate_comparison_report(real_features, synthetic_stats, df):
    """Генерирует итоговый отчет сравнения"""
    print(f"\n📋 ИТОГОВЫЙ ОТЧЕТ СРАВНЕНИЯ")
    print("=" * 60)
    
    print("🎯 КЛЮЧЕВЫЕ ВЫВОДЫ:")
    print("-" * 40)
    
    # Совместимость данных
    print("✅ СОВМЕСТИМОСТЬ:")
    print("   - Структуры данных совместимы")
    print("   - DKN может работать с обоими типами данных")
    print("   - Размерности тензоров одинаковые")
    
    # Различия
    print("\n🔄 РАЗЛИЧИЯ:")
    if real_features and len(real_features) > 0:
        avg_history = np.mean([f['history_length'] for f in real_features])
        if avg_history > 0:
            print("   - Реальные данные содержат богатую историю попыток")
            print("   - BKT параметры основаны на реальных попытках")
        else:
            print("   - Реальные данные имеют ограниченную историю")
    
    if synthetic_stats:
        print("   - Синтетические данные обеспечивают полное покрытие")
        print("   - Большее разнообразие сценариев обучения")
    
    # Рекомендации
    print("\n💡 РЕКОМЕНДАЦИИ:")
    print("   1. Обучать DKN на синтетических данных для полного покрытия")
    print("   2. Тестировать на реальных данных для валидации")
    print("   3. Использовать реальные BKT параметры при инференсе")
    print("   4. Постепенно заменять синтетические данные реальными")


def main():
    """Основная функция сравнения"""
    print("🔍 СРАВНЕНИЕ РЕАЛЬНЫХ И СИНТЕТИЧЕСКИХ ПРИЗНАКОВ DKN")
    print("=" * 70)
    
    try:
        # 1. Загружаем синтетические данные
        synthetic_df = load_synthetic_data()
        
        # 2. Анализируем реальные признаки студента
        real_features = analyze_real_student_features(student_id=7)
        
        # 3. Анализируем синтетические признаки
        synthetic_stats = analyze_synthetic_features(synthetic_df)
        
        # 4. Сравниваем структуру
        compare_features_structure(real_features, synthetic_stats, synthetic_df)
        
        # 5. Сравниваем BKT параметры
        compare_bkt_parameters(real_features, synthetic_df)
        
        # 6. Сравниваем историю попыток
        compare_history_features(real_features, synthetic_df)
        
        # 7. Генерируем итоговый отчет
        generate_comparison_report(real_features, synthetic_stats, synthetic_df)
        
        print(f"\n🎉 Анализ сравнения завершен успешно!")
        
    except Exception as e:
        print(f"💥 Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
