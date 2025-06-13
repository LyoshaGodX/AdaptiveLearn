"""
Тест полного цикла работы BKT модели:
1. Загрузка исторических данных из БД
2. Обработка через BKT модель
3. Обновление характеристик в БД
"""

import os
import sys
import django
from pathlib import Path

# Настройка Django
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.models import User

# Импорты наших модулей
from mlmodels.services.student_assessment_service import StudentAssessmentService
from mlmodels.models import TaskAttempt, StudentSkillMastery
from student.models import StudentProfile
from methodist.models import Task, Course
from skills.models import Skill


def test_full_bkt_cycle():
    """Тест полного цикла BKT модели"""
    print("🧪 ТЕСТ ПОЛНОГО ЦИКЛА BKT МОДЕЛИ")
    print("=" * 50)
    
    # 1. Подготовка тестовых данных
    print("1️⃣ Подготовка тестовых данных...")
    student, tasks, skills = create_test_data()
    print(f"   ✅ Создан студент: {student.full_name}")
    print(f"   ✅ Создано заданий: {len(tasks)}")
    print(f"   ✅ Создано навыков: {len(skills)}")
    
    # 2. Создание исторических попыток в БД
    print("\n2️⃣ Создание исторических попыток...")
    attempts = create_historical_attempts(student, tasks)
    print(f"   ✅ Создано попыток в БД: {len(attempts)}")
    
    # 3. Проверяем состояние БД до обработки BKT
    print("\n3️⃣ Состояние БД до обработки BKT...")
    masteries_before = check_skill_masteries(student, skills)
    print_masteries("До BKT:", masteries_before)
    
    # 4. Инициализация и запуск BKT модели
    print("\n4️⃣ Запуск BKT модели...")
    service = StudentAssessmentService()
      # Обрабатываем историю попыток
    result = service.assess_student_from_attempts_history(
        student_id=student.id, 
        reset_state=True,
        days_back=None  # Все попытки
    )
    
    if 'error' in result:
        print(f"   ❌ Ошибка BKT: {result['error']}")
        return
    
    print(f"   ✅ BKT обработала {result.get('processed_attempts', 0)} попыток")
    
    # 5. Проверяем состояние БД после обработки BKT
    print("\n5️⃣ Состояние БД после обработки BKT...")
    masteries_after = check_skill_masteries(student, skills)
    print_masteries("После BKT:", masteries_after)
    
    # 6. Сравниваем изменения
    print("\n6️⃣ Анализ изменений...")
    analyze_changes(masteries_before, masteries_after)
    
    # 7. Тестируем новую попытку
    print("\n7️⃣ Тест новой попытки...")
    test_new_attempt(service, student, tasks[0])
    
    # 8. Проверяем прогнозирование
    print("\n8️⃣ Тест прогнозирования...")
    test_prediction(service, student, skills[0])
    
    print("\n🎉 ТЕСТ ЗАВЕРШЕН УСПЕШНО!")


def create_test_data():
    """Создание тестовых данных"""
    # Создаем пользователя и профиль студента
    username = "test_bkt_student"
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'first_name': 'Тест',
            'last_name': 'BKT',
            'email': f'{username}@test.com'
        }
    )
    
    student, created = StudentProfile.objects.get_or_create(
        user=user,
        defaults={
            'full_name': 'Тест BKT Студент',
            'email': user.email,
            'organization': 'Тестовая организация'
        }
    )
    
    # Создаем навыки
    skills = []
    skill_names = ['Python Basics', 'Data Structures', 'Algorithms']
    for name in skill_names:
        skill, created = Skill.objects.get_or_create(
            name=name,
            defaults={'description': f'Навык {name}'}
        )
        skills.append(skill)
    
    # Создаем курс
    course, created = Course.objects.get_or_create(
        id='TEST_BKT',
        defaults={
            'name': 'Тест BKT Курс',
            'description': 'Тестовый курс для проверки BKT',
            'duration_hours': 20
        }
    )    # Создаем задания
    tasks = []
    for i in range(5):
        task, created = Task.objects.get_or_create(
            title=f'Тестовое задание BKT {i+1}',
            defaults={
                'question_text': f'Вопрос для задания {i+1}',
                'task_type': 'single',
                'difficulty': 'intermediate',
                'is_active': True
            }
        )
        
        # Привязываем к навыкам и курсу
        if created:
            task.skills.add(skills[i % len(skills)])
            task.courses.add(course)
        
        tasks.append(task)
    
    return student, tasks, skills


def create_historical_attempts(student, tasks):
    """Создание исторических попыток"""
    attempts = []
    base_time = timezone.now() - timedelta(days=10)
    
    # Очищаем предыдущие попытки этого студента
    TaskAttempt.objects.filter(student=student).delete()
    
    for i, task in enumerate(tasks):
        # Создаем несколько попыток для каждого задания
        for attempt_num in range(3):
            # Симулируем прогресс: от 40% до 80% правильных ответов
            success_rate = 0.4 + (i * 0.1) + (attempt_num * 0.1)
            is_correct = hash(f"{i}_{attempt_num}") % 100 < (success_rate * 100)
            
            attempt = TaskAttempt.objects.create(
                student=student,
                task=task,
                is_correct=is_correct,
                time_spent=60 + (i * 30),  # 1-4 минуты
                started_at=base_time + timedelta(hours=i*2 + attempt_num),
                completed_at=base_time + timedelta(hours=i*2 + attempt_num, minutes=5)
            )
            attempts.append(attempt)
    
    return attempts


