"""
Скрипт для полной выгрузки информации о студенте из базы данных
Включает:
- Базовую информацию о студенте
- Записи на курсы
- Историю прохождения заданий
- Освоение навыков (BKT данные)
- Статистику и аналитику
"""

import os
import sys
import django
from pathlib import Path
import json
from datetime import datetime

# Настройка Django
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

from django.contrib.auth.models import User
from student.models import StudentProfile, StudentCourseEnrollment
from methodist.models import Task, Course
from skills.models import Skill
from mlmodels.models import TaskAttempt, StudentSkillMastery


def export_student_full_data(username):
    """Полная выгрузка данных студента"""
    print(f"🔍 ПОЛНАЯ ВЫГРУЗКА ДАННЫХ СТУДЕНТА: {username}")
    print("=" * 60)
    
    try:
        # 1. Получаем студента
        user = User.objects.get(username=username)
        student = StudentProfile.objects.get(user=user)
        
        print(f"✅ Студент найден: {student.full_name}")
        
        # 2. Собираем все данные
        student_data = collect_all_student_data(student)
        
        # 3. Выводим информацию
        display_student_info(student_data)
        
        # 4. Сохраняем в файл
        save_to_file(student_data, username)
        
        return student_data
        
    except User.DoesNotExist:
        print(f"❌ Пользователь с username '{username}' не найден")
        return None
    except StudentProfile.DoesNotExist:
        print(f"❌ Профиль студента для пользователя '{username}' не найден")
        return None
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None


def collect_all_student_data(student):
    """Собирает все данные о студенте"""
    print("📊 Сбор данных...")
    
    # Базовая информация
    user_data = {
        'id': student.user.id,
        'username': student.user.username,
        'first_name': student.user.first_name,
        'last_name': student.user.last_name,
        'email': student.user.email,
        'date_joined': student.user.date_joined.isoformat() if student.user.date_joined else None,
        'last_login': student.user.last_login.isoformat() if student.user.last_login else None,
        'is_active': student.user.is_active,
    }
    
    student_profile_data = {
        'id': student.id,
        'full_name': student.full_name,
        'email': student.email,
        'organization': student.organization,
        'phone': getattr(student, 'phone', None),
        'date_of_birth': student.date_of_birth.isoformat() if getattr(student, 'date_of_birth', None) else None,
        'created_at': student.created_at.isoformat() if hasattr(student, 'created_at') and student.created_at else None,
    }
    
    # Записи на курсы
    enrollments = StudentCourseEnrollment.objects.filter(student=student).select_related('course')
    enrollments_data = []
    
    for enrollment in enrollments:
        enrollment_data = {
            'id': enrollment.id,
            'course_id': enrollment.course.id,
            'course_name': enrollment.course.name,
            'course_description': enrollment.course.description,
            'status': enrollment.status,
            'progress_percentage': enrollment.progress_percentage,
            'enrolled_at': enrollment.enrolled_at.isoformat() if enrollment.enrolled_at else None,
            'completed_at': enrollment.completed_at.isoformat() if getattr(enrollment, 'completed_at', None) else None,
        }
        enrollments_data.append(enrollment_data)
    
    # История попыток
    attempts = TaskAttempt.objects.filter(student=student).select_related('task').prefetch_related('task__skills', 'task__courses').order_by('completed_at')
    attempts_data = []
    
    for attempt in attempts:
        attempt_data = {
            'id': attempt.id,
            'task_id': attempt.task.id,
            'task_title': attempt.task.title,
            'task_type': attempt.task.task_type,
            'task_difficulty': attempt.task.difficulty,
            'task_skills': [skill.name for skill in attempt.task.skills.all()],
            'task_courses': [course.name for course in attempt.task.courses.all()],
            'is_correct': attempt.is_correct,
            'started_at': attempt.started_at.isoformat() if attempt.started_at else None,
            'completed_at': attempt.completed_at.isoformat() if attempt.completed_at else None,            'time_spent': attempt.time_spent,
            'given_answer': attempt.given_answer,
            'metadata': getattr(attempt, 'metadata', None),
        }
        attempts_data.append(attempt_data)    # Освоение навыков (BKT данные) - получаем ВСЕ навыки системы для этого студента
    masteries = StudentSkillMastery.objects.filter(student=student).select_related('skill')
    masteries_data = []
    
    # Получаем также все навыки системы (даже если студент их не изучал)
    all_skills = Skill.objects.all()
    skill_ids_with_mastery = set(mastery.skill.id for mastery in masteries)
      # Сначала добавляем навыки с данными BKT
    for mastery in masteries:
        mastery_data = {
            'id': mastery.id,
            'skill_id': mastery.skill.id,
            'skill_name': mastery.skill.name,
            'skill_description': mastery.skill.description,
            'has_bkt_data': True,
            'current_mastery_prob': mastery.current_mastery_prob,
            'attempts_count': mastery.attempts_count,
            'correct_attempts': mastery.correct_attempts,
            'last_updated': mastery.last_updated.isoformat() if mastery.last_updated else None,
            'metadata': getattr(mastery, 'metadata', None),
            'bkt_parameters': {
                'initial_mastery_prob': getattr(mastery, 'initial_mastery_prob', None),
                'current_mastery_prob': mastery.current_mastery_prob,
                'transition_prob': getattr(mastery, 'transition_prob', None),
                'guess_prob': getattr(mastery, 'guess_prob', None),
                'slip_prob': getattr(mastery, 'slip_prob', None),
            }
        }
        masteries_data.append(mastery_data)
    
    # Добавляем навыки без данных BKT (студент их не изучал)
    for skill in all_skills:
        if skill.id not in skill_ids_with_mastery:
            mastery_data = {
                'id': None,
                'skill_id': skill.id,
                'skill_name': skill.name,
                'skill_description': skill.description,
                'has_bkt_data': False,
                'current_mastery_prob': 0.0,
                'attempts_count': 0,
                'correct_attempts': 0,
                'last_updated': None,                'metadata': None,
                'bkt_parameters': {
                    'initial_mastery_prob': None,
                    'current_mastery_prob': 0.0,
                    'transition_prob': None,
                    'guess_prob': None,
                    'slip_prob': None,
                }
            }
            masteries_data.append(mastery_data)
    
    # Статистика
    stats = calculate_statistics(attempts, masteries, enrollments)
    
    return {
        'export_timestamp': datetime.now().isoformat(),
        'user': user_data,
        'student_profile': student_profile_data,
        'course_enrollments': enrollments_data,
        'task_attempts': attempts_data,
        'skill_masteries': masteries_data,
        'statistics': stats,
    }


