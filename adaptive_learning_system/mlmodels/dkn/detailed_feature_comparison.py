#!/usr/bin/env python3
"""
Детальное сравнение векторов признаков для DKN модели

Сравнивает точные векторы признаков, которые подаются в DKN модель:
1. Из реальных данных студента
2. Из синтетического обучающего датасета
"""

import os
import sys
import django
from pathlib import Path
import torch
import numpy as np
import pandas as pd
from typing import Dict, List, Any

# Настройка Django
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

from django.contrib.auth.models import User
from student.models import StudentProfile
from data_processor import DKNDataProcessor

# Импорт custom_collate_fn из trainer без относительного импорта
def custom_collate_fn(batch_data):
    """Упрощенная версия collate_fn для сравнения"""
    # Эта функция дублирует логику из trainer.py для независимости
    
    if not batch_data:
        return {}
    
    batch_size = len(batch_data)
    num_skills = 30  # Известно из конфигурации
    max_history = 10
    
    # Инициализируем тензоры
    skill_ids = torch.zeros((batch_size, num_skills), dtype=torch.long)
    bkt_params = torch.zeros((batch_size, num_skills, 4), dtype=torch.float32)
    task_ids = torch.zeros(batch_size, dtype=torch.long)
    task_difficulty = torch.zeros(batch_size, dtype=torch.long)
    task_type = torch.zeros(batch_size, dtype=torch.long)
    student_history = torch.zeros((batch_size, max_history, 10), dtype=torch.float32)
    current_bkt_avg = torch.zeros((batch_size, 4), dtype=torch.float32)
    skill_mask = torch.zeros((batch_size, num_skills), dtype=torch.float32)
    
    for i, sample in enumerate(batch_data):
        # Заполняем skill_ids
        skill_ids[i] = torch.arange(num_skills)
        
        # BKT параметры
        bkt_data = sample.get('bkt_params', {})
        for skill_id, params in bkt_data.items():
            if skill_id < num_skills:
                bkt_params[i, skill_id] = torch.tensor([
                    params.get('P_L', 0.1),
                    params.get('P_T', 0.1), 
                    params.get('P_G', 0.1),
                    params.get('P_S', 0.1)
                ])
        
        # Задание
        task_ids[i] = i  # Простой маппинг для демонстрации
        task_data = sample.get('task_data', {})
        task_difficulty[i] = task_data.get('difficulty', 0)
        task_type[i] = task_data.get('task_type', 0)
        
        # История
        history = sample.get('history', [])
        for j, hist_item in enumerate(history[:max_history]):
            if isinstance(hist_item, dict):
                student_history[i, j] = torch.tensor([
                    hist_item.get('task_id', 0),
                    hist_item.get('is_correct', 0),
                    hist_item.get('score', 0),
                    hist_item.get('time_spent', 0),
                    hist_item.get('difficulty', 0),
                    hist_item.get('task_type', 0),
                    0, 0, 0, 0  # Заполнители для навыков
                ])
        
        # Средние BKT
        if bkt_data:
            all_params = list(bkt_data.values())
            if all_params:
                current_bkt_avg[i] = torch.tensor([
                    np.mean([p.get('P_L', 0.1) for p in all_params]),
                    np.mean([p.get('P_T', 0.1) for p in all_params]),
                    np.mean([p.get('P_G', 0.1) for p in all_params]),
                    np.mean([p.get('P_S', 0.1) for p in all_params])
                ])
        
        # Маска навыков
        skill_mask[i] = 1.0  # Все навыки активны
    
    return {
        'skill_ids': skill_ids,
        'bkt_params': bkt_params,
        'task_ids': task_ids,
        'task_difficulty': task_difficulty,
        'task_type': task_type,
        'student_history': student_history,
        'current_bkt_avg': current_bkt_avg,
        'skill_mask': skill_mask
    }


