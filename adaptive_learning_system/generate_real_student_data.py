"""
Скрипт для генерации реальных данных о попытках студента:
1. Выгружает студента из БД
2. Находит курсы, на которые он записан
3. Находит задания этих курсов
4. Генерирует записи о попытках (по 2 попытки на задание)
5. Загружает данные в БД
"""

import os
import sys
import django
from pathlib import Path

# Настройка Django
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

import random
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import transaction

# Импорты наших моделей
from student.models import StudentProfile, StudentCourseEnrollment
from methodist.models import Task, Course
from skills.models import Skill
from mlmodels.models import TaskAttempt, StudentSkillMastery


def main():
    """Основная функция"""
    print("🎓 ГЕНЕРАТОР РЕАЛЬНЫХ ДАННЫХ О ПОПЫТКАХ СТУДЕНТА")
    print("=" * 60)
    
    # 1. Выгружаем студентов из БД
    print("1️⃣ Поиск студентов в базе данных...")
    students = get_students_from_db()
    
    if not students:
        print("   ❌ Студенты не найдены. Создаем тестового студента...")
        student = create_test_student()
    else:
        print(f"   ✅ Найдено студентов: {len(students)}")
        student = select_student(students)
    
    print(f"   👤 Выбран студент: {student.full_name}")
    
    # 2. Проверяем записи на курсы
    print(f"\n2️⃣ Проверка записей на курсы для {student.full_name}...")
    enrollments = check_course_enrollments(student)
    
    if not enrollments:
        print("   ❌ Студент не записан на курсы. Записываем на доступные курсы...")
        enrollments = enroll_student_to_courses(student)
    
    print(f"   ✅ Студент записан на {len(enrollments)} курсов:")
    for enrollment in enrollments:
        print(f"     📚 {enrollment.course.name}")
    
    # 3. Находим задания курсов
    print(f"\n3️⃣ Поиск заданий для курсов...")
    course_tasks = find_course_tasks(enrollments)
    
    total_tasks = sum(len(tasks) for tasks in course_tasks.values())
    print(f"   ✅ Найдено заданий: {total_tasks}")
    for course, tasks in course_tasks.items():
        print(f"     📚 {course.name}: {len(tasks)} заданий")
    
    # 4. Выбираем случайные задания (по 15 для каждого курса)
    print(f"\n4️⃣ Выбор случайных заданий...")
    selected_tasks = select_random_tasks(course_tasks, tasks_per_course=15)
    
    total_selected = sum(len(tasks) for tasks in selected_tasks.values())
    print(f"   ✅ Выбрано заданий: {total_selected}")
    for course, tasks in selected_tasks.items():
        print(f"     📚 {course.name}: {len(tasks)} заданий")
    
    # 5. Генерируем попытки (по 2 на задание)
    print(f"\n5️⃣ Генерация попыток решения заданий...")
    attempts = generate_attempts(student, selected_tasks, attempts_per_task=2)
    
    print(f"   ✅ Сгенерировано попыток: {len(attempts)}")
    
    # 6. Загружаем в базу данных
    print(f"\n6️⃣ Загрузка данных в базу данных...")
    save_attempts_to_db(attempts)
    
    # 7. Проверяем результат
    print(f"\n7️⃣ Проверка результатов...")
    verify_data(student)
    
    print(f"\n🎉 ГЕНЕРАЦИЯ ДАННЫХ ЗАВЕРШЕНА УСПЕШНО!")


def get_students_from_db():
    """Получает список студентов из БД"""
    students = StudentProfile.objects.all()
    
    print(f"   Найдено в БД:")
    for i, student in enumerate(students[:10], 1):  # Показываем первых 10
        print(f"     {i}. {student.full_name} ({student.user.username})")
        if student.organization:
            print(f"        🏢 {student.organization}")
    
    if students.count() > 10:
        print(f"     ... и еще {students.count() - 10} студентов")
    
    return list(students)


def select_student(students):
    """Выбирает студента для генерации данных"""
    if len(students) == 1:
        return students[0]
    
    # Выбираем первого студента или создаем логику выбора
    return students[0]


def create_test_student():
    """Создает тестового студента если нет в БД"""
    # Создаем пользователя
    username = "real_test_student"
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'first_name': 'Реальный',
            'last_name': 'Студент',
            'email': f'{username}@university.edu'
        }
    )
    
    # Создаем профиль студента
    student, created = StudentProfile.objects.get_or_create(
        user=user,
        defaults={
            'full_name': 'Реальный Тестовый Студент',
            'email': user.email,
            'organization': 'Тестовый Университет'
        }
    )
    
    return student


def check_course_enrollments(student):
    """Проверяет, на какие курсы записан студент"""
    enrollments = StudentCourseEnrollment.objects.filter(
        student=student
    ).select_related('course')
    
    return list(enrollments)


