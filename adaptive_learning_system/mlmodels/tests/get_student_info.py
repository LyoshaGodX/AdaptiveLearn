"""
Скрипт для получения информации о созданном студенте.

Показывает:
- ID студента и пользователя
- Логин (username)
- Пароль (если доступен)
- Профиль студента
- Статистику попыток и освоения навыков

Использование:
    python mlmodels/tests/get_student_info.py
    или
    python manage.py shell
    exec(open('mlmodels/tests/get_student_info.py').read())
"""

import os
import sys
import django
from pathlib import Path

# Настройка Django
def setup_django():
    """Настройка Django окружения"""
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
    django.setup()

setup_django()

from django.contrib.auth.models import User
from student.models import StudentProfile, StudentCourseEnrollment
from mlmodels.models import TaskAttempt, StudentSkillMastery
from skills.models import Course


def get_student_info(username="alex_klementev"):
    """
    Получает полную информацию о студенте
    
    Args:
        username: Логин студента (по умолчанию alex_klementev)
    """
    
    print("=" * 80)
    print("📋 ИНФОРМАЦИЯ О СТУДЕНТЕ")
    print("=" * 80)
    
    try:
        # Получаем пользователя
        user = User.objects.get(username=username)
        
        print("👤 ДАННЫЕ ПОЛЬЗОВАТЕЛЯ:")
        print(f"   • ID пользователя: {user.id}")
        print(f"   • Логин (username): {user.username}")
        print(f"   • Имя: {user.first_name}")
        print(f"   • Фамилия: {user.last_name}")
        print(f"   • Email: {user.email}")
        print(f"   • Активен: {'Да' if user.is_active else 'Нет'}")
        print(f"   • Суперпользователь: {'Да' if user.is_superuser else 'Нет'}")
        print(f"   • Персонал: {'Да' if user.is_staff else 'Нет'}")
        print(f"   • Дата создания: {user.date_joined.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   • Последний вход: {user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'Никогда'}")
        
        # Информация о пароле
        print(f"\n🔐 ПАРОЛЬ:")
        if user.password:
            print(f"   • Хеш пароля: {user.password[:50]}...")
            print(f"   • Алгоритм: {user.password.split('$')[0] if '$' in user.password else 'Unknown'}")
            print("   • ⚠️  Пароль зашифрован. Для входа используйте:")
            print("     - Логин: alex_klementev")
            print("     - Пароль: test123 (если был установлен при создании)")
            print("     - Или сбросьте пароль через админку Django")
        else:
            print("   • Пароль не установлен")
          # Получаем профиль студента
        try:
            student_profile = StudentProfile.objects.get(user=user)
            
            print(f"\n🎓 ПРОФИЛЬ СТУДЕНТА:")
            print(f"   • ID профиля: {student_profile.id}")
            print(f"   • Полное имя: {student_profile.full_name}")
            print(f"   • Email профиля: {student_profile.email}")
            print(f"   • Организация: {student_profile.organization}")
            print(f"   • Активен: {'Да' if student_profile.is_active else 'Нет'}")
            print(f"   • Дата создания: {student_profile.created_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(student_profile, 'created_at') else 'Не указана'}")
            
            # Записи на курсы
            enrollments = StudentCourseEnrollment.objects.filter(student=student_profile)
            print(f"\n📚 ЗАПИСИ НА КУРСЫ ({enrollments.count()}):")
            for enrollment in enrollments:
                print(f"   • {enrollment.course.name}: {enrollment.get_status_display()}")
                print(f"     Записан: {enrollment.enrolled_at.strftime('%Y-%m-%d %H:%M')}")
                if hasattr(enrollment, 'progress_percentage'):
                    print(f"     Прогресс: {enrollment.progress_percentage}%")
            
            # Статистика попыток
            attempts = TaskAttempt.objects.filter(student=student_profile)
            total_attempts = attempts.count()
            correct_attempts = attempts.filter(is_correct=True).count()
            
            print(f"\n📊 СТАТИСТИКА ПОПЫТОК:")
            print(f"   • Всего попыток: {total_attempts}")
            print(f"   • Правильных ответов: {correct_attempts}")
            print(f"   • Неправильных ответов: {total_attempts - correct_attempts}")
            print(f"   • Успешность: {correct_attempts/total_attempts*100:.1f}%" if total_attempts > 0 else "   • Успешность: 0%")
            
            # Последние попытки
            if total_attempts > 0:
                recent_attempts = attempts.order_by('-completed_at')[:5]
                print(f"\n📝 ПОСЛЕДНИЕ ПОПЫТКИ:")
                for attempt in recent_attempts:
                    status = "✅" if attempt.is_correct else "❌"
                    time_str = attempt.completed_at.strftime('%Y-%m-%d %H:%M')
                    skills = ", ".join([skill.name for skill in attempt.task.skills.all()])
                    print(f"   {status} {attempt.task.title}")
                    print(f"      Навыки: {skills}")
                    print(f"      Время: {time_str}, Потрачено: {attempt.time_spent}с")
            
            # Освоение навыков
            masteries = StudentSkillMastery.objects.filter(student=student_profile)
            
            print(f"\n🧠 ОСВОЕНИЕ НАВЫКОВ ({masteries.count()}):")
            
            fully_mastered = masteries.filter(current_mastery_prob__gte=0.8).order_by('-current_mastery_prob')
            if fully_mastered.exists():
                print(f"   ✅ ПОЛНОСТЬЮ ОСВОЕННЫЕ ({fully_mastered.count()}):")
                for mastery in fully_mastered:
                    print(f"      • {mastery.skill.name}: {mastery.current_mastery_prob:.3f} ({mastery.correct_attempts}/{mastery.attempts_count})")
            
            partially_mastered = masteries.filter(
                current_mastery_prob__gte=0.5, 
                current_mastery_prob__lt=0.8
            ).order_by('-current_mastery_prob')
            if partially_mastered.exists():
                print(f"   🟡 ЧАСТИЧНО ОСВОЕННЫЕ ({partially_mastered.count()}):")
                for mastery in partially_mastered:
                    print(f"      • {mastery.skill.name}: {mastery.current_mastery_prob:.3f} ({mastery.correct_attempts}/{mastery.attempts_count})")
            
            low_mastered = masteries.filter(current_mastery_prob__lt=0.5).order_by('-current_mastery_prob')
            if low_mastered.exists():
                print(f"   🔴 СЛАБО ОСВОЕННЫЕ ({low_mastered.count()}):")
                for mastery in low_mastered:
                    print(f"      • {mastery.skill.name}: {mastery.current_mastery_prob:.3f} ({mastery.correct_attempts}/{mastery.attempts_count})")
            
        except StudentProfile.DoesNotExist:
            print("\n❌ Профиль студента не найден!")
            print("   Возможно, пользователь создан, но профиль StudentProfile не создан.")
        
        print("\n" + "=" * 80)
        print("💡 ИНСТРУКЦИЯ ДЛЯ ВХОДА В СИСТЕМУ:")
        print("=" * 80)
        print("1. Откройте веб-интерфейс Django (обычно http://127.0.0.1:8000/)")
        print("2. Перейдите в админку (/admin/) или форму входа")
        print(f"3. Используйте данные:")
        print(f"   • Логин: {user.username}")
        print(f"   • Пароль: test123 (если был установлен)")
        print("4. Если пароль не подходит, сбросьте его через:")
        print("   python manage.py changepassword alex_klementev")
        print("=" * 80)
        
        return {
            'user_id': user.id,
            'username': user.username,
            'student_profile_id': student_profile.id if hasattr(user, 'studentprofile') else None,
            'total_attempts': total_attempts,
            'skills_mastered': masteries.count()
        }
        
    except User.DoesNotExist:
        print(f"❌ Пользователь с логином '{username}' не найден!")
        print("\nДоступные пользователи:")
        users = User.objects.all()
        for user in users:
            print(f"   • {user.username} ({user.first_name} {user.last_name})")
        return None