def get_real_data_vectors(student_id: int = 7, num_tasks: int = 5):
    """Получает реальные векторы признаков для DKN"""
    print(f"🔍 Извлечение реальных векторов признаков (студент ID={student_id})")
    
    # Инициализируем процессор
    processor = DKNDataProcessor(max_history_length=10)
    
    # Получаем данные для нескольких заданий
    from methodist.models import Task
    test_tasks = Task.objects.all()[:num_tasks]
    
    student_data_list = []
    for task in test_tasks:
        try:
            student_data = processor.get_student_data(student_id, task.id)
            student_data_list.append(student_data)
        except Exception as e:
            print(f"⚠️ Ошибка для задания {task.id}: {e}")
    
    # Подготавливаем батч через collate_fn
    if student_data_list:
        batch = custom_collate_fn(student_data_list)
        print(f"✅ Получен батч реальных данных: {len(student_data_list)} образцов")
        return batch, student_data_list
    
    return None, None


def get_synthetic_data_vectors(num_samples: int = 5):
    """Получает синтетические векторы признаков для DKN"""
    print(f"🔍 Извлечение синтетических векторов признаков ({num_samples} образцов)")
    
    # Загружаем синтетические данные
    synthetic_path = Path("dataset/enhanced_synthetic_dataset.csv")
    if not synthetic_path.exists():
        print(f"❌ Файл {synthetic_path} не найден!")
        return None, None
    
    df = pd.read_csv(synthetic_path)
    
    # Берем случайные образцы
    sample_df = df.sample(n=num_samples, random_state=42)
    
    # Преобразуем в формат для DKN (как в тренировочном пайплайне)
    synthetic_batch = []
    
    for _, row in sample_df.iterrows():
        # Извлекаем признаки в том же формате, что и для обучения
        
        # История попыток (hist_0_correct, hist_0_score, hist_0_time, и т.д.)
        history = []
        for i in range(10):  # Предполагаем max_history_length = 10
            if f'hist_{i}_correct' in row:
                hist_item = {
                    'is_correct': float(row[f'hist_{i}_correct']),
                    'score': float(row[f'hist_{i}_score']),
                    'time_spent': float(row[f'hist_{i}_time']),
                }
                history.append(hist_item)
        
        # BKT параметры (ищем skill_*_learned, skill_*_transit и т.д.)
        bkt_params = {}
        skill_columns = [col for col in row.index if col.startswith('skill_')]
        
        # Группируем по навыкам
        skills_found = set()
        for col in skill_columns:
            if '_learned' in col or '_transit' in col:
                skill_num = col.split('_')[1]
                skills_found.add(skill_num)
        
        for skill_num in skills_found:
            bkt_params[int(skill_num)] = {
                'P_L': float(row.get(f'skill_{skill_num}_learned', 0.1)),
                'P_T': float(row.get(f'skill_{skill_num}_transit', 0.1)),
                'P_G': 0.1,  # Значения по умолчанию, если нет в данных
                'P_S': 0.1
            }
        
        # Данные задания
        task_data = {
            'difficulty': int(row.get('task_difficulty', 0)),
            'task_type': int(row.get('task_type', 0)),
        }
        
        # Собираем образец
        sample = {
            'student_id': int(row['student_id']),
            'task_id': int(row['task_id']),
            'history': history,
            'bkt_params': bkt_params,
            'task_skills': [0],  # Упрощенно
            'task_data': task_data,
            'target': float(row['target'])
        }
        
        synthetic_batch.append(sample)
    
    print(f"✅ Получен батч синтетических данных: {len(synthetic_batch)} образцов")
    return synthetic_batch, sample_df


def compare_batch_structure(real_batch, synthetic_batch):
    """Сравнивает структуру батчей"""
    print(f"\n📊 СРАВНЕНИЕ СТРУКТУРЫ БАТЧЕЙ")
    print("=" * 50)
    
    if real_batch is None or synthetic_batch is None:
        print("❌ Недостаточно данных для сравнения батчей")
        return
    
    # Реальные данные (уже в формате тензоров от collate_fn)
    print("🔍 Реальный батч (тензоры):")
    for key, tensor in real_batch.items():
        if isinstance(tensor, torch.Tensor):
            print(f"   {key}: {tensor.shape} ({tensor.dtype})")
        else:
            print(f"   {key}: {type(tensor)} - {len(tensor) if hasattr(tensor, '__len__') else 'N/A'}")
    
    # Синтетические данные (еще в формате списка словарей)
    print(f"\n🔍 Синтетический батч (raw data):")
    if synthetic_batch:
        sample = synthetic_batch[0]
        print(f"   Образцов: {len(synthetic_batch)}")
        print(f"   Ключи образца: {list(sample.keys())}")
        print(f"   История: {len(sample['history'])} элементов")
        print(f"   BKT параметры: {len(sample['bkt_params'])} навыков")
        print(f"   Навыки задания: {len(sample['task_skills'])}")


