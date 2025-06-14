"""
Обработчик данных для DKN модели

Этот модуль подготавливает данные из Django моделей в формат, 
подходящий для обучения DKN модели.
"""

import torch
from torch.utils.data import Dataset, DataLoader
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import pandas as pd

# Django imports
from django.contrib.auth.models import User
from skills.models import Skill
from methodist.models import Task
from mlmodels.models import TaskAttempt, StudentSkillMastery
from student.models import StudentProfile
from mlmodels.bkt.base_model import BKTModel


class DKNDataset(Dataset):
    """Dataset для DKN модели"""
    
    def __init__(self, data: List[Dict]):
        self.data = data
        
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        return self.data[idx]


class DKNDataProcessor:
    """Обработчик данных для DKN"""
    
    def __init__(self, max_history_length: int = 50):
        self.max_history_length = max_history_length
        self.skill_to_id = {}
        self.task_to_id = {}
        self.id_to_skill = {}
        self.id_to_task = {}
        
        # Маппинги для типов заданий и сложности
        self.difficulty_map = {
            'beginner': 0,
            'intermediate': 1, 
            'advanced': 2
        }
        
        self.type_map = {
            'single_choice': 0,
            'multiple_choice': 1,
            'true_false': 2
        }
        
        self._build_mappings()
    
    def _build_mappings(self):
        """Создает маппинги между объектами и ID"""
        # Навыки
        skills = list(Skill.objects.all())
        for i, skill in enumerate(skills):
            self.skill_to_id[skill.id] = i
            self.id_to_skill[i] = skill.id
              # Задания
        tasks = list(Task.objects.all())
        for i, task in enumerate(tasks):
            self.task_to_id[task.id] = i
            self.id_to_task[i] = task.id

    def get_student_data(self, student_id: int, target_task_id: int) -> Dict:
        """
        Получает данные студента для предсказания успеха на задании
        
        Args:
            student_id: ID студента
            target_task_id: ID целевого задания
            
        Returns:
            Dict с подготовленными данными
        """
        user = User.objects.get(id=student_id)
        student_profile, created = StudentProfile.objects.get_or_create(user=user)
        target_task = Task.objects.get(id=target_task_id)
        
        # История попыток студента
        history = self._get_student_history(student_profile)
        
        # Текущие BKT параметры для всех навыков
        bkt_params = self._get_bkt_parameters(student_profile)
          # Навыки, связанные с заданием
        task_skills = list(target_task.skills.all())
        
        # Характеристики задания
        task_data = self._get_task_data(target_task)
        
        return {
            'student_id': student_id,
            'task_id': target_task_id,
            'history': history,            'bkt_params': bkt_params,
            'task_skills': [self.skill_to_id[s.id] for s in task_skills],
            'task_data': task_data
        }

    def _get_student_history(self, student_profile: StudentProfile) -> List[Dict]:
        """Получает историю попыток студента"""
        attempts = TaskAttempt.objects.filter(
            student=student_profile
        ).order_by('-started_at')[:self.max_history_length]
        
        history = []
        for attempt in reversed(attempts):  # Хронологический порядок
            # Получаем навыки для задания
            task_skills = list(attempt.task.skills.all())
            skill_vector = [0] * 5  # До 5 навыков на задание
            
            for i, skill in enumerate(task_skills[:5]):
                skill_vector[i] = self.skill_to_id.get(skill.id, 0)
            
            history_item = {
                'task_id': self.task_to_id.get(attempt.task.id, 0),
                'is_correct': 1.0 if attempt.is_correct else 0.0,
                'score': 1.0 if attempt.is_correct else 0.0,  # Используем результат как score
                'time_spent': min(attempt.time_spent or 60, 600),  # Ограничиваем время
                'difficulty': self.difficulty_map.get(attempt.task.difficulty, 0),
                'task_type': self.type_map.get(attempt.task.task_type, 0),
                'skills': skill_vector
            }
            history.append(history_item)
        
        # Дополняем до нужной длины нулями, если история короткая        while len(history) < self.max_history_length:
            history.append({
                'task_id': 0, 'is_correct': 0.0, 'score': 0.0,
                'time_spent': 0, 'difficulty': 0, 'task_type': 0,
                'skills': [0] * 5
            })
        
        return history

    def _get_bkt_parameters(self, student_profile: StudentProfile) -> Dict[int, Dict]:
        """Получает BKT параметры для всех навыков студента"""
        bkt_model = BKTModel()
        
        bkt_params = {}
        
        # Получаем все навыки студента
        masteries = StudentSkillMastery.objects.filter(student=student_profile)
        
        for mastery in masteries:
            skill_id = self.skill_to_id.get(mastery.skill.id, 0)
              # Используем сохраненные BKT параметры или дефолтные
            bkt_params[skill_id] = {
                'P_L': mastery.current_mastery_prob,  # Текущая вероятность освоения
                'P_T': mastery.transition_prob,       # Вероятность перехода
                'P_G': mastery.guess_prob,           # Вероятность угадывания
                'P_S': mastery.slip_prob             # Вероятность ошибки
            }
        
        # Для навыков без попыток используем дефолтные значения
        for skill_db_id in self.skill_to_id.keys():
            skill_id = self.skill_to_id[skill_db_id]
            if skill_id not in bkt_params:
                bkt_params[skill_id] = {
                    'P_L': 0.1,   # Низкая начальная вероятность
                    'P_T': 0.1,
                    'P_G': 0.1,
                    'P_S': 0.1
                }
        
        return bkt_params
    
    def _get_task_data(self, task: Task) -> Dict:
        """Получает характеристики задания"""
        return {
            'difficulty': self.difficulty_map.get(task.difficulty, 0),
            'task_type': self.type_map.get(task.task_type, 0),
            'skills': [self.skill_to_id[s.id] for s in task.skills.all()]
        }
    
    def prepare_batch(self, data_items: List[Dict]) -> Dict[str, torch.Tensor]:
        """Подготавливает батч данных для модели"""
        batch_size = len(data_items)
        max_skills = len(self.skill_to_id)
        
        # Инициализируем тензоры
        skill_ids = torch.zeros(batch_size, max_skills, dtype=torch.long)
        bkt_params = torch.zeros(batch_size, max_skills, 4)
        task_ids = torch.zeros(batch_size, dtype=torch.long)
        task_difficulty = torch.zeros(batch_size, dtype=torch.long)
        task_type = torch.zeros(batch_size, dtype=torch.long)
        
        # История студента
        history_tensor = torch.zeros(batch_size, self.max_history_length, 10)
        
        # Текущие усредненные BKT параметры
        current_bkt_avg = torch.zeros(batch_size, 4)
        
        # Маска для активных навыков
        skill_mask = torch.zeros(batch_size, max_skills)
        
        for i, item in enumerate(data_items):
            # Навыки
            for j in range(max_skills):
                skill_ids[i, j] = j
            
            # BKT параметры
            for skill_id, params in item['bkt_params'].items():
                if skill_id < max_skills:
                    bkt_params[i, skill_id] = torch.tensor([
                        params['P_L'], params['P_T'], 
                        params['P_G'], params['P_S']
                    ])
                    skill_mask[i, skill_id] = 1.0
            
            # Задания
            task_ids[i] = self.task_to_id.get(item['task_id'], 0)
            task_difficulty[i] = item['task_data']['difficulty']
            task_type[i] = item['task_data']['task_type']
            
            # История
            for j, hist_item in enumerate(item['history']):
                if j < self.max_history_length:
                    history_tensor[i, j] = torch.tensor([
                        hist_item['task_id'],
                        hist_item['is_correct'],
                        hist_item['score'],
                        hist_item['time_spent'] / 600.0,  # Нормализация времени
                        hist_item['difficulty'],
                        hist_item['task_type'],
                        *hist_item['skills'][:4]  # Первые 4 навыка
                    ])
            
            # Усредненные BKT параметры для всех навыков студента
            active_params = [params for params in item['bkt_params'].values()]
            if active_params:
                avg_params = {
                    'P_L': np.mean([p['P_L'] for p in active_params]),
                    'P_T': np.mean([p['P_T'] for p in active_params]),
                    'P_G': np.mean([p['P_G'] for p in active_params]),
                    'P_S': np.mean([p['P_S'] for p in active_params])
                }
                current_bkt_avg[i] = torch.tensor([
                    avg_params['P_L'], avg_params['P_T'],
                    avg_params['P_G'], avg_params['P_S']
                ])
        
        return {
            'skill_ids': skill_ids,
            'bkt_params': bkt_params,
            'task_ids': task_ids,
            'task_difficulty': task_difficulty,
            'task_type': task_type,
            'student_history': history_tensor,
            'current_bkt_avg': current_bkt_avg,
            'skill_mask': skill_mask
        }


