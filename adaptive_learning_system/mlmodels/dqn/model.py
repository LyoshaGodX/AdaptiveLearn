"""
Deep Q-Network (DQN) модель для рекомендации заданий в адаптивной системе обучения

DQN использует Reinforcement Learning для обучения оптимальной политике
рекомендации заданий на основе:
1. Текущего состояния студента (BKT параметры, история попыток)
2. Множества доступных заданий с учётом графа навыков
3. Наградой за улучшение обучения студента
4. Q-learning с Experience Replay для стабильного обучения

Модель учитывает:
- Граф навыков и prerequisite ограничения
- BKT параметры для каждого навыка студента
- Историю попыток и успехов
- Параметры заданий (тип, сложность, навык)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple, Optional, NamedTuple
import json
import random
from collections import deque
from pathlib import Path


class DQNConfig:
    """Конфигурация DQN модели"""
    
    def __init__(self):
        # Размерности
        self.skill_embedding_dim = 64
        self.task_embedding_dim = 64
        self.student_state_dim = 128
        self.hidden_dim = 256
        self.num_actions = 270  # Количество доступных заданий
        
        # RL параметры
        self.gamma = 0.99          # Коэффициент скидки
        self.epsilon_start = 1.0   # Начальная вероятность exploration
        self.epsilon_end = 0.1     # Конечная вероятность exploration
        self.epsilon_decay = 0.995 # Скорость затухания epsilon
        self.learning_rate = 0.001
        self.batch_size = 32
        self.memory_size = 10000   # Размер replay buffer
        self.target_update = 100   # Частота обновления target network
        
        # Архитектура
        self.dropout_rate = 0.2
        self.max_history_length = 50
        
        # Веса компонентов награды
        self.success_weight = 1.0      # Вес за успешное выполнение
        self.skill_improvement_weight = 2.0  # Вес за улучшение навыков
        self.difficulty_match_weight = 0.5   # Вес за соответствие сложности
        self.prerequisite_penalty = -1.0    # Штраф за нарушение prerequisite


class Experience(NamedTuple):
    """Опыт для replay buffer"""
    state: torch.Tensor
    action: int
    reward: float
    next_state: torch.Tensor
    done: bool


class ReplayBuffer:
    """Буфер для хранения опыта в DQN"""
    
    def __init__(self, capacity: int):
        self.buffer = deque(maxlen=capacity)
    
    def push(self, experience: Experience):
        """Добавляет опыт в буфер"""
        self.buffer.append(experience)
    
    def sample(self, batch_size: int) -> List[Experience]:
        """Сэмплирует батч опыта"""
        return random.sample(self.buffer, batch_size)
    
    def __len__(self):
        return len(self.buffer)


class StudentStateEncoder(nn.Module):
    """Кодировщик состояния студента для DQN"""
    
    def __init__(self, config: DQNConfig, num_skills: int = 30):
        super().__init__()
        self.config = config
        self.num_skills = num_skills
          # Обработка BKT параметров (навыки) - только вероятность знания
        self.bkt_encoder = nn.Sequential(
            nn.Linear(1, 32),  # 1 BKT параметр (вероятность знания) -> 32 dim
            nn.ReLU(),
            nn.Dropout(config.dropout_rate)
        )
          # Обработка истории попыток
        self.history_lstm = nn.LSTM(
            input_size=7,  # task_id, success, difficulty, task_type, skill_level, time, streak (убрали mastery_change)
            hidden_size=64,
            num_layers=2,
            batch_first=True,
            dropout=config.dropout_rate if config.dropout_rate > 0 else 0.0
        )
        
        # Агрегация состояния студента
        self.state_aggregator = nn.Sequential(
            nn.Linear(32 * num_skills + 64, config.student_state_dim),  # num_skills * 32 + 64 история
            nn.ReLU(),
            nn.Dropout(config.dropout_rate),
            nn.Linear(config.student_state_dim, config.student_state_dim),
            nn.Tanh()
        )
    
    def forward(self, bkt_params: torch.Tensor, history: torch.Tensor) -> torch.Tensor:
        """
        Args:
            bkt_params: [batch_size, num_skills, 1] - BKT параметры (только вероятность знания)
            history: [batch_size, seq_len, 7] - история попыток студента
        
        Returns:
            state: [batch_size, student_state_dim] - закодированное состояние студента
        """
        batch_size = bkt_params.size(0)
        
        # Кодируем BKT параметры для каждого навыка
        bkt_encoded = self.bkt_encoder(bkt_params)  # [batch_size, num_skills, 32]
        bkt_flattened = bkt_encoded.view(batch_size, -1)  # [batch_size, num_skills * 32]
        
        # Кодируем историю
        if history.size(1) > 0:
            _, (hidden, _) = self.history_lstm(history)
            history_encoded = hidden[-1]  # [batch_size, 64]
        else:
            history_encoded = torch.zeros(batch_size, 64, device=bkt_params.device)
        
        # Объединяем
        combined = torch.cat([bkt_flattened, history_encoded], dim=1)
        state = self.state_aggregator(combined)
        
        return state


class DQNNetwork(nn.Module):
    """Deep Q-Network для рекомендации заданий"""
    
    def __init__(self, config: DQNConfig, num_skills: int = 30):
        super().__init__()
        self.config = config
        self.num_skills = num_skills
        
        # Кодировщик состояния студента
        self.state_encoder = StudentStateEncoder(config, num_skills)
        
        # Q-network для оценки действий (заданий)
        self.q_network = nn.Sequential(
            nn.Linear(config.student_state_dim, config.hidden_dim),
            nn.ReLU(),
            nn.Dropout(config.dropout_rate),
            nn.Linear(config.hidden_dim, config.hidden_dim),
            nn.ReLU(),
            nn.Dropout(config.dropout_rate),
            nn.Linear(config.hidden_dim, config.num_actions)  # Q-values для каждого задания
        )
        
    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """
        Args:
            state: [batch_size, student_state_dim] - состояние студента
        
        Returns:
            q_values: [batch_size, num_actions] - Q-values для каждого действия
        """
        q_values = self.q_network(state)
        return q_values
    
    def encode_state(self, bkt_params: torch.Tensor, history: torch.Tensor) -> torch.Tensor:
        """Кодирует состояние студента"""
        return self.state_encoder(bkt_params, history)


class DQNAgent:
    """DQN агент для рекомендации заданий"""
    
    def __init__(self, config: DQNConfig, num_skills: int = 30):
        self.config = config
        self.num_skills = num_skills
        # Используем CPU для стабильности
        self.device = torch.device('cpu')
        
        # Создаем основную и целевую сети
        self.q_network = DQNNetwork(config, num_skills).to(self.device)
        self.target_network = DQNNetwork(config, num_skills).to(self.device)
        
        # Синхронизируем веса
        self.target_network.load_state_dict(self.q_network.state_dict())
        
        # Оптимизатор
        self.optimizer = torch.optim.Adam(self.q_network.parameters(), lr=config.learning_rate)
        
        # Replay buffer
        self.memory = ReplayBuffer(config.memory_size)
        
        # Счетчики для обучения
        self.steps_done = 0
        self.epsilon = config.epsilon_start
        
    def select_action(self, state: torch.Tensor, available_actions: Optional[List[int]] = None) -> int:
        """
        Выбирает действие используя epsilon-greedy политику с учётом доступных действий
        
        Args:
            state: [student_state_dim] - состояние студента
            available_actions: список доступных действий (заданий) с учётом prerequisite
        
        Returns:
            action: выбранное действие (ID задания)
        """
        # Epsilon-greedy exploration
        if random.random() < self.epsilon:
            # Случайное действие (exploration) из доступных
            if available_actions:
                return random.choice(available_actions)
            else:
                return random.randint(0, self.config.num_actions - 1)
        else:
            # Жадное действие (exploitation)            with torch.no_grad():
                state = state.unsqueeze(0).to(self.device)  # [1, state_dim]
                q_values = self.q_network(state)  # [1, num_actions]
                
                if available_actions:
                    # Маскируем недоступные действия (нарушающие prerequisite)
                    masked_q_values = q_values.clone()
                    mask = torch.ones(self.config.num_actions, dtype=torch.bool)
                    mask[available_actions] = False  # Доступные действия НЕ маскируем
                    masked_q_values[0, mask] = float('-inf')  # Недоступные получают -inf
                    action = masked_q_values.argmax().item()
                else:
                    action = q_values.argmax().item()
                
                return action
    
    def store_experience(self, state: torch.Tensor, action: int, reward: float, 
                        next_state: torch.Tensor, done: bool):
        """Сохраняет опыт в replay buffer"""
        experience = Experience(state, action, reward, next_state, done)
        self.memory.push(experience)
    
    def learn(self):
        """Обучение DQN на батче из replay buffer"""
        if len(self.memory) < self.config.batch_size:
            return 0.0
        
        # Сэмплируем батч
        experiences = self.memory.sample(self.config.batch_size)
        
        # Разделяем компоненты
        states = torch.stack([e.state for e in experiences]).to(self.device)
        actions = torch.tensor([e.action for e in experiences], dtype=torch.long).to(self.device)
        rewards = torch.tensor([e.reward for e in experiences], dtype=torch.float).to(self.device)
        next_states = torch.stack([e.next_state for e in experiences]).to(self.device)
        dones = torch.tensor([e.done for e in experiences], dtype=torch.bool).to(self.device)
        
        # Текущие Q-values
        current_q_values = self.q_network(states).gather(1, actions.unsqueeze(1))
        
        # Следующие Q-values от target network
        with torch.no_grad():
            next_q_values = self.target_network(next_states).max(1)[0].detach()
            target_q_values = rewards + (self.config.gamma * next_q_values * ~dones)
        
        # Loss
        loss = F.mse_loss(current_q_values.squeeze(), target_q_values)
        
        # Обновляем сеть
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_network.parameters(), 1.0)
        self.optimizer.step()
        
        # Обновляем epsilon
        self.epsilon = max(self.config.epsilon_end, 
                          self.epsilon * self.config.epsilon_decay)
        
        # Обновляем target network
        self.steps_done += 1
        if self.steps_done % self.config.target_update == 0:
            self.target_network.load_state_dict(self.q_network.state_dict())
        
        return loss.item()
    
    def save_model(self, path: str):
        """Сохранение модели"""
        torch.save({
            'q_network_state_dict': self.q_network.state_dict(),
            'target_network_state_dict': self.target_network.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'config': self.config.__dict__,
            'num_skills': self.num_skills,
            'steps_done': self.steps_done,
            'epsilon': self.epsilon
        }, path)
    
    def load_model(self, path: str):
        """Загрузка модели"""
        checkpoint = torch.load(path, map_location=self.device)
        self.q_network.load_state_dict(checkpoint['q_network_state_dict'])
        self.target_network.load_state_dict(checkpoint['target_network_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.steps_done = checkpoint['steps_done']
        self.epsilon = checkpoint['epsilon']
        return checkpoint


def create_dqn_agent(config: Optional[DQNConfig] = None, num_skills: int = 30) -> DQNAgent:
    """Фабричная функция для создания DQN агента"""
    if config is None:
        config = DQNConfig()
    
    agent = DQNAgent(config, num_skills)
    return agent


def create_dqn_model(num_skills: int, num_tasks: int, config: Optional[DQNConfig] = None) -> DQNNetwork:
    """Фабричная функция для создания DQN модели"""
    if config is None:
        config = DQNConfig()
    
    # Обновляем конфигурацию с учетом параметров
    config.num_actions = num_tasks
    
    model = DQNNetwork(config, num_skills)
    return model
