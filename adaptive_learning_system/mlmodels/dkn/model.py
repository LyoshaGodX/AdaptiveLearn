"""
Deep Knowledge Network (DKN) модель для рекомендации заданий

DKN использует:
1. Текущие BKT параметры студента (вероятности освоения навыков)
2. Характеристики заданий (сложность, навыки, тип)
3. Историю попыток студента
4. Граф зависимостей навыков

Для предсказания оптимального следующего задания
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple, Optional
import json
from pathlib import Path


class DKNConfig:
    """Конфигурация DKN модели"""
    
    def __init__(self):
        # Размерности
        self.skill_embedding_dim = 64
        self.task_embedding_dim = 64
        self.student_state_dim = 32
        self.hidden_dim = 256  # Было 128, но обученная модель использует 256
        self.output_dim = 1  # Вероятность успеха для задания
        
        # Гиперпараметры
        self.dropout_rate = 0.2
        self.learning_rate = 0.001
        self.batch_size = 32
        self.max_history_length = 50
        
        # Веса для разных компонентов
        self.bkt_weight = 0.4      # Вес BKT данных
        self.task_weight = 0.3     # Вес характеристик задания
        self.history_weight = 0.2  # Вес истории попыток
        self.graph_weight = 0.1    # Вес графа навыков


class SkillEmbedding(nn.Module):
    """Эмбеддинги для навыков с учетом их характеристик"""
    
    def __init__(self, num_skills: int, embedding_dim: int):
        super().__init__()
        self.num_skills = num_skills
        self.embedding_dim = embedding_dim
        
        # Основные эмбеддинги навыков
        self.skill_embeddings = nn.Embedding(num_skills, embedding_dim)
        
        # Дополнительные характеристики навыков
        self.skill_features = nn.Linear(4, embedding_dim // 4)  # 4 BKT параметра
        
        # Объединение
        self.fusion = nn.Linear(embedding_dim + embedding_dim // 4, embedding_dim)
        
    def forward(self, skill_ids: torch.Tensor, bkt_params: torch.Tensor) -> torch.Tensor:
        """
        Args:
            skill_ids: [batch_size, num_skills] - ID навыков
            bkt_params: [batch_size, num_skills, 4] - BKT параметры (P_L, P_T, P_G, P_S)
        """
        # Базовые эмбеддинги
        skill_emb = self.skill_embeddings(skill_ids)  # [batch_size, num_skills, embedding_dim]
        
        # Обработка BKT параметров
        bkt_features = self.skill_features(bkt_params)  # [batch_size, num_skills, embedding_dim//4]
        
        # Объединение
        combined = torch.cat([skill_emb, bkt_features], dim=-1)
        output = self.fusion(combined)
        
        return torch.tanh(output)


class TaskEmbedding(nn.Module):
    """Эмбеддинги для заданий"""
    
    def __init__(self, num_tasks: int, embedding_dim: int, num_skills: int):
        super().__init__()
        self.num_tasks = num_tasks
        self.embedding_dim = embedding_dim
        
        # Основные эмбеддинги заданий
        self.task_embeddings = nn.Embedding(num_tasks, embedding_dim)
        
        # Характеристики заданий
        self.difficulty_embedding = nn.Embedding(3, 16)  # beginner, intermediate, advanced
        self.type_embedding = nn.Embedding(3, 16)        # single, multiple, true_false
        
        # Связи с навыками (многие ко многим)
        self.skill_attention = nn.MultiheadAttention(embedding_dim, num_heads=8, batch_first=True)
        
        # Объединение характеристик
        self.feature_fusion = nn.Linear(embedding_dim + 32, embedding_dim)
        
    def forward(self, task_ids: torch.Tensor, difficulty: torch.Tensor, 
                task_type: torch.Tensor, skill_embeddings: torch.Tensor) -> torch.Tensor:
        """
        Args:
            task_ids: [batch_size] - ID заданий
            difficulty: [batch_size] - уровень сложности
            task_type: [batch_size] - тип задания
            skill_embeddings: [batch_size, num_skills, skill_emb_dim] - эмбеддинги навыков
        """
        batch_size = task_ids.size(0)
        
        # Базовые эмбеддинги заданий
        task_emb = self.task_embeddings(task_ids)  # [batch_size, embedding_dim]
        
        # Характеристики
        diff_emb = self.difficulty_embedding(difficulty)  # [batch_size, 16]
        type_emb = self.type_embedding(task_type)         # [batch_size, 16]
        
        # Внимание к связанным навыкам
        task_emb_expanded = task_emb.unsqueeze(1)  # [batch_size, 1, embedding_dim]
        attended_skills, _ = self.skill_attention(
            task_emb_expanded, skill_embeddings, skill_embeddings
        )  # [batch_size, 1, embedding_dim]
        
        attended_skills = attended_skills.squeeze(1)  # [batch_size, embedding_dim]
        
        # Объединение всех характеристик
        features = torch.cat([diff_emb, type_emb], dim=-1)  # [batch_size, 32]
        combined = torch.cat([attended_skills, features], dim=-1)
        
        output = self.feature_fusion(combined)
        return torch.tanh(output)


class StudentStateEncoder(nn.Module):
    """Кодировщик текущего состояния студента"""
    
    def __init__(self, config: DKNConfig):
        super().__init__()
        self.config = config
        
        # Обработка истории попыток
        self.history_lstm = nn.LSTM(
            input_size=10,  # task_id, is_correct, time_spent, difficulty, type, 5 навыков
            hidden_size=config.student_state_dim,
            num_layers=2,
            batch_first=True,
            dropout=config.dropout_rate
        )
        
        # Обработка текущего состояния BKT
        self.bkt_processor = nn.Sequential(
            nn.Linear(4, config.student_state_dim),  # 4 BKT параметра
            nn.ReLU(),
            nn.Dropout(config.dropout_rate),
            nn.Linear(config.student_state_dim, config.student_state_dim)
        )
        
        # Объединение
        self.state_fusion = nn.Sequential(
            nn.Linear(config.student_state_dim * 2, config.student_state_dim),
            nn.Tanh()
        )
        
    def forward(self, history: torch.Tensor, current_bkt: torch.Tensor) -> torch.Tensor:
        """
        Args:
            history: [batch_size, seq_len, 10] - история попыток
            current_bkt: [batch_size, 4] - текущие усредненные BKT параметры
        """
        # Обработка истории
        lstm_out, (hidden, _) = self.history_lstm(history)
        history_state = hidden[-1]  # Берем последний скрытый слой
        
        # Обработка текущего состояния BKT
        bkt_state = self.bkt_processor(current_bkt)
        
        # Объединение
        combined_state = torch.cat([history_state, bkt_state], dim=-1)
        student_state = self.state_fusion(combined_state)
        
        return student_state


class DKNModel(nn.Module):
    """Основная DKN модель"""
    
    def __init__(self, num_skills: int, num_tasks: int, config: DKNConfig):
        super().__init__()
        self.config = config
        self.num_skills = num_skills
        self.num_tasks = num_tasks
        
        # Компоненты модели
        self.skill_embedding = SkillEmbedding(num_skills, config.skill_embedding_dim)
        self.task_embedding = TaskEmbedding(num_tasks, config.task_embedding_dim, num_skills)
        self.student_encoder = StudentStateEncoder(config)
        
        # Предсказание успеха для задания
        self.success_predictor = nn.Sequential(
            nn.Linear(
                config.skill_embedding_dim + config.task_embedding_dim + config.student_state_dim,
                config.hidden_dim
            ),
            nn.ReLU(),
            nn.Dropout(config.dropout_rate),
            nn.Linear(config.hidden_dim, config.hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(config.dropout_rate),
            nn.Linear(config.hidden_dim // 2, config.output_dim),
            nn.Sigmoid()
        )
        
    def forward(self, batch) -> torch.Tensor:
        """
        Args:
            batch: словарь с данными батча
        
        Returns:
            torch.Tensor: вероятности успеха для каждого задания [batch_size]
        """
        # Извлекаем данные из батча
        skill_ids = batch['skill_ids']
        bkt_params = batch['bkt_params']
        task_ids = batch['task_ids']
        task_difficulty = batch['task_difficulty']
        task_type = batch['task_type']
        student_history = batch['student_history']
        current_bkt_avg = batch['current_bkt_avg']
        
        # Получаем эмбеддинги навыков
        skill_embeddings = self.skill_embedding(skill_ids, bkt_params)
        
        # Усредняем эмбеддинги навыков для задания
        skill_mask = batch.get('skill_mask', None)
        if skill_mask is not None:
            # Маскируем неактивные навыки
            skill_embeddings = skill_embeddings * skill_mask.unsqueeze(-1)
            skill_avg = skill_embeddings.sum(dim=1) / skill_mask.sum(dim=1, keepdim=True)
        else:
            skill_avg = skill_embeddings.mean(dim=1)
        
        # Получаем эмбеддинги заданий
        task_embeddings = self.task_embedding(
            task_ids, task_difficulty, task_type, skill_embeddings
        )
        
        # Кодируем состояние студента
        student_state = self.student_encoder(student_history, current_bkt_avg)
        
        # Объединяем все для предсказания
        combined_features = torch.cat([
            skill_avg, task_embeddings, student_state
        ], dim=-1)
        
        # Предсказываем вероятность успеха
        success_prob = self.success_predictor(combined_features)
        
        return success_prob.squeeze(-1)


class DKNTrainer:
    """Тренировщик для DKN модели"""
    
    def __init__(self, model: DKNModel, config: DKNConfig):
        self.model = model
        self.config = config
        self.optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
        self.criterion = nn.BCELoss()
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Перемещаем модель на устройство
        self.model.to(self.device)
        
    def train_step(self, batch) -> float:
        """Один шаг обучения"""
        self.model.train()
        self.optimizer.zero_grad()
        
        # Перемещаем данные на устройство
        batch = {k: v.to(self.device) if isinstance(v, torch.Tensor) else v 
                for k, v in batch.items()}
        
        # Прямой проход
        predictions = self.model(batch)
        targets = batch['targets'].float()
        
        # Вычисляем потери
        loss = self.criterion(predictions, targets)
        
        # Обратный проход
        loss.backward()
        self.optimizer.step()
        
        return loss.item()
    
    def evaluate(self, dataloader) -> Dict[str, float]:
        """Оценка модели"""
        self.model.eval()
        total_loss = 0.0
        correct_predictions = 0
        total_predictions = 0
        
        with torch.no_grad():
            for batch in dataloader:
                # Перемещаем данные на устройство
                batch = {k: v.to(self.device) if isinstance(v, torch.Tensor) else v 
                        for k, v in batch.items()}
                
                predictions = self.model(batch)
                targets = batch['targets'].float()
                
                # Потери
                loss = self.criterion(predictions, targets)
                total_loss += loss.item()
                
                # Точность
                predicted_labels = (predictions > 0.5).float()
                correct_predictions += (predicted_labels == targets).sum().item()
                total_predictions += targets.size(0)
        
        avg_loss = total_loss / len(dataloader)
        accuracy = correct_predictions / total_predictions
        
        return {
            'loss': avg_loss,
            'accuracy': accuracy
        }
    
    def save_model(self, path: str):
        """Сохранение модели"""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'config': self.config.__dict__
        }, path)
    
    def load_model(self, path: str):
        """Загрузка модели"""
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        return checkpoint['config']


def create_dkn_model(num_skills: int, num_tasks: int, config: Optional[DKNConfig] = None) -> DKNModel:
    """Фабричная функция для создания DKN модели"""
    if config is None:
        config = DKNConfig()
    
    model = DKNModel(num_skills, num_tasks, config)
    return model
