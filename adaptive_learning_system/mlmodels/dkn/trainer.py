"""
Расширенный тренер для DKN модели с валидацией и метриками

Этот модуль предоставляет продвинутые возможности для обучения
DKN модели, включая валидацию, метрики, early stopping и логирование.
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import numpy as np
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import json
from pathlib import Path
import logging
from datetime import datetime
import os

# Local imports
from .model import DKNModel, DKNConfig, DKNTrainer
from .data_processor import DKNDataProcessor, DKNDataset

logger = logging.getLogger(__name__)


class AdvancedDKNTrainer(DKNTrainer):
    """Расширенный тренер с дополнительными возможностями"""
    
    def __init__(self, model: DKNModel, config: DKNConfig, 
                 save_dir: str = 'checkpoints'):
        super().__init__(model, config)
        
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(exist_ok=True)
        
        # История обучения
        self.train_history = {
            'loss': [],
            'accuracy': [],
            'val_loss': [],
            'val_accuracy': [],
            'learning_rate': []
        }
        
        # Early stopping
        self.best_val_loss = float('inf')
        self.patience_counter = 0
        self.patience = 10
        
        # Scheduler для learning rate
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode='min', factor=0.5, patience=5
        )
        
    def train_epoch(self, train_loader: DataLoader, epoch: int) -> Dict[str, float]:
        """Обучение одной эпохи с подробными метриками"""
        self.model.train()
        
        total_loss = 0.0
        all_predictions = []
        all_targets = []
        
        for batch_idx, batch in enumerate(train_loader):
            # Перемещаем данные на устройство
            batch = {k: v.to(self.device) if isinstance(v, torch.Tensor) else v 
                    for k, v in batch.items()}
            
            self.optimizer.zero_grad()
            
            # Forward pass
            predictions = self.model(batch)
            targets = batch['targets'].float()
            
            # Потери
            loss = self.criterion(predictions, targets)
            
            # Backward pass
            loss.backward()
            
            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            
            self.optimizer.step()
            
            total_loss += loss.item()
            all_predictions.extend(predictions.detach().cpu().numpy())
            all_targets.extend(targets.cpu().numpy())
            
            # Логирование каждые 100 батчей
            if batch_idx % 100 == 0:
                logger.info(f'Epoch {epoch}, Batch {batch_idx}, Loss: {loss:.4f}')
        
        # Вычисляем метрики
        avg_loss = total_loss / len(train_loader)
        metrics = self._calculate_detailed_metrics(all_predictions, all_targets)
        metrics['loss'] = avg_loss
        
        return metrics

    def validate(self, val_loader: DataLoader) -> Dict[str, float]:
        """Валидация с подробными метриками"""
        self.model.eval()
        
        total_loss = 0.0
        all_predictions = []
        all_targets = []
        
        with torch.no_grad():
            for batch in val_loader:
                # Перемещаем данные на устройство
                batch = {k: v.to(self.device) if isinstance(v, torch.Tensor) else v 
                        for k, v in batch.items()}
                
                predictions = self.model(batch)
                targets = batch['targets'].float()
                
                # Потери
                loss = self.criterion(predictions, targets)
                total_loss += loss.item()
                
                all_predictions.extend(predictions.cpu().numpy())
                all_targets.extend(targets.cpu().numpy())
        
        # Вычисляем метрики
        avg_loss = total_loss / len(val_loader)
        metrics = self._calculate_detailed_metrics(all_predictions, all_targets)
        metrics['loss'] = avg_loss
        
        return metrics
    
    def _calculate_detailed_metrics(self, predictions: List[float], 
                                  targets: List[float]) -> Dict[str, float]:
        """Вычисляет подробные метрики качества"""
        pred_array = np.array(predictions)
        target_array = np.array(targets)
        
        # Бинарные предсказания
        predicted_labels = (pred_array > 0.5).astype(float)
        
        # Основные метрики
        accuracy = np.mean(predicted_labels == target_array)
        
        # Precision, Recall, F1
        true_positives = np.sum((predicted_labels == 1) & (target_array == 1))
        false_positives = np.sum((predicted_labels == 1) & (target_array == 0))
        false_negatives = np.sum((predicted_labels == 0) & (target_array == 1))
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        # AUC-ROC (упрощенная версия)
        # Сортируем по предсказаниям
        sorted_indices = np.argsort(predictions)[::-1]
        sorted_targets = target_array[sorted_indices]
        
        # Вычисляем TPR и FPR для разных порогов
        thresholds = np.unique(predictions)
        tpr_list = []
        fpr_list = []
        
        for threshold in thresholds:
            pred_at_threshold = (predictions >= threshold).astype(float)
            tp = np.sum((pred_at_threshold == 1) & (target_array == 1))
            fp = np.sum((pred_at_threshold == 1) & (target_array == 0))
            tn = np.sum((pred_at_threshold == 0) & (target_array == 0))
            fn = np.sum((pred_at_threshold == 0) & (target_array == 1))
            
            tpr = tp / (tp + fn) if (tp + fn) > 0 else 0
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
            
            tpr_list.append(tpr)
            fpr_list.append(fpr)
        
        # Простое приближение AUC
        try:
            auc = np.trapz(tpr_list, fpr_list) if len(tpr_list) > 1 else 0.5
            auc_value = float(auc) if isinstance(auc, (int, float, np.number)) else 0.5
        except:
            auc_value = 0.5
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'auc': auc_value
        }
    
    def train_with_validation(self, train_loader: DataLoader, 
                            val_loader: DataLoader, 
                            num_epochs: int = 50,
                            save_best: bool = True) -> Dict[str, List]:
        """Полное обучение с валидацией"""
        
        logger.info(f"Начинаем обучение DKN модели на {num_epochs} эпох")
        try:
            train_size = getattr(train_loader.dataset, '__len__', lambda: 'Unknown')()
            val_size = getattr(val_loader.dataset, '__len__', lambda: 'Unknown')()
            logger.info(f"Размер обучающей выборки: {train_size}")
            logger.info(f"Размер валидационной выборки: {val_size}")
        except:
            logger.info("Размеры выборок не определены")
        
        for epoch in range(num_epochs):
            start_time = datetime.now()
            
            # Обучение
            train_metrics = self.train_epoch(train_loader, epoch)
            
            # Валидация
            val_metrics = self.validate(val_loader)
            
            # Обновляем learning rate
            self.scheduler.step(val_metrics['loss'])
            current_lr = self.optimizer.param_groups[0]['lr']
            
            # Сохраняем историю
            self.train_history['loss'].append(train_metrics['loss'])
            self.train_history['accuracy'].append(train_metrics['accuracy'])
            self.train_history['val_loss'].append(val_metrics['loss'])
            self.train_history['val_accuracy'].append(val_metrics['accuracy'])
            self.train_history['learning_rate'].append(current_lr)
            
            # Логирование
            epoch_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"""
            Эпоха {epoch+1}/{num_epochs} ({epoch_time:.1f}s):
            Обучение - Loss: {train_metrics['loss']:.4f}, Accuracy: {train_metrics['accuracy']:.4f}, F1: {train_metrics.get('f1', 0):.4f}
            Валидация - Loss: {val_metrics['loss']:.4f}, Accuracy: {val_metrics['accuracy']:.4f}, F1: {val_metrics.get('f1', 0):.4f}
            Learning Rate: {current_lr:.6f}
            """)
            
            # Early stopping
            if val_metrics['loss'] < self.best_val_loss:
                self.best_val_loss = val_metrics['loss']
                self.patience_counter = 0
                
                if save_best:
                    self._save_checkpoint(epoch, 'best_model.pth', val_metrics)
            else:
                self.patience_counter += 1
                
            if self.patience_counter >= self.patience:
                logger.info(f"Early stopping на эпохе {epoch+1}")
                break
            
            # Периодические сохранения
            if (epoch + 1) % 10 == 0:
                self._save_checkpoint(epoch, f'checkpoint_epoch_{epoch+1}.pth', val_metrics)
        
        # Сохраняем финальную модель
        self._save_checkpoint(epoch, 'final_model.pth', val_metrics)
        
        # Сохраняем историю обучения
        self._save_training_history()
        
        return self.train_history
    
    def _save_checkpoint(self, epoch: int, filename: str, metrics: Dict):
        """Сохраняет checkpoint модели"""
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'best_val_loss': self.best_val_loss,
            'train_history': self.train_history,
            'metrics': metrics,
            'config': self.config.__dict__
        }
        
        checkpoint_path = self.save_dir / filename
        torch.save(checkpoint, checkpoint_path)
        logger.info(f"Checkpoint сохранен: {checkpoint_path}")
    
    def _save_training_history(self):
        """Сохраняет историю обучения"""
        history_path = self.save_dir / 'training_history.json'
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(self.train_history, f, indent=2, ensure_ascii=False)
        
        # Создаем графики
        self._plot_training_curves()
    
    def _plot_training_curves(self):
        """Создает графики обучения"""
        try:
            plt.figure(figsize=(15, 5))
            
            # График потерь
            plt.subplot(1, 3, 1)
            plt.plot(self.train_history['loss'], label='Обучение')
            plt.plot(self.train_history['val_loss'], label='Валидация')
            plt.title('Потери')
            plt.xlabel('Эпоха')
            plt.ylabel('Loss')
            plt.legend()
            plt.grid(True)
            
            # График точности
            plt.subplot(1, 3, 2)
            plt.plot(self.train_history['accuracy'], label='Обучение')
            plt.plot(self.train_history['val_accuracy'], label='Валидация')
            plt.title('Точность')
            plt.xlabel('Эпоха')
            plt.ylabel('Accuracy')
            plt.legend()
            plt.grid(True)
            
            # График learning rate
            plt.subplot(1, 3, 3)
            plt.plot(self.train_history['learning_rate'])
            plt.title('Learning Rate')
            plt.xlabel('Эпоха')
            plt.ylabel('LR')
            plt.yscale('log')
            plt.grid(True)
            
            plt.tight_layout()
            plt.savefig(self.save_dir / 'training_curves.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Графики сохранены: {self.save_dir / 'training_curves.png'}")
            
        except Exception as e:
            logger.warning(f"Не удалось создать графики: {e}")
    
    def load_checkpoint(self, checkpoint_path: str) -> Dict:
        """Загружает checkpoint модели"""
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        
        self.best_val_loss = checkpoint['best_val_loss']
        self.train_history = checkpoint['train_history']
        
        logger.info(f"Checkpoint загружен: {checkpoint_path}")
        
        return checkpoint['metrics']


def train_dkn_model(train_data: List[Dict], val_data: List[Dict],
                   config: Optional[DKNConfig] = None,
                   save_dir: str = 'checkpoints',
                   num_epochs: int = 50,
                   batch_size: int = 32) -> AdvancedDKNTrainer:
    """
    Полная функция обучения DKN модели
    
    Args:
        train_data: Тренировочные данные
        val_data: Валидационные данные  
        config: Конфигурация модели
        save_dir: Директория для сохранения
        num_epochs: Количество эпох
        batch_size: Размер батча
        
    Returns:
        Обученный тренер
    """
    
    if config is None:
        config = DKNConfig()
        config.batch_size = batch_size
    
    # Подготавливаем данные
    processor = DKNDataProcessor()
    
    train_dataset = DKNDataset(train_data)
    val_dataset = DKNDataset(val_data)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    # Создаем модель
    num_skills = len(processor.skill_to_id)
    num_tasks = len(processor.task_to_id)
    
    model = DKNModel(num_skills, num_tasks, config)
    
    # Создаем тренер
    trainer = AdvancedDKNTrainer(model, config, save_dir)
    
    # Обучаем
    history = trainer.train_with_validation(
        train_loader, val_loader, num_epochs, save_best=True
    )
    
    logger.info("Обучение завершено успешно!")
    
    return trainer


def evaluate_model_performance(model_path: str, test_data: List[Dict]) -> Dict:
    """
    Оценивает производительность обученной модели
    
    Args:
        model_path: Путь к сохраненной модели
        test_data: Тестовые данные
        
    Returns:
        Словарь с метриками производительности
    """
    
    # Загружаем модель
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    checkpoint = torch.load(model_path, map_location=device)
    
    config_dict = checkpoint['config']
    config = DKNConfig()
    for key, value in config_dict.items():
        setattr(config, key, value)
    
    processor = DKNDataProcessor()
    num_skills = len(processor.skill_to_id)
    num_tasks = len(processor.task_to_id)
    
    model = DKNModel(num_skills, num_tasks, config)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.to(device)
    model.eval()
    
    # Подготавливаем тестовые данные
    test_dataset = DKNDataset(test_data)
    test_loader = DataLoader(
        test_dataset, batch_size=32, shuffle=False
    )
    
    # Оценка
    trainer = AdvancedDKNTrainer(model, config)
    metrics = trainer.validate(test_loader)
    
    logger.info(f"Результаты тестирования: {metrics}")
    
    return metrics