def prepare_training_data(students: List[User], validation_split: float = 0.2) -> Tuple[List[Dict], List[Dict]]:
    """
    Подготавливает тренировочные данные из попыток студентов
    
    Args:
        students: Список студентов
        validation_split: Доля данных для валидации
        
    Returns:
        Tuple[train_data, val_data]
    """
    processor = DKNDataProcessor()
    all_data = []
    
    for student in students:
        # Получаем все попытки студента
        attempts = TaskAttempt.objects.filter(student__user=student).order_by('created_at')
        
        if len(attempts) < 2:  # Нужна история
            continue
            
        # Для каждой попытки создаем пример для обучения
        for i in range(1, len(attempts)):
            target_attempt = attempts[i]
            
            # Получаем данные студента на момент до попытки
            student_data = processor.get_student_data(
                student.id, 
                target_attempt.task.id
            )
            
            # Добавляем целевую переменную (успех попытки)
            student_data['target'] = 1.0 if target_attempt.is_correct else 0.0
            
            all_data.append(student_data)
    
    # Разделяем на тренировочные и валидационные данные
    split_idx = int(len(all_data) * (1 - validation_split))
    
    # Перемешиваем данные
    np.random.shuffle(all_data)
    
    train_data = all_data[:split_idx]
    val_data = all_data[split_idx:]
    
    return train_data, val_data


def create_data_loaders(train_data: List[Dict], val_data: List[Dict], 
                       batch_size: int = 32) -> Tuple[DataLoader, DataLoader]:
    """Создает DataLoader'ы для тренировки и валидации"""
    
    def collate_fn(batch):
        processor = DKNDataProcessor()
        
        # Подготавливаем батч
        model_batch = processor.prepare_batch(batch)
        
        # Добавляем целевые переменные
        targets = torch.tensor([item['target'] for item in batch], dtype=torch.float)
        model_batch['targets'] = targets
        
        return model_batch
    
    train_dataset = DKNDataset(train_data)
    val_dataset = DKNDataset(val_data)
    
    train_loader = DataLoader(
        train_dataset, 
        batch_size=batch_size, 
        shuffle=True, 
        collate_fn=collate_fn
    )
    
    val_loader = DataLoader(
        val_dataset, 
        batch_size=batch_size, 
        shuffle=False, 
        collate_fn=collate_fn
    )
    
    return train_loader, val_loader
