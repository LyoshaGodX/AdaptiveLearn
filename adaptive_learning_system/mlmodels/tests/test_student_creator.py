"""
Простой тест создания студента с попытками.

Проверяет базовую функциональность без полного создания студента.

Использование:
    python manage.py shell
    exec(open('mlmodels/tests/test_student_creator.py').read())
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

from mlmodels.tests.create_student_with_attempts import StudentCreatorWithAttempts
from django.contrib.auth.models import User
from student.models import StudentProfile
from methodist.models import Task
from skills.models import Skill


def test_basic_functionality():
    """Тест базовой функциональности"""
    print("🧪 Тестирование базовой функциональности...")
    
    creator = StudentCreatorWithAttempts()
    
    # Тест инициализации траектории
    creator.trajectory_builder.initialize()
    print(f"✓ Траектория инициализирована, навыков: {len(creator.trajectory_builder.skills_graph)}")
    
    # Тест генерации целевых уровней
    target_mastery = creator.generate_target_mastery_from_trajectory()
    print(f"✓ Целевые уровни сгенерированы: {len(target_mastery)} навыков")
    
    # Статистика целевых уровней
    mastered = sum(1 for level in target_mastery.values() if level >= 0.9)
    partial = sum(1 for level in target_mastery.values() if 0.3 <= level < 0.9)
    unlearned = sum(1 for level in target_mastery.values() if level < 0.3)
    
    print(f"   - Полное освоение: {mastered}")
    print(f"   - Частичное освоение: {partial}")
    print(f"   - Не изучено: {unlearned}")
    
    return True


def test_data_availability():
    """Тест доступности данных в БД"""
    print("\n📊 Проверка доступности данных в БД...")
    
    # Проверяем навыки
    skills_count = Skill.objects.count()
    print(f"✓ Навыков в БД: {skills_count}")
    
    # Проверяем задания
    tasks_count = Task.objects.count()
    print(f"✓ Заданий в БД: {tasks_count}")
    
    # Проверяем связи заданий и навыков
    tasks_with_skills = Task.objects.filter(skills__isnull=False).distinct().count()
    print(f"✓ Заданий со связанными навыками: {tasks_with_skills}")
    
    if tasks_with_skills == 0:
        print("⚠️  Нет заданий со связанными навыками - создание попыток может не работать")
        return False
    
    # Примеры заданий по навыкам
    print(f"\n📝 Примеры заданий по навыкам:")
    for skill in Skill.objects.all()[:5]:
        task_count = skill.tasks.count()
        print(f"   • {skill.name}: {task_count} заданий")
    
    return True


def test_student_creation_logic():
    """Тест логики создания студента (без сохранения)"""
    print("\n👨‍🎓 Тест логики создания студента...")
    
    creator = StudentCreatorWithAttempts()
    
    # Проверяем, что пользователь не существует
    username = "alex_klementev"
    exists_before = User.objects.filter(username=username).exists()
    print(f"✓ Пользователь {username} существует: {exists_before}")
    
    # Проверяем данные для создания
    full_name = "Клементьев Алексей Александрович"
    email = "Alex0.oKlem@gmail.com"
    organization = "РГПУ им. Герцена"
    
    print(f"✓ Данные для создания:")
    print(f"   - ФИО: {full_name}")
    print(f"   - Email: {email}")
    print(f"   - Организация: {organization}")
    
    return True


def test_attempt_creation_logic():
    """Тест логики создания попыток"""
    print("\n📝 Тест логики создания попыток...")
    
    creator = StudentCreatorWithAttempts()
    creator.trajectory_builder.initialize()
    
    # Берем первый навык с заданиями
    test_skill = None
    for skill in Skill.objects.all():
        if skill.tasks.exists():
            test_skill = skill
            break
    
    if not test_skill:
        print("❌ Не найден навык с заданиями для тестирования")
        return False
    
    print(f"✓ Тестовый навык: {test_skill.name}")
    print(f"   - Заданий: {test_skill.tasks.count()}")
    
    # Тестируем параметры для разных уровней освоения
    test_levels = [0.95, 0.6, 0.2]
    for level in test_levels:
        print(f"   - Уровень {level}: ", end="")
        
        if level >= 0.9:
            expected_attempts = "8-15, высокая успешность"
        elif level >= 0.3:
            expected_attempts = "5-10, средняя успешность"
        else:
            expected_attempts = "2-5, низкая успешность"
        
        print(expected_attempts)
    
    return True


def main():
    """Запуск всех тестов"""
    print("🚀 Запуск тестов создания студента...\n")
    
    try:
        test1 = test_basic_functionality()
        test2 = test_data_availability()
        test3 = test_student_creation_logic()
        test4 = test_attempt_creation_logic()
        
        if all([test1, test2, test3, test4]):
            print("\n✅ Все тесты прошли успешно!")
            print("\n🎯 Готов к созданию реального студента с командой:")
            print("   python manage.py create_student_with_attempts")
        else:
            print("\n⚠️ Некоторые тесты выявили проблемы")
        
    except Exception as e:
        print(f"\n❌ Ошибка в тестах: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
