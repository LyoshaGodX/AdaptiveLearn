"""
Скрипт для создания студента и симуляции попыток решения заданий.

Создает студента Клементьева Алексея Александровича и записывает попытки решения заданий
следуя графу навыков. BKT применяется автоматически при сохранении каждой попытки.

Использование:
    python manage.py shell
    exec(open('mlmodels/tests/create_student_with_attempts.py').read())
"""

import os
import sys
import django
from typing import Dict, List, Set, Optional
import random
from datetime import datetime, timedelta
from pathlib import Path
import json

# Настройка Django
def setup_django():
    """Настройка Django окружения"""
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
    django.setup()

setup_django()

from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from student.models import StudentProfile, StudentCourseEnrollment
from skills.models import Skill, Course
from methodist.models import Task, TaskType, DifficultyLevel
from mlmodels.models import TaskAttempt, StudentSkillMastery
from mlmodels.tests.parse_skills_graph import SkillsGraphParser


class StudentCreatorWithAttempts:
    """Создатель студента с симуляцией попыток решения заданий"""
    
    def __init__(self):
        self.student_profile = None
        self.skills_graph = {}  # Граф навыков с prerequisites
        self.skills_by_depth = {}  # Навыки по уровням глубины
        self.created_attempts = []
          # Параметры симуляции
        self.time_variation = (30, 600)  # От 30 секунд до 10 минут
        
    def initialize_skills_graph(self):
        """Инициализирует граф навыков"""
        print("🔄 Инициализация графа навыков...")
        
        parser = SkillsGraphParser()
        parser.parse_skills_graph()
        
        # Преобразуем граф в нужный формат (названия навыков вместо ID)
        skill_id_to_name = {skill.id: skill.name for skill in Skill.objects.all()}
        
        self.skills_graph = {}
        for skill_id, prereq_ids in parser.skills_graph.items():
            skill_name = skill_id_to_name.get(skill_id)
            if skill_name:
                prereq_names = []
                for prereq_id in prereq_ids:
                    prereq_name = skill_id_to_name.get(prereq_id)
                    if prereq_name:
                        prereq_names.append(prereq_name)
                
                self.skills_graph[skill_name] = {
                    'prerequisites': prereq_names,
                    'skill_id': skill_id
                }
        
        # Вычисляем глубины навыков
        skill_depths = parser._calculate_skill_depths()
        self.skills_by_depth = {}
        for skill_id, depth in skill_depths.items():
            skill_name = skill_id_to_name.get(skill_id)
            if skill_name:
                if depth not in self.skills_by_depth:
                    self.skills_by_depth[depth] = []
                self.skills_by_depth[depth].append(skill_name)
        
        print(f"✅ Граф навыков инициализирован:")
        print(f"   • Навыков: {len(self.skills_graph)}")
        print(f"   • Уровней глубины: {len(self.skills_by_depth)}")
        print(f"   • Максимальная глубина: {max(self.skills_by_depth.keys()) if self.skills_by_depth else 0}")
        
        return self.skills_graph
    
    def create_student(self, recreate=False) -> StudentProfile:
        """Создает или пересоздает студента"""
        username = "alex_klementev"
        
        if recreate:
            print("⚠️  Пересоздание студента...")
            try:
                user = User.objects.get(username=username)
                user.delete()
                print("✅ Старый студент удален")
            except User.DoesNotExist:
                pass
        
        print("👨‍🎓 Создание студента Клементьева Алексея Александровича...")
        
        # Создаем пользователя
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'first_name': "Алексей",
                'last_name': "Клементьев",
                'email': "Alex0.oKlem@gmail.com",
                'is_active': True
            }
        )
        
        if not created and not recreate:
            print(f"⚠️ Студент {username} уже существует. Используйте recreate=True для пересоздания.")
            self.student_profile = user.studentprofile
            return self.student_profile
        
        # Создаем профиль студента
        student_profile, _ = StudentProfile.objects.get_or_create(
            user=user,
            defaults={
                'full_name': "Клементьев Алексей Александрович",
                'email': "Alex0.oKlem@gmail.com",
                'organization': "РГПУ им. Герцена",
                'is_active': True
            }
        )
        
        # Записываем студента на курсы
        courses = Course.objects.all()
        for course in courses:
            StudentCourseEnrollment.objects.get_or_create(
                student=student_profile,
                course=course,
                defaults={
                    'enrolled_at': timezone.now(),
                    'status': 'enrolled'
                }
            )
        
        self.student_profile = student_profile
        
        print(f"✅ Студент создан:")
        print(f"   • ФИО: {student_profile.full_name}")
        print(f"   • Email: {student_profile.email}")
        print(f"   • Организация: {student_profile.organization}")
        print(f"   • Username: {user.username}")
        print(f"   • Записан на курсов: {courses.count()}")
        
        return student_profile
    
    def get_mastered_skills(self) -> Set[str]:
        """Возвращает освоенные навыки (BKT >= 0.7)"""
        if not self.student_profile:
            return set()
        
        masteries = StudentSkillMastery.objects.filter(
            student=self.student_profile,
            current_mastery_prob__gte=0.7
        )
        return {mastery.skill.name for mastery in masteries}
    
    def get_available_skills(self) -> Set[str]:
        """Возвращает навыки доступные для изучения (prerequisites выполнены)"""
        mastered_skills = self.get_mastered_skills()
        available_skills = set()
        
        for skill_name, skill_data in self.skills_graph.items():
            prerequisites = skill_data.get('prerequisites', [])
            
            # Если все prerequisites выполнены, навык доступен
            if all(prereq in mastered_skills for prereq in prerequisites):
                available_skills.add(skill_name)
        
        return available_skills
    
    def create_attempts_for_skill(self, skill_name: str, target_attempts: int, target_success_rate: float) -> List[TaskAttempt]:
        """Создает попытки для одного навыка"""
        try:
            skill = Skill.objects.get(name=skill_name)
        except Skill.DoesNotExist:
            print(f"⚠️ Навык '{skill_name}' не найден")
            return []
        
        # Получаем задания для этого навыка
        tasks = list(Task.objects.filter(skills=skill))
        if not tasks:
            print(f"⚠️ Нет заданий для навыка '{skill_name}'")
            return []
        
        print(f"   📚 {skill_name}: {target_attempts} попыток, цель {target_success_rate:.1%}")
        
        attempts = []
        current_time = timezone.now() - timedelta(days=random.randint(1, 30))
        
        for i in range(target_attempts):
            # Выбираем случайное задание
            task = random.choice(tasks)
            
            # Определяем правильность ответа (с ростом к концу)
            progress_factor = i / max(target_attempts - 1, 1)
            adjusted_success_rate = target_success_rate * (0.4 + 0.6 * progress_factor)
            is_correct = random.random() < adjusted_success_rate
            
            # Время решения
            base_time = random.randint(*self.time_variation)
            if task.difficulty == DifficultyLevel.ADVANCED:
                base_time = int(base_time * 1.5)
            elif task.difficulty == DifficultyLevel.BEGINNER:
                base_time = int(base_time * 0.7)
            
            if not is_correct:
                base_time = int(base_time * 1.3)
            
            # Создаем попытку
            attempt_start = current_time
            attempt_end = current_time + timedelta(seconds=base_time)
            
            attempt = TaskAttempt.objects.create(
                student=self.student_profile,
                task=task,
                is_correct=is_correct,
                given_answer=f"Ответ на {task.title}" if is_correct else "Неправильный ответ",
                correct_answer=f"Правильный ответ на {task.title}",
                started_at=attempt_start,
                completed_at=attempt_end,
                time_spent=base_time,
                metadata={
                    'skill': skill_name,
                    'attempt_number': i + 1,
                    'total_attempts': target_attempts,
                    'simulated': True
                }
            )
            # BKT применяется автоматически в TaskAttempt.save()!
            
            attempts.append(attempt)
            current_time = attempt_end + timedelta(minutes=random.randint(5, 60))
        
        return attempts
    def simulate_learning_progression(self, max_skills_to_learn=8):
        """Симулирует последовательное изучение навыков по графу"""
        print(f"\n🎯 Симуляция изучения навыков (максимум {max_skills_to_learn})...")
        
        learned_skills = 0
        iteration = 0
        max_iterations = 50  # Защита от бесконечного цикла
        target_fully_learned = 6  # Целевое количество полностью освоенных навыков
        
        while learned_skills < max_skills_to_learn and iteration < max_iterations:
            iteration += 1
            
            # Получаем доступные навыки
            available_skills = self.get_available_skills()
            mastered_skills = self.get_mastered_skills()
            
            # Исключаем уже изученные навыки
            available_skills = available_skills - mastered_skills
            
            if not available_skills:
                print("⚠️ Нет доступных навыков для изучения")
                break
            
            # Выбираем случайный доступный навык
            skill_to_learn = random.choice(list(available_skills))
            
            # Определяем параметры изучения
            if learned_skills < target_fully_learned:  # Первые 6 навыков - высокая успешность для полного освоения
                attempts = random.randint(8, 15)
                success_rate = random.uniform(0.75, 0.95)
            elif learned_skills == target_fully_learned:  # 7-й навык - средняя успешность для частичного освоения
                attempts = random.randint(4, 7)
                success_rate = random.uniform(0.45, 0.65)  # Для частичного освоения (0.5-0.8)
            else:  # Остальные навыки - низкая успешность
                attempts = random.randint(2, 5)
                success_rate = random.uniform(0.3, 0.5)
            
            # Создаем попытки для навыка
            skill_attempts = self.create_attempts_for_skill(skill_to_learn, attempts, success_rate)
            self.created_attempts.extend(skill_attempts)
            
            # Проверяем, освоен ли навык
            try:
                mastery = StudentSkillMastery.objects.get(
                    student=self.student_profile,
                    skill__name=skill_to_learn
                )
                if mastery.current_mastery_prob >= 0.8:
                    if learned_skills < target_fully_learned:
                        learned_skills += 1
                        print(f"   ✅ Навык '{skill_to_learn}' полностью освоен (BKT: {mastery.current_mastery_prob:.3f})")
                    else:
                        print(f"   ✅ Навык '{skill_to_learn}' неожиданно полностью освоен (BKT: {mastery.current_mastery_prob:.3f})")
                elif mastery.current_mastery_prob >= 0.5:
                    print(f"   🟡 Навык '{skill_to_learn}' частично освоен (BKT: {mastery.current_mastery_prob:.3f})")
                    if learned_skills >= target_fully_learned:
                        # Учитываем частично освоенный навык в общем счете
                        learned_skills += 1
                else:
                    print(f"   🔴 Навык '{skill_to_learn}' слабо освоен (BKT: {mastery.current_mastery_prob:.3f})")
            except StudentSkillMastery.DoesNotExist:
                print(f"   ❌ Нет данных BKT для навыка '{skill_to_learn}'")
        
        print(f"\n✅ Симуляция завершена:")
        print(f"   • Итераций: {iteration}")
        print(f"   • Изученных навыков: {learned_skills}")
        print(f"   • Всего попыток: {len(self.created_attempts)}")
    
    def analyze_student_progress(self) -> Dict:
        """Анализирует прогресс студента"""
        print("\n📊 Анализ прогресса студента...")
        
        if not self.student_profile:
            print("❌ Студент не создан")
            return {}
        
        # Получаем данные
        attempts = TaskAttempt.objects.filter(student=self.student_profile)
        masteries = StudentSkillMastery.objects.filter(student=self.student_profile)
        
        # Анализируем освоение навыков
        fully_mastered = masteries.filter(current_mastery_prob__gte=0.8)
        partially_mastered = masteries.filter(
            current_mastery_prob__gte=0.5, 
            current_mastery_prob__lt=0.8
        )
        low_mastered = masteries.filter(current_mastery_prob__lt=0.5)
        
        # Получаем доступные навыки
        available_skills = self.get_available_skills()
        mastered_skill_names = self.get_mastered_skills()
        truly_available = available_skills - mastered_skill_names
        
        results = {
            'total_attempts': attempts.count(),
            'correct_attempts': attempts.filter(is_correct=True).count(),
            'skills_with_data': masteries.count(),
            'fully_mastered': fully_mastered.count(),
            'partially_mastered': partially_mastered.count(),
            'low_mastered': low_mastered.count(),
            'available_skills': len(truly_available),
            'success_rate': attempts.filter(is_correct=True).count() / max(attempts.count(), 1)
        }
        
        print(f"✅ Анализ завершен:")
        print(f"   • Всего попыток: {results['total_attempts']}")
        print(f"   • Правильных: {results['correct_attempts']} ({results['success_rate']:.1%})")
        print(f"   • Навыков с данными BKT: {results['skills_with_data']}")
        print(f"   • Полностью освоено (≥0.8): {results['fully_mastered']}")
        print(f"   • Частично освоено (0.5-0.8): {results['partially_mastered']}")
        print(f"   • Слабо освоено (<0.5): {results['low_mastered']}")
        print(f"   • Доступно для изучения: {results['available_skills']}")
        
        # Показываем детали
        if fully_mastered.exists():
            print(f"\n✅ ПОЛНОСТЬЮ ОСВОЕННЫЕ НАВЫКИ ({fully_mastered.count()}):")
            for mastery in fully_mastered.order_by('-current_mastery_prob'):
                print(f"   • {mastery.skill.name}: {mastery.current_mastery_prob:.3f} "
                      f"({mastery.correct_attempts}/{mastery.attempts_count})")
        
        if partially_mastered.exists():
            print(f"\n🟡 ЧАСТИЧНО ОСВОЕННЫЕ НАВЫКИ ({partially_mastered.count()}):")
            for mastery in partially_mastered.order_by('-current_mastery_prob'):
                print(f"   • {mastery.skill.name}: {mastery.current_mastery_prob:.3f} "
                      f"({mastery.correct_attempts}/{mastery.attempts_count})")
        
        if truly_available:
            print(f"\n🎯 ДОСТУПНЫЕ ДЛЯ ИЗУЧЕНИЯ НАВЫКИ ({len(truly_available)}):")
            for skill_name in sorted(truly_available):
                prerequisites = self.skills_graph.get(skill_name, {}).get('prerequisites', [])
                print(f"   • {skill_name}" + (f" (требует: {', '.join(prerequisites)})" if prerequisites else ""))
        
        return results
    def create_student_with_learning_simulation(self, recreate=False, max_skills=8):
        """Основная функция создания студента с симуляцией обучения"""
        try:
            # Инициализация
            self.initialize_skills_graph()
            
            # Создание студента
            student = self.create_student(recreate=recreate)
            
            # Симуляция обучения
            self.simulate_learning_progression(max_skills_to_learn=max_skills)
            
            # Анализ результатов
            results = self.analyze_student_progress()
            
            print("\n" + "="*80)
            print("✨ СТУДЕНТ УСПЕШНО СОЗДАН С СИМУЛЯЦИЕЙ ОБУЧЕНИЯ!")
            print("="*80)
            
            return results
           
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    """Основная функция для запуска из командной строки"""
    creator = StudentCreatorWithAttempts()
    
    # Можно передать аргументы
    import sys
    recreate = '--recreate' in sys.argv
    with transaction.atomic():
        results = creator.create_student_with_learning_simulation(
            recreate=recreate, 
            max_skills=8
        )


if __name__ == "__main__":
    main()