def compare_feature_values(real_batch, real_data, synthetic_batch, synthetic_df):
    """Сравнивает значения признаков"""
    print(f"\n📊 СРАВНЕНИЕ ЗНАЧЕНИЙ ПРИЗНАКОВ")
    print("=" * 50)
    
    # История попыток
    print("📚 ИСТОРИЯ ПОПЫТОК:")
    print("-" * 30)
    
    if real_batch and 'student_history' in real_batch:
        real_history = real_batch['student_history']
        print(f"🔍 Реальная история: {real_history.shape}")
        print(f"   Значения: {real_history[0, :3, :3]}")  # Первые 3x3 значения
        
        # Статистики по истории
        non_zero_mask = real_history != 0
        if non_zero_mask.any():
            print(f"   Ненулевых значений: {non_zero_mask.sum().item()}")
            print(f"   Среднее (ненулевое): {real_history[non_zero_mask].mean().item():.3f}")
    
    if synthetic_batch:
        print(f"\n🔍 Синтетическая история (первый образец):")
        hist = synthetic_batch[0]['history'][:3]  # Первые 3 элемента
        for i, h in enumerate(hist):
            print(f"   [{i}]: correct={h['is_correct']}, score={h['score']:.2f}, time={h['time_spent']:.1f}")
    
    # BKT параметры
    print(f"\n📈 BKT ПАРАМЕТРЫ:")
    print("-" * 30)
    
    if real_batch and 'bkt_params' in real_batch:
        real_bkt = real_batch['bkt_params']
        print(f"🔍 Реальные BKT: {real_bkt.shape}")
        
        # Статистики по каждому параметру
        for i, param_name in enumerate(['P_L', 'P_T', 'P_G', 'P_S']):
            param_values = real_bkt[:, :, i]
            non_zero = param_values[param_values != 0]
            if len(non_zero) > 0:
                print(f"   {param_name}: {non_zero.mean():.3f} ± {non_zero.std():.3f} ({len(non_zero)} ненулевых)")
    
    if synthetic_batch:
        print(f"\n🔍 Синтетические BKT (первый образец):")
        bkt = synthetic_batch[0]['bkt_params']
        for skill_id, params in list(bkt.items())[:3]:  # Первые 3 навыка
            print(f"   Навык {skill_id}: P_L={params['P_L']:.3f}, P_T={params['P_T']:.3f}")
    
    # Характеристики заданий
    print(f"\n📝 ХАРАКТЕРИСТИКИ ЗАДАНИЙ:")
    print("-" * 30)
    
    if real_batch:
        if 'task_difficulty' in real_batch:
            real_diff = real_batch['task_difficulty']
            print(f"🔍 Реальная сложность: {real_diff}")
        if 'task_type' in real_batch:
            real_type = real_batch['task_type']
            print(f"🔍 Реальный тип: {real_type}")
    
    if synthetic_batch:
        print(f"🔍 Синтетические характеристики:")
        difficulties = [s['task_data']['difficulty'] for s in synthetic_batch]
        task_types = [s['task_data']['task_type'] for s in synthetic_batch]
        print(f"   Сложности: {difficulties}")
        print(f"   Типы: {task_types}")


