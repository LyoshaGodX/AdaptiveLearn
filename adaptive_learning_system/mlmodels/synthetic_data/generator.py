"""
Генератор синтетического датасета истории прохождения заданий.
Использует стратегии студентов для создания реалистичных данных обучения.
"""

from typing import List, Dict, Any, Optional, Tuple
import random
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import pandas as pd
from pathlib import Path

from mlmodels.student_strategies.strategies import (
    StudentStrategy, 
    StudentStrategyFactory,
    StudentCharacteristics
)
from mlmodels.data_interfaces.database_interface import (
    CourseDataInterface,
    SkillDataInterface,
    TaskDataInterface,
    StudentDataInterface
)
from mlmodels.data_interfaces.skills_graph import SkillsGraphInterface


@dataclass
class SyntheticStudent:
    """Синтетический студент для генерации данных"""
    student_id: int
    strategy: StudentStrategy
    course_ids: List[str]
    start_date: datetime
    
    # Текущее состояние
    skill_masteries: Dict[int, float]  # skill_id -> mastery_probability
    completed_tasks: List[int]         # task_ids
    session_count: int
    total_time_spent: float


@dataclass
class SyntheticAttempt:
    """Синтетическая попытка решения задания"""
    student_id: int
    task_id: int
    skill_id: int
    
    # Результат
    is_correct: bool
    time_spent: float  # в минутах
    attempt_datetime: datetime
    
    # Контекст
    mastery_before: float
    mastery_after: float
    bkt_parameters: Dict[str, float]
    
    # Метаданные
    session_id: int
    attempt_number_in_session: int
    difficulty: str
    task_type: str


