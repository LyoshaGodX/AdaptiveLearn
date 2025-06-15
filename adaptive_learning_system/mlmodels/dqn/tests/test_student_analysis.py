#!/usr/bin/env python3
"""
Детальный анализ состояния студента и его обучения

Этот тест позволяет получить полную картину:
- BKT оценки навыков студента
- Доступные для изучения навыки по графу зависимостей
- Историю попыток и рекомендации
- Детальную информацию о конкретной попытке
"""

import os
import sys
from pathlib import Path
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Добавляем путь к Django проекту
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')

import django
django.setup()

import torch
from django.contrib.auth.models import User
from django.db.models import Q, Avg, Count

from skills.models import Skill
from methodist.models import Task
from mlmodels.models import TaskAttempt, StudentSkillMastery, DQNRecommendation
from student.models import StudentProfile
from mlmodels.dqn.data_processor import DQNDataProcessor
from mlmodels.dqn.recommender import DQNRecommender


class StudentAnalyzer:
    """Анализатор состояния студента"""
    
    def __init__(self, student_id: int):
        self.student_id = student_id
        self.processor = DQNDataProcessor()
        self.user = User.objects.get(id=student_id)
        self.profile, _ = StudentProfile.objects.get_or_create(user=self.user)    
    def analyze_student_state(self):
        """Полный анализ состояния студента"""
        print("=" * 80)
        print(f"🎓 АНАЛИЗ СОСТОЯНИЯ СТУДЕНТА {self.student_id}")
        print(f"👤 Пользователь: {self.user.username} ({self.user.first_name} {self.user.last_name})")
        print("=" * 80)
        
        # 1. BKT оценки навыков
        self._analyze_bkt_skills()
        
        # 2. Доступные навыки для изучения
        self._analyze_available_skills_detailed()
        
        # 3. Последняя попытка и связанная рекомендация
        self._analyze_last_attempt_and_recommendation()
        
        # 4. Текущая рекомендация
        self._analyze_current_recommendation()
        
        print("=" * 80)
        print("✅ Анализ завершен")
        print("=" * 80)
    
    def _analyze_bkt_skills(self):
        """Анализ BKT оценок навыков"""
        print("\n📊 BKT ОЦЕНКИ НАВЫКОВ СТУДЕНТА")
        print("-" * 50)
          # Получаем BKT данные
        bkt_data = self.processor._get_all_bkt_parameters(self.profile)
        
        if bkt_data is None or len(bkt_data) == 0:
            print("⚠️ BKT данные не найдены")
            return
            
        # Получаем список всех навыков
        skills = list(Skill.objects.all().order_by('id'))
        
        print(f"📈 Всего навыков: {len(skills)}")
        print(f"📊 BKT данных: {len(bkt_data)}")
        
        # Категоризация по уровню освоения
        high_mastery = []  # > 0.8
        medium_mastery = []  # 0.5 - 0.8  
        low_mastery = []  # < 0.5
        
        print("\n🎯 ДЕТАЛИЗАЦИЯ ПО НАВЫКАМ:")
        for i, skill in enumerate(skills):
            if i < len(bkt_data):
                prob = float(bkt_data[i])
                level = "🔥" if prob > 0.8 else "🔶" if prob > 0.5 else "🔴"
                
                print(f"  {level} {skill.name:<30} | P(знание) = {prob:.4f}")
                
                if prob > 0.8:
                    high_mastery.append((skill, prob))
                elif prob > 0.5:
                    medium_mastery.append((skill, prob))
                else:
                    low_mastery.append((skill, prob))
            else:                print(f"  ❓ {skill.name:<30} | Нет BKT данных")
        
        print(f"\n📊 СТАТИСТИКА ОСВОЕНИЯ:")
        print(f"  🔥 Высокий уровень (>0.8): {len(high_mastery)} навыков")
        print(f"  🔶 Средний уровень (0.5-0.8): {len(medium_mastery)} навыков") 
        print(f"  🔴 Низкий уровень (<0.5): {len(low_mastery)} навыков")
    def _analyze_available_skills_detailed(self):
        """Детальный анализ доступных навыков для изучения"""
        print("\n🎯 ДОСТУПНЫЕ НАВЫКИ ДЛЯ ИЗУЧЕНИЯ")
        print("-" * 50)
        
        # Получаем BKT данные
        bkt_data = self.processor._get_all_bkt_parameters(self.profile)
        skills = list(Skill.objects.all().order_by('id'))
        
        if bkt_data is None or len(bkt_data) == 0:
            print("⚠️ BKT данные не найдены")
            return
        
        # Определяем освоенные навыки (порог 0.7)
        mastered_skills = set()
        for i, skill in enumerate(skills):
            if i < len(bkt_data) and float(bkt_data[i]) > 0.7:
                mastered_skills.add(skill.id)
        
        print(f"📊 АЛГОРИТМ ОПРЕДЕЛЕНИЯ ДОСТУПНОСТИ:")
        print(f"   1. Все навыки в системе: {len(skills)}")
        print(f"   2. Освоенные навыки (P>0.7): {len(mastered_skills)}")
        print(f"   3. Доступные = навыки без prerequisite ИЛИ с освоенными prerequisite")
        
        # Анализируем каждый навык
        available_skills = []
        blocked_skills = []
        
        for i, skill in enumerate(skills):
            bkt_prob = float(bkt_data[i]) if i < len(bkt_data) else 0.0
            
            # Получаем prerequisites
            prerequisites = skill.prerequisites.all()
            
            if not prerequisites.exists():
                # Нет prerequisites - навык доступен
                available_skills.append((skill, bkt_prob, []))
            else:
                # Проверяем prerequisites
                missing_prereqs = []
                for prereq in prerequisites:
                    if prereq.id not in mastered_skills:
                        missing_prereqs.append(prereq.name)
                
                if not missing_prereqs:
                    # Все prerequisites освоены - навык доступен
                    available_skills.append((skill, bkt_prob, [p.name for p in prerequisites]))
                else:
                    # Есть неосвоенные prerequisites - навык заблокирован
                    blocked_skills.append((skill, bkt_prob, missing_prereqs))
        
        print(f"\n🎯 ВСЕ ДОСТУПНЫЕ НАВЫКИ ({len(available_skills)}):")
        for skill, prob, prereqs in available_skills:
            status = "🔥 ОСВОЕН" if prob > 0.8 else "🔶 ИЗУЧАЕТСЯ" if prob > 0.5 else "🔴 ТРЕБУЕТ ИЗУЧЕНИЯ"
            prereq_info = f" | Требовал: {', '.join(prereqs[:3])}" if prereqs else " | Базовый навык"
            if len(prereqs) > 3:
                prereq_info += f" (+{len(prereqs)-3} ещё)"
            print(f"  {status} {skill.name:<35} | P={prob:.4f}{prereq_info}")
        
        print(f"\n🚫 ЗАБЛОКИРОВАННЫЕ НАВЫКИ ({len(blocked_skills)}):")
        for skill, prob, missing in blocked_skills[:10]:  # Показываем первые 10
            missing_str = ", ".join(missing[:3])
            if len(missing) > 3:
                missing_str += f" (+{len(missing)-3} ещё)"
            print(f"  ❌ {skill.name:<35} | P={prob:.4f} | Нужны: {missing_str}")
        
        if len(blocked_skills) > 10:
            print(f"  ... и ещё {len(blocked_skills) - 10} заблокированных навыков")
    
    def _analyze_last_attempt_and_recommendation(self):
        """Анализ последней попытки и связанной рекомендации"""
        print("\n� ПОСЛЕДНЯЯ ПОПЫТКА И СВЯЗАННАЯ РЕКОМЕНДАЦИЯ")
        print("-" * 50)
        
        # Получаем последнюю попытку
        attempt = TaskAttempt.objects.filter(
            student__user_id=self.student_id
        ).select_related('task', 'student').order_by('-completed_at').first()
        
        if not attempt:
            print("⚠️ Попытки не найдены")
            return
        
        status = "✅ Правильно" if attempt.is_correct else "❌ Неправильно"
        print(f"🎯 Попытка #{attempt.id} | {status}")
        print(f"📅 Время: {attempt.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📋 Задание: {attempt.task.title}")
        print(f"⚡ Сложность: {attempt.task.difficulty}")
          # Навыки задания
        task_skills = attempt.task.skills.all()
        print(f"🎯 Развиваемые навыки ({task_skills.count()}):")
        for skill in task_skills:
            print(f"  • {skill.name}")
        
        # Поиск связанной рекомендации
        print(f"\n🤖 СВЯЗАННАЯ РЕКОМЕНДАЦИЯ:")
        try:
            # Сначала ищем прямую связь через поле attempt в DQNRecommendation
            recommendation = DQNRecommendation.objects.filter(attempt=attempt).first()
            
            if recommendation:
                print(f"✅ Найдена прямая связь (рекомендация -> попытка):")
                self._print_recommendation_details(recommendation)
            else:
                # Если прямой связи нет, ищем по времени и заданию
                print(f"🔍 Прямая связь не найдена, ищем по времени и заданию...")
                
                # Ищем рекомендации для этого студента по тому же заданию
                potential_recs = DQNRecommendation.objects.filter(
                    student__user_id=self.user.id,
                    task=attempt.task
                ).order_by('-created_at')
                
                if potential_recs.exists():
                    closest_rec = None
                    min_time_diff = None
                    
                    for rec in potential_recs:
                        # Вычисляем разность во времени
                        time_diff = abs((attempt.completed_at - rec.created_at).total_seconds())
                        if min_time_diff is None or time_diff < min_time_diff:
                            min_time_diff = time_diff
                            closest_rec = rec
                    
                    if closest_rec and min_time_diff <= 3600:  # В пределах часа
                        print(f"� Найдена вероятная связь (разница во времени: {min_time_diff:.0f} сек):")
                        self._print_recommendation_details(closest_rec)
                    else:
                        print(f"❌ Подходящая рекомендация не найдена")
                else:
                    print(f"❌ Рекомендации для этого задания не найдены")
                
        except Exception as e:
            print(f"⚠️ Ошибка поиска рекомендации: {e}")
    
    def _analyze_current_recommendation(self):
        """Анализ текущей рекомендации"""
        print("\n📌 ТЕКУЩАЯ РЕКОМЕНДАЦИЯ")
        print("-" * 50)
        
        try:
            from mlmodels.models import StudentCurrentRecommendation
            current = StudentCurrentRecommendation.objects.filter(
                student__user_id=self.student_id
            ).select_related('recommendation__task').first()
            
            if current:
                print(f"✅ Найдена текущая рекомендация:")
                print(f"📅 Установлена: {current.set_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"👁️ Просмотров: {current.times_viewed}")
                
                # LLM объяснение в текущей рекомендации
                if hasattr(current, 'llm_explanation') and current.llm_explanation:
                    print(f"🤖 LLM объяснение в текущей записи: ✅ Есть ({len(current.llm_explanation)} символов)")
                    preview = current.llm_explanation[:150] + "..." if len(current.llm_explanation) > 150 else current.llm_explanation
                    print(f"   📝 Превью: {preview}")
                else:
                    print(f"🤖 LLM объяснение в текущей записи: ❌ Пустое")
                
                self._print_recommendation_details(current.recommendation)
            else:
                print(f"❌ Текущая рекомендация не установлена")
                
        except Exception as e:
            print(f"⚠️ Ошибка получения текущей рекомендации: {e}")
    
    def _print_recommendation_details(self, recommendation):
        """Печатает все доступные поля рекомендации"""
        print(f"  🆔 ID рекомендации: {recommendation.id}")
        print(f"  📋 ID задания: {recommendation.task.id}")
        print(f"  📝 Название задания: {recommendation.task.title}")
        print(f"  👤 Студент ID (User): {recommendation.student.user.id}")
        print(f"  � Студент ID (Profile): {recommendation.student.id}")
        print(f"  �📊 Q-value: {recommendation.q_value:.6f}")
        print(f"  📈 Уверенность: {recommendation.confidence:.6f}")
        print(f"  💡 Причина: {recommendation.reason}")
        print(f"  📅 Создана: {recommendation.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  🎯 Активная: {'Да' if recommendation.is_active else 'Нет'}")
        print(f"  ⚡ Сложность задания: {recommendation.task.difficulty}")
        print(f"  🔤 Тип задания: {recommendation.task.task_type}")
        print(f"  ✅ Задание активно: {'Да' if recommendation.task.is_active else 'Нет'}")
        
        # Связанная попытка
        if recommendation.attempt:
            status = "✅ Правильно" if recommendation.attempt.is_correct else "❌ Неправильно"
            print(f"  🔗 Связанная попытка: #{recommendation.attempt.id} {status}")
            print(f"     📅 Выполнена: {recommendation.attempt.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"  🔗 Связанная попытка: Не выполнена")
          # Снимок состояния студента
        if hasattr(recommendation, 'student_state_snapshot') and recommendation.student_state_snapshot:
            print(f"  📊 Снимок состояния: Сохранен ({len(str(recommendation.student_state_snapshot))} символов)")
        else:
            print(f"  📊 Снимок состояния: Не сохранен")
          # LLM объяснение в рекомендации
        if hasattr(recommendation, 'llm_explanation') and recommendation.llm_explanation:
            print(f"  🤖 LLM объяснение в рекомендации: ✅ Есть ({len(recommendation.llm_explanation)} символов)")
            preview = recommendation.llm_explanation[:150] + "..." if len(recommendation.llm_explanation) > 150 else recommendation.llm_explanation
            print(f"     📝 Превью: {preview}")
        else:
            print(f"  🤖 LLM объяснение в рекомендации: ❌ Пустое")
        
        # LLM контекстные поля
        print(f"\n  📊 LLM КОНТЕКСТНЫЕ ПОЛЯ:")
        
        # Prerequisite навыки
        if hasattr(recommendation, 'prerequisite_skills_snapshot') and recommendation.prerequisite_skills_snapshot:
            print(f"  🔗 Prerequisite навыки: ✅ Есть ({len(recommendation.prerequisite_skills_snapshot)} записей)")
            for skill in recommendation.prerequisite_skills_snapshot[:3]:  # Показываем первые 3
                print(f"     • {skill.get('skill_name', 'N/A')} | P(знание) = {skill.get('mastery_probability', 0):.4f}")
        else:
            print(f"  🔗 Prerequisite навыки: ❌ Пустое")
        
        # Зависимые навыки
        if hasattr(recommendation, 'dependent_skills_snapshot') and recommendation.dependent_skills_snapshot:
            print(f"  🔄 Зависимые навыки: ✅ Есть ({len(recommendation.dependent_skills_snapshot)} записей)")
            for skill in recommendation.dependent_skills_snapshot[:3]:  # Показываем первые 3
                print(f"     • {skill.get('skill_name', 'N/A')} | P(знание) = {skill.get('mastery_probability', 0):.4f}")
        else:
            print(f"  🔄 Зависимые навыки: ❌ Пустое")
        
        # Целевой навык
        if hasattr(recommendation, 'target_skill_info') and recommendation.target_skill_info:
            print(f"  🎯 Целевой навык: ✅ Есть ({len(recommendation.target_skill_info)} записей)")
            for skill in recommendation.target_skill_info[:2]:  # Показываем первые 2
                print(f"     • {skill.get('skill_name', 'N/A')} | Текущая P(знание) = {skill.get('current_mastery_probability', 0):.4f}")
                print(f"       Попыток: {skill.get('attempts_count', 0)} | Успех: {skill.get('success_rate', 0):.2%}")
        else:
            print(f"  🎯 Целевой навык: ❌ Пустое")
        
        # Альтернативные задания
        if hasattr(recommendation, 'alternative_tasks_considered') and recommendation.alternative_tasks_considered:
            print(f"  🔀 Альтернативы: ✅ Есть ({len(recommendation.alternative_tasks_considered)} заданий)")
            for task in recommendation.alternative_tasks_considered[:2]:  # Показываем первые 2
                print(f"     • Задание {task.get('task_id', 'N/A')}: {task.get('task_title', 'N/A')} | Q={task.get('q_value', 0):.4f}")
        else:
            print(f"  🔀 Альтернативы: ❌ Пустое")
        
        # Контекст прогресса
        if hasattr(recommendation, 'student_progress_context') and recommendation.student_progress_context:
            progress = recommendation.student_progress_context
            print(f"  📈 Контекст прогресса: ✅ Есть")
            print(f"     • Общих попыток: {progress.get('total_attempts', 0)}")
            print(f"     • Общий успех: {progress.get('total_success_rate', 0):.2%}")
            print(f"     • Недавних попыток: {progress.get('recent_attempts_count', 0)}")
            print(f"     • Недавний успех: {progress.get('recent_success_rate', 0):.2%}")
        else:
            print(f"  📈 Контекст прогресса: ❌ Пустое")
def test_student_analysis():
    """Главная функция теста"""
    print("🧪 ТЕСТ ДЕТАЛЬНОГО АНАЛИЗА СОСТОЯНИЯ СТУДЕНТА")
    print("=" * 80)
    
    # Найдем студента с данными
    students_with_attempts = TaskAttempt.objects.values('student__user_id').annotate(
        attempt_count=Count('id')
    ).filter(attempt_count__gt=0).order_by('-attempt_count')[:5]
    
    if not students_with_attempts:
        print("⚠️ Студенты с попытками не найдены")
        
        # Создаем тестового студента
        print("🔧 Создаем тестового студента...")
        user, created = User.objects.get_or_create(
            username='test_student_analysis',
            defaults={'first_name': 'Test', 'last_name': 'Student'}
        )
        student_id = user.id
        print(f"👤 Создан студент ID: {student_id}")
        
    else:
        # Берем студента с наибольшим количеством попыток
        student_id = students_with_attempts[0]['student__user_id']
        attempt_count = students_with_attempts[0]['attempt_count']
        print(f"👤 Выбран студент ID: {student_id} ({attempt_count} попыток)")
    
    # Запускаем анализ
    analyzer = StudentAnalyzer(student_id)
    analyzer.analyze_student_state()
    
    return True


if __name__ == "__main__":
    try:
        success = test_student_analysis()
        if success:
            print("\n🎉 Тест успешно выполнен!")
        else:
            print("\n❌ Тест завершился с ошибками")
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
