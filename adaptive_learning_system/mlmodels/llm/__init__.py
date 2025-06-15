"""
LLM модуль для генерации объяснений рекомендаций

Этот модуль содержит:
- Загрузку и управление локальной LLM
- Генерацию объяснений рекомендаций на естественном языке  
- Промптинг и форматирование для образовательного контекста
"""

from .explanation_generator import ExplanationGenerator
from .model_manager import LLMModelManager
from .prompt_templates import PromptTemplates

__all__ = [
    'ExplanationGenerator',
    'LLMModelManager', 
    'PromptTemplates'
]