class SyntheticDataGenerator:
    """Генератор синтетических данных обучения"""
    
    def __init__(self, course_ids: Optional[List[str]] = None):
        self.course_ids = course_ids or []
        self.skills_graph = SkillsGraphInterface()
        
        # Кэш данных
        self._courses_data = {}
        self._skills_data = {}
        self._tasks_data = {}
        
        self._load_course_data()
    
    def _load_course_data(self):
        """Загрузить данные курсов, навыков и заданий"""
        print("Загрузка данных курсов...")
        
        if not self.course_ids:
            # Если курсы не указаны, берем все доступные
            courses = CourseDataInterface.get_all_courses()
            self.course_ids = [course.id for course in courses]
        
        for course_id in self.course_ids:
            # Данные курса
            course_stats = CourseDataInterface.get_course_statistics(course_id)
            self._courses_data[course_id] = course_stats
            
            # Данные навыков курса
            skills = CourseDataInterface.get_course_skills(course_id)
            for skill in skills:
                if skill.id not in self._skills_data:
                    self._skills_data[skill.id] = {
                        'id': skill.id,
                        'name': skill.name,
                        'is_base': skill.is_base,
                        'courses': [course_id],
                        'prerequisites': [p.id for p in skill.prerequisites.all()],
                        'difficulty_estimate': self._estimate_skill_difficulty(skill)
                    }
                else:
                    self._skills_data[skill.id]['courses'].append(course_id)
            
            # Данные заданий курса
            tasks = CourseDataInterface.get_course_tasks(course_id)
            for task in tasks:
                if task.id not in self._tasks_data:
                    self._tasks_data[task.id] = {
                        'id': task.id,
                        'title': task.title,
                        'difficulty': task.difficulty,
                        'task_type': task.task_type,
                        'skills': [skill.id for skill in task.skills.all()],
                        'estimated_time': self._estimate_task_time(task)
                    }
        
        # Строим граф навыков
        if self.course_ids:
            # Граф для конкретных курсов
            for course_id in self.course_ids:
                self.skills_graph.build_graph_from_database(course_id)
                break  # Используем первый курс как базу
        else:
            self.skills_graph.build_graph_from_database()
        
        print(f"Загружено: {len(self._courses_data)} курсов, {len(self._skills_data)} навыков, {len(self._tasks_data)} заданий")
    
    def _estimate_skill_difficulty(self, skill) -> str:
        """Оценить сложность навыка на основе его позиции в графе"""
        # Простая эвристика: чем больше пререквизитов, тем сложнее
        prereqs_count = skill.prerequisites.count()
        
        if prereqs_count == 0:
            return 'beginner'
        elif prereqs_count <= 2:
            return 'intermediate'
        else:
            return 'advanced'
    
    def _estimate_task_time(self, task) -> float:
        """Оценить базовое время выполнения задания (в минутах)"""
        base_times = {
            'true_false': 2.0,
            'single': 3.0,
            'multiple': 5.0
        }
        
        difficulty_multipliers = {
            'beginner': 1.0,
            'intermediate': 1.5,
            'advanced': 2.5
        }
        
        base_time = base_times.get(task.task_type, 3.0)
        multiplier = difficulty_multipliers.get(task.difficulty, 1.0)
        
        return base_time * multiplier
    
    def generate_synthetic_students(
        self,
        num_students: int,
        strategy_distribution: Optional[Dict[str, float]] = None
    ) -> List[SyntheticStudent]:
        """Сгенерировать синтетических студентов"""
        
        strategies = StudentStrategyFactory.create_mixed_population(
            num_students, 
            strategy_distribution
        )
        
        students = []
        base_date = datetime(2024, 1, 1)
        
        for i, strategy in enumerate(strategies):
            # Случайная дата начала обучения
            days_offset = random.randint(0, 90)
            start_date = base_date + timedelta(days=days_offset)
            
            # Случайный выбор курсов (1-3 курса)
            num_courses = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
            student_courses = random.sample(self.course_ids, min(num_courses, len(self.course_ids)))
            
            # Инициализация навыков
            skill_masteries = {}
            for course_id in student_courses:
                course_skills = [s['id'] for s in self._courses_data[course_id]['skills']]
                for skill_id in course_skills:
                    if skill_id not in skill_masteries:
                        skill_difficulty = self._skills_data[skill_id]['difficulty_estimate']
                        initial_mastery = strategy.get_initial_mastery_prob(skill_difficulty)
                        # Добавляем небольшой шум
                        noise = random.gauss(0, 0.05)
                        skill_masteries[skill_id] = max(0.0, min(1.0, initial_mastery + noise))
            
            student = SyntheticStudent(
                student_id=i + 1,
                strategy=strategy,
                course_ids=student_courses,
                start_date=start_date,
                skill_masteries=skill_masteries,
                completed_tasks=[],
                session_count=0,
                total_time_spent=0.0
            )
            
            students.append(student)
        
        return students
    
    def simulate_learning_session(
        self,
        student: SyntheticStudent,
        session_duration_minutes: float = 60.0,
        max_tasks_per_session: int = 10
    ) -> List[SyntheticAttempt]:
        """Симуляция учебной сессии студента"""
        
        attempts = []
        student.session_count += 1
        student.strategy.reset_session()
        
        session_start = student.start_date + timedelta(days=student.session_count)
        current_time = session_start
        time_spent_in_session = 0.0
        tasks_in_session = 0
        
        while (time_spent_in_session < session_duration_minutes and 
               tasks_in_session < max_tasks_per_session):
            
            # Выбираем подходящее задание
            task_id = self._select_task_for_student(student)
            if not task_id:
                break  # Нет подходящих заданий
            
            task_data = self._tasks_data[task_id]
            
            # Выбираем навык для этого задания
            available_skills = [s for s in task_data['skills'] if s in student.skill_masteries]
            if not available_skills:
                continue
            
            skill_id = random.choice(available_skills)
            current_mastery = student.skill_masteries[skill_id]
            skill_difficulty = self._skills_data[skill_id]['difficulty_estimate']
            
            # Проверяем, хочет ли студент делать это задание (учитываем тип задания)
            if not student.strategy.should_attempt_task_with_type(
                task_data['difficulty'], current_mastery, task_data['task_type']
            ):
                continue
            
            # Получаем BKT параметры
            bkt_params = student.strategy.get_bkt_parameters(
                skill_difficulty, 
                len([a for a in attempts if a.skill_id == skill_id]) + 1
            )
              # Симулируем результат попытки
            is_correct = self._simulate_task_result(
                current_mastery, 
                bkt_params, 
                task_data['task_type'], 
                task_data['difficulty']
            )
            
            # Вычисляем время выполнения
            base_time = task_data['estimated_time']
            time_multiplier = student.strategy.get_time_multiplier(task_data['difficulty'])
            time_spent = base_time * time_multiplier * random.uniform(0.7, 1.3)
            
            # Обновляем освоение навыка
            new_mastery = self._update_mastery_bkt(current_mastery, is_correct, bkt_params)
            student.skill_masteries[skill_id] = new_mastery
            
            # Создаем запись о попытке
            attempt = SyntheticAttempt(
                student_id=student.student_id,
                task_id=task_id,
                skill_id=skill_id,
                is_correct=is_correct,
                time_spent=time_spent,
                attempt_datetime=current_time,
                mastery_before=current_mastery,
                mastery_after=new_mastery,
                bkt_parameters=bkt_params,
                session_id=student.session_count,
                attempt_number_in_session=tasks_in_session + 1,
                difficulty=task_data['difficulty'],
                task_type=task_data['task_type']
            )
            
            attempts.append(attempt)
            
            # Обновляем состояние студента
            student.strategy.update_session_state(is_correct, time_spent)
            if is_correct:
                student.completed_tasks.append(task_id)
            
            # Обновляем время
            current_time += timedelta(minutes=time_spent)
            time_spent_in_session += time_spent
            tasks_in_session += 1
            student.total_time_spent += time_spent
        
        return attempts
    
    def _select_task_for_student(self, student: SyntheticStudent) -> Optional[int]:
        """Выбрать подходящее задание для студента"""
        
        # Получаем все задания из курсов студента
        available_tasks = []
        for course_id in student.course_ids:
            course_skills = [s['id'] for s in self._courses_data[course_id]['skills']]
            for task_id, task_data in self._tasks_data.items():
                # Проверяем, что задание связано с навыками курса
                if any(skill_id in course_skills for skill_id in task_data['skills']):
                    # Исключаем уже выполненные задания
                    if task_id not in student.completed_tasks:
                        available_tasks.append(task_id)
        
        if not available_tasks:
            return None
        
        # Простая стратегия выбора: случайный выбор с весами по релевантности
        task_weights = []
        for task_id in available_tasks:
            task_data = self._tasks_data[task_id]
            
            # Вычисляем релевантность на основе освоения связанных навыков
            relevance = 0
            for skill_id in task_data['skills']:
                if skill_id in student.skill_masteries:
                    mastery = student.skill_masteries[skill_id]
                    # Задания наиболее релевантны при среднем уровне освоения
                    if 0.2 <= mastery <= 0.8:
                        relevance += 1 - abs(mastery - 0.5) * 2
                    elif mastery < 0.2:
                        relevance += 0.3  # Базовые задания
            
            task_weights.append(max(0.1, relevance))
          # Выбираем задание с учетом весов
        selected_task = random.choices(available_tasks, weights=task_weights)[0]
        return selected_task
    
    def _simulate_task_result(
        self, 
        mastery_prob: float, 
        bkt_params: Dict[str, float], 
        task_type: str = 'single',
        difficulty: str = 'intermediate'
    ) -> bool:
        """Симулировать результат выполнения задания на основе BKT с учётом типа задания"""
        
        P_T = bkt_params['P_T']
        P_G = bkt_params['P_G']
        P_S = bkt_params['P_S']
        
        # Адаптируем вероятности для типа задания
        task_adjustments = {
            'true_false': {'P_G': 0.5, 'P_S_mult': 0.8},      # 50% угадать, меньше ошибок
            'single': {'P_G': 0.25, 'P_S_mult': 1.0},         # 25% угадать, стандартные ошибки
            'multiple': {'P_G': 0.1, 'P_S_mult': 1.3}         # 10% угадать, больше ошибок
        }
        
        # Корректировки для уровня сложности
        difficulty_adjustments = {
            'beginner': {'P_S_mult': 0.8, 'P_T_mult': 1.2},    # Легче, меньше ошибок
            'intermediate': {'P_S_mult': 1.0, 'P_T_mult': 1.0}, # Базовый уровень
            'advanced': {'P_S_mult': 1.4, 'P_T_mult': 0.8}     # Сложнее, больше ошибок
        }
        
        # Применяем корректировки
        task_adj = task_adjustments.get(task_type, task_adjustments['single'])
        diff_adj = difficulty_adjustments.get(difficulty, difficulty_adjustments['intermediate'])
        
        adapted_P_G = task_adj['P_G']
        adapted_P_S = min(0.9, P_S * task_adj['P_S_mult'] * diff_adj['P_S_mult'])
        
        # Вероятность правильного ответа согласно BKT
        p_correct = adapted_P_G * (1 - mastery_prob) + (1 - adapted_P_S) * mastery_prob
        
        return random.random() < p_correct
    
    def _update_mastery_bkt(
        self, 
        current_mastery: float, 
        is_correct: bool, 
        bkt_params: Dict[str, float]
    ) -> float:
        """Обновить освоение навыка согласно формулам BKT"""
        
        P_T = bkt_params['P_T']
        P_G = bkt_params['P_G']
        P_S = bkt_params['P_S']
        
        # Обновляем вероятность по Байесу
        if is_correct:
            numerator = current_mastery * (1 - P_S)
            denominator = (current_mastery * (1 - P_S) + 
                          (1 - current_mastery) * P_G)
        else:
            numerator = current_mastery * P_S
            denominator = (current_mastery * P_S + 
                          (1 - current_mastery) * (1 - P_G))
        
        if denominator > 0:
            updated_mastery = numerator / denominator
        else:
            updated_mastery = current_mastery
        
        # Применяем вероятность изучения
        new_mastery = updated_mastery + (1 - updated_mastery) * P_T
        
        return max(0.0, min(1.0, new_mastery))
    
    def generate_dataset(
        self,
        num_students: int,
        sessions_per_student: Tuple[int, int] = (10, 30),
        strategy_distribution: Optional[Dict[str, float]] = None,
        output_format: str = 'pandas'
    ) -> Any:
        """
        Генерировать полный синтетический датасет
        
        Args:
            num_students: количество студентов
            sessions_per_student: диапазон количества сессий на студента (min, max)
            strategy_distribution: распределение стратегий студентов
            output_format: формат вывода ('pandas', 'dict', 'json')
        """
        
        print(f"Генерация датасета для {num_students} студентов...")
        
        # Создаем студентов
        students = self.generate_synthetic_students(num_students, strategy_distribution)
        
        all_attempts = []
        
        for i, student in enumerate(students):
            if i % 10 == 0:
                print(f"Обработка студента {i + 1}/{num_students}")
            
            # Случайное количество сессий для каждого студента
            num_sessions = random.randint(*sessions_per_student)
            
            for session in range(num_sessions):
                # Случайная продолжительность сессии
                session_duration = random.uniform(20, 120)  # от 20 до 120 минут
                
                session_attempts = self.simulate_learning_session(
                    student, 
                    session_duration_minutes=session_duration
                )
                
                all_attempts.extend(session_attempts)
        
        print(f"Сгенерировано {len(all_attempts)} попыток решения заданий")
        
        # Форматируем вывод
        if output_format == 'pandas':
            return self._to_pandas_dataframe(all_attempts, students)
        elif output_format == 'dict':
            return self._to_dict(all_attempts, students)
        elif output_format == 'json':
            return self._to_json(all_attempts, students)
        else:
            raise ValueError(f"Неподдерживаемый формат: {output_format}")
    
    def _to_pandas_dataframe(self, attempts: List[SyntheticAttempt], students: List[SyntheticStudent]) -> pd.DataFrame:
        """Конвертировать в pandas DataFrame"""
        
        data = []
        for attempt in attempts:
            data.append({
                'student_id': attempt.student_id,
                'task_id': attempt.task_id,
                'skill_id': attempt.skill_id,
                'is_correct': attempt.is_correct,
                'time_spent_minutes': attempt.time_spent,
                'attempt_datetime': attempt.attempt_datetime,
                'mastery_before': attempt.mastery_before,
                'mastery_after': attempt.mastery_after,
                'session_id': attempt.session_id,
                'attempt_number_in_session': attempt.attempt_number_in_session,
                'difficulty': attempt.difficulty,
                'task_type': attempt.task_type,
                'bkt_P_T': attempt.bkt_parameters['P_T'],
                'bkt_P_G': attempt.bkt_parameters['P_G'],
                'bkt_P_S': attempt.bkt_parameters['P_S'],
                'student_strategy': attempt.student_id  # Будет заменено на название стратегии
            })
        
        df = pd.DataFrame(data)
        
        # Добавляем информацию о стратегиях студентов
        strategy_mapping = {s.student_id: s.strategy.get_strategy_name() for s in students}
        df['student_strategy'] = df['student_id'].map(strategy_mapping)
        
        return df
    
    def _to_dict(self, attempts: List[SyntheticAttempt], students: List[SyntheticStudent]) -> Dict[str, Any]:
        """Конвертировать в словарь"""
        
        attempts_data = []
        for attempt in attempts:
            attempts_data.append({
                'student_id': attempt.student_id,
                'task_id': attempt.task_id,
                'skill_id': attempt.skill_id,
                'is_correct': attempt.is_correct,
                'time_spent_minutes': attempt.time_spent,
                'attempt_datetime': attempt.attempt_datetime.isoformat(),
                'mastery_before': attempt.mastery_before,
                'mastery_after': attempt.mastery_after,
                'session_id': attempt.session_id,
                'attempt_number_in_session': attempt.attempt_number_in_session,
                'difficulty': attempt.difficulty,
                'task_type': attempt.task_type,
                'bkt_parameters': attempt.bkt_parameters
            })
        
        students_data = []
        for student in students:
            students_data.append({
                'student_id': student.student_id,
                'strategy_name': student.strategy.get_strategy_name(),
                'course_ids': student.course_ids,
                'start_date': student.start_date.isoformat(),
                'session_count': student.session_count,
                'total_time_spent': student.total_time_spent,
                'final_skill_masteries': student.skill_masteries
            })
        
        return {
            'attempts': attempts_data,
            'students': students_data,
            'metadata': {
                'total_attempts': len(attempts_data),
                'total_students': len(students_data),
                'courses': list(self._courses_data.keys()),
                'skills': list(self._skills_data.keys()),
                'tasks': list(self._tasks_data.keys())
            }
        }
    
    def _to_json(self, attempts: List[SyntheticAttempt], students: List[SyntheticStudent]) -> str:
        """Конвертировать в JSON"""
        data_dict = self._to_dict(attempts, students)
        return json.dumps(data_dict, ensure_ascii=False, indent=2, default=str)
    
    def save_dataset(
        self, 
        attempts: List[SyntheticAttempt], 
        students: List[SyntheticStudent],
        filepath: str,
        format_type: str = 'csv'    ):
        """Сохранить датасет в файл"""
        
        file_path = Path(filepath)
        
        if format_type == 'csv':
            df = self._to_pandas_dataframe(attempts, students)
            df.to_csv(file_path, index=False)
        
        elif format_type == 'json':
            json_data = self._to_json(attempts, students)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_data)
        
        elif format_type == 'parquet':
            df = self._to_pandas_dataframe(attempts, students)
            df.to_parquet(file_path, index=False)
        
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {format_type}")
        
        print(f"Датасет сохранен в {file_path}")
    
    def get_dataset_statistics(self, attempts: List[SyntheticAttempt], students: List[SyntheticStudent]) -> Dict[str, Any]:
        """Получить статистику сгенерированного датасета"""
        
        df = self._to_pandas_dataframe(attempts, students)
        
        stats = {
            'basic_stats': {
                'total_attempts': len(attempts),
                'total_students': len(students),
                'unique_tasks': df['task_id'].nunique(),
                'unique_skills': df['skill_id'].nunique(),
                'date_range': {
                    'start': df['attempt_datetime'].min(),
                    'end': df['attempt_datetime'].max()
                }
            },
            'success_rates': {
                'overall': df['is_correct'].mean(),
                'by_difficulty': df.groupby('difficulty')['is_correct'].mean().to_dict(),
                'by_strategy': df.groupby('student_strategy')['is_correct'].mean().to_dict()
            },
            'time_stats': {
                'avg_time_per_attempt': df['time_spent_minutes'].mean(),
                'by_difficulty': df.groupby('difficulty')['time_spent_minutes'].mean().to_dict(),
                'by_task_type': df.groupby('task_type')['time_spent_minutes'].mean().to_dict()
            },
            'mastery_progression': {
                'avg_mastery_gain': (df['mastery_after'] - df['mastery_before']).mean(),
                'by_strategy': df.groupby('student_strategy').apply(
                    lambda x: (x['mastery_after'] - x['mastery_before']).mean()
                ).to_dict()
            },
            'student_activity': {
                'avg_attempts_per_student': len(attempts) / len(students),
                'avg_sessions_per_student': df.groupby('student_id')['session_id'].max().mean()
            }
        }
        
        return stats
