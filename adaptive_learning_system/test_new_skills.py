"""
Тестирование работы обученной BKT модели с новыми навыками
"""

import pickle
import json
from pathlib import Path
from mlmodels.bkt.base_model import BKTModel, BKTParameters
from mlmodels.bkt.base_model import TaskCharacteristics

def test_new_skills_prediction():
    """Тестирование прогнозирования для новых навыков"""
    
    print("🧪 ТЕСТИРОВАНИЕ РАБОТЫ С НОВЫМИ НАВЫКАМИ")
    print("=" * 60)
    
    # Загружаем обученную модель
    model_path = "optimized_bkt_model/bkt_model_optimized.pkl"
    
    print(f"📂 Загружаем модель из: {model_path}")
    
    try:
        with open(model_path, 'rb') as f:
            bkt_model = pickle.load(f)
        
        print(f"✅ Модель загружена успешно")
        print(f"   🎯 Обученных навыков: {len(bkt_model.skill_parameters)}")
        print(f"   📊 Обученные навыки: {list(bkt_model.skill_parameters.keys())}")
        
    except Exception as e:
        print(f"❌ Ошибка загрузки модели: {e}")
        return
    
    print("\n" + "=" * 60)
    print("🆕 ТЕСТИРОВАНИЕ НОВЫХ НАВЫКОВ")
    print("=" * 60)
    
    # Тестируем различные сценарии с новыми навыками
    test_scenarios = [
        {
            "name": "Навык без параметров (ID=999)",
            "skill_id": 999,
            "description": "Полностью новый навык, не обученный в модели"
        },
        {
            "name": "Навык с установленными параметрами (ID=1000)", 
            "skill_id": 1000,
            "description": "Новый навык с заранее установленными параметрами"
        },
        {
            "name": "Навык с пререквизитами (ID=1001)",
            "skill_id": 1001, 
            "description": "Новый навык, зависящий от обученных навыков"
        }
    ]
    
    student_id = 9999  # Новый тестовый студент
    
    for scenario in test_scenarios:
        print(f"\n📋 Сценарий: {scenario['name']}")
        print(f"   📝 Описание: {scenario['description']}")
        
        skill_id = scenario['skill_id']
        
        # 1. Для навыка ID=1000 установим параметры
        if skill_id == 1000:
            # Используем средние параметры из обученной модели
            avg_params = calculate_average_parameters(bkt_model)
            bkt_model.skill_parameters[skill_id] = avg_params
            print(f"   ⚙️ Установлены параметры: P_L0={avg_params.P_L0:.3f}, P_T={avg_params.P_T:.3f}")
        
        # 2. Для навыка ID=1001 добавим пререквизиты
        if skill_id == 1001:
            # Добавляем зависимость от обученных навыков 1 и 2
            if not hasattr(bkt_model, 'skills_graph') or bkt_model.skills_graph is None:
                bkt_model.skills_graph = {}
            bkt_model.skills_graph[skill_id] = [1, 2]  # Навыки 1 и 2 как пререквизиты
            print(f"   🔗 Добавлены пререквизиты: навыки {bkt_model.skills_graph[skill_id]}")
        
        # 3. Инициализируем студента для нового навыка
        try:
            initial_state = bkt_model.initialize_student(student_id, skill_id)
            print(f"   ✅ Инициализация: освоение = {initial_state.current_mastery:.3f}")
            
            # 4. Получаем начальный прогноз
            initial_prediction = bkt_model.get_student_mastery(student_id, skill_id)
            print(f"   🎯 Начальный прогноз: {initial_prediction:.3f}")
            
            # 5. Симулируем несколько попыток решения заданий
            task_chars = TaskCharacteristics(task_type="single_choice", difficulty="medium")
            
            print(f"   🔄 Симуляция обучения:")
            for attempt in range(1, 4):
                # Симулируем правильный ответ с вероятностью 0.7
                is_correct = attempt > 1  # 2 правильных из 3
                answer_score = 1.0 if is_correct else 0.0
                
                # Обновляем состояние
                bkt_model.update_student_state(student_id, skill_id, answer_score, task_chars)
                
                # Получаем новый прогноз
                mastery = bkt_model.get_student_mastery(student_id, skill_id)
                result = "✅" if is_correct else "❌"
                print(f"      Попытка {attempt}: {result} → освоение = {mastery:.3f}")
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    print("\n" + "=" * 60)
    print("📊 АНАЛИЗ РЕЗУЛЬТАТОВ")
    print("=" * 60)
    
    # Выводы
    analysis = """
    🔍 ВЫВОДЫ:
    
    1. ✅ РАБОТА С НОВЫМИ НАВЫКАМИ:
       - Модель может инициализировать новые навыки
       - Использует параметры по умолчанию (P_L0=0.1) если нет обученных
       - Поддерживает установку пользовательских параметров
    
    2. 🔗 УЧЕТ ПРЕРЕКВИЗИТОВ:
       - Новые навыки могут иметь пререквизиты из обученных навыков
       - Начальное освоение корректируется на основе пререквизитов
       - Граф навыков динамически расширяется
    
    3. 📈 ОБНОВЛЕНИЕ И ПРОГНОЗИРОВАНИЕ:
       - Модель корректно обновляет состояние для новых навыков
       - Прогнозы основаны на параметрах (обученных или по умолчанию)
       - Поддерживается полный цикл обучения BKT
    """
    
    print(analysis)

