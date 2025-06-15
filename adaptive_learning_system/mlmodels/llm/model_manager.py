"""
Менеджер для управления локальными LLM моделями
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from typing import Optional, Dict, Any
import logging
from pathlib import Path
import os
from .config import DEFAULT_MODEL

logger = logging.getLogger(__name__)

# Глобальный кэш моделей для избежания повторных загрузок
_MODEL_CACHE = {}
_TOKENIZER_CACHE = {}


class LLMModelManager:
    """Менеджер для управления LLM моделями"""
      # Конфигурации поддерживаемых моделей
    SUPPORTED_MODELS = {
        'qwen2.5-0.5b': {
            'model_name': 'Qwen/Qwen2.5-0.5B-Instruct',
            'size_gb': 1.0,
            'description': 'Быстрая и компактная модель от Alibaba',
            'chat_template': 'qwen'
        },
        'phi3.5-mini': {
            'model_name': 'microsoft/Phi-3.5-mini-instruct',
            'size_gb': 2.3,
            'description': 'Высококачественная мини-модель от Microsoft',
            'chat_template': 'phi3'
        },
        'gemma-2b': {
            'model_name': 'google/gemma-2b-it',
            'size_gb': 2.0,
            'description': 'Быстрая и эффективная модель от Google',
            'chat_template': 'gemma'
        },
        'saiga-mistral-7b': {
            'model_name': 'IlyaGusev/saiga_mistral_7b',
            'size_gb': 4.0,
            'description': 'Русскоязычная модель на базе Mistral',
            'chat_template': 'saiga'
        }
    }
    
    def __init__(self, model_key: str = DEFAULT_MODEL, device: str = 'auto'):
        """
        Args:
            model_key: Ключ модели из SUPPORTED_MODELS
            device: Устройство для инференса ('cpu', 'cuda', 'auto')
        """
        self.model_key = model_key
        self.model_config = self.SUPPORTED_MODELS[model_key]
        self.device = self._get_device(device)
        
        self.tokenizer = None
        self.model = None
        self.is_loaded = False
        
    def _get_device(self, device: str) -> str:
        """Определяет оптимальное устройство"""
        if device == 'auto':
            if torch.cuda.is_available():
                return 'cuda'
            else:
                return 'cpu'
        return device
    
    def load_model(self, use_quantization: bool = True) -> bool:
        """
        Загружает модель и токенизатор с кэшированием
        
        Args:
            use_quantization: Использовать ли квантизацию для экономии памяти
            
        Returns:
            True если загрузка успешна
        """
        global _MODEL_CACHE, _TOKENIZER_CACHE
        
        model_name = self.model_config['model_name']
        cache_key = f"{model_name}_{self.device}"  # Упрощаем ключ кэша
        
        try:
            # Проверяем кэш токенизатора
            if model_name in _TOKENIZER_CACHE:
                logger.info(f"Загрузка токенизатора из кэша для {model_name}")
                self.tokenizer = _TOKENIZER_CACHE[model_name]
            else:
                logger.info(f"Загрузка токенизатора {model_name}...")
                self.tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    trust_remote_code=True
                )
                _TOKENIZER_CACHE[model_name] = self.tokenizer
            
            # Проверяем кэш модели
            if cache_key in _MODEL_CACHE:
                logger.info(f"Загрузка модели из кэша для {model_name}")
                self.model = _MODEL_CACHE[cache_key]
            else:
                logger.info(f"Загрузка модели {model_name} (это может занять время)...")                # Настройка параметров модели для максимальной производительности
                model_kwargs = {
                    'trust_remote_code': True,
                    'attn_implementation': 'eager',  # Phi-3 пока не поддерживает SDPA
                    'torch_dtype': torch.float16,  # Всегда используем fp16 для скорости
                    'low_cpu_mem_usage': True,  # Экономим память CPU
                }                
                if use_quantization and self.device == 'cuda':
                    # Используем 8-битную квантизацию для лучшей совместимости
                    quantization_config = BitsAndBytesConfig(
                        load_in_8bit=True,
                        llm_int8_threshold=6.0,
                        llm_int8_has_fp16_weight=False
                    )
                    model_kwargs['quantization_config'] = quantization_config
                    model_kwargs['device_map'] = 'auto'
                    model_kwargs['torch_dtype'] = 'auto'
                elif use_quantization and self.device == 'cpu':
                    # Для CPU используем обычную квантизацию
                    model_kwargs['torch_dtype'] = torch.float32  # CPU лучше работает с float32
                else:
                    if self.device == 'cuda':
                        model_kwargs['device_map'] = 'auto'
                        model_kwargs['torch_dtype'] = torch.float16
                    else:
                        model_kwargs['torch_dtype'] = torch.float32  # CPU требует float32
                
                # Загружаем модель
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    **model_kwargs
                )
                
                # Перемещаем на CPU если нужно
                if self.device == 'cpu':
                    self.model = self.model.to('cpu')
                
                # Сохраняем в кэш
                _MODEL_CACHE[cache_key] = self.model
            
            self.is_loaded = True
            logger.info(f"Модель {model_name} готова к использованию на {self.device}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            return False
    
    def generate_text(self,
                     prompt: str, 
                     max_length: int = 150,  # Уменьшаем для быстрых тестов
                     temperature: float = 0.7,
                     do_sample: bool = True) -> str:
        """
        Генерирует текст по промпту
        
        Args:
            prompt: Входной промпт
            max_length: Максимальная длина генерации (в токенах)
            temperature: Температура сэмплирования
            do_sample: Использовать ли сэмплирование
            
        Returns:
            Сгенерированный текст
        """
        if not self.is_loaded:
            raise RuntimeError("Модель не загружена. Вызовите load_model() сначала.")
        
        try:            # Токенизируем промпт
            inputs = self.tokenizer(prompt, return_tensors="pt")
            if self.device == 'cuda':
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            input_length = inputs['input_ids'].shape[1]            # Генерируем текст с оптимизированными параметрами для скорости
            with torch.no_grad():
                try:
                    # Пробуем с кэшем
                    if do_sample:
                        outputs = self.model.generate(
                            **inputs,
                            max_new_tokens=max_length,
                            temperature=temperature,
                            do_sample=True,
                            top_p=0.9,  # Ограничиваем выбор токенов для скорости
                            top_k=50,   # Еще больше ограничиваем
                            pad_token_id=self.tokenizer.eos_token_id,
                            use_cache=True  # Пробуем с кэшем
                        )
                    else:
                        outputs = self.model.generate(
                            **inputs,
                            max_new_tokens=max_length,
                            do_sample=False,
                            pad_token_id=self.tokenizer.eos_token_id,
                            use_cache=True  # Пробуем с кэшем
                        )
                except Exception as cache_error:
                    # Если ошибка с кэшем, пробуем без него
                    logger.warning(f"Ошибка с кэшем: {cache_error}. Пробуем без кэша.")
                    if do_sample:
                        outputs = self.model.generate(
                            **inputs,
                            max_new_tokens=max_length,
                            temperature=temperature,
                            do_sample=True,
                            top_p=0.9,
                            top_k=50,
                            pad_token_id=self.tokenizer.eos_token_id,
                            use_cache=False  # Отключаем кэш
                        )
                    else:
                        outputs = self.model.generate(
                            **inputs,
                            max_new_tokens=max_length,
                            do_sample=False,
                            pad_token_id=self.tokenizer.eos_token_id,
                            use_cache=False  # Отключаем кэш
                        )
            
            # Декодируем только новую часть
            generated_ids = outputs[0][input_length:]
            generated_text = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
            
            return generated_text.strip()
            
        except Exception as e:
            logger.error(f"Ошибка генерации текста: {e}")
            return ""
    
    def get_model_info(self) -> Dict[str, Any]:
        """Возвращает информацию о модели"""
        return {
            'model_key': self.model_key,
            'model_name': self.model_config['model_name'],
            'size_gb': self.model_config['size_gb'],
            'description': self.model_config['description'],
            'device': self.device,
            'is_loaded': self.is_loaded
        }
    
    @classmethod
    def list_supported_models(cls) -> Dict[str, Dict[str, Any]]:
        """Возвращает список поддерживаемых моделей"""
        return cls.SUPPORTED_MODELS
    
    @classmethod
    def clear_cache(cls):
        """Очищает кэш моделей и токенизаторов"""
        global _MODEL_CACHE, _TOKENIZER_CACHE
        
        # Освобождаем память от моделей
        for model in _MODEL_CACHE.values():
            if hasattr(model, 'cpu'):
                model.cpu()
            del model
        
        _MODEL_CACHE.clear()
        _TOKENIZER_CACHE.clear()
        
        # Очистка кэша GPU
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("Кэш моделей очищен")
    
    @classmethod
    def get_cache_info(cls) -> Dict[str, Any]:
        """Возвращает информацию о кэше"""
        return {
            'cached_models': list(_MODEL_CACHE.keys()),
            'cached_tokenizers': list(_TOKENIZER_CACHE.keys()),
            'cache_size': len(_MODEL_CACHE) + len(_TOKENIZER_CACHE)
        }
