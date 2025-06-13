"""
Программный интерфейс для переоценки характеристик студента
на основе истории прохождения заданий с использованием BKT модели
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pickle
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import logging

# Django imports
from django.conf import settings
from django.db import transaction
from django.core.cache import cache

# Local imports
from mlmodels.bkt.base_model import BKTModel, BKTParameters, TaskCharacteristics
from mlmodels.bkt.new_skill_manager import NewSkillManager
from methodist.models import Course, Task
from skills.models import Skill
from student.models import StudentProfile

# Настройка логирования
logger = logging.getLogger(__name__)

@dataclass
class AttemptData:
    """Данные об одной попытке студента"""
    student_id: int
    task_id: int
    skill_id: int
    course_id: Optional[int]
    is_correct: bool
    answer_score: float  # 0.0-1.0
    task_type: str
    difficulty: str
    timestamp: datetime
    attempt_number: int = 1

@dataclass
class SkillAssessment:
    """Оценка освоения навыка"""
    skill_id: int
    skill_name: str
    current_mastery: float  # 0.0-1.0
    attempts_count: int
    correct_attempts: int
    accuracy: float  # 0.0-1.0
    last_updated: datetime
    confidence_level: str  # 'low', 'medium', 'high'

@dataclass 
class CourseAssessment:
    """Оценка освоения курса"""
    course_id: int
    course_name: str
    overall_mastery: float  # 0.0-1.0
    skills_mastery: Dict[int, float]  # skill_id -> mastery
    completed_skills: int
    total_skills: int
    progress_percentage: float  # 0.0-100.0
    estimated_completion: Optional[datetime]
    difficulty_trend: str  # 'improving', 'stable', 'declining'

@dataclass
class StudentCharacteristics:
    """Характеристики студента"""
    student_id: int
    overall_performance: float  # 0.0-1.0
    learning_rate: float  # Скорость обучения
    consistency: float  # Стабильность результатов
    strong_areas: List[str]  # Сильные области
    weak_areas: List[str]  # Слабые области
    recommended_difficulty: str  # 'easy', 'medium', 'hard'
    study_time_estimate: int  # Часы в неделю
    last_assessment: datetime

class StudentAssessmentInterface:
    """Программный интерфейс для переоценки характеристик студента"""
    
    def __init__(self, model_path: str = "optimized_bkt_model/bkt_model_optimized.pkl"):
        """
        Инициализация интерфейса
        
        Args:
            model_path: Путь к обученной BKT модели
        """
        self.model_path = model_path
        self.bkt_model = None
        self.skill_manager = None
        self._load_model()
        
    def _load_model(self):
        """Загрузить BKT модель"""
        try:
            with open(self.model_path, 'rb') as f:
                self.bkt_model = pickle.load(f)
            self.skill_manager = NewSkillManager(self.bkt_model)
            logger.info(f"BKT модель загружена из {self.model_path}")
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            raise
    
    def process_attempt_history(
        self, 
        student_id: int, 
        attempts: List[AttemptData],
        reset_state: bool = False
    ) -> Dict[str, Any]:
        """
        Обработать историю попыток студента и обновить его характеристики
        
        Args:
            student_id: ID студента
            attempts: Список попыток студента
            reset_state: Сбросить состояние студента перед обработкой
            
        Returns:
            Dict: Обновленные характеристики студента
        """
        if not attempts:
            raise ValueError("Список попыток не может быть пустым")
        
        # Сбрасываем состояние если требуется
        if reset_state:
            self._reset_student_state(student_id)
        
        # Группируем попытки по навыкам
        attempts_by_skill = self._group_attempts_by_skill(attempts)
        
        # Обрабатываем попытки для каждого навыка
        skill_assessments = {}
        for skill_id, skill_attempts in attempts_by_skill.items():
            skill_assessment = self._process_skill_attempts(
                student_id, skill_id, skill_attempts
            )
            skill_assessments[skill_id] = skill_assessment
        
        # Вычисляем характеристики курсов
        course_assessments = self._calculate_course_assessments(
            student_id, attempts, skill_assessments
        )
        
        # Вычисляем общие характеристики студента
        student_characteristics = self._calculate_student_characteristics(
            student_id, attempts, skill_assessments, course_assessments
        )
        
        # Кэшируем результаты
        self._cache_assessment_results(student_id, {
            'skills': skill_assessments,
            'courses': course_assessments,
            'characteristics': student_characteristics,
            'last_updated': datetime.now()
        })
        
        return {
            'student_id': student_id,
            'skills': skill_assessments,
            'courses': course_assessments,
            'characteristics': student_characteristics,
            'processed_attempts': len(attempts),
            'assessment_timestamp': datetime.now()
        }
    
    def _group_attempts_by_skill(self, attempts: List[AttemptData]) -> Dict[int, List[AttemptData]]:
        """Группировать попытки по навыкам"""
        grouped = {}
        for attempt in attempts:
            if attempt.skill_id not in grouped:
                grouped[attempt.skill_id] = []
            grouped[attempt.skill_id].append(attempt)
        
        # Сортируем по времени
        for skill_id in grouped:
            grouped[skill_id].sort(key=lambda x: x.timestamp)
        
        return grouped
    
    def _process_skill_attempts(
        self, 
        student_id: int, 
        skill_id: int, 
        attempts: List[AttemptData]
    ) -> SkillAssessment:
        """Обработать попытки для конкретного навыка"""
        
        # Инициализируем студента для навыка если необходимо
        if (student_id not in self.bkt_model.student_states or 
            skill_id not in self.bkt_model.student_states[student_id]):
            self.bkt_model.initialize_student(student_id, skill_id)
        
        # Обрабатываем каждую попытку
        for attempt in attempts:
            task_chars = TaskCharacteristics(
                task_type=attempt.task_type,
                difficulty=attempt.difficulty
            )
            
            self.bkt_model.update_student_state(
                student_id, skill_id, attempt.answer_score, task_chars
            )
        
        # Получаем текущее освоение
        current_mastery = self.bkt_model.get_student_mastery(student_id, skill_id)
        
        # Вычисляем статистики
        correct_attempts = sum(1 for a in attempts if a.is_correct)
        accuracy = correct_attempts / len(attempts) if attempts else 0.0
        
        # Определяем уровень уверенности
        confidence_level = self._calculate_confidence_level(len(attempts), accuracy, current_mastery)
        
        # Получаем название навыка
        skill_name = self._get_skill_name(skill_id)
        
        return SkillAssessment(
            skill_id=skill_id,
            skill_name=skill_name,
            current_mastery=current_mastery,
            attempts_count=len(attempts),
            correct_attempts=correct_attempts,
            accuracy=accuracy,
            last_updated=attempts[-1].timestamp if attempts else datetime.now(),
            confidence_level=confidence_level
        )
    
    def _calculate_course_assessments(
        self, 
        student_id: int, 
        attempts: List[AttemptData],
        skill_assessments: Dict[int, SkillAssessment]
    ) -> Dict[int, CourseAssessment]:
        """Вычислить оценки освоения курсов"""
        course_assessments = {}
        
        # Группируем попытки по курсам
        courses_attempts = {}
        for attempt in attempts:
            if attempt.course_id:
                if attempt.course_id not in courses_attempts:
                    courses_attempts[attempt.course_id] = []
                courses_attempts[attempt.course_id].append(attempt)
        
        # Обрабатываем каждый курс
        for course_id, course_attempts in courses_attempts.items():
            course_assessment = self._calculate_single_course_assessment(
                course_id, course_attempts, skill_assessments
            )
            course_assessments[course_id] = course_assessment
        
        return course_assessments
    
    def _calculate_single_course_assessment(
        self, 
        course_id: int, 
        attempts: List[AttemptData],
        skill_assessments: Dict[int, SkillAssessment]
    ) -> CourseAssessment:
        """Вычислить оценку освоения одного курса"""
        
        # Получаем навыки курса
        course_skills = self._get_course_skills(course_id)
        
        # Вычисляем освоение навыков курса
        skills_mastery = {}
        total_mastery = 0.0
        completed_skills = 0
        
        for skill_id in course_skills:
            if skill_id in skill_assessments:
                mastery = skill_assessments[skill_id].current_mastery
                skills_mastery[skill_id] = mastery
                total_mastery += mastery
                if mastery >= 0.8:  # Порог для "освоенного" навыка
                    completed_skills += 1
            else:
                # Если нет данных, используем начальную оценку
                mastery = self.bkt_model.get_student_mastery(self._get_or_create_student_id(course_id), skill_id)
                skills_mastery[skill_id] = mastery
                total_mastery += mastery
        
        # Вычисляем общие метрики
        overall_mastery = total_mastery / len(course_skills) if course_skills else 0.0
        progress_percentage = (completed_skills / len(course_skills)) * 100 if course_skills else 0.0
        
        # Оцениваем тренд сложности
        difficulty_trend = self._calculate_difficulty_trend(attempts)
        
        # Оцениваем время до завершения
        estimated_completion = self._estimate_completion_time(
            overall_mastery, progress_percentage, attempts
        )
        
        # Получаем название курса
        course_name = self._get_course_name(course_id)
        
        return CourseAssessment(
            course_id=course_id,
            course_name=course_name,
            overall_mastery=overall_mastery,
            skills_mastery=skills_mastery,
            completed_skills=completed_skills,
            total_skills=len(course_skills),
            progress_percentage=progress_percentage,
            estimated_completion=estimated_completion,
            difficulty_trend=difficulty_trend
        )
    
    def _calculate_student_characteristics(
        self, 
        student_id: int, 
        attempts: List[AttemptData],
        skill_assessments: Dict[int, SkillAssessment],
        course_assessments: Dict[int, CourseAssessment]
    ) -> StudentCharacteristics:
        """Вычислить общие характеристики студента"""
        
        if not attempts:
            # Возвращаем базовые характеристики
            return StudentCharacteristics(
                student_id=student_id,
                overall_performance=0.0,
                learning_rate=0.5,
                consistency=0.5,
                strong_areas=[],
                weak_areas=[],
                recommended_difficulty='medium',
                study_time_estimate=5,
                last_assessment=datetime.now()
            )
        
        # Вычисляем общую производительность
        overall_performance = sum(
            assessment.accuracy for assessment in skill_assessments.values()
        ) / len(skill_assessments) if skill_assessments else 0.0
        
        # Вычисляем скорость обучения
        learning_rate = self._calculate_learning_rate(attempts, skill_assessments)
        
        # Вычисляем стабильность
        consistency = self._calculate_consistency(attempts)
        
        # Определяем сильные и слабые области
        strong_areas, weak_areas = self._identify_strength_weakness_areas(skill_assessments)
        
        # Рекомендуем уровень сложности
        recommended_difficulty = self._recommend_difficulty_level(
            overall_performance, learning_rate, consistency
        )
        
        # Оцениваем необходимое время обучения
        study_time_estimate = self._estimate_study_time(
            overall_performance, learning_rate, course_assessments
        )
        
        return StudentCharacteristics(
            student_id=student_id,
            overall_performance=overall_performance,
            learning_rate=learning_rate,
            consistency=consistency,
            strong_areas=strong_areas,
            weak_areas=weak_areas,
            recommended_difficulty=recommended_difficulty,
            study_time_estimate=study_time_estimate,
            last_assessment=datetime.now()
        )
    
    def get_student_assessment(self, student_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить кэшированную оценку студента
        
        Args:
            student_id: ID студента
            
        Returns:
            Dict: Кэшированная оценка или None
        """
        cache_key = f"student_assessment_{student_id}"
        return cache.get(cache_key)
    
    def update_single_attempt(
        self, 
        student_id: int, 
        attempt: AttemptData
    ) -> SkillAssessment:
        """
        Обновить оценку студента на основе одной новой попытки
        
        Args:
            student_id: ID студента
            attempt: Новая попытка
            
        Returns:
            SkillAssessment: Обновленная оценка навыка
        """
        return self._process_skill_attempts(student_id, attempt.skill_id, [attempt])
    
    def predict_skill_mastery(
        self, 
        student_id: int, 
        skill_id: int,
        future_attempts: int = 5
    ) -> List[float]:
        """
        Предсказать изменение освоения навыка при будущих попытках
        
        Args:
            student_id: ID студента
            skill_id: ID навыка
            future_attempts: Количество будущих попыток для прогноза
            
        Returns:
            List[float]: Прогнозируемые значения освоения
        """
        predictions = []
        current_mastery = self.bkt_model.get_student_mastery(student_id, skill_id)
        
        # Симулируем будущие попытки
        temp_model = pickle.loads(pickle.dumps(self.bkt_model))  # Deep copy
        
        for i in range(future_attempts):
            # Предполагаем вероятность правильного ответа = текущему освоению
            is_correct = current_mastery > 0.5
            answer_score = 1.0 if is_correct else 0.0
            
            task_chars = TaskCharacteristics("single_choice", "medium")
            temp_model.update_student_state(student_id, skill_id, answer_score, task_chars)
            
            new_mastery = temp_model.get_student_mastery(student_id, skill_id)
            predictions.append(new_mastery)
            current_mastery = new_mastery
        
        return predictions
    
    def get_learning_recommendations(
        self, 
        student_id: int
    ) -> Dict[str, Any]:
        """
        Получить рекомендации по обучению для студента
        
        Args:
            student_id: ID студента
            
        Returns:
            Dict: Рекомендации по обучению
        """
        assessment = self.get_student_assessment(student_id)
        if not assessment:
            return {"error": "Нет данных для студента"}
        
        characteristics = assessment['characteristics']
        skills = assessment['skills']
        courses = assessment['courses']
        
        # Рекомендации по навыкам
        skills_to_improve = [
            skill for skill in skills.values() 
            if skill.current_mastery < 0.6
        ]
        skills_to_improve.sort(key=lambda x: x.current_mastery)
        
        # Рекомендации по сложности
        if characteristics.overall_performance > 0.8:
            difficulty_rec = "Увеличьте сложность заданий"
        elif characteristics.overall_performance < 0.4:
            difficulty_rec = "Сосредоточьтесь на базовых навыках"
        else:
            difficulty_rec = "Продолжайте текущий уровень сложности"
        
        # Рекомендации по времени обучения
        if characteristics.learning_rate > 0.7:
            time_rec = f"Достаточно {characteristics.study_time_estimate} часов в неделю"
        else:
            time_rec = f"Рекомендуется увеличить время до {characteristics.study_time_estimate + 2} часов в неделю"
        
        return {
            'priority_skills': [skill.skill_name for skill in skills_to_improve[:3]],
            'difficulty_recommendation': difficulty_rec,
            'time_recommendation': time_rec,
            'strong_areas': characteristics.strong_areas,
            'areas_for_improvement': characteristics.weak_areas,
            'overall_progress': characteristics.overall_performance * 100,
            'learning_efficiency': characteristics.learning_rate * 100
        }
    
    # Вспомогательные методы
    def _reset_student_state(self, student_id: int):
        """Сбросить состояние студента"""
        if student_id in self.bkt_model.student_states:
            del self.bkt_model.student_states[student_id]
    
    def _calculate_confidence_level(self, attempts_count: int, accuracy: float, mastery: float) -> str:
        """Вычислить уровень уверенности в оценке"""
        if attempts_count < 3:
            return 'low'
        elif attempts_count >= 10 and accuracy > 0.7 and mastery > 0.8:
            return 'high'
        else:
            return 'medium'
    
    def _calculate_learning_rate(self, attempts: List[AttemptData], skill_assessments: Dict[int, SkillAssessment]) -> float:
        """Вычислить скорость обучения"""
        if len(attempts) < 5:
            return 0.5  # Средняя оценка
        
        # Анализируем улучшение точности со временем
        attempts_sorted = sorted(attempts, key=lambda x: x.timestamp)
        early_attempts = attempts_sorted[:len(attempts_sorted)//2]
        late_attempts = attempts_sorted[len(attempts_sorted)//2:]
        
        early_accuracy = sum(1 for a in early_attempts if a.is_correct) / len(early_attempts)
        late_accuracy = sum(1 for a in late_attempts if a.is_correct) / len(late_attempts)
        
        improvement = late_accuracy - early_accuracy
        return max(0.0, min(1.0, 0.5 + improvement))
    
    def _calculate_consistency(self, attempts: List[AttemptData]) -> float:
        """Вычислить стабильность результатов"""
        if len(attempts) < 3:
            return 0.5
        
        # Вычисляем стандартное отклонение результатов
        scores = [a.answer_score for a in attempts]
        mean_score = sum(scores) / len(scores)
        variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)
        std_dev = variance ** 0.5
        
        # Конвертируем в показатель консистентности (меньше отклонение = больше консистентность)
        consistency = max(0.0, 1.0 - std_dev)
        return consistency
    
    def _identify_strength_weakness_areas(self, skill_assessments: Dict[int, SkillAssessment]) -> Tuple[List[str], List[str]]:
        """Определить сильные и слабые области"""
        if not skill_assessments:
            return [], []
        
        # Группируем навыки по областям (это упрощенная логика)
        strong_areas = []
        weak_areas = []
        
        for skill_assessment in skill_assessments.values():
            if skill_assessment.current_mastery > 0.8:
                strong_areas.append(skill_assessment.skill_name)
            elif skill_assessment.current_mastery < 0.4:
                weak_areas.append(skill_assessment.skill_name)
        
        return strong_areas[:3], weak_areas[:3]  # Топ-3 в каждой категории
    
    def _recommend_difficulty_level(self, performance: float, learning_rate: float, consistency: float) -> str:
        """Рекомендовать уровень сложности"""
        avg_score = (performance + learning_rate + consistency) / 3
        
        if avg_score > 0.7:
            return 'hard'
        elif avg_score > 0.4:
            return 'medium'
        else:
            return 'easy'
    
    def _estimate_study_time(self, performance: float, learning_rate: float, course_assessments: Dict[int, CourseAssessment]) -> int:
        """Оценить необходимое время обучения"""
        base_time = 5  # Базовое время в часах
        
        if performance < 0.4:
            base_time += 3
        elif performance > 0.8:
            base_time -= 2
        
        if learning_rate < 0.3:
            base_time += 2
        elif learning_rate > 0.7:
            base_time -= 1
        
        return max(2, min(15, base_time))
    
    def _calculate_difficulty_trend(self, attempts: List[AttemptData]) -> str:
        """Вычислить тренд сложности"""
        if len(attempts) < 5:
            return 'stable'
        
        # Анализируем последние попытки
        recent_attempts = sorted(attempts, key=lambda x: x.timestamp)[-5:]
        recent_accuracy = sum(1 for a in recent_attempts if a.is_correct) / len(recent_attempts)
        
        # Сравниваем с предыдущими
        earlier_attempts = sorted(attempts, key=lambda x: x.timestamp)[:-5]
        if earlier_attempts:
            earlier_accuracy = sum(1 for a in earlier_attempts if a.is_correct) / len(earlier_attempts)
            
            if recent_accuracy > earlier_accuracy + 0.1:
                return 'improving'
            elif recent_accuracy < earlier_accuracy - 0.1:
                return 'declining'
        
        return 'stable'
    
    def _estimate_completion_time(self, mastery: float, progress: float, attempts: List[AttemptData]) -> Optional[datetime]:
        """Оценить время завершения курса"""
        if progress >= 95:
            return datetime.now()
        
        if not attempts or progress == 0:
            return None
        
        # Простая оценка на основе текущего прогресса
        remaining_progress = 100 - progress
        days_per_percent = len(attempts) / max(progress, 1)  # Дней на процент
        estimated_days = remaining_progress * days_per_percent
        
        return datetime.now() + timedelta(days=estimated_days)
    
    def _get_skill_name(self, skill_id: int) -> str:
        """Получить название навыка"""
        try:
            skill = Skill.objects.get(id=skill_id)
            return skill.name
        except Skill.DoesNotExist:
            return f"Навык {skill_id}"
    
    def _get_course_name(self, course_id: int) -> str:
        """Получить название курса"""
        try:
            course = Course.objects.get(id=course_id)
            return course.name
        except Course.DoesNotExist:
            return f"Курс {course_id}"
    
    def _get_course_skills(self, course_id: int) -> List[int]:
        """Получить навыки курса"""
        try:
            course = Course.objects.get(id=course_id)
            # Получаем навыки через задания курса
            task_skills = Task.objects.filter(courses=course).values_list('skills__id', flat=True)
            return list(set(filter(None, task_skills)))
        except Course.DoesNotExist:
            return []
    
    def _get_or_create_student_id(self, course_id: int) -> int:
        """Получить или создать ID студента для курса"""
        # Это заглушка - в реальной системе нужна другая логика
        return 1000  # Временный ID
    
    def _cache_assessment_results(self, student_id: int, results: Dict[str, Any]):
        """Кэшировать результаты оценки"""
        cache_key = f"student_assessment_{student_id}"
        cache.set(cache_key, results, timeout=3600)  # Кэш на 1 час


# Функция-утилита для создания данных попытки из Django моделей
def create_attempt_data_from_django(
    student_profile,
    task,
    is_correct: bool,
    answer_score: float,
    timestamp: datetime,
    attempt_number: int = 1
) -> AttemptData:
    """
    Создать AttemptData из Django моделей
    
    Args:
        student_profile: Объект StudentProfile
        task: Объект Task
        is_correct: Правильность ответа
        answer_score: Оценка ответа (0.0-1.0)
        timestamp: Время попытки
        attempt_number: Номер попытки
        
    Returns:
        AttemptData: Объект данных попытки    """
    # Получаем первый навык задания (упрощенная логика)
    skills = task.skills.all()
    skill_id = skills[0].id if skills else None
    
    if not skill_id:
        raise ValueError(f"Задание {task.id} не связано с навыками")
    
    return AttemptData(
        student_id=student_profile.id,
        task_id=task.id,
        skill_id=skill_id,
        course_id=task.courses.first().id if task.courses.exists() else None,
        is_correct=is_correct,
        answer_score=answer_score,
        task_type=task.task_type,
        difficulty=task.difficulty,
        timestamp=timestamp,
        attempt_number=attempt_number
    )
