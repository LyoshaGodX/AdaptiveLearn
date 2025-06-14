"""
Простой тест для проверки построения траектории обучения.

Использование:
    python manage.py shell
    exec(open('mlmodels/tests/test_trajectory_builder.py').read())
"""

import os
import sys
import django
from pathlib import Path

# Настройка Django
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

from mlmodels.tests.learning_trajectory_builder import LearningTrajectoryBuilder


def test_trajectory_building():
    """Тест построения траектории"""
    print("🧪 Тестирование построения траектории обучения...")
    
    builder = LearningTrajectoryBuilder()
    builder.initialize()
    
    # Тест симуляции студента
    result = builder.simulate_student_learning(
        target_mastered_count=5,
        target_partial_count=3
    )
    
    print(f"✓ Результат симуляции: {type(result)}")
    
    if isinstance(result, tuple) and len(result) == 2:
        mastery, learning_steps = result
        print(f"✓ Mastery: {type(mastery)}, размер: {len(mastery)}")
        print(f"✓ Learning steps: {type(learning_steps)}, размер: {len(learning_steps)}")
        
        # Тест получения доступных навыков
        available = builder.get_available_skills(mastery)
        print(f"✓ Доступных навыков: {len(available)}")
        
        # Тест рекомендаций
        recommendations = builder.get_learning_recommendations(mastery, limit=5)
        print(f"✓ Рекомендаций: {len(recommendations)}")
        
        # Тест валидации
        is_valid, errors = builder.validate_mastery_consistency(mastery)
        print(f"✓ Валидация: {'OK' if is_valid else 'Ошибки'}")
        if errors:
            print(f"   Ошибок: {len(errors)}")
            for error in errors[:2]:
                print(f"   - {error}")
        
        # Примеры данных
        print(f"\n📝 ПРИМЕРЫ ДАННЫХ:")
        
        # Пример освоенных навыков
        mastered = [(k, v) for k, v in mastery.items() if v >= 0.9]
        print(f"   Освоенных навыков: {len(mastered)}")
        for skill_id, level in mastered[:3]:
            name = builder.skill_info[skill_id].name
            print(f"     • {name}: {level:.2f}")
        
        # Пример шагов обучения
        print(f"   Шагов обучения: {len(learning_steps)}")
        for step in learning_steps[:3]:
            print(f"     • Шаг {step['step']}: {step['skill_name']} ({step['mastery_level']:.2f})")
        
        # Пример рекомендаций
        print(f"   Рекомендаций: {len(recommendations)}")
        for rec in recommendations[:3]:
            print(f"     • {rec['skill_name']} (приоритет: {rec['priority_score']:.1f})")
        
        return True
    else:
        print(f"❌ Неожиданный результат: {result}")
        return False


def test_export():
    """Тест экспорта данных"""
    print("\n💾 Тестирование экспорта...")
    
    builder = LearningTrajectoryBuilder()
    builder.initialize()
    
    mastery, learning_steps = builder.simulate_student_learning(
        target_mastered_count=3,
        target_partial_count=2
    )
    
    # Тест экспорта
    temp_dir = Path(__file__).parent.parent.parent / 'temp_dir'
    builder.export_trajectory_data(mastery, learning_steps, str(temp_dir))
    
    # Проверяем созданный файл
    export_file = temp_dir / 'student_learning_trajectory.json'
    if export_file.exists():
        print(f"✓ Файл экспортирован: {export_file.stat().st_size} bytes")
        
        # Проверяем содержимое
        import json
        with open(export_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✓ Структура данных:")
        for key in data.keys():
            print(f"   - {key}")
        
        return True
    else:
        print(f"❌ Файл не создан")
        return False


def main():
    """Запуск всех тестов"""
    print("🚀 Запуск тестов построения траектории...\n")
    
    try:
        success1 = test_trajectory_building()
        success2 = test_export()
        
        if success1 and success2:
            print("\n✅ Все тесты прошли успешно!")
        else:
            print("\n⚠️ Некоторые тесты не прошли")
        
    except Exception as e:
        print(f"\n❌ Ошибка в тестах: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
