"""
БЫСТРЫЙ СТАРТ - Создание студента Клементьева А.А.

Этот файл содержит пошаговую инструкцию для создания студента
с симуляцией обучения на основе графа навыков.
"""

print("""
🚀 БЫСТРЫЙ СТАРТ: Создание студента с попытками решения заданий

📋 ЧТО ДЕЛАЕТ СКРИПТ:
   • Создает студента: Клементьев Алексей Александрович
   • Генерирует траекторию обучения на основе графа навыков
   • Создает попытки решения заданий (правильные и неправильные)
   • Применяет BKT для обновления уровней освоения навыков
   • Валидирует логическую согласованность результата

🎯 ЦЕЛЕВОЙ РЕЗУЛЬТАТ:
   • 12 полностью освоенных навыков (уровень ≥ 0.9)
   • 8 частично освоенных навыков (уровень 0.3-0.9)
   • ~100-150 попыток решения заданий
   • Успешность ~70% (имитация реального обучения)

⚡ БЫСТРЫЙ ЗАПУСК:

1. Через Django management команду (рекомендуется):
   python manage.py create_student_with_attempts

2. Через Django shell:
   python manage.py shell
   exec(open('mlmodels/tests/create_student_with_attempts.py').read())

3. С кастомными параметрами:
   python manage.py create_student_with_attempts --mastered 15 --partial 10

4. Для воспроизводимости результатов:
   python manage.py create_student_with_attempts --seed 42

🔧 ДОПОЛНИТЕЛЬНЫЕ ОПЦИИ:
   --recreate     Пересоздать студента если уже существует
   --output-dir   Директория для экспорта данных
   --seed         Seed для одинаковых результатов

📊 ПРОВЕРКА РЕЗУЛЬТАТА:
   • В админке Django: /admin/student/studentprofile/
   • TaskAttempt модели: /admin/mlmodels/taskattempt/
   • StudentSkillMastery: /admin/mlmodels/studentskillmastery/

🧪 ПРЕДВАРИТЕЛЬНОЕ ТЕСТИРОВАНИЕ:
   python manage.py shell
   exec(open('mlmodels/tests/test_student_creator.py').read())

💾 ЭКСПОРТ ДАННЫХ:
   Результаты сохраняются в temp_dir/created_student_data.json

⚠️  ТРЕБОВАНИЯ:
   • В БД должны быть навыки (Skill)
   • В БД должны быть задания (Task) со связанными навыками
   • Навыки должны иметь корректные prerequisite связи

📖 ПОДРОБНАЯ ДОКУМЕНТАЦИЯ:
   См. файл mlmodels/tests/README.md
""")

# Проверяем готовность системы
try:
    import os
    import sys
    import django
    from pathlib import Path
    
    # Настройка Django
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
    django.setup()
    
    from skills.models import Skill
    from methodist.models import Task
    from django.contrib.auth.models import User
    
    print("\n🔍 ПРОВЕРКА ГОТОВНОСТИ СИСТЕМЫ:")
    
    # Проверка навыков
    skills_count = Skill.objects.count()
    print(f"   ✓ Навыков в БД: {skills_count}")
    
    # Проверка заданий
    tasks_count = Task.objects.count()
    tasks_with_skills = Task.objects.filter(skills__isnull=False).distinct().count()
    print(f"   ✓ Заданий в БД: {tasks_count}")
    print(f"   ✓ Заданий со связанными навыками: {tasks_with_skills}")
    
    # Проверка существующего студента
    username = "alex_klementev"
    student_exists = User.objects.filter(username=username).exists()
    print(f"   ✓ Студент {username} существует: {student_exists}")
    
    if skills_count > 0 and tasks_with_skills > 0:
        print("\n🎉 СИСТЕМА ГОТОВА К РАБОТЕ!")
        print("\n▶️  ЗАПУСТИТЕ КОМАНДУ:")
        print("   python manage.py create_student_with_attempts")
        
        if student_exists:
            print("\n⚠️  Для пересоздания студента добавьте --recreate")
    else:
        print("\n❌ СИСТЕМА НЕ ГОТОВА:")
        if skills_count == 0:
            print("   • Нет навыков в БД")
        if tasks_with_skills == 0:
            print("   • Нет заданий со связанными навыками")
            
except Exception as e:
    print(f"\n❌ Ошибка проверки: {e}")
    print("   Возможно, Django не настроен или отсутствуют зависимости")