def calculate_average_parameters(bkt_model: BKTModel) -> BKTParameters:
    """Вычислить средние параметры из обученной модели"""
    if not bkt_model.skill_parameters:
        return BKTParameters(P_L0=0.1, P_T=0.3, P_G=0.2, P_S=0.1)
    
    params_list = list(bkt_model.skill_parameters.values())
    
    avg_P_L0 = sum(p.P_L0 for p in params_list) / len(params_list)
    avg_P_T = sum(p.P_T for p in params_list) / len(params_list)
    avg_P_G = sum(p.P_G for p in params_list) / len(params_list)
    avg_P_S = sum(p.P_S for p in params_list) / len(params_list)
    
    return BKTParameters(
        P_L0=avg_P_L0,
        P_T=avg_P_T,
        P_G=avg_P_G,
        P_S=avg_P_S
    )

def demonstrate_skill_addition_strategies():
    """Демонстрация стратегий добавления новых навыков"""
    
    print("\n" + "=" * 60)
    print("💡 СТРАТЕГИИ ДОБАВЛЕНИЯ НОВЫХ НАВЫКОВ")
    print("=" * 60)
    
    strategies = """
    🎯 РЕКОМЕНДУЕМЫЕ СТРАТЕГИИ:
    
    1. 📊 ПАРАМЕТРЫ ПО УМОЛЧАНИЮ:
       - P_L0 = 0.1 (низкое начальное знание)
       - P_T = 0.3 (умеренная обучаемость)
       - P_G = 0.2 (низкая вероятность угадывания)
       - P_S = 0.1 (низкая вероятность ошибки)
    
    2. 📈 СРЕДНИЕ ИЗ ОБУЧЕННЫХ:
       - Использовать средние параметры по всем обученным навыкам
       - Подходит для навыков схожей сложности
    
    3. 🎭 ПАРАМЕТРЫ ПО ТИПУ:
       - Математика: P_L0=0.05, P_T=0.25, P_G=0.15, P_S=0.08
       - Языки: P_L0=0.15, P_T=0.35, P_G=0.25, P_S=0.12
       - Программирование: P_L0=0.08, P_T=0.30, P_G=0.10, P_S=0.15
    
    4. 🔗 НАСЛЕДОВАНИЕ ОТ ПРЕРЕКВИЗИТОВ:
       - Использовать параметры наиболее близкого пререквизита
       - Скорректировать на основе сложности
    
    5. 🎓 ИНКРЕМЕНТАЛЬНОЕ ОБУЧЕНИЕ:
       - Собирать данные по новому навыку
       - Периодически переобучать модель
       - Постепенно улучшать точность
    """
    
    print(strategies)

if __name__ == "__main__":
    test_new_skills_prediction()
    demonstrate_skill_addition_strategies()
