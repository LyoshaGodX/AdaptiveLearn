"""
DQN Trainer - Тренер для обучения модели DQN с подкреплением

Реализует:
- Обучение DQN модели на основе экспертной обратной связи
- Оптимизацию с помощью градиентного спуска
- Сохранение и загрузку моделей
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from typing import Tuple, List, Optional
import os

from .model import DQNAgent, DQNConfig


class DQNTrainer:
    """Тренер для обучения DQN модели"""
    
    def __init__(self, state_dim: int, action_dim: int, 
                 learning_rate: float = 1e-4, gamma: float = 0.99):
        """
        Args:
            state_dim: Размерность вектора состояния
            action_dim: Количество возможных действий
            learning_rate: Скорость обучения
            gamma: Коэффициент дисконтирования
        """
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.learning_rate = learning_rate
        self.gamma = gamma
        
        # Инициализируем модель
        # Создаем конфигурацию и модель
        config = DQNConfig()
        config.num_actions = action_dim
        self.model = DQNAgent(config, num_skills=state_dim)
        
        # Оптимизатор
        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        
        # Функция потерь
        self.criterion = nn.MSELoss()
        
        # Устройство для вычислений
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
          # Инициализация параметров
    
    def train_step(self, states: torch.Tensor, actions: torch.Tensor, 
                  rewards: torch.Tensor) -> float:
        """
        Выполняет один шаг обучения
        
        Args:
            states: Батч состояний [batch_size, state_dim]
            actions: Батч действий [batch_size]
            rewards: Батч наград [batch_size]
            
        Returns:
            Значение функции потерь
        """
        # Переводим на устройство
        states = states.to(self.device)
        actions = actions.to(self.device)
        rewards = rewards.to(self.device)
        
        # Предсказываем Q-values для всех действий
        q_values = self.model.q_network(states)  # [batch_size, action_dim]
        
        # Получаем Q-values для выбранных действий
        selected_q_values = q_values.gather(1, actions.unsqueeze(1)).squeeze(1)
        
        # Целевые Q-values равны наградам (упрощенная версия без следующего состояния)
        target_q_values = rewards
        
        # Вычисляем потерю
        loss = self.criterion(selected_q_values, target_q_values)
        
        # Обратное распространение
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        return loss.item()
    
    def train_batch(self, training_examples: List[dict], batch_size: int = 32) -> List[float]:
        """
        Обучает модель на батче примеров
        
        Args:
            training_examples: Список обучающих примеров
            batch_size: Размер батча
            
        Returns:
            Список значений потерь для каждого батча
        """
        losses = []
        
        # Разбиваем на батчи
        for i in range(0, len(training_examples), batch_size):
            batch = training_examples[i:i + batch_size]
            
            # Конвертируем в тензоры
            states, actions, rewards = self._convert_batch_to_tensors(batch)
            
            # Обучающий шаг
            loss = self.train_step(states, actions, rewards)
            losses.append(loss)
        
        return losses
    
    def evaluate(self, states: torch.Tensor, actions: torch.Tensor, 
                rewards: torch.Tensor) -> dict:
        """
        Оценивает модель на тестовых данных
        
        Args:
            states: Тестовые состояния
            actions: Тестовые действия
            rewards: Тестовые награды
            
        Returns:
            Словарь с метриками оценки
        """
        self.model.eval()
        
        with torch.no_grad():
            states = states.to(self.device)
            actions = actions.to(self.device)
            rewards = rewards.to(self.device)
            
            # Предсказания
            q_values = self.model.q_network(states)
            selected_q_values = q_values.gather(1, actions.unsqueeze(1)).squeeze(1)
            
            # Метрики
            mse_loss = self.criterion(selected_q_values, rewards).item()
            mae_loss = torch.mean(torch.abs(selected_q_values - rewards)).item()
            
            # Точность предсказания знака (положительная/отрицательная награда)
            predicted_signs = torch.sign(selected_q_values)
            actual_signs = torch.sign(rewards)
            sign_accuracy = (predicted_signs == actual_signs).float().mean().item()
        
        self.model.train()
        
        return {
            'mse_loss': mse_loss,
            'mae_loss': mae_loss,
            'sign_accuracy': sign_accuracy,
            'avg_predicted_q': selected_q_values.mean().item(),
            'avg_actual_reward': rewards.mean().item()        }
    
    def save_model(self, path: str):
        """
        Сохраняет модель
        
        Args:
            path: Путь для сохранения
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        checkpoint = {
            'model_state_dict': self.model.q_network.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'state_dim': self.state_dim,
            'action_dim': self.action_dim,
            'learning_rate': self.learning_rate,
            'gamma': self.gamma        }
        
        torch.save(checkpoint, path)
    
    def load_model(self, path: str):
        """
        Загружает модель
        
        Args:
            path: Путь к модели
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Модель не найдена: {path}")
        
        checkpoint = torch.load(path, map_location=self.device)
        
        # Проверяем совместимость размерностей
        if (checkpoint['state_dim'] != self.state_dim or 
            checkpoint['action_dim'] != self.action_dim):
            raise ValueError(
                f"Несовместимые размерности модели: "
                f"ожидается ({self.state_dim}, {self.action_dim}), "
                f"найдено ({checkpoint['state_dim']}, {checkpoint['action_dim']})"
            )
        
        # Загружаем веса        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
    
    def get_model_info(self) -> dict:
        """Возвращает информацию о модели"""
        return {
            'state_dim': self.state_dim,
            'action_dim': self.action_dim,
            'learning_rate': self.learning_rate,
            'gamma': self.gamma,
            'device': str(self.device),
            'model_parameters': sum(p.numel() for p in self.model.parameters()),
            'trainable_parameters': sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        }
    
    def _convert_batch_to_tensors(self, batch: List[dict]) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Конвертирует батч примеров в тензоры"""
        states = []
        actions = []
        rewards = []
        
        for example in batch:
            # Состояние: конкатенация BKT, истории и графа
            state = example['state']
            bkt = torch.tensor(state['bkt_params'], dtype=torch.float32)
            history = torch.tensor(state['history'], dtype=torch.float32)
            graph = torch.tensor(state['skills_graph'], dtype=torch.float32)
            
            # Объединяем в один вектор состояния
            combined_state = torch.cat([
                bkt.flatten(),
                history.flatten(),
                graph.flatten()
            ])
            
            states.append(combined_state)
            actions.append(example['action'])
            rewards.append(example['reward'])
        
        return (
            torch.stack(states),
            torch.tensor(actions, dtype=torch.long),
            torch.tensor(rewards, dtype=torch.float32)
        )
    
    def set_learning_rate(self, lr: float):
        """Устанавливает новую скорость обучения"""
        self.learning_rate = lr
        
        for param_group in self.optimizer.param_groups:
            param_group['lr'] = lr
    
    def get_learning_rate(self) -> float:
        """Возвращает текущую скорость обучения"""
        return self.optimizer.param_groups[0]['lr']


class ReplayBuffer:
    """Буфер воспроизведения для DQN (если потребуется в будущем)"""
    
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.buffer = []
        self.position = 0
    
    def push(self, state, action, reward, next_state, done):
        """Добавляет опыт в буфер"""
        if len(self.buffer) < self.capacity:
            self.buffer.append(None)
        
        self.buffer[self.position] = (state, action, reward, next_state, done)
        self.position = (self.position + 1) % self.capacity
    
    def sample(self, batch_size: int):
        """Возвращает случайную выборку из буфера"""
        import random
        return random.sample(self.buffer, batch_size)
    
    def __len__(self):
        return len(self.buffer)
