#!/usr/bin/env python3
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
    print(f"Исходных записей: {len(df)}")
    
    # Определяем ОБЯЗАТЕЛЬНЫЕ колонки для DKN
    required_columns = ['student_id', 'task_id', 'skill_id', 'target']
    
    # Удаляем избыточные признаки, но сохраняем обязательные
    features_to_remove = ['hist_3_time', 'hist_6_correct', 'hist_8_score', 'hist_9_score', 'hist_7_correct', 'hist_1_time', 'hist_6_score', 'hist_0_correct', 'hist_4_score', 'hist_4_correct', 'hist_1_correct', 'hist_7_time', 'hist_0_time', 'hist_2_time', 'hist_2_score', 'hist_8_correct', 'hist_7_score', 'hist_2_correct', 'skill_0_transit', 'hist_9_time', 'hist_1_score', 'hist_5_correct', 'task_type', 'hist_5_score', 'skill_0_learned', 'hist_6_time', 'hist_9_correct', 'hist_8_time', 'hist_0_score', 'hist_3_score', 'hist_3_correct', 'hist_4_time', 'hist_5_time']
    
    # Исключаем обязательные колонки из удаления
    features_to_remove = [col for col in features_to_remove if col not in required_columns]
    
    df_optimized = df.drop(columns=[col for col in features_to_remove if col in df.columns])
    print(f"Удалено признаков: {len([col for col in features_to_remove if col in df.columns])}")
    print(f"Сохранены обязательные колонки: {required_columns}")
    
    # Проверяем, что все обязательные колонки присутствуют
    missing_required = [col for col in required_columns if col not in df_optimized.columns]
    if missing_required:
        print(f"❌ ОШИБКА: Отсутствуют обязательные колонки: {missing_required}")
        return False
    
    # Корректируем целевую переменную (если нужно)
    current_success_rate = df_optimized['target'].mean()
    target_success_rate = 0.75  # Целевая успешность на основе реальных данных
    
    if abs(current_success_rate - target_success_rate) > 0.1:
        print(f"Корректируем успешность: {current_success_rate:.1%} -> {target_success_rate:.1%}")
        
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
    print(f"Оптимизированные данные сохранены: {output_path}")
    print(f"Финальных записей: {len(df_optimized)}")
    print(f"Финальных признаков: {len(df_optimized.columns)}")
    print(f"Финальные колонки: {list(df_optimized.columns)}")
    
    return True

if __name__ == "__main__":
    optimize_synthetic_data()
