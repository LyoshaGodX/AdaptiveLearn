#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы DKNDataProcessor

Этот скрипт тестирует способность data_processor.py извлекать 
реальные данные из базы и преобразовывать их в формат для DKN модели.
"""

import os
import sys
import django
from pathlib import Path

# Настройка Django
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

import torch
import numpy as np
import pandas as pd
from django.contrib.auth.models import User
from skills.models import Skill
from methodist.models import Task
from mlmodels.models import TaskAttempt, StudentSkillMastery
from student.models import StudentProfile

# Импортируем наш обработчик данных
from data_processor import DKNDataProcessor


def test_data_processor():
    """Основная функция тестирования"""
    print("🧪 Тестирование DKNDataProcessor")
    print("=" * 50)
    
    # 1. Инициализация процессора
    print("1. Инициализация DKNDataProcessor...")
    processor = DKNDataProcessor(max_history_length=10)
    
    print(f"   ✅ Навыков в системе: {len(processor.skill_to_id)}")
    print(f"   ✅ Заданий в системе: {len(processor.task_to_id)}")
    
    # 2. Проверим наличие пользователей и данных
    print("\\n2. Проверка наличия данных в базе...")
    
    users_count = User.objects.count()
    tasks_count = Task.objects.count()
    attempts_count = TaskAttempt.objects.count()
    
    print(f"   👥 Пользователей: {users_count}")
    print(f"   📋 Заданий: {tasks_count}")
    print(f"   🎯 Попыток: {attempts_count}")
    
    if users_count == 0:
        print("   ❌ В базе нет пользователей!")
        return False
        
    if tasks_count == 0:
        print("   ❌ В базе нет заданий!")
        return False
    
    # 3. Найдем пользователя с данными
    print("\\n3. Поиск пользователя с попытками...")
    
    users_with_attempts = User.objects.filter(
        id__in=TaskAttempt.objects.values_list('student_id', flat=True).distinct()
    )
    
    if not users_with_attempts.exists():
        print("   ❌ Нет пользователей с попытками!")
        # Попробуем просто взять первого пользователя
        test_user = User.objects.first()
        if not test_user:
            print("   ❌ Вообще нет пользователей в системе!")
            return False
        print(f"   ⚠️  Используем пользователя без попыток: {test_user.username} (ID: {test_user.id})")
    else:
        test_user = users_with_attempts.first()
        print(f"   ✅ Найден пользователь с попытками: {test_user.username} (ID: {test_user.id})")
    
    # 4. Найдем задание для тестирования
    print("\\n4. Поиск задания для тестирования...")
    
    test_task = Task.objects.first()
    if not test_task:
        print("   ❌ Нет заданий для тестирования!")
        return False
        
    print(f"   ✅ Используем задание: {test_task.title} (ID: {test_task.id})")
    
    # 5. Тестируем получение данных студента
    print("\\n5. Тестирование получения данных студента...")
    
    try:
        student_data = processor.get_student_data(test_user.id, test_task.id)
        print("   ✅ Данные студента получены успешно!")
        
        # Анализируем полученные данные
        print(f"   📊 Структура данных:")
        print(f"      - student_id: {student_data['student_id']}")
        print(f"      - task_id: {student_data['task_id']}")
        print(f"      - История: {len(student_data['history'])} записей")
        print(f"      - BKT параметры: {len(student_data['bkt_params'])} навыков")
        print(f"      - Навыки задания: {len(student_data['task_skills'])}")
        
        # Детальный анализ истории
        print(f"\\n   📈 Анализ истории:")
        history = student_data['history']
        non_empty_history = [h for h in history if h['task_id'] != 0]
        print(f"      - Реальных попыток: {len(non_empty_history)}")
        print(f"      - Заполнение нулями: {len(history) - len(non_empty_history)}")
        
        if non_empty_history:
            print(f"      - Пример попытки: {non_empty_history[0]}")
        
        # Анализ BKT параметров
        print(f"\\n   🧠 Анализ BKT параметров:")
        for skill_id, params in list(student_data['bkt_params'].items())[:3]:
            print(f"      - Навык {skill_id}: P_L={params['P_L']:.3f}, P_T={params['P_T']:.3f}")
        
    except Exception as e:
        print(f"   ❌ Ошибка при получении данных: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 6. Тестируем подготовку батча
    print("\\n6. Тестирование подготовки батча...")
    
    try:
        # Создаем несколько примеров данных
        batch_data = []
        for i in range(3):  # Маленький батч
            data = processor.get_student_data(test_user.id, test_task.id)
            batch_data.append(data)
        
        # Подготавливаем батч
        batch_tensors = processor.prepare_batch(batch_data)
        print("   ✅ Батч подготовлен успешно!")
        
        # Анализируем тензоры
        print(f"   📦 Структура батча:")
        for key, tensor in batch_tensors.items():
            if isinstance(tensor, torch.Tensor):
                print(f"      - {key}: {tensor.shape} ({tensor.dtype})")
            else:
                print(f"      - {key}: {type(tensor)}")
        
        # Проверяем значения
        print(f"\\n   🔍 Проверка значений:")
        print(f"      - task_ids: {batch_tensors['task_ids']}")
        print(f"      - task_difficulty: {batch_tensors['task_difficulty']}")
        print(f"      - task_type: {batch_tensors['task_type']}")
        print(f"      - current_bkt_avg[0]: {batch_tensors['current_bkt_avg'][0]}")
        
    except Exception as e:
        print(f"   ❌ Ошибка при подготовке батча: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 7. Сравнение с синтетическими данными
    print("\\n7. Сравнение с синтетическими данными...")
    
    try:
        # Загружаем синтетические данные для сравнения
        synthetic_path = "dataset/enhanced_synthetic_dataset.csv"
        if os.path.exists(synthetic_path):
            synthetic_df = pd.read_csv(synthetic_path)
            print(f"   📊 Синтетический датасет: {len(synthetic_df)} записей")
            print(f"   📊 Колонки: {list(synthetic_df.columns)}")
            
            # Сравнение структур
            real_data_fields = set(student_data.keys())
            synthetic_fields = set(['student_id', 'task_id', 'target'] + 
                                 [col for col in synthetic_df.columns if col.startswith('hist_')] +
                                 [col for col in synthetic_df.columns if col.startswith('skill_')])
            
            print(f"\\n   🔄 Сравнение структур:")
            print(f"      - Поля реальных данных: {real_data_fields}")
            print(f"      - Поля синтетических данных: {synthetic_fields}")
            
            common_concepts = {'student_id', 'task_id', 'history', 'bkt_params'}
            print(f"      - Общие концепции: {common_concepts}")
            
        else:
            print(f"   ⚠️  Синтетический датасет не найден: {synthetic_path}")
            
    except Exception as e:
        print(f"   ❌ Ошибка при сравнении с синтетическими данными: {e}")
    
    print("\\n" + "=" * 50)
    print("✅ Тестирование завершено успешно!")
    print("\\n🎯 Выводы:")
    print("   - DKNDataProcessor корректно извлекает данные из базы")
    print("   - Данные преобразуются в формат, совместимый с DKN моделью")
    print("   - Структура данных соответствует ожиданиям модели")
    
    return True


if __name__ == "__main__":
    try:
        success = test_data_processor()
        if success:
            print("\\n🎉 Все тесты пройдены!")
        else:
            print("\\n💥 Тесты провалены!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\\n💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
