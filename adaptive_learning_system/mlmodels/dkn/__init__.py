"""
Deep Knowledge Network (DKN) модуль для рекомендации заданий

Этот модуль содержит:
- DKN модель для предсказания успешности выполнения заданий
- Систему рекомендаций на основе DKN и BKT
- Обработчики данных для подготовки тренировочных данных
- Утилиты для обучения и оценки модели
"""

from .model import (
    DKNConfig, 
    DKNModel, 
    DKNTrainer,
    SkillEmbedding,
    TaskEmbedding,
    StudentStateEncoder,
    create_dkn_model
)

from .data_processor import (
    DKNDataProcessor,
    prepare_training_data,
    create_data_loaders
)

from .recommender import (
    DKNRecommender,
    RecommendationResult,
    get_next_task_recommendation
)

__all__ = [
    'DKNConfig',
    'DKNModel', 
    'DKNTrainer',
    'SkillEmbedding',
    'TaskEmbedding', 
    'StudentStateEncoder',
    'create_dkn_model',
    'DKNDataProcessor',
    'prepare_training_data',
    'create_data_loaders',
    'DKNRecommender',
    'RecommendationResult',
    'get_next_task_recommendation'
]
