#!/usr/bin/env python3
"""
Простой тест LLM для диагностики
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

def test_llm():
    print("=== ТЕСТ LLM ===")
    
    # Простой промпт
    prompt = "Привет! Как дела?"
    
    model_name = 'google/gemma-2b-it'
    
    try:
        print(f"Загружаем модель {model_name}...")
        
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            trust_remote_code=True,
            torch_dtype=torch.float32
        )
        
        print("Модель загружена!")
        
        # Тестируем генерацию
        inputs = tokenizer(prompt, return_tensors="pt")
        input_length = inputs['input_ids'].shape[1]
        
        print(f"Промпт: '{prompt}'")
        print(f"Входных токенов: {input_length}")
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=50,
                temperature=0.7,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
        
        generated_ids = outputs[0][input_length:]
        generated_text = tokenizer.decode(generated_ids, skip_special_tokens=True)
        
        print(f"Сгенерированных токенов: {len(generated_ids)}")
        print(f"Ответ: '{generated_text}'")
        
        if not generated_text.strip():
            print("❌ ПУСТОЙ ОТВЕТ!")
        else:
            print("✅ Ответ получен")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    test_llm()
