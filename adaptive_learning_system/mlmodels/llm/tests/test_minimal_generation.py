"""
Минимальный тест LLM с коротким ответом
"""
import os
import sys
from pathlib import Path

# Настройка Django
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')

import django
django.setup()

from mlmodels.llm.model_manager import LLMModelManager


def minimal_test():
    """Минимальный тест с очень коротким ответом"""
    print("=== МИНИМАЛЬНЫЙ ТЕСТ LLM ===\n")
      # Создаем менеджер модели
    manager = LLMModelManager(model_key='gemma-2b', device='auto')
    
    # Загружаем модель
    print("🔄 Загрузка модели...")
    success = manager.load_model(use_quantization=True)
    
    if not success:
        print("❌ Не удалось загрузить модель")
        return False
    
    print("✅ Модель загружена")
    
    # Очень простой промпт с ожидаемым коротким ответом
    prompt = "Завершите предложение: Python - это язык программирования"
    
    print(f"\n🚀 Генерация (макс. 20 токенов)...")
    print(f"Промпт: {prompt}")
    
    try:
        # Генерируем с очень малыми параметрами
        result = manager.generate_text(
            prompt=prompt,
            max_length=20,  # Очень короткий ответ
            temperature=0.3,  # Меньше креативности
            do_sample=False  # Детерминированная генерация
        )
        
        print(f"\n✅ РЕЗУЛЬТАТ: '{result}'")
        print(f"Длина: {len(result)} символов")
        
        if result and len(result.strip()) > 0:
            print("🎉 Генерация работает!")
            return True
        else:
            print("⚠️ Пустой результат")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


if __name__ == '__main__':
    minimal_test()
