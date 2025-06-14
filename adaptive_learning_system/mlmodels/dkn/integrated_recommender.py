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
            # Определяем путь к модели
            if model_path is None:
                model_path = str(Path(__file__).parent / "training" / "models" / "best_model.pth")
            
            config = DKNConfig()
            self.dkn_model = DKNModel(
                num_skills=len(self.data_processor.skill_to_id),
                num_tasks=len(self.data_processor.task_to_id),
                config=config
            )
            
            if model_path and os.path.exists(model_path):
                checkpoint = torch.load(model_path, map_location='cpu')
                if 'model_state_dict' in checkpoint:
                    self.dkn_model.load_state_dict(checkpoint['model_state_dict'])
                else:
                    self.dkn_model.load_state_dict(checkpoint)
                print(f"✅ DKN модель загружена из {model_path}")
            else:
                print(f"⚠️  Файл модели не найден: {model_path}")
                print("⚠️  Использую необученную DKN модель")
                
            self.dkn_model.eval()
            
        except Exception as e:
            print(f"⚠️  Ошибка загрузки DKN модели: {e}")
            print(f"⚠️  Детали ошибки: {type(e).__name__}")
            self.dkn_model = None
    
    def get_recommendations(self, student_id: int, num_recommendations: int = 5) -> List[IntegratedRecommendation]:
        """
        Получает интегрированные рекомендации: DKN + анализ навыков
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
        
        return skill_analysis
    
    def _get_skill_status(self, mastery_prob: float) -> str:
        """Определяет статус освоения навыка"""
        if mastery_prob >= self.mastery_threshold:
            return '✅'  # Освоен
        elif mastery_prob >= self.near_mastery_threshold:
            return '🔄'  # Близко к освоению
        else:
            return '❌'  # Не освоен
    
    def _build_integrated_recommendations(self, skill_analysis: Dict, student_profile: StudentProfile, student_id: int) -> List[IntegratedRecommendation]:
        """Строит интегрированные рекомендации: навыки + DKN"""
        print("\n🎯 ПОСТРОЕНИЕ ИНТЕГРИРОВАННЫХ РЕКОМЕНДАЦИЙ:")
        
        recommendations = []
        task_data_list = []
        tasks_for_prediction = []
        
        # Собираем задания для навыков, которые нужно изучать
        for skill_name, skill_data in skill_analysis.items():
            skill = skill_data['skill']
            mastery_prob = skill_data['mastery_prob']
            status = skill_data['status']
            
            # Рекомендуем задания для навыков, которые нужно изучать
            if status in ['🔄', '❌']:
                tasks = Task.objects.filter(skills=skill)[:3]  # Максимум 3 задания на навык
                
                for task in tasks:
                    tasks_for_prediction.append(task)
                    
                    # Подготавливаем данные для DKN модели
                    if self.dkn_model:
                        try:
                            student_data = self.data_processor.get_student_data(student_id, task.id)
                            task_data_list.append(student_data)
                        except Exception as e:
                            print(f"   ⚠️  Ошибка получения данных для задания {task.id}: {e}")
                            task_data_list.append(None)
                    else:
                        task_data_list.append(None)
        
        # Получаем DKN предсказания для всех заданий
        dkn_predictions = self._get_dkn_predictions(task_data_list)
        
        # Создаем финальные рекомендации
        recommendation_idx = 0
        for skill_name, skill_data in skill_analysis.items():
            skill = skill_data['skill']
            mastery_prob = skill_data['mastery_prob']
            status = skill_data['status']
            
            if status in ['🔄', '❌']:
                tasks = Task.objects.filter(skills=skill)[:3]
                
                for task in tasks:
                    if recommendation_idx < len(dkn_predictions):
                        dkn_pred = dkn_predictions[recommendation_idx]
                        prediction_value = dkn_pred if dkn_pred is not None else 0.5
                    else:
                        prediction_value = 0.5  # Значение по умолчанию
                    
                    priority = self._calculate_integrated_priority(skill_name, mastery_prob, task, prediction_value, skill_analysis)
                    confidence = self._calculate_confidence(mastery_prob, prediction_value)
                    reasoning = self._generate_integrated_reasoning(skill_name, mastery_prob, task, prediction_value)
                    
                    recommendation = IntegratedRecommendation(
                        task_id=task.id,
                        task_title=task.title,
                        skill_name=skill_name,
                        skill_mastery=mastery_prob,
                        task_difficulty=task.difficulty,
                        dkn_prediction=prediction_value,
                        priority=priority,
                        reasoning=reasoning,
                        confidence=confidence
                    )
                    
                    recommendations.append(recommendation)
                    
                    print(f"   📋 {task.title}")
                    print(f"      Навык: {skill_name} ({mastery_prob:.1%})")
                    print(f"      DKN предсказание: {prediction_value:.1%}")
                    print(f"      Приоритет: {priority}")
                    print(f"      Уверенность: {confidence:.2f}")
                    print()
                    
                    recommendation_idx += 1
        
        return recommendations
    
    def _get_dkn_predictions(self, task_data_list: List) -> List[Optional[float]]:
        """Получает предсказания DKN модели для списка заданий"""
        if not self.dkn_model or not task_data_list:
            return [None] * len(task_data_list)
        
        try:
            # Фильтруем валидные данные
            valid_data = [data for data in task_data_list if data is not None]
            
            if not valid_data:
                return [None] * len(task_data_list)
            
            # Подготавливаем батч
            batch = self.data_processor.prepare_batch(valid_data)
            
            # Получаем предсказания
            with torch.no_grad():
                predictions = self.dkn_model(batch)
            
            # Преобразуем в список
            pred_values = predictions.numpy().tolist()
            
            # Восстанавливаем порядок (учитываем None значения)
            result = []
            pred_idx = 0
            for data in task_data_list:
                if data is not None:
                    result.append(pred_values[pred_idx])
                    pred_idx += 1
                else:
                    result.append(None)
            
            return result
            
        except Exception as e:
            print(f"   ⚠️  Ошибка получения DKN предсказаний: {e}")
            return [None] * len(task_data_list)
    
    def _calculate_integrated_priority(self, skill_name: str, mastery_prob: float, task: Task, dkn_prediction: float, skill_analysis: Dict) -> int:
        """Рассчитывает приоритет с учетом навыков и DKN"""
        # Базовый приоритет на основе освоения навыка
        if mastery_prob < 0.3:
            base_priority = 1  # Критично важно
        elif mastery_prob < 0.6:
            base_priority = 2  # Важно
        else:
            base_priority = 3  # Средняя важность
        
        # Корректируем на основе DKN предсказания
        if dkn_prediction > 0.7:
            dkn_modifier = -1  # Высокая вероятность успеха - повышаем приоритет
        elif dkn_prediction < 0.3:
            dkn_modifier = 1   # Низкая вероятность - понижаем приоритет
        else:
            dkn_modifier = 0
        
        # Учитываем сложность
        if task.difficulty == 'beginner':
            difficulty_modifier = 0
        elif task.difficulty == 'intermediate':
            difficulty_modifier = 1
        else:
            difficulty_modifier = 2
        
        final_priority = max(1, min(5, base_priority + dkn_modifier + difficulty_modifier))
        return final_priority
    
    def _calculate_confidence(self, mastery_prob: float, dkn_prediction: float) -> float:
        """Рассчитывает уверенность в рекомендации"""
        # Уверенность выше, когда данные BKT и DKN согласованы
        if mastery_prob > 0.6 and dkn_prediction > 0.6:
            return 0.9  # Высокая уверенность
        elif mastery_prob < 0.4 and dkn_prediction < 0.4:
            return 0.8  # Высокая уверенность (согласованность)
        elif abs(mastery_prob - dkn_prediction) < 0.2:
            return 0.7  # Средняя уверенность
        else:
            return 0.5  # Низкая уверенность (несогласованность)
    
    def _generate_integrated_reasoning(self, skill_name: str, mastery_prob: float, task: Task, dkn_prediction: float) -> str:
        """Генерирует обоснование с учетом BKT и DKN данных"""
        # Анализ освоения навыка
        if mastery_prob < 0.3:
            skill_status = "не освоен"
        elif mastery_prob < 0.7:
            skill_status = "частично освоен"
        else:
            skill_status = "близок к освоению"
        
        # Анализ DKN предсказания
        if dkn_prediction > 0.7:
            dkn_status = "высокая вероятность успеха"
        elif dkn_prediction > 0.5:
            dkn_status = "средняя вероятность успеха"
        else:
            dkn_status = "низкая вероятность успеха"
        
        reasoning = f"Навык '{skill_name}' {skill_status} (BKT: {mastery_prob:.1%}). "
        reasoning += f"DKN модель предсказывает {dkn_status} ({dkn_prediction:.1%}). "
        reasoning += f"Задание уровня '{task.difficulty}' рекомендуется для развития навыка."
        
        return reasoning
    
    def print_detailed_analysis(self, student_id: int):
        """Выводит детальный анализ и рекомендации"""
        print(f"\n🔍 ДЕТАЛЬНЫЙ АНАЛИЗ ИНТЕГРИРОВАННЫХ РЕКОМЕНДАЦИЙ")
        print("=" * 60)
        
        recommendations = self.get_recommendations(student_id, num_recommendations=5)
        
        print(f"\n🎯 ТОП-5 ИНТЕГРИРОВАННЫХ РЕКОМЕНДАЦИЙ:")
        print("-" * 40)
        
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec.task_title}")
            print(f"   🎯 Навык: {rec.skill_name}")
            print(f"   📊 BKT освоение: {rec.skill_mastery:.1%}")
            print(f"   🧠 DKN предсказание: {rec.dkn_prediction:.1%}")
            print(f"   📈 Сложность: {rec.task_difficulty}")
            print(f"   ⭐ Приоритет: {rec.priority}/5")
            print(f"   🎯 Уверенность: {rec.confidence:.2f}")
            print(f"   💭 Обоснование: {rec.reasoning}")
            print()


def test_integrated_recommender(student_id: int = 7):
    """Тестирует интегрированную систему рекомендаций"""
    print("🧪 ТЕСТИРОВАНИЕ ИНТЕГРИРОВАННОЙ СИСТЕМЫ РЕКОМЕНДАЦИЙ")
    print("=" * 70)
    
    # Пытаемся найти обученную модель
    model_paths = [
        "training/models/best_model.pth",
        "../checkpoints/best_model.pth", 
        "../best_enhanced_model.pth",
        "../best_simple_model.pth"
    ]
    
    model_path = None
    for path in model_paths:
        if os.path.exists(path):
            model_path = path
            break
    
    recommender = IntegratedSkillRecommender(model_path)
    recommender.print_detailed_analysis(student_id)
    
    print("\n✅ Тестирование завершено!")
    print("\n🎯 Преимущества интегрированной системы:")
    print("   ✅ Комбинирует DKN предсказания и BKT анализ навыков")
    print("   ✅ Учитывает согласованность разных источников данных")
    print("   ✅ Приоритизирует на основе важности навыков и точности предсказаний")
    print("   ✅ Предоставляет уверенность в рекомендациях")
    print("   ✅ Объясняет рекомендации через множественные источники")
    print("   ✅ Интегрирует полный цикл: База → DKN → Навыки → Рекомендации")


if __name__ == "__main__":
    test_integrated_recommender(student_id=7)
