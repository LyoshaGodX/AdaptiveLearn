"""
Модуль для сбора артефактов обучения DKN модели.

Включает функции для:
- Визуализации процесса обучения
- Сбора статистики и метрик
- Создания отчетов об обучении
- Анализа производительности модели
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import json
import torch
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio
from sklearn.metrics import (
    confusion_matrix, classification_report, 
    roc_curve, auc, precision_recall_curve
)
import warnings
warnings.filterwarnings('ignore')

# Настройка стилей
plt.style.use('default')
sns.set_palette("husl")


class TrainingArtifactsCollector:
    """Класс для сбора и создания артефактов обучения DKN модели"""
    
    def __init__(self, artifacts_dir: str = "mlmodels/dkn/training"):
        """
        Инициализация коллектора артефактов
        
        Args:
            artifacts_dir: Директория для сохранения артефактов
        """
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        # Создание поддиректорий
        self.plots_dir = self.artifacts_dir / "plots"
        self.metrics_dir = self.artifacts_dir / "metrics"
        self.models_dir = self.artifacts_dir / "models"
        self.reports_dir = self.artifacts_dir / "reports"
        
        for dir_path in [self.plots_dir, self.metrics_dir, self.models_dir, self.reports_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # История обучения
        self.training_history = {
            'train_loss': [],
            'val_loss': [],
            'train_accuracy': [],
            'val_accuracy': [],
            'learning_rate': [],
            'epoch': [],
            'timestamp': []
        }
        
        # Метрики по эпохам
        self.epoch_metrics = []
        
        # Информация об обучении
        self.training_info = {
            'start_time': None,
            'end_time': None,
            'total_epochs': 0,
            'best_epoch': 0,
            'best_val_loss': float('inf'),
            'best_val_accuracy': 0.0,
            'early_stopped': False,
            'final_model_path': None
        }
    
    def log_epoch(self, epoch: int, train_loss: float, val_loss: float,
                  train_accuracy: float, val_accuracy: float, 
                  learning_rate: float, additional_metrics: Dict = None):
        """
        Логирование метрик эпохи
        
        Args:
            epoch: Номер эпохи
            train_loss: Потери на обучении
            val_loss: Потери на валидации
            train_accuracy: Точность на обучении
            val_accuracy: Точность на валидации
            learning_rate: Текущий learning rate
            additional_metrics: Дополнительные метрики
        """
        timestamp = datetime.now()
        
        # Обновление истории
        self.training_history['epoch'].append(epoch)
        self.training_history['train_loss'].append(train_loss)
        self.training_history['val_loss'].append(val_loss)
        self.training_history['train_accuracy'].append(train_accuracy)
        self.training_history['val_accuracy'].append(val_accuracy)
        self.training_history['learning_rate'].append(learning_rate)
        self.training_history['timestamp'].append(timestamp.isoformat())
        
        # Сохранение метрик эпохи
        epoch_data = {
            'epoch': epoch,
            'train_loss': train_loss,
            'val_loss': val_loss,
            'train_accuracy': train_accuracy,
            'val_accuracy': val_accuracy,
            'learning_rate': learning_rate,
            'timestamp': timestamp.isoformat()
        }
        
        if additional_metrics:
            epoch_data.update(additional_metrics)
        
        self.epoch_metrics.append(epoch_data)
        
        # Обновление лучших метрик
        if val_loss < self.training_info['best_val_loss']:
            self.training_info['best_val_loss'] = val_loss
            self.training_info['best_epoch'] = epoch
        
        if val_accuracy > self.training_info['best_val_accuracy']:
            self.training_info['best_val_accuracy'] = val_accuracy
    
    def create_training_curves(self, save_plot: bool = True) -> go.Figure:
        """
        Создание графиков кривых обучения
        
        Args:
            save_plot: Сохранить график в файл
            
        Returns:
            Plotly Figure объект
        """
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Функция потерь', 'Точность', 'Learning Rate', 'Сравнение метрик'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": True}]]
        )
        
        epochs = self.training_history['epoch']
        
        # График потерь
        fig.add_trace(
            go.Scatter(x=epochs, y=self.training_history['train_loss'],
                      name='Train Loss', line=dict(color='blue')),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=epochs, y=self.training_history['val_loss'],
                      name='Val Loss', line=dict(color='red')),
            row=1, col=1
        )
        
        # График точности
        fig.add_trace(
            go.Scatter(x=epochs, y=self.training_history['train_accuracy'],
                      name='Train Accuracy', line=dict(color='green')),
            row=1, col=2
        )
        fig.add_trace(
            go.Scatter(x=epochs, y=self.training_history['val_accuracy'],
                      name='Val Accuracy', line=dict(color='orange')),
            row=1, col=2
        )
        
        # График learning rate
        fig.add_trace(
            go.Scatter(x=epochs, y=self.training_history['learning_rate'],
                      name='Learning Rate', line=dict(color='purple')),
            row=2, col=1
        )
        
        # Комбинированный график
        fig.add_trace(
            go.Scatter(x=epochs, y=self.training_history['val_loss'],
                      name='Val Loss', line=dict(color='red')),
            row=2, col=2
        )
        fig.add_trace(
            go.Scatter(x=epochs, y=self.training_history['val_accuracy'],
                      name='Val Accuracy', line=dict(color='orange'),
                      yaxis='y2'),
            row=2, col=2, secondary_y=True
        )
        
        # Обновление макетов
        fig.update_xaxes(title_text="Эпоха")
        fig.update_yaxes(title_text="Потери", row=1, col=1)
        fig.update_yaxes(title_text="Точность", row=1, col=2)
        fig.update_yaxes(title_text="Learning Rate", row=2, col=1)
        fig.update_yaxes(title_text="Потери", row=2, col=2)
        fig.update_yaxes(title_text="Точность", row=2, col=2, secondary_y=True)
        
        fig.update_layout(
            title_text="Кривые обучения DKN модели",
            showlegend=True,
            height=800
        )
        
        if save_plot:
            plot_path = self.plots_dir / "training_curves.html"
            fig.write_html(str(plot_path))
            
            # Также сохраним PNG версию
            png_path = self.plots_dir / "training_curves.png"
            pio.write_image(fig, str(png_path), width=1200, height=800)
        
        return fig
    
    def create_metrics_dashboard(self, test_predictions: np.ndarray = None,
                               test_targets: np.ndarray = None,
                               save_plot: bool = True) -> go.Figure:
        """
        Создание дашборда с метриками модели
        
        Args:
            test_predictions: Предсказания на тестовой выборке
            test_targets: Целевые значения тестовой выборки
            save_plot: Сохранить график в файл
            
        Returns:
            Plotly Figure объект
        """
        if test_predictions is not None and test_targets is not None:
            # ROC кривая
            fpr, tpr, _ = roc_curve(test_targets, test_predictions)
            roc_auc = auc(fpr, tpr)
            
            # Precision-Recall кривая
            precision, recall, _ = precision_recall_curve(test_targets, test_predictions)
            pr_auc = auc(recall, precision)
            
            # Матрица ошибок
            y_pred_binary = (test_predictions > 0.5).astype(int)
            cm = confusion_matrix(test_targets, y_pred_binary)
            
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('ROC Кривая', 'Precision-Recall Кривая', 
                              'Матрица ошибок', 'Распределение предсказаний'),
                specs=[[{"type": "scatter"}, {"type": "scatter"}],
                       [{"type": "heatmap"}, {"type": "histogram"}]]
            )
            
            # ROC кривая
            fig.add_trace(
                go.Scatter(x=fpr, y=tpr,
                          name=f'ROC (AUC = {roc_auc:.3f})',
                          line=dict(color='blue')),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(x=[0, 1], y=[0, 1],
                          name='Случайный классификатор',
                          line=dict(color='red', dash='dash')),
                row=1, col=1
            )
            
            # Precision-Recall кривая
            fig.add_trace(
                go.Scatter(x=recall, y=precision,
                          name=f'PR (AUC = {pr_auc:.3f})',
                          line=dict(color='green')),
                row=1, col=2
            )
            
            # Матрица ошибок
            fig.add_trace(
                go.Heatmap(z=cm, x=['Predicted 0', 'Predicted 1'],
                          y=['Actual 0', 'Actual 1'],
                          colorscale='Blues', showscale=True),
                row=2, col=1
            )
            
            # Распределение предсказаний
            fig.add_trace(
                go.Histogram(x=test_predictions[test_targets == 0],
                           name='Класс 0', opacity=0.7, nbinsx=50),
                row=2, col=2
            )
            fig.add_trace(
                go.Histogram(x=test_predictions[test_targets == 1],
                           name='Класс 1', opacity=0.7, nbinsx=50),
                row=2, col=2
            )
        else:
            # Если нет тестовых данных, показываем только историю обучения
            fig = make_subplots(
                rows=1, cols=2,
                subplot_titles=('История потерь', 'История точности')
            )
            
            epochs = self.training_history['epoch']
            
            fig.add_trace(
                go.Scatter(x=epochs, y=self.training_history['train_loss'],
                          name='Train Loss', line=dict(color='blue')),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(x=epochs, y=self.training_history['val_loss'],
                          name='Val Loss', line=dict(color='red')),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Scatter(x=epochs, y=self.training_history['train_accuracy'],
                          name='Train Accuracy', line=dict(color='green')),
                row=1, col=2
            )
            fig.add_trace(
                go.Scatter(x=epochs, y=self.training_history['val_accuracy'],
                          name='Val Accuracy', line=dict(color='orange')),
                row=1, col=2
            )
        
        fig.update_layout(
            title_text="Дашборд метрик DKN модели",
            showlegend=True,
            height=800
        )
        
        if save_plot:
            plot_path = self.plots_dir / "metrics_dashboard.html"
            fig.write_html(str(plot_path))
            
            png_path = self.plots_dir / "metrics_dashboard.png"
            pio.write_image(fig, str(png_path), width=1200, height=800)
        
        return fig
    
    def save_training_statistics(self, additional_stats: Dict = None):
        """
        Сохранение статистики обучения в JSON файл
        
        Args:
            additional_stats: Дополнительные статистики для сохранения
        """
        stats = {
            'training_info': self.training_info,
            'training_history': self.training_history,
            'final_metrics': {
                'best_val_loss': self.training_info['best_val_loss'],
                'best_val_accuracy': self.training_info['best_val_accuracy'],
                'best_epoch': self.training_info['best_epoch'],
                'total_epochs': len(self.training_history['epoch'])
            }
        }
        
        if additional_stats:
            stats.update(additional_stats)
        
        stats_path = self.metrics_dir / "training_statistics.json"
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
    
    def save_epoch_metrics(self):
        """Сохранение метрик по эпохам в CSV файл"""
        df = pd.DataFrame(self.epoch_metrics)
        csv_path = self.metrics_dir / "epoch_metrics.csv"
        df.to_csv(csv_path, index=False)
    
    def generate_training_report(self, model_config: Dict = None,
                               dataset_info: Dict = None,
                               test_metrics: Dict = None) -> str:
        """
        Генерация детального отчета об обучении
        
        Args:
            model_config: Конфигурация модели
            dataset_info: Информация о датасете
            test_metrics: Метрики на тестовой выборке
            
        Returns:
            Путь к созданному отчету
        """
        report_content = self._create_report_content(
            model_config, dataset_info, test_metrics
        )
        
        report_path = self.reports_dir / "training_report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return str(report_path)
    
    def _create_report_content(self, model_config: Dict = None,
                             dataset_info: Dict = None,
                             test_metrics: Dict = None) -> str:
        """Создание содержимого отчета об обучении"""
        
        start_time = self.training_info.get('start_time', 'N/A')
        end_time = self.training_info.get('end_time', 'N/A')
        
        if start_time != 'N/A' and end_time != 'N/A':
            duration = pd.to_datetime(end_time) - pd.to_datetime(start_time)
            duration_str = str(duration)
        else:
            duration_str = 'N/A'
        
        report = f"""# Отчет об обучении DKN модели

