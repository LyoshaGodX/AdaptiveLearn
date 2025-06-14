#!/usr/bin/env python3
"""
Простой тест импорта и инициализации DKN модели
"""

import os
import sys
import torch
import pandas as pd
import numpy as np

# Настройка Django
print("Настройка Django...")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()
print("Django настроен успешно")

# Тестируем импорты
print("Тестируем импорты...")
try:
    from mlmodels.dkn.model import DKNConfig, DKNModel
    print("✓ DKN model импортирован")
except Exception as e:
    print(f"✗ Ошибка импорта DKN model: {e}")
    sys.exit(1)

try:
    from mlmodels.dkn.data_processor import DKNDataProcessor, DKNDataset
    print("✓ DKN data_processor импортирован")
except Exception as e:
    print(f"✗ Ошибка импорта DKN data_processor: {e}")
    sys.exit(1)

try:
    from mlmodels.dkn.trainer import AdvancedDKNTrainer
    print("✓ DKN trainer импортирован")
except Exception as e:
    print(f"✗ Ошибка импорта DKN trainer: {e}")
    sys.exit(1)

# Создаем простые тестовые данные
print("Создаем тестовые данные...")
test_data = []
for i in range(10):
    record = {
        'student_id': i,
        'task_id': i % 3,
        'targets': float(i % 2),
        'skill_ids': [0],
        'skill_mask': [1.0],
        'bkt_params': [[0.5, 0.1, 0.2, 0.1]],
        'current_bkt_avg': 0.5,
        'task_difficulty': i % 3,
        'task_type': i % 3,
        'task_ids': i % 3,
        'student_history': [[0.0, 0.0, 60.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0] for _ in range(10)]
    }
    test_data.append(record)

print(f"Создано {len(test_data)} тестовых записей")

# Тестируем collate функцию
def test_collate_fn(batch):
    batch_data = {
        'skill_ids': [],
        'bkt_params': [],
        'task_ids': [],
        'task_difficulty': [],
        'task_type': [],
        'student_history': [],
        'current_bkt_avg': [],
        'targets': [],
        'skill_mask': []
    }
    
    for item in batch:
        batch_data['skill_ids'].append(item['skill_ids'])
        batch_data['bkt_params'].append(item['bkt_params'])
        batch_data['task_ids'].append(item['task_ids'])
        batch_data['task_difficulty'].append(item['task_difficulty'])
        batch_data['task_type'].append(item['task_type'])
        batch_data['current_bkt_avg'].append(item['current_bkt_avg'])
        batch_data['targets'].append(item['targets'])
        batch_data['skill_mask'].append(item['skill_mask'])
        batch_data['student_history'].append(item['student_history'])
    
    return {
        'skill_ids': torch.tensor(batch_data['skill_ids'], dtype=torch.long),
        'bkt_params': torch.tensor(batch_data['bkt_params'], dtype=torch.float32),
        'task_ids': torch.tensor(batch_data['task_ids'], dtype=torch.long),
        'task_difficulty': torch.tensor(batch_data['task_difficulty'], dtype=torch.long),
        'task_type': torch.tensor(batch_data['task_type'], dtype=torch.long),
        'student_history': torch.tensor(batch_data['student_history'], dtype=torch.float32),
        'current_bkt_avg': torch.tensor(batch_data['current_bkt_avg'], dtype=torch.float32),
        'targets': torch.tensor(batch_data['targets'], dtype=torch.float32),
        'skill_mask': torch.tensor(batch_data['skill_mask'], dtype=torch.float32)
    }

print("Тестируем collate функцию...")
test_batch = test_collate_fn(test_data[:4])
print("✓ Collate функция работает")
print(f"Размеры тензоров:")
for key, value in test_batch.items():
    print(f"  {key}: {value.shape}")

# Тестируем создание модели
print("Тестируем создание модели...")
try:
    config = DKNConfig()
    config.hidden_dim = 64
    config.num_layers = 2
    
    # Создаем процессор данных
    processor = DKNDataProcessor()
    num_skills = max(1, len(processor.skill_to_id))
    num_tasks = max(1, len(processor.task_to_id))
    
    print(f"Количество навыков: {num_skills}")
    print(f"Количество заданий: {num_tasks}")
    
    model = DKNModel(num_skills, num_tasks, config)
    print("✓ Модель создана успешно")
    
    # Тестируем forward pass
    print("Тестируем forward pass...")
    model.eval()
    with torch.no_grad():
        output = model(test_batch)
        print(f"✓ Forward pass успешен, размер выхода: {output.shape}")
    
except Exception as e:
    print(f"✗ Ошибка при создании/тестировании модели: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("Все тесты пройдены успешно!")
