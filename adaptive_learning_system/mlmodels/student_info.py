"""
Модуль для получения и отображения информации о студенте из базы данных Django.
Выводит информацию о студенте, его попытках прохождения заданий и характеристиках освоения навыков.
"""

import os
import sys
import django
from datetime import datetime
from django.db import models
from django.utils import timezone


def setup_django():
    """Настройка Django для работы с базой данных"""
    # Добавляем путь к корневой папке проекта в sys.path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(project_root)
    
    # Устанавливаем переменную окружения для настроек Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
    
    # Инициализируем Django
    django.setup()


def get_student_info(student_id):
    """
    Получает полную информацию о студенте по его ID
    
    Args:
        student_id (int): ID студента
        
    Returns:
        dict: Словарь с информацией о студенте или None если студент не найден
    """
    from student.models import StudentProfile, StudentCourseEnrollment
    from mlmodels.models import StudentSkillMastery, TaskAttempt, StudentLearningProfile
    from skills.models import Skill
    from methodist.models import Task
    
    try:
        # Получаем профиль студента
        student = StudentProfile.objects.get(id=student_id)
        
        # Получаем записи на курсы
        course_enrollments = StudentCourseEnrollment.objects.filter(student=student)
        
        # Получаем попытки решения заданий
        task_attempts = TaskAttempt.objects.filter(student=student).order_by('-completed_at')
        
        # Получаем освоение навыков
        skill_masteries = StudentSkillMastery.objects.filter(student=student).order_by('-current_mastery_prob')
        
        # Получаем ВСЕ навыки из курсов студента
        all_course_skills = Skill.objects.filter(
            courses__in=[enrollment.course for enrollment in course_enrollments]
        ).distinct().order_by('name')
        
        # Получаем профиль обучения (если существует)
        try:
            learning_profile = StudentLearningProfile.objects.get(student=student)
        except StudentLearningProfile.DoesNotExist:
            learning_profile = None
        
        # Формируем результат
        student_info = {
            'profile': student,
            'course_enrollments': course_enrollments,
            'task_attempts': task_attempts,
            'skill_masteries': skill_masteries,
            'all_course_skills': all_course_skills,
            'learning_profile': learning_profile,
            'statistics': _calculate_statistics(student, task_attempts, skill_masteries, all_course_skills)
        }
        
        return student_info
        
    except StudentProfile.DoesNotExist:
        return None


def _calculate_statistics(student, task_attempts, skill_masteries, all_course_skills):
    """
    Вычисляет статистические данные о студенте
    
    Args:
        student: Профиль студента
        task_attempts: QuerySet попыток решения заданий
        skill_masteries: QuerySet освоения навыков
        all_course_skills: QuerySet всех навыков из курсов студента
        
    Returns:
        dict: Статистические данные
    """
    total_attempts = task_attempts.count()
    correct_attempts = task_attempts.filter(is_correct=True).count()
    
    # Общая точность
    overall_accuracy = (correct_attempts / total_attempts * 100) if total_attempts > 0 else 0
    
    # Освоенные навыки (порог 80%)
    mastered_skills = skill_masteries.filter(current_mastery_prob__gte=0.8).count()
    total_skills = all_course_skills.count()  # Используем общее количество навыков из курсов
    
    # Среднее время на задание
    attempts_with_time = task_attempts.filter(time_spent__isnull=False)
    avg_time_seconds = attempts_with_time.aggregate(
        avg=models.Avg('time_spent')
    )['avg']
    avg_time_minutes = round(avg_time_seconds / 60, 2) if avg_time_seconds else 0
    
    # Активность за последние 7 дней
    week_ago = timezone.now() - timezone.timedelta(days=7)
    recent_activity = task_attempts.filter(completed_at__gte=week_ago).count()
    
    # Топ навыков по освоению
    top_skills = skill_masteries.order_by('-current_mastery_prob')[:5]
    
    # Самые проблемные навыки
    problematic_skills = skill_masteries.filter(
        current_mastery_prob__lt=0.5,
        attempts_count__gte=3
    ).order_by('current_mastery_prob')[:5]
    
    return {
        'total_attempts': total_attempts,
        'correct_attempts': correct_attempts,
        'overall_accuracy': overall_accuracy,
        'mastered_skills_count': mastered_skills,
        'total_skills_count': total_skills,
        'mastery_percentage': (mastered_skills / total_skills * 100) if total_skills > 0 else 0,
        'avg_time_minutes': avg_time_minutes,
        'recent_activity_count': recent_activity,
        'top_skills': top_skills,
        'problematic_skills': problematic_skills
    }