## 📊 Основная информация

**Дата создания отчета**: {datetime.now().strftime('%d.%m.%Y %H:%M')}
**Время начала обучения**: {start_time}
**Время окончания обучения**: {end_time}
**Продолжительность**: {duration_str}

## 🎯 Результаты обучения

### Лучшие метрики
- **Лучшая эпоха**: {self.training_info['best_epoch']}
- **Лучшие потери на валидации**: {self.training_info['best_val_loss']:.6f}
- **Лучшая точность на валидации**: {self.training_info['best_val_accuracy']:.4f}
- **Общее количество эпох**: {len(self.training_history['epoch'])}
- **Early stopping**: {'Да' if self.training_info.get('early_stopped', False) else 'Нет'}

### Финальные метрики
- **Финальные потери на обучении**: {self.training_history['train_loss'][-1]:.6f if self.training_history['train_loss'] else 'N/A'}
- **Финальные потери на валидации**: {self.training_history['val_loss'][-1]:.6f if self.training_history['val_loss'] else 'N/A'}
- **Финальная точность на обучении**: {self.training_history['train_accuracy'][-1]:.4f if self.training_history['train_accuracy'] else 'N/A'}
- **Финальная точность на валидации**: {self.training_history['val_accuracy'][-1]:.4f if self.training_history['val_accuracy'] else 'N/A'}

