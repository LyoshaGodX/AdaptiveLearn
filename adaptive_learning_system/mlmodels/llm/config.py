"""
Оптимизированная конфигурация LLM модуля для gemma-2b
"""

# Основные параметры
DEFAULT_MODEL = 'gemma-2b'
DEFAULT_DEVICE = 'auto'  # Оставляем автоопределение GPU/CPU
USE_QUANTIZATION = True  # Сохраняем квантование для ускорения

# Параметры генерации (подобраны для сбалансированной генерации)
GENERATION_CONFIG = {
    'max_length': 1024,              # Увеличено для более содержательных ответов
    'temperature': 0.7,              # Умеренное разнообразие
    'do_sample': True,               # Сэмплирование включено
    'top_p': 0.95,                   # Расширенный p-семплинг
    'repetition_penalty': 1.15       # Умеренное штрафование повторов
}

# Лимиты длины объяснений (если используется фильтрация или ограничение)
MAX_EXPLANATION_LENGTH = 900        # Увеличено, чтобы не обрезать полезный вывод
MIN_EXPLANATION_LENGTH = 100        # Повышен нижний порог

# Настройки логирования
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Кэш моделей
MODEL_CACHE_DIR = './models_cache'

# Языки
SUPPORTED_LANGUAGES = ['ru', 'en']
DEFAULT_LANGUAGE = 'ru'