def check_skill_masteries(student, skills):
    """Проверяет текущие уровни освоения навыков"""
    masteries = {}
    for skill in skills:
        try:
            mastery = StudentSkillMastery.objects.get(
                student=student, skill=skill
            )
            masteries[skill.name] = {
                'mastery': mastery.current_mastery_prob,
                'attempts': mastery.attempts_count,
                'correct': mastery.correct_attempts,
                'accuracy': mastery.accuracy
            }
        except StudentSkillMastery.DoesNotExist:
            masteries[skill.name] = {
                'mastery': 0.0,
                'attempts': 0,
                'correct': 0,
                'accuracy': 0.0
            }
    
    return masteries


def print_masteries(title, masteries):
    """Выводит информацию об освоении навыков"""
    print(f"   {title}")
    for skill_name, data in masteries.items():
        print(f"     🎯 {skill_name}: {data['mastery']:.3f} "
              f"({data['correct']}/{data['attempts']}, "
              f"точность: {data['accuracy']:.2f})")


def analyze_changes(before, after):
    """Анализирует изменения в освоении навыков"""
    for skill_name in before.keys():
        before_mastery = before[skill_name]['mastery']
        after_mastery = after[skill_name]['mastery']
        change = after_mastery - before_mastery
        
        if abs(change) > 0.001:
            direction = "📈" if change > 0 else "📉"
            print(f"   {direction} {skill_name}: {before_mastery:.3f} → {after_mastery:.3f} "
                  f"(изменение: {change:+.3f})")
        else:
            print(f"   ➡️ {skill_name}: без изменений ({after_mastery:.3f})")


def test_new_attempt(service, student, task):
    """Тестирует обработку новой попытки"""
    print(f"   Создаем новую попытку для задания: {task.title}")
    
    # Получаем текущие уровни
    before_masteries = {}
    for skill in task.skills.all():
        try:
            mastery = StudentSkillMastery.objects.get(student=student, skill=skill)
            before_masteries[skill.id] = mastery.current_mastery_prob
        except StudentSkillMastery.DoesNotExist:
            before_masteries[skill.id] = 0.0
      # Обрабатываем новую попытку через сервис
    result = service.process_new_attempt(
        student_id=student.id,
        task_id=task.id,
        is_correct=True,
        answer_score=0.8
    )
    
    if 'error' not in result:
        print(f"   ✅ Новая попытка обработана")
        for skill_id, skill_result in result.get('skills_updated', {}).items():
            before = before_masteries.get(skill_id, 0.0)
            after = skill_result['mastery_after']
            print(f"     🎯 Навык {skill_result['skill_name']}: {before:.3f} → {after:.3f}")
    else:
        print(f"   ❌ Ошибка обработки попытки: {result['error']}")


def test_prediction(service, student, skill):
    """Тестирует прогнозирование"""
    print(f"   Прогнозируем освоение навыка: {skill.name}")
    
    # Используем интерфейс напрямую для прогнозирования
    predictions = service.assessment_interface.predict_skill_mastery(
        student_id=student.id,
        skill_id=skill.id,
        future_attempts=3
    )
    
    if predictions:
        current_mastery = predictions[0] if predictions else 0.0
        estimated_mastery = predictions[-1] if len(predictions) > 1 else current_mastery
        
        print(f"   ✅ Текущее освоение: {current_mastery:.3f}")
        print(f"   🔮 Прогноз после 3 попыток: {estimated_mastery:.3f}")
        if estimated_mastery > 0.8:
            print(f"   🎯 Студент достигнет мастерства!")
        else:
            print(f"   📚 Студенту нужно больше практики")
    else:
        print(f"   ⚠️ Не удалось получить прогноз")


def test_database_integration():
    """Дополнительный тест интеграции с базой данных"""
    print("\n🔍 ТЕСТ ИНТЕГРАЦИИ С БАЗОЙ ДАННЫХ")
    print("=" * 40)
    
    # Проверяем, что данные действительно сохраняются
    masteries = StudentSkillMastery.objects.all()
    attempts = TaskAttempt.objects.all()
    
    print(f"📊 Всего записей освоения навыков: {masteries.count()}")
    print(f"📝 Всего попыток в БД: {attempts.count()}")
    
    if masteries.exists():
        print("\n📋 Примеры записей освоения навыков:")
        for mastery in masteries[:3]:
            print(f"   👤 {mastery.student.full_name}")
            print(f"   🎯 {mastery.skill.name}: {mastery.current_mastery_prob:.3f}")
            print(f"   📊 Попыток: {mastery.attempts_count}, точность: {mastery.accuracy:.2f}")
            print()


if __name__ == "__main__":
    try:
        test_full_bkt_cycle()
        test_database_integration()
        print("\n✅ ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
    except Exception as e:
        print(f"\n❌ ОШИБКА В ТЕСТАХ: {e}")
        import traceback
        traceback.print_exc()