"""

        # Конфигурация модели
        if model_config:
            report += f"""## ⚙️ Конфигурация модели

```json
{json.dumps(model_config, indent=2, ensure_ascii=False)}
```

"""

        # Информация о датасете
        if dataset_info:
            report += f"""## 📚 Информация о датасете

```json
{json.dumps(dataset_info, indent=2, ensure_ascii=False)}
```

"""

        # Тестовые метрики
        if test_metrics:
            report += f"""## 🧪 Метрики на тестовой выборке

```json
{json.dumps(test_metrics, indent=2, ensure_ascii=False)}
```

"""

        # Файлы артефактов
        report += f"""## 📁 Артефакты обучения

### Визуализации
- `plots/training_curves.html` - Интерактивные кривые обучения
- `plots/training_curves.png` - Кривые обучения (PNG)
- `plots/metrics_dashboard.html` - Дашборд метрик
- `plots/metrics_dashboard.png` - Дашборд метрик (PNG)

### Метрики и статистика
- `metrics/training_statistics.json` - Полная статистика обучения
- `metrics/epoch_metrics.csv` - Метрики по эпохам

### Модели
- `models/best_model.pth` - Лучшая модель
- `models/final_model.pth` - Финальная модель
- `models/model_config.json` - Конфигурация модели

