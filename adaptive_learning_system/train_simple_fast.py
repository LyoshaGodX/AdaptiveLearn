#!/usr/bin/env python3
"""
Быстрое и точное обучение DKN - упрощенная оптимизированная версия
"""

import os
import sys
import django
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import logging
import time
import json

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

# Логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def quick_train():
    """Быстрое обучение с максимальными оптимизациями"""
    logger.info("=== БЫСТРОЕ ОБУЧЕНИЕ DKN ===")
    
    try:
        # 1. Загрузка данных (только 10K примеров для скорости)
        logger.info("Загрузка данных...")
        df = pd.read_csv('mlmodels/dkn/dataset/enhanced_synthetic_dataset.csv')
        df_small = df.sample(n=10000, random_state=42).reset_index(drop=True)
        
        # Простое разделение
        train_size = int(0.8 * len(df_small))
        train_df = df_small[:train_size]
        val_df = df_small[train_size:]
        
        logger.info(f"Данные: {len(train_df)} train, {len(val_df)} val")
        
        # 2. Простая подготовка данных
        def simple_prepare(data_df):
            X, y = [], []
            for _, row in data_df.iterrows():
                # Простые признаки: BKT параметры + характеристики задания
                features = [
                    row.get('skill_0_learned', 0.5),
                    row.get('skill_0_transit', 0.1),
                    float(row.get('task_difficulty', 0)) / 2.0,  # Нормализация
                    float(row.get('task_type', 0)) / 2.0,
                    float(row['task_id'] % 10) / 10.0,  # ID задания (упрощенно)
                ]
                
                # Добавляем простую историю (средние значения)
                hist_features = []
                for i in range(5):  # Только 5 последних
                    hist_features.extend([
                        row.get(f'hist_{i}_correct', 0.0),
                        row.get(f'hist_{i}_score', 0.0),
                        row.get(f'hist_{i}_time', 60.0) / 100.0  # Нормализация
                    ])
                
                features.extend(hist_features)
                X.append(features)
                y.append(float(row['target']))
            
            return torch.tensor(X, dtype=torch.float32), torch.tensor(y, dtype=torch.float32)
        
        X_train, y_train = simple_prepare(train_df)
        X_val, y_val = simple_prepare(val_df)
        
        logger.info(f"Размерность признаков: {X_train.shape[1]}")
        
        # 3. Простая модель
        class SimpleDKN(nn.Module):
            def __init__(self, input_size):
                super().__init__()
                self.model = nn.Sequential(
                    nn.Linear(input_size, 64),
                    nn.ReLU(),
                    nn.Dropout(0.2),
                    nn.Linear(64, 32),
                    nn.ReLU(),
                    nn.Dropout(0.2),
                    nn.Linear(32, 16),
                    nn.ReLU(),
                    nn.Linear(16, 1),
                    nn.Sigmoid()
                )
            
            def forward(self, x):
                return self.model(x).squeeze()
        
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        model = SimpleDKN(X_train.shape[1]).to(device)
        
        logger.info(f"Модель создана на {device}")
        logger.info(f"Параметров: {sum(p.numel() for p in model.parameters()):,}")
        
        # 4. Оптимизатор и критерий
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.01, weight_decay=0.01)
        criterion = nn.BCELoss()
        
        # 5. Быстрое обучение
        logger.info("Начинаем обучение...")
        
        X_train, y_train = X_train.to(device), y_train.to(device)
        X_val, y_val = X_val.to(device), y_val.to(device)
        
        best_val_acc = 0.0
        history = {'train_loss': [], 'val_loss': [], 'train_acc': [], 'val_acc': []}
        
        for epoch in range(20):
            start_time = time.time()
            
            # Обучение
            model.train()
            optimizer.zero_grad()
            
            train_pred = model(X_train)
            train_loss = criterion(train_pred, y_train)
            train_loss.backward()
            optimizer.step()
            
            # Валидация
            model.eval()
            with torch.no_grad():
                val_pred = model(X_val)
                val_loss = criterion(val_pred, y_val)
                
                # Метрики
                train_acc = ((train_pred > 0.5) == y_train).float().mean().item()
                val_acc = ((val_pred > 0.5) == y_val).float().mean().item()
            
            epoch_time = time.time() - start_time
            
            # Сохранение истории
            history['train_loss'].append(train_loss.item())
            history['val_loss'].append(val_loss.item())
            history['train_acc'].append(train_acc)
            history['val_acc'].append(val_acc)
            
            # Логирование
            logger.info(f"Эпоха {epoch+1:2d} ({epoch_time:.1f}s): "
                       f"Train Loss={train_loss:.4f}, Acc={train_acc:.4f} | "
                       f"Val Loss={val_loss:.4f}, Acc={val_acc:.4f}")
            
            # Сохранение лучшей модели
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                torch.save(model.state_dict(), 'best_simple_model.pth')
                logger.info(f"  >>> Новая лучшая точность: {best_val_acc:.4f}")
            
            # Early stopping
            if epoch > 5 and val_acc < max(history['val_acc'][-5:]) - 0.01:
                logger.info(f"Early stopping на эпохе {epoch+1}")
                break
        
        # 6. Результаты
        logger.info(f"Обучение завершено! Лучшая точность: {best_val_acc:.4f}")
        
        # Сохранение результатов
        results = {
            'best_validation_accuracy': best_val_acc,
            'final_train_accuracy': history['train_acc'][-1],
            'final_val_accuracy': history['val_acc'][-1],
            'num_epochs': len(history['train_acc']),
            'history': history,
            'model_parameters': sum(p.numel() for p in model.parameters()),
            'data_size': len(train_df)
        }
        
        with open('quick_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info("Результаты сохранены в quick_results.json")
        
        return model, results
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None

if __name__ == "__main__":
    model, results = quick_train()
    if results:
        print(f"\n🎯 ИТОГОВЫЕ РЕЗУЛЬТАТЫ:")
        print(f"📊 Лучшая точность на валидации: {results['best_validation_accuracy']:.4f}")
        print(f"🔢 Параметров в модели: {results['model_parameters']:,}")
        print(f"📈 Эпох обучения: {results['num_epochs']}")
        print(f"📝 Размер данных: {results['data_size']:,} примеров")