def reset_student_password(username="alex_klementev", new_password="test123"):
    """
    Сбрасывает пароль студента
    
    Args:
        username: Логин студента
        new_password: Новый пароль
    """
    try:
        user = User.objects.get(username=username)
        user.set_password(new_password)
        user.save()
        
        print(f"✅ Пароль для пользователя '{username}' изменен на '{new_password}'")
        return True
        
    except User.DoesNotExist:
        print(f"❌ Пользователь '{username}' не найден!")
        return False


def main():
    """Основная функция"""
    import sys
    
    # Проверяем аргументы командной строки
    if len(sys.argv) > 1:
        if sys.argv[1] == "--reset-password":
            username = sys.argv[2] if len(sys.argv) > 2 else "alex_klementev"
            password = sys.argv[3] if len(sys.argv) > 3 else "test123"
            reset_student_password(username, password)
        else:
            username = sys.argv[1]
            get_student_info(username)
    else:
        # По умолчанию показываем информацию о alex_klementev
        result = get_student_info("alex_klementev")
        
        # Предлагаем сбросить пароль
        if result:
            print("\n🔧 Хотите сбросить пароль? Выполните:")
            print("python mlmodels/tests/get_student_info.py --reset-password alex_klementev test123")


if __name__ == "__main__":
    main()
