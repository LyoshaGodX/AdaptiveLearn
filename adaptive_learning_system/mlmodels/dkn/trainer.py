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
from model import DKNModel, DKNConfig, DKNTrainer
from data_processor import DKNDataProcessor, DKNDataset
from training_artifacts import TrainingArtifactsCollector

logger = logging.getLogger(__name__)


class AdvancedDKNTrainer(DKNTrainer):
    """Расширенный тренер с дополнительными возможностями"""
    
    def __init__(self, model: DKNModel, config: DKNConfig, 
                 save_dir: str = 'checkpoints',
                 artifacts_dir: str = 'mlmodels/dkn/training'):
        super().__init__(model, config)
        
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(exist_ok=True)
        
        # Инициализация коллектора артефактов
        self.artifacts_collector = TrainingArtifactsCollector(artifacts_dir)
        
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
              # Логирование каждые 500 батчей (вместо 100)
            if batch_idx % 500 == 0:
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
        """Быстрое вычисление метрик качества (оптимизированная версия)"""
        pred_array = np.array(predictions)
        target_array = np.array(targets)
        
        # Бинарные предсказания с фиксированным порогом
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
        
        # Упрощенный AUC (без медленного перебора порогов)
        try:
            from sklearn.metrics import roc_auc_score
            auc_value = roc_auc_score(target_array, pred_array)
        except:
            # Простое приближение без sklearn
            auc_value = 0.5 + abs(accuracy - 0.5)
        
        return {
            'accuracy': float(accuracy),
            'precision': float(precision),
            'recall': float(recall),
            'f1': float(f1),
            'auc': float(auc_value)
        }
    
    def train_with_validation(self, train_loader: DataLoader, 
                            val_loader: DataLoader, 
                            num_epochs: int = 50,
                            save_best: bool = True) -> Dict[str, List]:
        """Полное обучение с валидацией и сбором артефактов"""
        
        # Инициализация времени начала обучения
        self.artifacts_collector.set_training_start()
        
        logger.info(f"Начинаем обучение DKN модели на {num_epochs} эпох")
        try:
            train_size = getattr(train_loader.dataset, '__len__', lambda: 'Unknown')()
            val_size = getattr(val_loader.dataset, '__len__', lambda: 'Unknown')()
            logger.info(f"Размер обучающей выборки: {train_size}")
            logger.info(f"Размер валидационной выборки: {val_size}")
        except:
            logger.info("Размеры выборок не определены")
        
        early_stopped = False
        
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
            
            # Логируем в коллектор артефактов
            additional_metrics = {
                'train_f1': train_metrics.get('f1', 0),
                'val_f1': val_metrics.get('f1', 0),
                'train_precision': train_metrics.get('precision', 0),
                'val_precision': val_metrics.get('precision', 0),
                'train_recall': train_metrics.get('recall', 0),
                'val_recall': val_metrics.get('recall', 0),
                'epoch_time_seconds': (datetime.now() - start_time).total_seconds()
            }
            
            self.artifacts_collector.log_epoch(
                epoch=epoch,
                train_loss=train_metrics['loss'],
                val_loss=val_metrics['loss'],
                train_accuracy=train_metrics['accuracy'],
                val_accuracy=val_metrics['accuracy'],
                learning_rate=current_lr,
                additional_metrics=additional_metrics
            )
            
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
                    best_model_path = self._save_checkpoint(epoch, 'best_model.pth', val_metrics)
                    self.artifacts_collector.training_info['best_model_path'] = str(best_model_path)
            else:
                self.patience_counter += 1
                
            if self.patience_counter >= self.patience:
                logger.info(f"Early stopping на эпохе {epoch+1}")
                early_stopped = True
                break
            
            # Периодические сохранения
            if (epoch + 1) % 10 == 0:
                self._save_checkpoint(epoch, f'checkpoint_epoch_{epoch+1}.pth', val_metrics)
        
        # Сохраняем финальную модель
        final_model_path = self._save_checkpoint(epoch, 'final_model.pth', val_metrics)
        self.artifacts_collector.training_info['final_model_path'] = str(final_model_path)
        
        # Сохраняем конфигурацию модели
        self._save_model_config()
        
        # Финализация обучения с артефактами
        self.artifacts_collector.finalize_training(early_stopped=early_stopped)
        
        # Сохраняем историю обучения
        self._save_training_history()
        
        logger.info("Обучение завершено! Артефакты сохранены в: " +                   str(self.artifacts_collector.artifacts_dir))
        
        return self.train_history
    
    def _save_checkpoint(self, epoch: int, filename: str, metrics: Dict) -> Path:
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
        
        # Сохраняем в обычное место
        checkpoint_path = self.save_dir / filename
        torch.save(checkpoint, checkpoint_path)
        
        # Также сохраняем в директорию артефактов
        artifacts_checkpoint_path = self.artifacts_collector.models_dir / filename
        torch.save(checkpoint, artifacts_checkpoint_path)
        
        logger.info(f"Checkpoint сохранен: {checkpoint_path}")
        return artifacts_checkpoint_path
    
    def _save_model_config(self):
        """Сохраняет конфигурацию модели"""
        config_dict = self.config.__dict__.copy()
        
        # Сохраняем в директорию артефактов
        config_path = self.artifacts_collector.models_dir / 'model_config.json'
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Конфигурация модели сохранена: {config_path}")
    
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
                   artifacts_dir: str = 'mlmodels/dkn/training',
                   num_epochs: int = 50,
                   batch_size: int = 32,
                   test_data: Optional[List[Dict]] = None,
                   collate_fn = None,
                   num_skills: Optional[int] = None,
                   num_tasks: Optional[int] = None) -> AdvancedDKNTrainer:
    """
    Полная функция обучения DKN модели с созданием артефактов
    
    Args:
        train_data: Тренировочные данные
        val_data: Валидационные данные  
        config: Конфигурация модели
        save_dir: Директория для сохранения checkpoints
        artifacts_dir: Директория для артефактов обучения
        num_epochs: Количество эпох
        batch_size: Размер батча
        test_data: Тестовые данные (опционально)
        
    Returns:
        Обученный тренер с артефактами
    """
    
    if config is None:
        config = DKNConfig()
        config.batch_size = batch_size
      # Подготавливаем данные
    train_dataset = DKNDataset(train_data)
    val_dataset = DKNDataset(val_data)
    
    # Используем переданный collate_fn или создаем процессор для дефолтного
    if collate_fn is None:
        processor = DKNDataProcessor()
        used_collate_fn = processor.collate_fn
        # Используем параметры из процессора если не переданы
        if num_skills is None:
            model_num_skills = len(processor.skill_to_id)
        else:
            model_num_skills = num_skills
        if num_tasks is None:
            model_num_tasks = len(processor.task_to_id)
        else:
            model_num_tasks = num_tasks
    else:
        used_collate_fn = collate_fn
        # Для кастомного collate_fn обязательно нужны параметры
        if num_skills is None or num_tasks is None:
            raise ValueError("При использовании кастомного collate_fn необходимо передать num_skills и num_tasks")
        model_num_skills = num_skills
        model_num_tasks = num_tasks
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, collate_fn=used_collate_fn)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, collate_fn=used_collate_fn)    # Создаем модель
    model = DKNModel(model_num_skills, model_num_tasks, config)
    
    # Создаем тренер с поддержкой артефактов
    trainer = AdvancedDKNTrainer(model, config, save_dir, artifacts_dir)
      # Собираем информацию о датасете
    dataset_info = {
        'train_size': len(train_data),
        'val_size': len(val_data),
        'test_size': len(test_data) if test_data else 0,
        'num_skills': model_num_skills,
        'num_tasks': model_num_tasks,
        'batch_size': batch_size
    }
    
    # Обучаем
    logger.info("Начинаем обучение DKN модели с полным сбором артефактов...")
    history = trainer.train_with_validation(
        train_loader, val_loader, num_epochs, save_best=True
    )
    
    # Если есть тестовые данные, проводим оценку
    test_metrics = None
    if test_data:
        logger.info("Проводим тестирование модели...")
        test_dataset = DKNDataset(test_data)
        test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, collate_fn=collate_fn)
        test_metrics = trainer.validate(test_loader)
        
        # Получаем предсказания для создания расширенного дашборда
        all_predictions = []
        all_targets = []
        
        trainer.model.eval()
        with torch.no_grad():
            for batch in test_loader:
                batch = {k: v.to(trainer.device) if isinstance(v, torch.Tensor) else v 
                        for k, v in batch.items()}
                predictions = trainer.model(batch)
                targets = batch['targets'].float()
                
                all_predictions.extend(predictions.cpu().numpy())
                all_targets.extend(targets.cpu().numpy())
        
        # Создаем расширенный дашборд с тестовыми метриками
        trainer.artifacts_collector.create_metrics_dashboard(
            test_predictions=np.array(all_predictions),
            test_targets=np.array(all_targets)
        )
        
        logger.info(f"Результаты тестирования: {test_metrics}")
      # Создаем итоговый отчет
    report_path = trainer.artifacts_collector.generate_training_report(
        model_config=config.__dict__,
        dataset_info=dataset_info,
        test_metrics=test_metrics or {}
    )
    
    logger.info("Обучение завершено успешно!")
    logger.info(f"Артефакты сохранены в: {trainer.artifacts_collector.artifacts_dir}")
    logger.info(f"Отчет об обучении: {report_path}")
    
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
