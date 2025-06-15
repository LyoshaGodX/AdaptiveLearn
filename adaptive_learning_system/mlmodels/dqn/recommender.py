"""
DQN Рекомендательная система для адаптивного обучения

Этот модуль реализует рекоменда        # Загружаем модель если указан путь
        if model_path:
            try:
                self.agent.q_network.load_state_dict(torch.load(model_path))
                self.agent.q_network.eval()
            except Exception as e:
                pass
        
        # Переводим модель в режим оценки
        self.agent.q_network.eval()тему, которая:
1. Получает текущее состояние студента (BKT параметры, история, граф навыков)
2. Использует обученную DQN модель для получения рекомендаций
3. Возвращает детальную информацию о состоянии и рекомендованных заданиях
"""

import torch
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

# Django imports
from django.contrib.auth.models import User
from methodist.models import Task

# DQN imports
from .data_processor import DQNDataProcessor, DQNEnvironment
from .model import DQNConfig, create_dqn_agent


@dataclass
class StudentStateInfo:
    """Информация о состоянии студента"""
    student_id: int
    bkt_params: torch.Tensor
    history: torch.Tensor
    skills_graph: torch.Tensor
    available_actions: List[int]
    
    # Статистики
    total_skills: int
    high_mastery_skills: int    # > 0.8
    medium_mastery_skills: int  # 0.5 - 0.8
    low_mastery_skills: int     # < 0.5
    
    total_attempts: int
    success_rate: float
    avg_difficulty: float
    
    total_tasks: int
    available_tasks: int
    filtered_tasks: int


@dataclass
class TaskRecommendation:
    """Рекомендация задания"""
    task_id: int
    action_index: int
    q_value: float
    confidence: float
    
    # Информация о задании
    difficulty: str
    task_type: str
    skills: List[int]
    estimated_time: int
    
    # Причина рекомендации
    reason: str
    skill_match_score: float


@dataclass
class RecommendationResult:
    """Результат рекомендательной системы"""
    student_state: StudentStateInfo
    recommendations: List[TaskRecommendation]
    model_info: Dict
    timestamp: datetime


