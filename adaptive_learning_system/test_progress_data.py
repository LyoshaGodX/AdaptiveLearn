import os
import sys
import django

# Добавляем путь к Django проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

from student.models import StudentProfile
from mlmodels.models import StudentSkillMastery
from django.contrib.auth.models import User

def test_progress_data():
    """Тестируем данные для прогресс-баров"""
    
    # Находим первого студента
    try:
        user = User.objects.first()
        if not user:
            print("❌ Нет пользователей в системе")
            return
            
        profile, created = StudentProfile.objects.get_or_create(
            user=user,
            defaults={
                'full_name': f"{user.first_name} {user.last_name}".strip() or user.username,
                'email': user.email or f"{user.username}@example.com"
            }
        )
        
        print(f"✅ Тестируем профиль: {profile.full_name}")
        
        # Получаем данные о мастерстве навыков
        skill_masteries = StudentSkillMastery.objects.filter(
            student=profile
        ).select_related('skill')
        
        print(f"📊 Найдено записей о навыках: {skill_masteries.count()}")
        
        for mastery in skill_masteries[:5]:  # Первые 5 навыков
            percentage = round(mastery.current_mastery_prob * 100, 1)
            print(f"   • {mastery.skill.name}: {percentage}% (prob: {mastery.current_mastery_prob})")
            
            # Проверяем, что процент в допустимом диапазоне
            if 0 <= percentage <= 100:
                print(f"     ✅ Процент в норме")
            else:
                print(f"     ❌ Процент вне диапазона!")
                
        # Тестируем различные значения
        test_values = [0, 0.25, 0.5, 0.75, 1.0, 1.2, -0.1]
        print("\n🧪 Тест различных значений вероятности:")
        
        for prob in test_values:
            percentage = round(prob * 100, 1)
            # Ограничиваем диапазон 0-100%
            safe_percentage = max(0, min(100, percentage))
            
            print(f"   Prob: {prob} → {percentage}% → Safe: {safe_percentage}%")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    test_progress_data()
