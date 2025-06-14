#!/usr/bin/env python3
"""
Интегрированная система рекомендаций:
DKN предсказания + анализ графа навыков + BKT данные

Полный цикл:
1. data_processor - извлечение данных из базы
2. model - получение предсказаний DKN 
3. skill_based_recommender - финальные рекомендации с учетом навыков
"""

import os
import sys
import django
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging
import torch
import numpy as np

# Настройка Django
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

from django.contrib.auth.models import User
from skills.models import Skill
from methodist.models import Task
from mlmodels.models import TaskAttempt, StudentSkillMastery
from student.models import StudentProfile

# Импорты DKN модулей
from data_processor import DKNDataProcessor
from model import DKNModel, DKNConfig

logger = logging.getLogger(__name__)


@dataclass
class IntegratedRecommendation:
    """Результат интегрированной рекомендации"""
    task_id: int
    task_title: str
    skill_name: str
    skill_mastery: float
    task_difficulty: str
    dkn_prediction: float  # Предсказание DKN модели
    priority: int  # 1-5, где 1 - самый важный
    reasoning: str
    confidence: float  # Уверенность в рекомендации


class IntegratedSkillRecommender:
    """Интегрированная система рекомендаций: DKN + анализ навыков"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.mastery_threshold = 0.8  # Навык считается освоенным при 80%
        self.near_mastery_threshold = 0.6  # Близко к освоению при 60%
        
        # Инициализация DKN компонентов
        self.data_processor = DKNDataProcessor()
        self.dkn_model = None
        
        # Пытаемся загрузить обученную DKN модель
        self._load_dkn_model(model_path)
    
    def _load_dkn_model(self, model_path: Optional[str]):
        """Загружает DKN модель"""
        try:
            config = DKNConfig()
            self.dkn_model = DKNModel(
                num_skills=len(self.data_processor.skill_to_id),
                num_tasks=len(self.data_processor.task_to_id),
                config=config
            )
            
            if model_path and os.path.exists(model_path):
                checkpoint = torch.load(model_path, map_location='cpu')
                self.dkn_model.load_state_dict(checkpoint['model_state_dict'])
                print(f"✅ DKN модель загружена из {model_path}")
            else:
                print("⚠️  Использую необученную DKN модель")
                
            self.dkn_model.eval()
            
        except Exception as e:
            print(f"⚠️  Ошибка загрузки DKN модели: {e}")
            self.dkn_model = None
      def get_recommendations(self, student_id: int, num_recommendations: int = 5) -> List[IntegratedRecommendation]:
        """
        Получает интегрированные рекомендации: DKN + анализ навыков
        
        Алгоритм:
        1. Анализирует навыки студента (BKT данные)
        2. Получает DKN предсказания для кандидатов заданий
        3. Комбинирует информацию для финальных рекомендаций
        4. Приоритизирует по важности навыков и точности предсказаний
        """
        print(f"\n🎯 ИНТЕГРИРОВАННЫЕ РЕКОМЕНДАЦИИ ДЛЯ СТУДЕНТА {student_id}")
        print("=" * 60)
        
        try:
            # 1. Получаем студента
            user = User.objects.get(id=student_id)
            student_profile = StudentProfile.objects.get(user=user)
            print(f"👤 Студент: {user.username}")
            
            # 2. Анализируем освоение навыков
            skill_analysis = self._analyze_student_skills(student_profile)
            
            # 3. Получаем кандидатов заданий и DKN предсказания
            recommendations = self._build_integrated_recommendations(skill_analysis, student_profile, student_id)
            
            # 4. Сортируем по приоритету и уверенности
            recommendations.sort(key=lambda x: (x.priority, -x.confidence, -x.dkn_prediction))
            
            return recommendations[:num_recommendations]
            
        except Exception as e:
            logger.error(f"Ошибка получения рекомендаций: {e}")
            print(f"❌ Ошибка: {e}")
            return []
    
    def _analyze_student_skills(self, student_profile: StudentProfile) -> Dict[str, Dict]:
        """Анализирует освоение навыков студентом"""
        print("\n📊 АНАЛИЗ ОСВОЕНИЯ НАВЫКОВ:")
        
        # Получаем все навыки и их освоение
        skill_masteries = StudentSkillMastery.objects.filter(student=student_profile)
        
        skill_analysis = {}
        
        for mastery in skill_masteries:
            skill_name = mastery.skill.name
            mastery_prob = mastery.current_mastery_prob
            
            status = self._get_skill_status(mastery_prob)
            
            skill_analysis[skill_name] = {
                'skill_id': mastery.skill.id,
                'mastery_prob': mastery_prob,
                'status': status,
                'skill': mastery.skill
            }
            
            print(f"   {status} {skill_name}: {mastery_prob:.1%}")
        
        print(f"\n📈 Всего навыков: {len(skill_analysis)}")
        
        # Подсчитываем статистику
        mastered = sum(1 for s in skill_analysis.values() if s['status'] == '✅')
        learning = sum(1 for s in skill_analysis.values() if s['status'] == '🔄')
        not_started = sum(1 for s in skill_analysis.values() if s['status'] == '❌')
        
        print(f"   ✅ Освоенные: {mastered}")
        print(f"   🔄 Изучаемые: {learning}")
        print(f"   ❌ Не начатые: {not_started}")
        
        return skill_analysis
    
    def _get_skill_status(self, mastery_prob: float) -> str:
        """Определяет статус освоения навыка"""
        if mastery_prob >= self.mastery_threshold:
            return '✅'  # Освоен
        elif mastery_prob >= self.near_mastery_threshold:
            return '🔄'  # Близко к освоению
        else:
            return '❌'  # Не освоен
    
    def _build_skill_recommendations(self, skill_analysis: Dict, student_profile: StudentProfile) -> List[SkillBasedRecommendation]:
        """Строит рекомендации на основе анализа навыков"""
        print("\n🎯 ПОСТРОЕНИЕ РЕКОМЕНДАЦИЙ:")
        
        recommendations = []
        
        # Проходим по всем навыкам и определяем приоритеты
        for skill_name, skill_data in skill_analysis.items():
            skill = skill_data['skill']
            mastery_prob = skill_data['mastery_prob']
            status = skill_data['status']
            
            # Рекомендуем задания для навыков, которые нужно изучать
            if status in ['🔄', '❌']:
                # Получаем задания для этого навыка
                tasks = Task.objects.filter(skills=skill)[:3]  # Максимум 3 задания на навык
                
                for task in tasks:
                    priority = self._calculate_priority(skill_name, mastery_prob, task, skill_analysis)
                    
                    # Выбираем сложность задания на основе освоения навыка
                    preferred_difficulty = self._choose_task_difficulty(mastery_prob, task.difficulty)
                    
                    # Создаем обоснование
                    reasoning = self._generate_reasoning(skill_name, mastery_prob, task, skill_analysis)
                    
                    recommendation = SkillBasedRecommendation(
                        task_id=task.id,
                        task_title=task.title,
                        skill_name=skill_name,
                        skill_mastery=mastery_prob,
                        task_difficulty=task.difficulty,
                        reasoning=reasoning,
                        priority=priority
                    )
                    
                    recommendations.append(recommendation)
                    
                    print(f"   📋 {task.title}")
                    print(f"      Навык: {skill_name} ({mastery_prob:.1%})")
                    print(f"      Сложность: {task.difficulty}")
                    print(f"      Приоритет: {priority}")
                    print(f"      Обоснование: {reasoning[:100]}...")
                    print()
        
        return recommendations
    
    def _calculate_priority(self, skill_name: str, mastery_prob: float, task: Task, skill_analysis: Dict) -> int:
        """
        Рассчитывает приоритет задания
        
        Приоритет 1 (самый важный) - базовые неосвоенные навыки
        Приоритет 5 (менее важный) - продвинутые навыки
        """
        # Базовая логика: чем меньше освоен навык, тем выше приоритет
        if mastery_prob < 0.3:
            base_priority = 1  # Критично важно
        elif mastery_prob < 0.6:
            base_priority = 2  # Важно
        else:
            base_priority = 3  # Средняя важность
        
        # Корректируем приоритет на основе сложности задания
        if task.difficulty == 'beginner':
            difficulty_modifier = 0  # Предпочитаем простые задания
        elif task.difficulty == 'intermediate':
            difficulty_modifier = 1
        else:  # advanced
            difficulty_modifier = 2
        
        # Проверяем, является ли навык базовым (по количеству связанных заданий)
        skill_tasks_count = Task.objects.filter(skills__name=skill_name).count()
        if skill_tasks_count > 10:  # Много заданий = базовый навык
            base_priority -= 1  # Повышаем приоритет
        
        final_priority = max(1, min(5, base_priority + difficulty_modifier))
        return final_priority
    
    def _choose_task_difficulty(self, mastery_prob: float, current_difficulty: str) -> str:
        """Выбирает подходящую сложность задания на основе освоения навыка"""
        if mastery_prob < 0.3:
            return 'beginner'  # Начинаем с базового уровня
        elif mastery_prob < 0.7:
            return 'intermediate'  # Переходим к среднему уровню
        else:
            return 'advanced'  # Можем пробовать сложные задания
    
    def _generate_reasoning(self, skill_name: str, mastery_prob: float, task: Task, skill_analysis: Dict) -> str:
        """Генерирует обоснование рекомендации"""
        
        # Определяем статус навыка
        if mastery_prob < 0.3:
            skill_status = "не освоен"
            action = "необходимо начать изучение"
        elif mastery_prob < 0.7:
            skill_status = "частично освоен"
            action = "требуется дополнительная практика"
        else:
            skill_status = "близок к освоению"
            action = "можно переходить к более сложным заданиям"
        
        # Анализируем связанные навыки
        related_skills = []
        for other_skill, other_data in skill_analysis.items():
            if other_skill != skill_name and other_data['mastery_prob'] > 0.8:
                related_skills.append(other_skill)
        
        base_reasoning = f"Навык '{skill_name}' {skill_status} ({mastery_prob:.1%}), {action}."
        
        if related_skills and len(related_skills) <= 2:
            base_reasoning += f" У вас хорошо освоены связанные навыки: {', '.join(related_skills[:2])}."
        
        difficulty_reasoning = f" Задание уровня '{task.difficulty}' подходит для вашего текущего уровня."
        
        return base_reasoning + difficulty_reasoning
    
    def print_detailed_analysis(self, student_id: int):
        """Выводит детальный анализ и рекомендации"""
        print(f"\n🔍 ДЕТАЛЬНЫЙ АНАЛИЗ РЕКОМЕНДАЦИЙ")
        print("=" * 60)
        
        recommendations = self.get_recommendations(student_id, num_recommendations=5)
        
        print(f"\n🎯 ТОП-5 РЕКОМЕНДАЦИЙ:")
        print("-" * 40)
        
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec.task_title}")
            print(f"   🎯 Навык: {rec.skill_name}")
            print(f"   📊 Освоение: {rec.skill_mastery:.1%}")
            print(f"   📈 Сложность: {rec.task_difficulty}")
            print(f"   ⭐ Приоритет: {rec.priority}/5")
            print(f"   💭 Обоснование: {rec.reasoning}")
            print()


def test_skill_recommender(student_id: int = 7):
    """Тестирует систему рекомендаций на основе навыков"""
    print("🧪 ТЕСТИРОВАНИЕ СИСТЕМЫ РЕКОМЕНДАЦИЙ НА ОСНОВЕ НАВЫКОВ")
    print("=" * 70)
    
    recommender = SkillBasedRecommender()
    recommender.print_detailed_analysis(student_id)
    
    print("\n✅ Тестирование завершено!")
    print("\n🎯 Преимущества новой системы:")
    print("   ✅ Анализ реальных BKT данных освоения навыков")
    print("   ✅ Учет иерархии навыков (базовые → продвинутые)")
    print("   ✅ Приоритизация на основе степени освоения")
    print("   ✅ Адаптивный выбор сложности заданий")
    print("   ✅ Понятные объяснения рекомендаций")
    print("   ✅ Простая и прозрачная логика")


if __name__ == "__main__":
    test_skill_recommender(student_id=7)
