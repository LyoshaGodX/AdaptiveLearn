#!/usr/bin/env python3
"""
Улучшенная быстрая модель DKN с лучшими признаками для повышения точности
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
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

# Логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_enhanced_features(df):
    """Создает улучшенные признаки для повышения точности"""
    features_list = []
    targets = []
    
    for _, row in df.iterrows():
        features = []
        
        # 1. BKT параметры (основные)
        skill_learned = row.get('skill_0_learned', 0.5)
        skill_transit = row.get('skill_0_transit', 0.1)
        features.extend([skill_learned, skill_transit])
        
        # 2. Характеристики задания
        task_difficulty = float(row.get('task_difficulty', 0))
        task_type = float(row.get('task_type', 0))
        features.extend([task_difficulty, task_type])
        
        # 3. Исторические данные (агрегированные)
        hist_correct_sum = 0
        hist_score_avg = 0
        hist_time_avg = 0
        hist_count = 0
        
        for i in range(10):
            hist_correct = row.get(f'hist_{i}_correct', 0)
            hist_score = row.get(f'hist_{i}_score', 0.0)
            hist_time = row.get(f'hist_{i}_time', 60.0)
            
            if hist_correct > 0 or hist_score > 0:
                hist_correct_sum += hist_correct
                hist_score_avg += hist_score
                hist_time_avg += hist_time
                hist_count += 1
        
        if hist_count > 0:
            hist_score_avg /= hist_count
            hist_time_avg /= hist_count
        
        # Агрегированные исторические признаки
        features.extend([
            hist_correct_sum,  # Общее количество правильных ответов
            hist_score_avg,    # Средний скор
            hist_time_avg / 100.0,  # Среднее время (нормализованное)
            hist_count,        # Количество попыток
        ])
        
        # 4. Производные признаки
        # Тренд производительности (последние vs первые попытки)
        recent_performance = 0
        early_performance = 0
        
        for i in [0, 1, 2]:  # Первые 3
            early_performance += row.get(f'hist_{i}_score', 0.0)
        for i in [7, 8, 9]:  # Последние 3
            recent_performance += row.get(f'hist_{i}_score', 0.0)
        
        performance_trend = recent_performance - early_performance
        features.append(performance_trend)
        
        # 5. Взаимодействие признаков
        # Соответствие сложности задания и уровня студента
        difficulty_match = abs(task_difficulty - (skill_learned * 2))
        features.append(difficulty_match)
        
        # Консистентность производительности
        hist_scores = [row.get(f'hist_{i}_score', 0.0) for i in range(10)]
        consistency = 1.0 - np.std(hist_scores) if len(hist_scores) > 1 else 1.0
        features.append(consistency)
        
        # 6. Контекстные признаки
        # ID задания (закодированное)
        task_id_encoded = (row['task_id'] % 100) / 100.0
        features.append(task_id_encoded)
        
        features_list.append(features)
        targets.append(float(row['target']))
    
    return np.array(features_list), np.array(targets)

class EnhancedDKN(nn.Module):
    """Улучшенная архитектура с attention и residual connections"""
    
    def __init__(self, input_size):
        super().__init__()
        
        # Первый блок с batch normalization
        self.input_block = nn.Sequential(
            nn.Linear(input_size, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.3)
        )
        
        # Attention механизм (упрощенный)
        self.attention = nn.Sequential(
            nn.Linear(128, 64),
            nn.Tanh(),
            nn.Linear(64, 128),
            nn.Sigmoid()
        )
        
        # Основные слои с residual connections
        self.hidden1 = nn.Sequential(
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.2)
        )
        
        self.hidden2 = nn.Sequential(
            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Dropout(0.1)
        )
        
        # Выходной слой
        self.output = nn.Sequential(
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        # Входной блок
        x1 = self.input_block(x)
        
        # Attention
        attention_weights = self.attention(x1)
        x1_attended = x1 * attention_weights
        
        # Основные слои
        x2 = self.hidden1(x1_attended)
        x3 = self.hidden2(x2)
        
        # Выход
        output = self.output(x3)
        return output.squeeze()

def enhanced_train():
    """Улучшенное обучение с лучшими признаками"""
    logger.info("=== УЛУЧШЕННОЕ БЫСТРОЕ ОБУЧЕНИЕ DKN ===")
    
    try:
        # 1. Загрузка и подготовка данных
        logger.info("Загрузка и подготовка данных...")
        df = pd.read_csv('mlmodels/dkn/dataset/enhanced_synthetic_dataset.csv')
        
        # Используем больше данных для лучшей точности
        df_sample = df.sample(n=min(50000, len(df)), random_state=42).reset_index(drop=True)
        
        # Создание улучшенных признаков
        X, y = create_enhanced_features(df_sample)
        logger.info(f"Создано признаков: {X.shape[1]}")
        
        # Нормализация признаков
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Разделение данных
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42, stratify=y
        )
        X_train, X_val, y_train, y_val = train_test_split(
            X_train, y_train, test_size=0.25, random_state=42, stratify=y_train
        )
        
        logger.info(f"Данные: {len(X_train)} train, {len(X_val)} val, {len(X_test)} test")
        
        # 2. Преобразование в тензоры
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        X_train = torch.tensor(X_train, dtype=torch.float32).to(device)
        y_train = torch.tensor(y_train, dtype=torch.float32).to(device)
        X_val = torch.tensor(X_val, dtype=torch.float32).to(device)
        y_val = torch.tensor(y_val, dtype=torch.float32).to(device)
        X_test = torch.tensor(X_test, dtype=torch.float32).to(device)
        y_test = torch.tensor(y_test, dtype=torch.float32).to(device)
        
        # 3. Модель
        model = EnhancedDKN(X_train.shape[1]).to(device)
        logger.info(f"Модель создана на {device}")
        logger.info(f"Параметров: {sum(p.numel() for p in model.parameters()):,}")
        
        # 4. Оптимизатор и планировщик
        optimizer = torch.optim.AdamW(
            model.parameters(), 
            lr=0.001, 
            weight_decay=0.01,
            betas=(0.9, 0.999)
        )
        
        scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
            optimizer, T_0=10, T_mult=2, eta_min=1e-6
        )
        
        criterion = nn.BCELoss()
        
        # 5. Обучение с early stopping
        logger.info("Начинаем улучшенное обучение...")
        
        best_val_acc = 0.0
        patience = 5
        patience_counter = 0
        history = {'train_loss': [], 'val_loss': [], 'train_acc': [], 'val_acc': []}
        
        start_training = time.time()
        
        for epoch in range(200):  # Больше эпох для лучшей точности
            start_time = time.time()
            
            # Обучение
            model.train()
            optimizer.zero_grad()
            
            train_pred = model(X_train)
            train_loss = criterion(train_pred, y_train)
            train_loss.backward()
            
            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            
            optimizer.step()
            scheduler.step()
            
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
            
            # Логирование каждые 5 эпох
            if epoch % 5 == 0 or epoch < 10:
                lr = optimizer.param_groups[0]['lr']
                logger.info(f"Эпоха {epoch+1:2d} ({epoch_time:.1f}s): "
                           f"Train Loss={train_loss:.4f}, Acc={train_acc:.4f} | "
                           f"Val Loss={val_loss:.4f}, Acc={val_acc:.4f} | LR={lr:.6f}")
            
            # Early stopping и сохранение лучшей модели
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                patience_counter = 0
                torch.save(model.state_dict(), 'best_enhanced_model.pth')
                if epoch % 5 == 0 or val_acc > 0.7:
                    logger.info(f"  >>> Новая лучшая точность: {best_val_acc:.4f}")
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    logger.info(f"Early stopping на эпохе {epoch+1}")
                    break
        
        training_time = time.time() - start_training
        
        # 6. Финальная оценка на тесте
        model.load_state_dict(torch.load('best_enhanced_model.pth'))
        model.eval()
        
        with torch.no_grad():
            test_pred = model(X_test)
            test_loss = criterion(test_pred, y_test)
            test_acc = ((test_pred > 0.5) == y_test).float().mean().item()
            
            # Дополнительные метрики
            test_pred_prob = test_pred.cpu().numpy()
            test_true = y_test.cpu().numpy()
            
            # Precision, Recall, F1
            tp = np.sum((test_pred_prob > 0.5) & (test_true == 1))
            fp = np.sum((test_pred_prob > 0.5) & (test_true == 0))
            fn = np.sum((test_pred_prob <= 0.5) & (test_true == 1))
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        # 7. Результаты
        logger.info(f"\n🎯 ФИНАЛЬНЫЕ РЕЗУЛЬТАТЫ:")
        logger.info(f"📊 Лучшая валидационная точность: {best_val_acc:.4f}")
        logger.info(f"🎯 Тестовая точность: {test_acc:.4f}")
        logger.info(f"📈 Precision: {precision:.4f}")
        logger.info(f"📈 Recall: {recall:.4f}")
        logger.info(f"📈 F1-score: {f1:.4f}")
        logger.info(f"⏱️ Время обучения: {training_time:.1f}с")
        
        # Сохранение результатов
        results = {
            'best_validation_accuracy': best_val_acc,
            'test_accuracy': test_acc,
            'test_precision': precision,
            'test_recall': recall,
            'test_f1': f1,
            'training_time': training_time,
            'num_epochs': len(history['train_acc']),
            'history': history,
            'model_parameters': sum(p.numel() for p in model.parameters()),
            'data_size': len(df_sample),
            'features_count': X.shape[1]
        }
        
        with open('enhanced_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info("Результаты сохранены в enhanced_results.json")
        
        return model, results, scaler
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None, None, None

if __name__ == "__main__":
    model, results, scaler = enhanced_train()
    if results:
        print(f"\n🚀 ИТОГОВЫЕ РЕЗУЛЬТАТЫ:")
        print(f"📊 Тестовая точность: {results['test_accuracy']:.4f}")
        print(f"📈 F1-score: {results['test_f1']:.4f}")
        print(f"🔢 Параметров в модели: {results['model_parameters']:,}")
        print(f"📝 Признаков: {results['features_count']}")
        print(f"⏱️ Время обучения: {results['training_time']:.1f}с")
        print(f"📦 Размер данных: {results['data_size']:,} примеров")