def enroll_student_to_courses(student):
    """Записывает студента на доступные курсы"""
    # Получаем все доступные курсы
    courses = Course.objects.all()
    
    if not courses.exists():
        # Создаем тестовые курсы если их нет
        courses = create_test_courses()
    
    enrollments = []
    
    # Записываем на первые 2-3 курса
    for course in courses[:3]:
        enrollment, created = StudentCourseEnrollment.objects.get_or_create(
            student=student,
            course=course,
            defaults={
                'status': 'in_progress',
                'progress_percentage': random.randint(10, 80),
                'enrolled_at': timezone.now() - timedelta(days=random.randint(30, 90))
            }
        )
        enrollments.append(enrollment)
    
    return enrollments


def create_test_courses():
    """Создает тестовые курсы если их нет в БД"""
    courses = []
    
    course_data = [
        ('PROG101', 'Основы программирования', 'Изучение основ программирования на Python'),
        ('MATH201', 'Высшая математика', 'Математический анализ и линейная алгебра'),
        ('CS301', 'Структуры данных', 'Алгоритмы и структуры данных')
    ]
    
    for course_id, name, description in course_data:
        course, created = Course.objects.get_or_create(
            id=course_id,
            defaults={
                'name': name,
                'description': description,
                'duration_hours': random.randint(40, 80)
            }
        )
        courses.append(course)
    
    return courses


def find_course_tasks(enrollments):
    """Находит задания для курсов студента"""
    course_tasks = {}
    
    for enrollment in enrollments:
        course = enrollment.course
        
        # Находим задания, привязанные к курсу
        tasks = Task.objects.filter(
            courses=course,
            is_active=True
        ).prefetch_related('skills', 'courses')
        
        if not tasks.exists():
            # Создаем тестовые задания для курса
            tasks = create_test_tasks_for_course(course)
        
        course_tasks[course] = list(tasks)
    
    return course_tasks


def create_test_tasks_for_course(course):
    """Создает тестовые задания для курса"""
    tasks = []
    
    # Получаем или создаем навыки
    skills = get_or_create_skills_for_course(course)
    
    # Создаем 20 тестовых заданий для курса
    for i in range(1, 21):
        task, created = Task.objects.get_or_create(
            title=f'Задание {i} по курсу {course.name}',
            defaults={
                'question_text': f'Вопрос {i} для курса {course.name}. Выберите правильный ответ.',
                'task_type': random.choice(['single', 'multiple', 'true_false']),
                'difficulty': random.choice(['beginner', 'intermediate', 'advanced']),
                'is_active': True
            }
        )
        
        if created:
            # Привязываем к курсу
            task.courses.add(course)
            
            # Привязываем к случайным навыкам (1-3 навыка на задание)
            task_skills = random.sample(skills, k=random.randint(1, min(3, len(skills))))
            task.skills.add(*task_skills)
        
        tasks.append(task)
    
    return tasks


def get_or_create_skills_for_course(course):
    """Получает или создает навыки для курса"""
    # Пытаемся найти существующие навыки
    existing_skills = list(Skill.objects.all()[:5])
    
    if existing_skills:
        return existing_skills
    
    # Создаем базовые навыки если их нет
    skill_names = [
        'Основы программирования',
        'Переменные и типы данных', 
        'Условные операторы',
        'Циклы',
        'Функции',
        'Работа с данными',
        'Объектно-ориентированное программирование'
    ]
    
    skills = []
    for name in skill_names:
        skill, created = Skill.objects.get_or_create(
            name=name,
            defaults={
                'description': f'Навык: {name}',
                'is_base': name == 'Основы программирования'
            }
        )
        skills.append(skill)
    
    return skills


def select_random_tasks(course_tasks, tasks_per_course=15):
    """Выбирает случайные задания для каждого курса"""
    selected_tasks = {}
    
    for course, tasks in course_tasks.items():
        # Выбираем до tasks_per_course заданий случайно
        num_to_select = min(tasks_per_course, len(tasks))
        selected = random.sample(tasks, k=num_to_select)
        selected_tasks[course] = selected
    
    return selected_tasks