def print_student_info(student_id):
    """
    Выводит полную информацию о студенте в консоль
    
    Args:
        student_id (int): ID студента
    """
    print("=" * 80)
    print(f"ИНФОРМАЦИЯ О СТУДЕНТЕ (ID: {student_id})")
    print("=" * 80)
    
    student_info = get_student_info(student_id)
    
    if student_info is None:
        print(f"❌ Студент с ID {student_id} не найден в базе данных.")
        return
    
    student = student_info['profile']
    stats = student_info['statistics']
    
    # Основная информация о студенте
    print("\n📋 ОСНОВНАЯ ИНФОРМАЦИЯ:")
    print(f"   ФИО: {student.full_name}")
    print(f"   Username: {student.user.username}")
    print(f"   Email: {student.email}")
    print(f"   Организация: {student.organization or 'Не указана'}")
    print(f"   Дата создания профиля: {student.created_at.strftime('%d.%m.%Y %H:%M')}")
    print(f"   Последнее обновление: {student.updated_at.strftime('%d.%m.%Y %H:%M')}")
    print(f"   Статус: {'Активный' if student.is_active else 'Неактивный'}")
    print(f"   Фото профиля: {'Есть' if student.has_photo else 'Нет'}")
    
    # Записи на курсы
    print("\n📚 ЗАПИСИ НА КУРСЫ:")
    enrollments = student_info['course_enrollments']
    if enrollments.exists():
        for enrollment in enrollments:
            status_emoji = {
                'enrolled': '📝',
                'in_progress': '⏳',
                'completed': '✅',
                'suspended': '⏸️',
                'dropped': '❌'
            }.get(enrollment.status, '❓')
            
            print(f"   {status_emoji} {enrollment.course.name}")
            print(f"      Статус: {enrollment.get_status_display()}")
            print(f"      Прогресс: {enrollment.progress_percentage}%")
            print(f"      Записан: {enrollment.enrolled_at.strftime('%d.%m.%Y')}")
            if enrollment.completed_at:
                print(f"      Завершен: {enrollment.completed_at.strftime('%d.%m.%Y')}")
            if enrollment.final_grade:
                print(f"      Итоговая оценка: {enrollment.final_grade}")
    else:
        print("   Студент не записан ни на один курс")
    
    # Общая статистика
    print(f"\n📊 ОБЩАЯ СТАТИСТИКА:")
    print(f"   Всего попыток решения заданий: {stats['total_attempts']}")
    print(f"   Правильных ответов: {stats['correct_attempts']}")
    print(f"   Общая точность: {stats['overall_accuracy']:.1f}%")
    print(f"   Освоенных навыков: {stats['mastered_skills_count']}/{stats['total_skills_count']}")
    print(f"   Процент освоения навыков: {stats['mastery_percentage']:.1f}%")
    print(f"   Среднее время на задание: {stats['avg_time_minutes']} мин")
    print(f"   Активность за последнюю неделю: {stats['recent_activity_count']} попыток")
    
    # Профиль обучения
    learning_profile = student_info['learning_profile']
    if learning_profile:
        print(f"\n🎯 ПРОФИЛЬ ОБУЧЕНИЯ:")
        print(f"   Скорость обучения: {learning_profile.learning_speed:.2f}")
        print(f"   Уровень настойчивости: {learning_profile.persistence_level:.2f}")
        print(f"   Предпочитаемая сложность: {learning_profile.get_difficulty_preference_display()}")
        print(f"   Первая активность: {learning_profile.first_activity.strftime('%d.%m.%Y %H:%M') if learning_profile.first_activity else 'Не определена'}")
        print(f"   Последняя активность: {learning_profile.last_activity.strftime('%d.%m.%Y %H:%M') if learning_profile.last_activity else 'Не определена'}")
      # Топ навыков
    print(f"\n🏆 ТОП-5 НАВЫКОВ ПО ОСВОЕНИЮ:")
    if stats['top_skills']:
        for i, mastery in enumerate(stats['top_skills'], 1):
            prob_percent = mastery.current_mastery_prob * 100
            status = "✅" if mastery.is_mastered else "🔄"
            print(f"   {i}. {status} {mastery.skill.name}")
            print(f"      Вероятность освоения: {prob_percent:.1f}%")
            print(f"      Попыток: {mastery.attempts_count}, правильных: {mastery.correct_attempts}")
            print(f"      Точность: {mastery.accuracy * 100:.1f}%")
    else:
        print("   Нет данных о навыках")

    # НОВЫЙ РАЗДЕЛ: Все навыки с BKT характеристиками
    print(f"\n🧠 ВСЕ НАВЫКИ ИЗ КУРСОВ СТУДЕНТА (ДЕТАЛЬНЫЙ BKT АНАЛИЗ):")
    all_skills = student_info['all_course_skills']
    skill_masteries_dict = {sm.skill.id: sm for sm in student_info['skill_masteries']}
    
    if all_skills:
        for i, skill in enumerate(all_skills, 1):
            mastery = skill_masteries_dict.get(skill.id)
            
            if mastery:
                # Есть данные о освоении навыка
                prob_percent = mastery.current_mastery_prob * 100
                status = "✅" if mastery.is_mastered else "🔄" if prob_percent >= 50 else "❌"
                print(f"   {i}. {status} {skill.name}")
                print(f"      📊 ТЕКУЩЕЕ СОСТОЯНИЕ:")
                print(f"         • Текущая вероятность освоения: {prob_percent:.2f}%")
                print(f"         • Попыток: {mastery.attempts_count}, правильных: {mastery.correct_attempts}")
                print(f"         • Точность: {mastery.accuracy * 100:.1f}%")
                print(f"         • Последнее обновление: {mastery.last_updated.strftime('%d.%m.%Y %H:%M')}")
                
                print(f"      🎯 BKT ПАРАМЕТРЫ:")
                print(f"         • Начальная вероятность освоения (P_L0): {mastery.initial_mastery_prob:.3f}")
                print(f"         • Вероятность перехода (P_T): {mastery.transition_prob:.3f}")
                print(f"         • Вероятность угадывания (P_G): {mastery.guess_prob:.3f}")
                print(f"         • Вероятность ошибки (P_S): {mastery.slip_prob:.3f}")
                
                # Вычисляем вероятность правильного ответа по BKT
                p_correct = mastery.current_mastery_prob * (1 - mastery.slip_prob) + \
                           (1 - mastery.current_mastery_prob) * mastery.guess_prob
                print(f"         • Предсказанная вероятность правильного ответа: {p_correct:.3f}")
                
            else:
                # Нет данных о освоении навыка
                print(f"   {i}. ⚪ {skill.name}")
                print(f"      📊 СОСТОЯНИЕ: Нет попыток решения заданий")
                print(f"      🎯 BKT ПАРАМЕТРЫ: Не инициализированы")
                print(f"         • Будут установлены при первой попытке решения задания")
                print(f"         • Используются дефолтные или оптимизированные параметры")
    else:
        print("   Студент не записан на курсы или в курсах нет навыков")
    
    # Проблемные навыки
    if stats['problematic_skills']:
        print(f"\n⚠️  ПРОБЛЕМНЫЕ НАВЫКИ (требуют внимания):")
        for i, mastery in enumerate(stats['problematic_skills'], 1):
            prob_percent = mastery.current_mastery_prob * 100
            print(f"   {i}. ❌ {mastery.skill.name}")
            print(f"      Вероятность освоения: {prob_percent:.1f}%")
            print(f"      Попыток: {mastery.attempts_count}, правильных: {mastery.correct_attempts}")
            print(f"      Точность: {mastery.accuracy * 100:.1f}%")
    
    # Последние попытки
    print(f"\n📝 ПОСЛЕДНИЕ 10 ПОПЫТОК РЕШЕНИЯ ЗАДАНИЙ:")
    recent_attempts = student_info['task_attempts'][:10]
    if recent_attempts:
        for attempt in recent_attempts:
            status = "✅" if attempt.is_correct else "❌"
            time_info = f" ({attempt.duration_minutes} мин)" if attempt.duration_minutes else ""
            print(f"   {status} {attempt.task.title}{time_info}")
            print(f"      Дата: {attempt.completed_at.strftime('%d.%m.%Y %H:%M')}")
            if attempt.given_answer:
                print(f"      Ответ студента: {attempt.given_answer[:100]}...")
            print(f"      Навыки: {', '.join([skill.name for skill in attempt.task.skills.all()])}")
    else:
        print("   Нет попыток решения заданий")
    
    print("\n" + "=" * 80)


def main():
    """Основная функция для запуска модуля"""
    print("Модуль информации о студенте")
    print("Подключение к базе данных Django...")
    
    try:
        setup_django()
        print("Подключение к базе данных успешно!")
    except Exception as e:
        print(f"Ошибка подключения к базе данных: {e}")
        return
    
    # Запрашиваем ID студента
    try:
        student_id = input("\nВведите ID студента: ")
        student_id = int(student_id)
        
        print_student_info(student_id)
        
    except ValueError:
        print("❌ Ошибка: ID студента должен быть числом")
    except Exception as e:
        print(f"❌ Произошла ошибка: {e}")


if __name__ == "__main__":
    main()