### Отчеты
- `reports/training_report.md` - Этот отчет

## 📈 Анализ обучения

### Сходимость
{'Модель успешно сошлась' if self.training_info['best_val_loss'] < float('inf') else 'Проблемы со сходимостью'}

### Переобучение
{self._analyze_overfitting()}

### Рекомендации
{self._generate_recommendations()}

---

*Отчет сгенерирован автоматически системой TrainingArtifactsCollector*
"""

        return report
    
    def _analyze_overfitting(self) -> str:
        """Анализ переобучения"""
        if not self.training_history['train_loss'] or not self.training_history['val_loss']:
            return "Недостаточно данных для анализа"
        
        final_train_loss = self.training_history['train_loss'][-1]
        final_val_loss = self.training_history['val_loss'][-1]
        
        if final_val_loss > final_train_loss * 1.2:
            return "⚠️ Возможно переобучение - валидационные потери значительно выше обучающих"
        elif final_val_loss > final_train_loss * 1.1:
            return "⚠️ Легкие признаки переобучения"
        else:
            return "✅ Признаков переобучения не обнаружено"
    
    def _generate_recommendations(self) -> str:
        """Генерация рекомендаций"""
        recommendations = []
        
        if not self.training_history['val_accuracy']:
            return "Недостаточно данных для рекомендаций"
        
        best_val_acc = max(self.training_history['val_accuracy'])
        
        if best_val_acc < 0.6:
            recommendations.append("• Рассмотрите увеличение размера модели или улучшение архитектуры")
        
        if self.training_info.get('early_stopped', False):
            recommendations.append("• Обучение было остановлено early stopping - возможно стоит увеличить patience")
        
        if len(self.training_history['epoch']) < 10:
            recommendations.append("• Обучение было коротким - рассмотрите увеличение количества эпох")
        
        final_train_loss = self.training_history['train_loss'][-1]
        final_val_loss = self.training_history['val_loss'][-1]
        
        if final_val_loss > final_train_loss * 1.2:
            recommendations.append("• Добавьте регуляризацию или dropout для борьбы с переобучением")
        
        if not recommendations:
            recommendations.append("• Обучение прошло успешно, дополнительных рекомендаций нет")
        
        return "\n".join(recommendations)
    
    def finalize_training(self, end_time: str = None, early_stopped: bool = False):
        """
        Финализация процесса обучения
        
        Args:
            end_time: Время окончания обучения
            early_stopped: Было ли обучение остановлено early stopping
        """
        self.training_info['end_time'] = end_time or datetime.now().isoformat()
        self.training_info['early_stopped'] = early_stopped
        self.training_info['total_epochs'] = len(self.training_history['epoch'])
        
        # Сохранение всех артефактов
        self.save_training_statistics()
        self.save_epoch_metrics()
        self.create_training_curves()
        self.create_metrics_dashboard()
    
    def set_training_start(self, start_time: str = None):
        """
        Установка времени начала обучения
        
        Args:
            start_time: Время начала обучения
        """
        self.training_info['start_time'] = start_time or datetime.now().isoformat()


def create_training_artifacts_collector(artifacts_dir: str = "mlmodels/dkn/training") -> TrainingArtifactsCollector:
    """
    Фабричная функция для создания коллектора артефактов
    
    Args:
        artifacts_dir: Директория для сохранения артефактов
        
    Returns:
        Настроенный TrainingArtifactsCollector
    """
    return TrainingArtifactsCollector(artifacts_dir)
