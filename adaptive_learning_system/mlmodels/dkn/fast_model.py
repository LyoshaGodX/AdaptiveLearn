"""
Упрощенная и быстрая версия DKN модели
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, Optional


class FastDKNConfig:
    """Упрощенная конфигурация для быстрой модели"""
    
    def __init__(self):
        # Минимальные размерности для скорости
        self.skill_embedding_dim = 16
        self.task_embedding_dim = 16  
        self.student_state_dim = 8
        self.hidden_dim = 32
        self.output_dim = 1
        
        # Оптимизированные гиперпараметры
        self.dropout_rate = 0.2
        self.learning_rate = 0.005  # Более высокий LR
        self.batch_size = 64
        self.max_history_length = 5  # Сокращенная история


class SimplifiedSkillEmbedding(nn.Module):
    """Упрощенные эмбеддинги навыков"""
    
    def __init__(self, num_skills: int, embedding_dim: int):
        super().__init__()
        self.num_skills = num_skills
        self.embedding_dim = embedding_dim
        
        # Только основные эмбеддинги
        self.skill_embeddings = nn.Embedding(num_skills, embedding_dim)
        
        # Простая обработка BKT параметров
        self.bkt_processor = nn.Linear(4, embedding_dim // 2)
        
        # Объединение
        self.combiner = nn.Linear(embedding_dim + embedding_dim // 2, embedding_dim)
        
    def forward(self, skill_ids: torch.Tensor, bkt_params: torch.Tensor) -> torch.Tensor:
        batch_size = skill_ids.size(0)
        
        # Эмбеддинги навыков
        skill_emb = self.skill_embeddings(skill_ids)  # [batch, num_skills, emb_dim]
        
        # BKT параметры
        bkt_features = self.bkt_processor(bkt_params)  # [batch, num_skills, emb_dim//2]
        
        # Простое объединение
        combined = torch.cat([skill_emb, bkt_features], dim=-1)
        output = self.combiner(combined)
        
        return torch.tanh(output)


class SimplifiedTaskEmbedding(nn.Module):
    """Упрощенные эмбеддинги заданий"""
    
    def __init__(self, num_tasks: int, embedding_dim: int):
        super().__init__()
        self.task_embeddings = nn.Embedding(num_tasks, embedding_dim)
        self.difficulty_embedding = nn.Embedding(3, 8)
        self.type_embedding = nn.Embedding(3, 8)
        
        # Простое объединение
        self.combiner = nn.Linear(embedding_dim + 16, embedding_dim)
        
    def forward(self, task_ids: torch.Tensor, difficulty: torch.Tensor, 
                task_type: torch.Tensor) -> torch.Tensor:
        
        task_emb = self.task_embeddings(task_ids)
        diff_emb = self.difficulty_embedding(difficulty)
        type_emb = self.type_embedding(task_type)
        
        # Объединение характеристик
        features = torch.cat([diff_emb, type_emb], dim=-1)
        combined = torch.cat([task_emb, features], dim=-1)
        
        return torch.tanh(self.combiner(combined))


class SimplifiedStudentEncoder(nn.Module):
    """Упрощенный кодировщик состояния студента"""
    
    def __init__(self, config: FastDKNConfig):
        super().__init__()
        self.config = config
        
        # Простая обработка истории (без LSTM для скорости)
        self.history_processor = nn.Sequential(
            nn.Linear(10 * 5, config.student_state_dim),  # 10 features * 5 history entries
            nn.ReLU(),
            nn.Dropout(config.dropout_rate)
        )
        
        # Обработка текущего состояния BKT
        self.bkt_processor = nn.Sequential(
            nn.Linear(4, config.student_state_dim),
            nn.ReLU()
        )
        
        # Простое объединение
        self.combiner = nn.Linear(config.student_state_dim * 2, config.student_state_dim)
        
    def forward(self, history: torch.Tensor, current_bkt: torch.Tensor) -> torch.Tensor:
        batch_size = history.size(0)
        
        # Простое разворачивание истории
        history_flat = history.view(batch_size, -1)
        history_features = self.history_processor(history_flat)
        
        # BKT состояние
        bkt_features = self.bkt_processor(current_bkt)
        
        # Объединение
        combined = torch.cat([history_features, bkt_features], dim=-1)
        return torch.tanh(self.combiner(combined))


class FastDKNModel(nn.Module):
    """Быстрая упрощенная DKN модель"""
    
    def __init__(self, num_skills: int, num_tasks: int, config: FastDKNConfig):
        super().__init__()
        self.config = config
        self.num_skills = num_skills
        self.num_tasks = num_tasks
        
        # Упрощенные компоненты
        self.skill_embedding = SimplifiedSkillEmbedding(num_skills, config.skill_embedding_dim)
        self.task_embedding = SimplifiedTaskEmbedding(num_tasks, config.task_embedding_dim)
        self.student_encoder = SimplifiedStudentEncoder(config)
        
        # Простой предиктор
        self.predictor = nn.Sequential(
            nn.Linear(
                config.skill_embedding_dim + config.task_embedding_dim + config.student_state_dim,
                config.hidden_dim
            ),
            nn.ReLU(),
            nn.Dropout(config.dropout_rate),
            nn.Linear(config.hidden_dim, config.output_dim),
            nn.Sigmoid()
        )
        
    def forward(self, batch) -> torch.Tensor:
        # Извлекаем данные
        skill_ids = batch['skill_ids']
        bkt_params = batch['bkt_params']
        task_ids = batch['task_ids']
        task_difficulty = batch['task_difficulty']
        task_type = batch['task_type']
        student_history = batch['student_history']
        current_bkt_avg = batch['current_bkt_avg']
        
        # Эмбеддинги
        skill_embeddings = self.skill_embedding(skill_ids, bkt_params)
        task_embeddings = self.task_embedding(task_ids, task_difficulty, task_type)
        student_state = self.student_encoder(student_history, current_bkt_avg)
        
        # Усреднение навыков (простое)
        skill_mask = batch.get('skill_mask', None)
        if skill_mask is not None:
            skill_avg = (skill_embeddings * skill_mask.unsqueeze(-1)).sum(dim=1) / skill_mask.sum(dim=1, keepdim=True)
        else:
            skill_avg = skill_embeddings.mean(dim=1)
        
        # Объединение и предсказание
        combined = torch.cat([skill_avg, task_embeddings, student_state], dim=-1)
        prediction = self.predictor(combined)
        
        return prediction.squeeze(-1)