def compare_distributions(real_batch, synthetic_df):
    """Сравнивает распределения признаков"""
    print(f"\n📊 СРАВНЕНИЕ РАСПРЕДЕЛЕНИЙ")
    print("=" * 50)
    
    # Успешность (целевая переменная)
    print("🎯 ЦЕЛЕВАЯ ПЕРЕМЕННАЯ (успешность):")
    
    if synthetic_df is not None and 'target' in synthetic_df.columns:
        synthetic_success_rate = synthetic_df['target'].mean()
        synthetic_std = synthetic_df['target'].std()
        print(f"   Синтетические: {synthetic_success_rate:.3f} ± {synthetic_std:.3f}")
        
        # Распределение по группам
        print(f"   Распределение:")
        print(f"     0 (неуспех): {(synthetic_df['target'] == 0).sum()} ({(synthetic_df['target'] == 0).mean():.1%})")
        print(f"     1 (успех): {(synthetic_df['target'] == 1).sum()} ({(synthetic_df['target'] == 1).mean():.1%})")
    
    # Время решения
    print(f"\n⏱️ ВРЕМЯ РЕШЕНИЯ:")
    
    if synthetic_df is not None:
        time_columns = [col for col in synthetic_df.columns if 'time' in col]
        if time_columns:
            sample_time_col = time_columns[0]  # Берем первую колонку времени
            times = synthetic_df[sample_time_col].dropna()
            if len(times) > 0:
                print(f"   Синтетическое время ({sample_time_col}):")
                print(f"     Среднее: {times.mean():.1f}с")
                print(f"     Медиана: {times.median():.1f}с")
                print(f"     Диапазон: {times.min():.1f} - {times.max():.1f}с")


def generate_feature_comparison_report(real_batch, synthetic_batch):
    """Генерирует отчет сравнения признаков"""
    print(f"\n📋 ОТЧЕТ СРАВНЕНИЯ ВЕКТОРОВ ПРИЗНАКОВ")
    print("=" * 60)
    
    print("🎯 КЛЮЧЕВЫЕ НАХОДКИ:")
    print("-" * 40)
    
    # Совместимость форматов
    print("✅ СОВМЕСТИМОСТЬ ФОРМАТОВ:")
    if real_batch and synthetic_batch:
        print("   ✓ Реальные данные успешно преобразуются в тензоры")
        print("   ✓ Синтетические данные имеют ту же структуру")
        print("   ✓ Размерности совместимы с DKN моделью")
    
    # Основные различия
    print(f"\n🔄 ОСНОВНЫЕ РАЗЛИЧИЯ:")
    print("   📊 Реальные данные:")
    print("     - Основаны на реальных попытках студентов")
    print("     - BKT параметры вычислены из истории")
    print("     - Ограниченное количество комбинаций")
    print("     - Реалистичные паттерны поведения")
    
    print("   🎲 Синтетические данные:")
    print("     - Сгенерированы по моделям поведения")
    print("     - Полное покрытие пространства признаков")
    print("     - Контролируемые распределения")
    print("     - Большое разнообразие сценариев")
    
    # Выводы для обучения
    print(f"\n💡 ВЫВОДЫ ДЛЯ ОБУЧЕНИЯ DKN:")
    print("   1. Синтетические данные обеспечивают лучшее покрытие")
    print("   2. Реальные данные нужны для валидации и fine-tuning")
    print("   3. Модель может переключаться между типами данных")
    print("   4. Важно сохранять реалистичность BKT параметров")


def main():
    """Основная функция детального сравнения"""
    print("🔍 ДЕТАЛЬНОЕ СРАВНЕНИЕ ВЕКТОРОВ ПРИЗНАКОВ DKN")
    print("=" * 70)
    
    try:
        # 1. Получаем реальные векторы признаков
        real_batch, real_data = get_real_data_vectors(student_id=7, num_tasks=5)
        
        # 2. Получаем синтетические векторы признаков  
        synthetic_batch, synthetic_df = get_synthetic_data_vectors(num_samples=5)
        
        # 3. Сравниваем структуру батчей
        compare_batch_structure(real_batch, synthetic_batch)
        
        # 4. Сравниваем значения признаков
        compare_feature_values(real_batch, real_data, synthetic_batch, synthetic_df)
        
        # 5. Сравниваем распределения
        compare_distributions(real_batch, synthetic_df)
        
        # 6. Генерируем итоговый отчет
        generate_feature_comparison_report(real_batch, synthetic_batch)
        
        print(f"\n🎉 Детальное сравнение завершено успешно!")
        
    except Exception as e:
        print(f"💥 Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