def generate_attempts(student, selected_tasks, attempts_per_task=2):
    """Генерирует попытки решения заданий"""
    attempts = []
    
    # Базовое время - месяц назад
    base_time = timezone.now() - timedelta(days=30)
    current_time = base_time
    
    for course, tasks in selected_tasks.items():
        print(f"     📚 Генерируем попытки для курса: {course.name}")
        
        # Определяем уровень студента для курса (прогресс от плохого к хорошему)
        course_progress = 0.3  # Начинаем с 30% успеха
        
        for task_idx, task in enumerate(tasks):
            # Увеличиваем шанс успеха по мере прохождения курса
            success_rate = min(0.9, course_progress + (task_idx * 0.02))
            
            for attempt_num in range(attempts_per_task):
                # Вторая попытка обычно лучше первой
                adjusted_success_rate = success_rate
                if attempt_num > 0:
                    adjusted_success_rate = min(0.95, success_rate + 0.2)
                
                is_correct = random.random() < adjusted_success_rate
                
                # Время попытки (интервалы между попытками)
                attempt_time = current_time + timedelta(
                    hours=random.randint(1, 48),  # От 1 до 48 часов между попытками
                    minutes=random.randint(0, 59)
                )
                
                # Время выполнения задания
                time_spent = random.randint(30, 600)  # От 30 сек до 10 мин
                
                attempt_data = {
                    'student': student,
                    'task': task,
                    'is_correct': is_correct,
                    'started_at': attempt_time - timedelta(seconds=time_spent),
                    'completed_at': attempt_time,
                    'time_spent': time_spent,
                    'given_answer': f"Ответ {attempt_num + 1} на задание {task.title}",
                    'metadata': {
                        'course': course.name,
                        'attempt_number': attempt_num + 1,
                        'success_rate': adjusted_success_rate,
                        'generated': True
                    }
                }
                
                attempts.append(attempt_data)
                current_time = attempt_time
    
    return attempts


def save_attempts_to_db(attempts):
    """Сохраняет попытки в базу данных"""
    saved_count = 0
    
    # Очищаем предыдущие попытки этого студента (если есть)
    student = attempts[0]['student']
    TaskAttempt.objects.filter(student=student).delete()
    print(f"   🧹 Очищены предыдущие попытки студента")
    
    with transaction.atomic():
        for attempt_data in attempts:
            try:
                attempt = TaskAttempt.objects.create(**attempt_data)
                saved_count += 1
                
                if saved_count % 10 == 0:
                    print(f"   💾 Сохранено попыток: {saved_count}")
                    
            except Exception as e:
                print(f"   ⚠️ Ошибка сохранения попытки: {e}")
    
    print(f"   ✅ Всего сохранено попыток: {saved_count}")


def verify_data(student):
    """Проверяет сохраненные данные"""
    # Проверяем попытки
    attempts = TaskAttempt.objects.filter(student=student)
    print(f"   📊 Всего попыток в БД: {attempts.count()}")
    
    # Проверяем освоение навыков
    masteries = StudentSkillMastery.objects.filter(student=student)
    print(f"   🎯 Записей освоения навыков: {masteries.count()}")
    
    # Статистика по курсам
    course_stats = {}
    for attempt in attempts:
        for course in attempt.task.courses.all():
            if course.name not in course_stats:
                course_stats[course.name] = {'total': 0, 'correct': 0}
            course_stats[course.name]['total'] += 1
            if attempt.is_correct:
                course_stats[course.name]['correct'] += 1
    
    print(f"   📈 Статистика по курсам:")
    for course_name, stats in course_stats.items():
        accuracy = (stats['correct'] / stats['total']) * 100 if stats['total'] > 0 else 0
        print(f"     📚 {course_name}: {stats['correct']}/{stats['total']} ({accuracy:.1f}%)")
    
    # Проверяем обновление BKT
    if masteries.exists():
        print(f"   🧠 Примеры освоения навыков (BKT):")
        for mastery in masteries[:5]:
            print(f"     🎯 {mastery.skill.name}: {mastery.current_mastery_prob:.3f} "
                  f"({mastery.correct_attempts}/{mastery.attempts_count})")


def show_final_summary(student):
    """Показывает финальную сводку"""
    print(f"\n📋 ФИНАЛЬНАЯ СВОДКА ДЛЯ СТУДЕНТА: {student.full_name}")
    print("=" * 60)
    
    # Общая статистика
    total_attempts = TaskAttempt.objects.filter(student=student).count()
    total_masteries = StudentSkillMastery.objects.filter(student=student).count()
    total_enrollments = StudentCourseEnrollment.objects.filter(student=student).count()
    
    print(f"📊 Общая статистика:")
    print(f"   👤 Студент: {student.full_name}")
    print(f"   🏢 Организация: {student.organization}")
    print(f"   📚 Курсов: {total_enrollments}")
    print(f"   📝 Попыток: {total_attempts}")
    print(f"   🎯 Навыков отслеживается: {total_masteries}")
    
    # Готовность к тестированию BKT
    print(f"\n🚀 ГОТОВНОСТЬ К ТЕСТИРОВАНИЮ BKT:")
    print(f"   ✅ Данные студента загружены")
    print(f"   ✅ История попыток создана ({total_attempts} записей)")
    print(f"   ✅ BKT модель может быть протестирована")
    print(f"   ✅ Система готова к анализу обучения")


if __name__ == "__main__":
    try:
        main()
        
        # Получаем студента для финальной сводки
        students = StudentProfile.objects.all()
        if students.exists():
            show_final_summary(students.first())
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