class DQNRecommender:
    """DQN рекомендательная система"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Args:
            model_path: путь к обученной модели (если None, используется случайная модель)
        """
        self.data_processor = DQNDataProcessor()
        self.model_path = model_path
        
        # Создаем DQN агента
        config = DQNConfig()
        config.num_actions = self.data_processor.get_num_tasks()
        num_skills = self.data_processor.get_num_skills()
        
        self.agent = create_dqn_agent(config, num_skills)        # Загружаем модель если указан путь
        if model_path:
            try:
                self.agent.q_network.load_state_dict(torch.load(model_path))
                self.agent.q_network.eval()
                print(f"✅ Модель загружена из {model_path}")
            except Exception as e:
                print(f"⚠️ Не удалось загрузить модель: {e}")
                print("🎯 Используется инициализированная модель DQN с базовыми весами")
        else:
            print("🎯 Используется инициализированная модель DQN с базовыми весами")
    
    def get_recommendations(self, student_id: int, top_k: int = 5) -> RecommendationResult:
        """
        Получает рекомендации для студента
        
        Args:
            student_id: ID студента
            top_k: количество рекомендаций
            
        Returns:
            RecommendationResult с полной информацией
        """
        # Получаем состояние студента
        state_data = self.data_processor.get_student_state(student_id)
        env = state_data['environment']
        
        # Анализируем состояние
        student_state = self._analyze_student_state(student_id, state_data)
        
        # Получаем рекомендации от DQN
        recommendations = self._get_dqn_recommendations(state_data, env, top_k)
        
        # Информация о модели
        model_info = {
            'model_type': 'DQN',
            'model_path': self.model_path,
            'num_skills': self.data_processor.get_num_skills(),
            'num_tasks': self.data_processor.get_num_tasks(),
            'state_dim': student_state.bkt_params.shape,
            'history_dim': student_state.history.shape,
            'graph_dim': student_state.skills_graph.shape
        }
        
        return RecommendationResult(
            student_state=student_state,
            recommendations=recommendations,
            model_info=model_info,
            timestamp=datetime.now()
        )
    
    def _analyze_student_state(self, student_id: int, state_data: Dict) -> StudentStateInfo:
        """Анализирует состояние студента"""
        bkt_params = state_data['bkt_params']
        history = state_data['history']
        skills_graph = state_data['skills_graph']
        available_actions = state_data['available_actions']
        
        # Анализ BKT параметров
        mastery_levels = bkt_params.squeeze().tolist()
        high_mastery = sum(1 for m in mastery_levels if m > 0.8)
        medium_mastery = sum(1 for m in mastery_levels if 0.5 <= m <= 0.8)
        low_mastery = sum(1 for m in mastery_levels if m < 0.5)
        
        # Анализ истории
        total_attempts = history.shape[0] if history.numel() > 0 else 0
        success_rate = 0.0
        avg_difficulty = 0.0
        
        if total_attempts > 0:
            success_rate = (history[:, 1] == 1.0).float().mean().item()
            avg_difficulty = history[:, 2].mean().item()
        
        # Анализ доступных заданий
        total_tasks = self.data_processor.get_num_tasks()
        available_tasks = len(available_actions)
        filtered_tasks = total_tasks - available_tasks
        
        return StudentStateInfo(
            student_id=student_id,
            bkt_params=bkt_params,
            history=history,
            skills_graph=skills_graph,
            available_actions=available_actions,
            total_skills=len(mastery_levels),
            high_mastery_skills=high_mastery,
            medium_mastery_skills=medium_mastery,
            low_mastery_skills=low_mastery,
            total_attempts=total_attempts,
            success_rate=success_rate,
            avg_difficulty=avg_difficulty,
            total_tasks=total_tasks,
            available_tasks=available_tasks,            filtered_tasks=filtered_tasks
        )
    
    def _get_dqn_recommendations(self, state_data: Dict, env: DQNEnvironment, top_k: int) -> List[TaskRecommendation]:
        """Получает рекомендации от DQN модели"""
        bkt_params = state_data['bkt_params'].unsqueeze(0)
        history = state_data['history'].unsqueeze(0)
        available_actions = state_data['available_actions']
        
        if not available_actions:
            return []
        
        try:
            # Кодируем состояние
            with torch.no_grad():
                encoded_state = self.agent.q_network.encode_state(bkt_params, history)
                q_values = self.agent.q_network(encoded_state)  # [1, num_actions]
            
            # Получаем Q-values для доступных действий
            recommendations = []
            available_q_values = []
            
            for action_idx in available_actions:
                q_val = q_values[0, action_idx].item()
                available_q_values.append((action_idx, q_val))
            
            # Сортируем по Q-value (убывание)
            available_q_values.sort(key=lambda x: x[1], reverse=True)
            
            # Создаем рекомендации для топ-k действий
            for i, (action_idx, q_val) in enumerate(available_q_values[:top_k]):
                task_id = env.action_to_task_id[action_idx]
                
                # Получаем информацию о задании
                task_info = self._get_task_info(task_id, env)
                
                # Вычисляем confidence (нормализованный Q-value)
                min_q = min(q for _, q in available_q_values)
                max_q = max(q for _, q in available_q_values)
                confidence = (q_val - min_q) / (max_q - min_q) if max_q > min_q else 1.0
                
                # Определяем причину рекомендации
                reason = self._get_recommendation_reason(task_info, state_data, i)
                
                # Вычисляем соответствие навыков
                skill_match_score = self._calculate_skill_match(task_info, bkt_params.squeeze())
                
                recommendation = TaskRecommendation(
                    task_id=task_id,
                    action_index=action_idx,
                    q_value=q_val,
                    confidence=confidence,
                    difficulty=task_info['difficulty'],
                    task_type=task_info['task_type'],
                    skills=task_info['skills'],
                    estimated_time=task_info['estimated_time'],
                    reason=reason,
                    skill_match_score=skill_match_score
                )
                
                recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            return []
    
    def _get_task_info(self, task_id: int, env: DQNEnvironment) -> Dict:
        """Получает информацию о задании"""
        try:
            task = Task.objects.get(id=task_id)
            
            difficulty_map = {'beginner': 'Простая', 'intermediate': 'Средняя', 'advanced': 'Сложная'}
            type_map = {'single_choice': 'Одиночный выбор', 'multiple_choice': 'Множественный выбор', 'true_false': 'Верно/Неверно'}
            
            return {
                'difficulty': difficulty_map.get(task.difficulty, 'Неизвестно'),
                'task_type': type_map.get(task.task_type, 'Неизвестно'),
                'skills': list(env.task_to_skills.get(task_id, set())),
                'estimated_time': getattr(task, 'estimated_time', 300)
            }
        except Task.DoesNotExist:
            return {
                'difficulty': 'Неизвестно',
                'task_type': 'Неизвестно',
                'skills': [],
                'estimated_time': 300
            }
    
    def _get_recommendation_reason(self, task_info: Dict, state_data: Dict, rank: int) -> str:
        """Определяет причину рекомендации"""
        if rank == 0:
            return "Лучший выбор по оценке DQN модели"
        elif task_info['difficulty'] == 'Простая':
            return "Подходящая сложность для закрепления навыков"
        elif task_info['difficulty'] == 'Сложная':
            return "Вызов для развития продвинутых навыков"
        else:
            return f"Альтернативный вариант #{rank + 1}"
    
    def _calculate_skill_match(self, task_info: Dict, bkt_params: torch.Tensor) -> float:
        """Вычисляет соответствие задания уровню навыков студента"""
        skills = task_info['skills']
        if not skills:
            return 0.5
        
        skill_levels = []
        for skill_id in skills:
            skill_idx = self.data_processor.skill_to_id.get(skill_id)
            if skill_idx is not None and skill_idx < len(bkt_params):
                mastery = bkt_params[skill_idx].item()
                skill_levels.append(mastery)
        
        if not skill_levels:
            return 0.5
        
        avg_mastery = np.mean(skill_levels)
        
        # Соответствие сложности уровню навыков
        difficulty = task_info['difficulty']
        if difficulty == 'Простая' and avg_mastery < 0.6:
            return 0.9  # Хорошее соответствие
        elif difficulty == 'Средняя' and 0.4 <= avg_mastery <= 0.8:
            return 0.9
        elif difficulty == 'Сложная' and avg_mastery > 0.7:
            return 0.9
        else:
            return 0.5  # Среднее соответствие
    
    def explain_recommendation(self, recommendation: TaskRecommendation, student_state: StudentStateInfo) -> str:
        """Объясняет рекомендацию в понятном виде"""
        explanation = f"Задание {recommendation.task_id}:\n"
        explanation += f"• Сложность: {recommendation.difficulty}\n"
        explanation += f"• Тип: {recommendation.task_type}\n"
        explanation += f"• Q-value: {recommendation.q_value:.4f}\n"
        explanation += f"• Уверенность: {recommendation.confidence:.1%}\n"
        explanation += f"• Соответствие навыкам: {recommendation.skill_match_score:.1%}\n"
        explanation += f"• Причина: {recommendation.reason}\n"
        
        if recommendation.skills:
            explanation += f"• Развиваемые навыки: {recommendation.skills}\n"
            
            # Показываем уровни этих навыков
            for skill_id in recommendation.skills:
                skill_idx = self.data_processor.skill_to_id.get(skill_id)
                if skill_idx is not None and skill_idx < len(student_state.bkt_params):
                    mastery = student_state.bkt_params[skill_idx, 0].item()
                    explanation += f"  - Навык {skill_id}: {mastery:.1%} освоения\n"
        
        return explanation
