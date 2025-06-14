#!/usr/bin/env python3
"""
Скрипт для запуска обучения DKN модели на синтетических данных
с полным сбором артефактов.
"""

import os
import sys
import pandas as pd
import numpy as np
import torch
from pathlib import Path
import logging

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dkn_training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_synthetic_dataset(dataset_path: str = "mlmodels/dkn/dataset/enhanced_synthetic_dataset.csv"):
    """
    Загружает синтетический датасет для обучения DKN
    
    Args:
        dataset_path: Путь к CSV файлу с датасетом
        
    Returns:
        Загруженный DataFrame
    """
    logger.info(f"Загружаем датасет: {dataset_path}")
    
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Датасет не найден: {dataset_path}")
    
    df = pd.read_csv(dataset_path)
    logger.info(f"Датасет загружен: {len(df)} примеров, {len(df.columns)} признаков")
    
    return df


def prepare_data_for_dkn(df: pd.DataFrame, test_size: float = 0.15, val_size: float = 0.15):
    """
    Подготавливает данные для обучения DKN модели
    
    Args:
        df: DataFrame с данными
        test_size: Размер тестовой выборки
        val_size: Размер валидационной выборки
        
    Returns:
        Tuple[List[Dict], List[Dict], List[Dict]]: train_data, val_data, test_data
    """
    logger.info("Подготавливаем данные для DKN...")
    
    # Разделяем по студентам, чтобы избежать утечки данных
    unique_students = df['student_id'].unique()
    np.random.shuffle(unique_students)
    
    n_students = len(unique_students)
    n_test = int(n_students * test_size)
    n_val = int(n_students * val_size)
    n_train = n_students - n_test - n_val
    
    test_students = unique_students[:n_test]
    val_students = unique_students[n_test:n_test + n_val]
    train_students = unique_students[n_test + n_val:]
    
    # Разделяем данные
    train_df = df[df['student_id'].isin(train_students)]
    val_df = df[df['student_id'].isin(val_students)]
    test_df = df[df['student_id'].isin(test_students)]
    
    logger.info(f"Разделение данных:")
    logger.info(f"  Обучение: {len(train_df)} примеров от {len(train_students)} студентов")
    logger.info(f"  Валидация: {len(val_df)} примеров от {len(val_students)} студентов")
    logger.info(f"  Тест: {len(test_df)} примеров от {len(test_students)} студентов")    # Конвертируем в формат для DKN
    def df_to_dkn_format(data_df):
        records = []
        NUM_SKILLS = 30  # Общее количество навыков в системе
        
        for _, row in data_df.iterrows():
            # Получаем активные навыки для задания (из синтетических данных)
            active_skills = []
            skill_mask = []
            bkt_params = []
            
            # Проходим по всем навыкам и собираем информацию
            for skill_idx in range(NUM_SKILLS):
                skill_learned = row.get(f'skill_{skill_idx}_learned', 0.0)
                skill_transit = row.get(f'skill_{skill_idx}_transit', 0.0)
                
                # Считаем навык активным, если есть данные о нем
                if skill_learned > 0 or skill_transit > 0:
                    active_skills.append(skill_idx + 1)  # skill_id начинается с 1
                    skill_mask.append(1.0)
                    bkt_params.append([
                        skill_learned,  # P_L - вероятность освоения
                        skill_transit,  # P_T - вероятность перехода  
                        0.2,  # P_G - вероятность угадывания (guess)
                        0.1   # P_S - вероятность ошибки (slip)
                    ])
                else:
                    active_skills.append(0)  # неактивный навык
                    skill_mask.append(0.0)
                    bkt_params.append([0.0, 0.0, 0.0, 0.0])
            
            # Если нет активных навыков, используем первый как дефолтный
            if sum(skill_mask) == 0:
                active_skills[0] = 1
                skill_mask[0] = 1.0
                bkt_params[0] = [0.5, 0.1, 0.2, 0.1]
            
            # Усредненные BKT параметры для current_bkt_avg
            total_weight = sum(skill_mask)
            if total_weight > 0:
                current_bkt_avg = [
                    sum(params[i] * mask for params, mask in zip(bkt_params, skill_mask)) / total_weight
                    for i in range(4)
                ]
            else:
                current_bkt_avg = [0.5, 0.1, 0.2, 0.1]  # дефолтные значения
            
            # Создаем базовую запись
            record = {
                'student_id': int(row['student_id']),
                'task_id': int(row['task_id']),
                'targets': float(row['target']),  # Переименовываем target в targets
                
                # Навыки для задания
                'skill_ids': active_skills,  # Все навыки (активные и неактивные)
                'skill_mask': skill_mask,    # Маска для активных навыков
                
                # BKT параметры: P_L, P_T, P_G, P_S для каждого навыка
                'bkt_params': bkt_params,
                'current_bkt_avg': current_bkt_avg,  # Усредненные BKT параметры [4]
                
                # Характеристики задания  
                'task_difficulty': int(row.get('task_difficulty', 0)),
                'task_type': int(row.get('task_type', 0)),
                'task_ids': int(row['task_id'])
            }            # Добавляем историю студента
            history = []
            
            # Функция для преобразования task_id в индекс
            def task_id_to_index(task_id, num_tasks=270):
                return task_id % num_tasks
            
            for i in range(10):  # последние 10 попыток
                hist_correct = row.get(f'hist_{i}_correct', 0)
                hist_score = row.get(f'hist_{i}_score', 0.0)
                hist_time = row.get(f'hist_{i}_time', 60.0)
                
                # Формат: [task_id, is_correct, time_spent, difficulty, type, 5 навыков]
                history_entry = [
                    float(task_id_to_index(int(row['task_id']))),  # task_id преобразован в индекс
                    float(hist_correct),    # is_correct
                    float(hist_time),       # time_spent
                    float(row.get('task_difficulty', 0)),  # difficulty
                    float(row.get('task_type', 0)),        # type
                    1.0, 0.0, 0.0, 0.0, 0.0  # 5 навыков (один активный)
                ]
                history.append(history_entry)
            
            record['student_history'] = history
            records.append(record)
        
        return records
    
    train_data = df_to_dkn_format(train_df)
    val_data = df_to_dkn_format(val_df)
    test_data = df_to_dkn_format(test_df)
    
    return train_data, val_data, test_data


