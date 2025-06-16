#!/usr/bin/env python3
"""
Диагностический тест для model_manager.generate_text()
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import sys
import os
from pathlib import Path

# Добавляем путь к Django проекту
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')

import django
django.setup()

from mlmodels.llm.model_manager import LLMModelManager

def test_model_manager_step_by_step():
    """Пошаговая диагностика model_manager"""
    
    print("=== ДИАГНОСТИКА MODEL_MANAGER ===")
    
    # 1. Инициализация
    print("\n1. Инициализация LLMModelManager...")
    manager = LLMModelManager(model_key='gemma-2b', device='auto')
    print(f"   Модель: {manager.model_config['model_name']}")
    print(f"   Устройство: {manager.device}")
    
    # 2. Загрузка модели
    print("\n2. Загрузка модели...")
    success = manager.load_model(use_quantization=False)  # Без квантизации для диагностики
    if not success:
        print("❌ Не удалось загрузить модель")
        return
    
    print("✅ Модель загружена успешно")
    print(f"   Токенизатор: {type(manager.tokenizer).__name__}")
    print(f"   Модель: {type(manager.model).__name__}")
    
    # 3. Тестируем простейший промпт
    print("\n3. Тест простого промпта...")
    simple_prompt = "Привет!"
    
    try:
        # Токенизация
        print(f"   Промпт: '{simple_prompt}'")
        inputs = manager.tokenizer(simple_prompt, return_tensors="pt")
        print(f"   Токенизация успешна: {inputs['input_ids'].shape}")
        
        # Проверяем специальные токены
        print(f"   EOS токен: {manager.tokenizer.eos_token}")
        print(f"   EOS токен ID: {manager.tokenizer.eos_token_id}")
        print(f"   PAD токен: {manager.tokenizer.pad_token}")
        print(f"   PAD токен ID: {manager.tokenizer.pad_token_id}")
        
        # Генерация с минимальными параметрами
        print("\n4. Генерация с минимальными параметрами...")
        
        with torch.no_grad():
            input_length = inputs['input_ids'].shape[1]
            
            # Пробуем генерировать только 5 токенов
            outputs = manager.model.generate(
                **inputs,
                max_new_tokens=5,
                do_sample=False,  # Жадная генерация
                pad_token_id=manager.tokenizer.eos_token_id
            )
            
            print(f"   Входных токенов: {input_length}")
            print(f"   Выходных токенов: {outputs.shape}")
            
            # Декодируем весь выход
            full_output = manager.tokenizer.decode(outputs[0], skip_special_tokens=True)
            print(f"   Полный выход: '{full_output}'")
            
            # Декодируем только новую часть
            generated_ids = outputs[0][input_length:]
            generated_text = manager.tokenizer.decode(generated_ids, skip_special_tokens=True)
            print(f"   Только новая часть: '{generated_text}'")
            print(f"   Длина: {len(generated_text)}")
            
        # 5. Тестируем через model_manager.generate_text
        print("\n5. Тест через model_manager.generate_text()...")
        result = manager.generate_text(
            prompt=simple_prompt,
            max_length=5,
            temperature=0.1,
            do_sample=False
        )
        print(f"   Результат model_manager.generate_text(): '{result}'")
        print(f"   Длина результата: {len(result)}")
        
    except Exception as e:
        print(f"❌ Ошибка в тестировании: {e}")
        import traceback
        traceback.print_exc()

def test_different_prompts():
    """Тестируем разные типы промптов"""
    
    print("\n=== ТЕСТ РАЗЛИЧНЫХ ПРОМПТОВ ===")
    
    manager = LLMModelManager(model_key='gemma-2b', device='auto')
    if not manager.load_model(use_quantization=False):
        print("❌ Не удалось загрузить модель")
        return
    
    test_prompts = [
        "Привет",
        "Hello",
        "Что такое Python?",
        "Объясни переменные",
        "1 + 1 = ",
        "def hello():",
    ]
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n{i}. Промпт: '{prompt}'")
        
        try:
            # Прямая генерация
            inputs = manager.tokenizer(prompt, return_tensors="pt")
            with torch.no_grad():
                outputs = manager.model.generate(
                    **inputs,
                    max_new_tokens=10,
                    do_sample=False,
                    pad_token_id=manager.tokenizer.eos_token_id
                )
            
            input_length = inputs['input_ids'].shape[1]
            generated_ids = outputs[0][input_length:]
            generated_text = manager.tokenizer.decode(generated_ids, skip_special_tokens=True)
            
            print(f"   Прямая генерация: '{generated_text}'")
            
            # Через model_manager
            result = manager.generate_text(prompt, max_length=10, do_sample=False)
            print(f"   Через model_manager: '{result}'")
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")

def test_chat_template():
    """Тестируем с chat template для Gemma"""
    
    print("\n=== ТЕСТ CHAT TEMPLATE ===")
    
    manager = LLMModelManager(model_key='gemma-2b', device='auto')
    if not manager.load_model(use_quantization=False):
        print("❌ Не удалось загрузить модель")
        return
    
    # Проверяем, есть ли chat template
    if hasattr(manager.tokenizer, 'chat_template') and manager.tokenizer.chat_template:
        print("✅ Найден chat template")
        
        # Форматируем сообщение как чат
        messages = [
            {"role": "user", "content": "Привет! Как дела?"}
        ]
        
        try:
            formatted_prompt = manager.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            print(f"Отформатированный промпт: '{formatted_prompt}'")
            
            # Тестируем генерацию
            result = manager.generate_text(formatted_prompt, max_length=20)
            print(f"Результат с chat template: '{result}'")
            
        except Exception as e:
            print(f"❌ Ошибка с chat template: {e}")
    else:
        print("❌ Chat template не найден")

if __name__ == "__main__":
    test_model_manager_step_by_step()
    test_different_prompts()
    test_chat_template()