def calculate_statistics(attempts, masteries, enrollments):
    """Вычисляет статистику по студенту"""
    stats = {
        'total_enrollments': enrollments.count(),
        'total_attempts': attempts.count(),
        'total_skills_tracked': masteries.count(),
        'correct_attempts': attempts.filter(is_correct=True).count(),
        'incorrect_attempts': attempts.filter(is_correct=False).count(),
    }
    
    # Процент правильных ответов
    if stats['total_attempts'] > 0:
        stats['accuracy_percentage'] = (stats['correct_attempts'] / stats['total_attempts']) * 100
    else:
        stats['accuracy_percentage'] = 0
    
    # Статистика по курсам
    course_stats = {}
    for enrollment in enrollments:
        course_attempts = attempts.filter(task__courses=enrollment.course)
        course_correct = course_attempts.filter(is_correct=True).count()
        course_total = course_attempts.count()
        
        course_stats[enrollment.course.name] = {
            'total_attempts': course_total,
            'correct_attempts': course_correct,
            'accuracy': (course_correct / course_total * 100) if course_total > 0 else 0,
            'progress_percentage': enrollment.progress_percentage,
        }
    
    stats['courses'] = course_stats
    
    # Статистика по навыкам
    skill_stats = {}
    for mastery in masteries:
        skill_stats[mastery.skill.name] = {
            'mastery_probability': mastery.current_mastery_prob,
            'attempts_count': mastery.attempts_count,
            'correct_attempts': mastery.correct_attempts,
            'accuracy': (mastery.correct_attempts / mastery.attempts_count * 100) if mastery.attempts_count > 0 else 0,
        }
    
    stats['skills'] = skill_stats
    
    # Временная статистика
    if attempts.exists():
        first_attempt = attempts.first()
        last_attempt = attempts.last()
        stats['learning_period'] = {
            'first_attempt': first_attempt.completed_at.isoformat() if first_attempt.completed_at else None,
            'last_attempt': last_attempt.completed_at.isoformat() if last_attempt.completed_at else None,
        }
        
        # Среднее время выполнения
        total_time = sum(attempt.time_spent for attempt in attempts if attempt.time_spent)
        stats['average_time_per_attempt'] = total_time / attempts.count() if attempts.count() > 0 else 0
    
    return stats