def custom_collate_fn(batch):
    """
    Собирает батч данных для DKN модели
    
    Args:
        batch: Список записей данных
        
    Returns:
        Dict с тензорами для модели
    """
    # Собираем данные из батча
    batch_data = {
        'skill_ids': [],
        'bkt_params': [],
        'task_ids': [],
        'task_difficulty': [],
        'task_type': [],
        'student_history': [],
        'current_bkt_avg': [],
        'targets': [],
        'skill_mask': []
    }
      # Получаем все уникальные task_ids для создания маппинга
    # Используем простой хэш от task_id для создания стабильного индекса
    def task_id_to_index(task_id, num_tasks=270):
        return task_id % num_tasks  # Простой способ сопоставления
    
    for item in batch:
        batch_data['skill_ids'].append(item['skill_ids'])
        batch_data['bkt_params'].append(item['bkt_params'])
        
        # Преобразуем task_id в валидный индекс
        task_index = task_id_to_index(item['task_ids'])
        batch_data['task_ids'].append(task_index)
        
        batch_data['task_difficulty'].append(item['task_difficulty'])
        batch_data['task_type'].append(item['task_type'])
        batch_data['current_bkt_avg'].append(item['current_bkt_avg'])
        batch_data['targets'].append(item['targets'])
        batch_data['skill_mask'].append(item['skill_mask'])
          # Обрабатываем историю студента
        history = item['student_history']
        # Берем только последние несколько записей и паддим/обрезаем до фиксированной длины
        max_hist_len = 10
        if len(history) > max_hist_len:
            history = history[-max_hist_len:]
        
        # Паддинг до max_hist_len если нужно
        while len(history) < max_hist_len:
            # Паддинг с дефолтными значениями [task_id, correct, time, difficulty, type, 5 навыков]
            history.append([0.0, 0.0, 60.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        
        batch_data['student_history'].append(history)
      # Конвертируем в тензоры
    return {
        'skill_ids': torch.tensor(batch_data['skill_ids'], dtype=torch.long),
        'bkt_params': torch.tensor(batch_data['bkt_params'], dtype=torch.float32),  # [batch_size, num_skills, 4]
        'task_ids': torch.tensor(batch_data['task_ids'], dtype=torch.long),
        'task_difficulty': torch.tensor(batch_data['task_difficulty'], dtype=torch.long),
        'task_type': torch.tensor(batch_data['task_type'], dtype=torch.long),
        'student_history': torch.tensor(batch_data['student_history'], dtype=torch.float32),
        'current_bkt_avg': torch.tensor(batch_data['current_bkt_avg'], dtype=torch.float32),
        'targets': torch.tensor(batch_data['targets'], dtype=torch.float32),
        'skill_mask': torch.tensor(batch_data['skill_mask'], dtype=torch.float32)
    }


def main():
    """Основная функция запуска обучения"""
    
    logger.info("Запуск обучения DKN модели")
    logger.info("=" * 60)
    
    try:
        # 1. Загружаем данные
        logger.info("Шаг 1: Загрузка синтетического датасета")
        df = load_synthetic_dataset()
        
        # 2. Подготавливаем данные
        logger.info("Шаг 2: Подготовка данных для DKN")
        train_data, val_data, test_data = prepare_data_for_dkn(df)
          # 3. Импортируем тренер (после настройки Django)
        from mlmodels.dkn.trainer import train_dkn_model
        from mlmodels.dkn.model import DKNConfig
        from mlmodels.dkn.data_processor import DKNDataset
        from torch.utils.data import DataLoader        # 4. Настраиваем конфигурацию
        logger.info("Шаг 3: Настройка конфигурации модели")
        config = DKNConfig()
        config.hidden_dim = 256
        config.num_layers = 3
        config.dropout = 0.2
        config.learning_rate = 0.001
        config.batch_size = 16
        
        # Параметры системы
        NUM_SKILLS = 30    # Количество навыков в системе
        NUM_TASKS = 270    # Количество заданий в системе        # 5. Запускаем обучение
        logger.info("Шаг 4: Запуск обучения с созданием артефактов")
        trainer = train_dkn_model(
            train_data=train_data,
            val_data=val_data,
            test_data=test_data,
            config=config,
            num_skills=NUM_SKILLS,
            num_tasks=NUM_TASKS,
            save_dir='checkpoints',            artifacts_dir='mlmodels/dkn/training',
            num_epochs=5,  # Сокращаем для тестирования
            batch_size=16,
            collate_fn=custom_collate_fn
        )
        
        logger.info("Обучение завершено успешно!")
        logger.info(f"📁 Артефакты сохранены в: {trainer.artifacts_collector.artifacts_dir}")
        
        # 6. Выводим краткую сводку
        best_val_loss = trainer.artifacts_collector.training_info['best_val_loss']
        best_val_accuracy = trainer.artifacts_collector.training_info['best_val_accuracy']
        best_epoch = trainer.artifacts_collector.training_info['best_epoch']
        
        logger.info("Итоговые результаты:")
        logger.info(f"   Лучшая эпоха: {best_epoch}")
        logger.info(f"   Лучшие потери на валидации: {best_val_loss:.6f}")
        logger.info(f"   Лучшая точность на валидации: {best_val_accuracy:.4f}")
        
        return trainer
        
    except Exception as e:
        logger.error(f"Ошибка при обучении: {e}")
        raise


if __name__ == "__main__":
    trainer = main()
