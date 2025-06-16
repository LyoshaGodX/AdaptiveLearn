"""
Генератор объяснений рекомендаций с использованием LLM

Интегрируется с DQN системой рекомендаций для создания
понятных объяснений на естественном языке
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .model_manager import LLMModelManager
from .prompt_templates import PromptTemplates

logger = logging.getLogger(__name__)


class ExplanationGenerator:
    """Генератор объяснений рекомендаций"""
    
    def __init__(self, model_key: str = 'qwen2.5-0.5b', device: str = 'auto'):
        """
        Args:
            model_key: Ключ модели для использования
            device: Устройство для инференса
        """
        self.model_manager = LLMModelManager(model_key, device)
        self.prompt_templates = PromptTemplates()
        self.is_initialized = False
        
    def initialize(self, use_quantization: bool = True) -> bool:
        """
        Инициализирует LLM модель
        
        Args:
            use_quantization: Использовать ли квантизацию
            
        Returns:
            True если инициализация успешна
        """
        try:
            logger.info("Инициализация LLM для генерации объяснений...")
            success = self.model_manager.load_model(use_quantization)
            self.is_initialized = success
            
            if success:
                logger.info("LLM успешно инициализирована")
            else:
                logger.error("Ошибка инициализации LLM")
                
            return success
            
        except Exception as e:
            logger.error(f"Критическая ошибка инициализации LLM: {e}")
            return False
    
    def generate_recommendation_explanation(self, recommendation_data: Dict[str, Any]) -> str:
        """
        Генерирует объяснение рекомендации на основе данных из БД
        
        Args:
            recommendation_data: Данные рекомендации из DQNRecommendation
            
        Returns:
            Объяснение рекомендации на естественном языке
        """
        if not self.is_initialized:
            logger.warning("LLM не инициализирована. Возвращаем стандартное объяснение.")
            return self._get_fallback_explanation(recommendation_data)
        
        try:
            # Извлекаем нужные данные
            student_name = recommendation_data.get('student_name', 'Студент')
            task_title = recommendation_data.get('task_title', 'Задание')
            task_difficulty = recommendation_data.get('task_difficulty', 'intermediate')
            task_type = recommendation_data.get('task_type', 'single')  # Новый параметр
            
            # Информация о целевом навыке
            target_skill_info = recommendation_data.get('target_skill_info', [])
            if target_skill_info:
                target_skill = target_skill_info[0].get('skill_name', 'Неизвестный навык')
                target_skill_mastery = target_skill_info[0].get('current_mastery_probability', 0.1)
            else:
                target_skill = 'Программирование'
                target_skill_mastery = 0.1
            
            # Prerequisite навыки
            prerequisite_skills = recommendation_data.get('prerequisite_skills_snapshot', [])
            
            # Зависимые навыки
            dependent_skills = recommendation_data.get('dependent_skills_snapshot', [])
            
            # Прогресс студента
            student_progress = recommendation_data.get('student_progress_context', {})
            
            # Создаем промпт с новыми параметрами
            prompt = self.prompt_templates.recommendation_explanation_prompt(
                student_name=student_name,
                task_title=task_title,
                task_difficulty=task_difficulty,
                task_type=task_type,
                target_skill=target_skill,
                target_skill_mastery=target_skill_mastery,
                prerequisite_skills=prerequisite_skills,
                dependent_skills=dependent_skills,
                student_progress=student_progress
            )
              # Генерируем объяснение
            logger.info(f"Генерируем объяснение с промптом длиной {len(prompt)} символов")
            logger.debug(f"Промпт: {prompt[:200]}...")
            
            explanation = self.model_manager.generate_text(
                prompt=prompt,
                max_length=400,  # Увеличиваем для более подробных объяснений
                temperature=0.7,
                do_sample=True
            )
            
            logger.info(f"LLM вернула: '{explanation}' (длина: {len(explanation) if explanation else 0})")
            
            # Очищаем и проверяем результат
            explanation = self._clean_explanation(explanation)
            
            if not explanation or len(explanation) < 10:  # Уменьшаем порог с 20 до 10
                logger.warning(f"LLM вернула пустое или слишком короткое объяснение: '{explanation}'")
                logger.warning("Используем fallback объяснение")
                return self._get_fallback_explanation(recommendation_data)
            
            logger.info(f"Сгенерировано объяснение: {explanation[:50]}...")
            return explanation
            
        except Exception as e:
            logger.error(f"Ошибка генерации объяснения: {e}")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            import traceback
            logger.error(f"Полный стек ошибки:\n{traceback.format_exc()}")
            return self._get_fallback_explanation(recommendation_data)
    
    def generate_skill_progress_explanation(self, skill_data: Dict[str, Any]) -> str:
        """Генерирует объяснение прогресса по навыку"""
        if not self.is_initialized:
            return f"Прогресс по навыку '{skill_data.get('skill_name', 'Неизвестный')}'."
        
        try:
            prompt = self.prompt_templates.skill_progress_prompt(
                skill_name=skill_data.get('skill_name', 'Неизвестный навык'),
                current_mastery=skill_data.get('current_mastery_probability', 0),
                attempts_count=skill_data.get('attempts_count', 0),
                success_rate=skill_data.get('success_rate', 0)
            )
            
            logger.info(f"Генерируем объяснение прогресса для навыка: {skill_data.get('skill_name', 'Неизвестный')}")
            
            explanation = self.model_manager.generate_text(
                prompt=prompt,
                max_length=400,
                temperature=0.6
            )
            
            logger.info(f"LLM вернула для прогресса: '{explanation}' (длина: {len(explanation) if explanation else 0})")
            
            cleaned = self._clean_explanation(explanation)
            if not cleaned:
                logger.warning(f"Пустое объяснение прогресса для навыка {skill_data.get('skill_name')}")
                return f"Изучаешь навык '{skill_data.get('skill_name', 'Неизвестный')}'."
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Ошибка генерации объяснения прогресса: {e}")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            import traceback
            logger.error(f"Полный стек ошибки:\n{traceback.format_exc()}")
            return f"Продолжай развивать навык '{skill_data.get('skill_name', 'Неизвестный')}'!"
    
    def generate_motivation_message(self, student_data: Dict[str, Any]) -> str:
        """Генерирует мотивационное сообщение"""
        if not self.is_initialized:
            return "Продолжай учиться! Каждое задание делает тебя лучше!"
        try:
            prompt = self.prompt_templates.motivation_prompt(
                student_name=student_data.get('student_name', 'Студент'),
                recent_successes=student_data.get('recent_successes', 0),
                recent_failures=student_data.get('recent_failures', 0)
            )
            
            logger.info(f"Генерируем мотивационное сообщение для студента: {student_data.get('student_name', 'Студент')}")
            logger.debug(f"Мотивационный промпт: {prompt[:100]}...")
            
            message = self.model_manager.generate_text(
                prompt=prompt,
                max_length=400,
                temperature=0.8
            )
            
            logger.info(f"LLM вернула мотивацию: '{message}' (длина: {len(message) if message else 0})")
            
            cleaned = self._clean_explanation(message)
            if not cleaned:
                logger.warning("Пустое мотивационное сообщение от LLM")
                return "Отличная работа! Продолжай в том же духе!"
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Ошибка генерации мотивационного сообщения: {e}")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            import traceback
            logger.error(f"Полный стек ошибки:\n{traceback.format_exc()}")
            return "Ты делаешь успехи! Каждая попытка приближает к цели!"
    def _clean_explanation(self, text: str) -> str:
        """Очищает и форматирует сгенерированный текст"""
        logger.debug(f"_clean_explanation получил: '{text}' (тип: {type(text)}, длина: {len(text) if text else 0})")
        
        if not text:
            logger.debug("Текст пустой или None, возвращаем пустую строку")
            return ""
        
        original_text = text
        
        # Убираем лишние пробелы и переносы
        text = text.strip()
        logger.debug(f"После strip(): '{text}' (длина: {len(text)})")
        
        # Убираем повторяющиеся знаки препинания
        text = text.replace('..', '.')
        text = text.replace('!!', '!')
        text = text.replace('??', '?')
        logger.debug(f"После очистки знаков: '{text}' (длина: {len(text)})")
        
        # Ограничиваем длину
        if len(text) > 250:
            # Находим последнее предложение в пределах лимита
            sentences = text[:250].split('.')
            if len(sentences) > 1:
                text = '.'.join(sentences[:-1]) + '.'
            else:
                text = text[:250] + '...'
            logger.debug(f"После ограничения длины: '{text}' (длина: {len(text)})")
        
        logger.debug(f"_clean_explanation возвращает: '{text}' (длина: {len(text)})")
        return text
    
    def _get_fallback_explanation(self, recommendation_data: Dict[str, Any]) -> str:
        """Возвращает стандартное объяснение при ошибке LLM"""
        task_title = recommendation_data.get('task_title', 'это задание')
        
        # Простые шаблоны на основе сложности
        difficulty = recommendation_data.get('task_difficulty', 'intermediate')
        
        if difficulty == 'beginner':
            return f"Задание '{task_title}' подходит для начального изучения основ. Самое время начать!"
        elif difficulty == 'advanced':
            return f"Задание '{task_title}' поможет углубить знания и освоить сложные концепции."
        else:
            return f"Задание '{task_title}' оптимально для твоего текущего уровня. Вперед к новым знаниям!"
    
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус генератора объяснений"""
        return {
            'is_initialized': self.is_initialized,
            'model_info': self.model_manager.get_model_info() if self.is_initialized else None,
            'timestamp': datetime.now().isoformat()
        }