def display_student_info(data):
    """Отображает информацию о студенте"""
    print("\n" + "="*60)
    print("👤 ИНФОРМАЦИЯ О СТУДЕНТЕ")
    print("="*60)
    
    # Базовая информация
    user = data['user']
    profile = data['student_profile']
    
    print(f"🆔 ID пользователя: {user['id']}")
    print(f"👤 Username: {user['username']}")
    print(f"📝 Полное имя: {profile['full_name']}")
    print(f"📧 Email: {profile['email']}")
    print(f"🏢 Организация: {profile['organization']}")
    print(f"📅 Дата регистрации: {user['date_joined']}")
    print(f"🔄 Последний вход: {user['last_login']}")
    print(f"✅ Активен: {'Да' if user['is_active'] else 'Нет'}")
    
    # Записи на курсы
    print(f"\n📚 ЗАПИСИ НА КУРСЫ ({len(data['course_enrollments'])})")
    print("-" * 40)
    for enrollment in data['course_enrollments']:
        print(f"📖 {enrollment['course_name']}")
        print(f"   📊 Прогресс: {enrollment['progress_percentage']}%")
        print(f"   📅 Записан: {enrollment['enrolled_at']}")
        print(f"   🎯 Статус: {enrollment['status']}")
        print()
    
    # Статистика
    stats = data['statistics']
    print(f"📊 ОБЩАЯ СТАТИСТИКА")
    print("-" * 40)
    print(f"📚 Курсов: {stats['total_enrollments']}")
    print(f"📝 Всего попыток: {stats['total_attempts']}")
    print(f"✅ Правильных: {stats['correct_attempts']}")
    print(f"❌ Неправильных: {stats['incorrect_attempts']}")
    print(f"🎯 Точность: {stats['accuracy_percentage']:.1f}%")
    print(f"🧠 Навыков в системе: {len(data['skill_masteries'])}")
    print(f"🎓 Изученных навыков: {len([s for s in data['skill_masteries'] if s['has_bkt_data']])}")
    
    if 'average_time_per_attempt' in stats:
        print(f"⏱️ Среднее время на задание: {stats['average_time_per_attempt']:.1f} сек")
    
    # Статистика по курсам
    if stats['courses']:
        print(f"\n📚 СТАТИСТИКА ПО КУРСАМ")
        print("-" * 40)
        for course_name, course_stats in stats['courses'].items():
            print(f"📖 {course_name}:")
            print(f"   📝 Попыток: {course_stats['total_attempts']}")
            print(f"   ✅ Правильных: {course_stats['correct_attempts']}")
            print(f"   🎯 Точность: {course_stats['accuracy']:.1f}%")
            print(f"   📊 Прогресс: {course_stats['progress_percentage']}%")
            print()
      # Освоение навыков
    if data['skill_masteries']:
        print(f"🧠 ОСВОЕНИЕ НАВЫКОВ (BKT) - ВСЕ НАВЫКИ СИСТЕМЫ")
        print("-" * 60)
        
        # Разделяем на изученные и неизученные навыки
        studied_skills = [s for s in data['skill_masteries'] if s['has_bkt_data']]
        unstudied_skills = [s for s in data['skill_masteries'] if not s['has_bkt_data']]
        
        # Сортируем изученные по вероятности освоения
        studied_skills = sorted(studied_skills, 
                               key=lambda x: x['current_mastery_prob'], 
                               reverse=True)
        
        print(f"✅ ИЗУЧЕННЫЕ НАВЫКИ ({len(studied_skills)}):")
        for i, mastery in enumerate(studied_skills, 1):
            prob_percent = mastery['current_mastery_prob'] * 100
            print(f"  {i:2d}. 🎯 {mastery['skill_name']}: {prob_percent:.1f}%")
            print(f"       📝 Попыток: {mastery['attempts_count']} | ✅ Правильных: {mastery['correct_attempts']}")
            if mastery['last_updated']:
                print(f"       📅 Последнее обновление: {mastery['last_updated']}")
              # BKT параметры если есть
            bkt = mastery['bkt_parameters']
            if any(bkt.values()):
                print(f"       🧠 BKT параметры:")
                print(f"          📊 P(L0) = {bkt.get('initial_mastery_prob', 'не задано'):.3f}" if bkt.get('initial_mastery_prob') is not None else "          📊 P(L0) = не задано")
                print(f"          📊 P(Lt) = {bkt.get('current_mastery_prob', 0):.3f}")
                print(f"          📊 P(T) = {bkt.get('transition_prob', 'не задано'):.3f}" if bkt.get('transition_prob') is not None else "          📊 P(T) = не задано")
                print(f"          📊 P(G) = {bkt.get('guess_prob', 'не задано'):.3f}" if bkt.get('guess_prob') is not None else "          📊 P(G) = не задано")
                print(f"          📊 P(S) = {bkt.get('slip_prob', 'не задано'):.3f}" if bkt.get('slip_prob') is not None else "          📊 P(S) = не задано")
            print()
        
        if unstudied_skills:
            print(f"⭕ НЕИЗУЧЕННЫЕ НАВЫКИ ({len(unstudied_skills)}):")
            for i, skill in enumerate(unstudied_skills, 1):
                print(f"  {i:2d}. 🎯 {skill['skill_name']}: не изучался")
                if skill['skill_description']:
                    print(f"       📖 {skill['skill_description']}")
            print()
    
    # История попыток - ПОЛНАЯ ИСТОРИЯ
    if data['task_attempts']:
        print(f"📝 ПОЛНАЯ ИСТОРИЯ ПОПЫТОК ({len(data['task_attempts'])} записей)")
        print("-" * 60)
        
        # Группируем попытки по курсам
        attempts_by_course = {}
        for attempt in data['task_attempts']:
            for course in attempt['task_courses']:
                if course not in attempts_by_course:
                    attempts_by_course[course] = []
                attempts_by_course[course].append(attempt)
        
        for course_name, course_attempts in attempts_by_course.items():
            print(f"📚 КУРС: {course_name} ({len(course_attempts)} попыток)")
            print("    " + "-" * 50)
            
            # Сортируем по времени
            course_attempts.sort(key=lambda x: x['completed_at'] or '')
            
            for i, attempt in enumerate(course_attempts, 1):
                status = "✅" if attempt['is_correct'] else "❌"
                print(f"    {i:2d}. {status} {attempt['task_title']}")
                print(f"        🎯 Навыки: {', '.join(attempt['task_skills'])}")
                print(f"        ⏱️  Время: {attempt['time_spent']}с | 📅 {attempt['completed_at']}")
                if attempt['given_answer']:
                    answer_preview = str(attempt['given_answer'])[:50]
                    if len(str(attempt['given_answer'])) > 50:
                        answer_preview += "..."
                    print(f"        💬 Ответ: {answer_preview}")
                print()
            print()


def save_to_file(data, username):
    """Сохраняет данные в JSON файл"""
    filename = f"student_export_{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = Path(__file__).parent / filename
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 ДАННЫЕ СОХРАНЕНЫ В ФАЙЛ:")
        print(f"📁 {filepath}")
        print(f"📏 Размер файла: {filepath.stat().st_size} байт")
        
    except Exception as e:
        print(f"❌ Ошибка сохранения файла: {e}")


if __name__ == "__main__":
    # Выгружаем данные студента student2
    username = "student2"
    export_student_full_data(username)
