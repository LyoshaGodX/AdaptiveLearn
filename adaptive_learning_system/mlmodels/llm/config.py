"""
Конфигурация LLM модуля
"""

# Настройки по умолчанию
DEFAULT_MODEL = 'gemma-2b'  # Переключаемся на более быструю Gemma
DEFAULT_DEVICE = 'auto'
USE_QUANTIZATION = True

# Параметры генерации
GENERATION_CONFIG = {
    'max_length': 200,
    'temperature': 0.7,
    'do_sample': True,
    'top_p': 0.9,
    'repetition_penalty': 1.1
}

# Лимиты длины объяснений
MAX_EXPLANATION_LENGTH = 250
MIN_EXPLANATION_LENGTH = 20

# Настройки логирования
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Пути для кэширования моделей
MODEL_CACHE_DIR = './models_cache'

# Поддерживаемые языки
SUPPORTED_LANGUAGES = ['ru', 'en']
DEFAULT_LANGUAGE = 'ru'
