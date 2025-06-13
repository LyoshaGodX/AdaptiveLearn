"""
Базовая реализация модели Bayesian Knowledge Tracing (BKT).
Простая и надежная реализация с поддержкой графа навыков.
"""

from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from dataclasses import dataclass
from abc import ABC, abstractmethod
import json
import pickle
from pathlib import Path


@dataclass
class BKTParameters:
    """Параметры BKT модели для навыка"""
    P_L0: float  # Начальная вероятность знания навыка
    P_T: float   # Вероятность изучения навыка за одну попытку
    P_G: float   # Вероятность угадывания при незнании
    P_S: float   # Вероятность ошибки при знании
    
    def __post_init__(self):
        """Валидация параметров"""
        for param_name, value in [('P_L0', self.P_L0), ('P_T', self.P_T), 
                                 ('P_G', self.P_G), ('P_S', self.P_S)]:
            if not (0 <= value <= 1):
                raise ValueError(f"{param_name} должен быть в диапазоне [0, 1], получен {value}")
    
    def to_dict(self) -> Dict[str, float]:
        """Конвертировать в словарь"""
        return {
            'P_L0': self.P_L0,
            'P_T': self.P_T,
            'P_G': self.P_G,
            'P_S': self.P_S
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'BKTParameters':
        """Создать из словаря"""
        return cls(
            P_L0=data['P_L0'],
            P_T=data['P_T'],
            P_G=data['P_G'],
            P_S=data['P_S']
        )


@dataclass
class StudentSkillState:
    """Состояние освоения навыка студентом"""
    skill_id: int
    current_mastery: float  # Текущая вероятность освоения P(L_t)
    attempts_count: int
    correct_attempts: int
    last_updated: Optional[str] = None
    
    @property
    def accuracy(self) -> float:
        """Точность ответов"""
        if self.attempts_count == 0:
            return 0.0
        return self.correct_attempts / self.attempts_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертировать в словарь"""
        return {
            'skill_id': self.skill_id,
            'current_mastery': self.current_mastery,
            'attempts_count': self.attempts_count,
            'correct_attempts': self.correct_attempts,
            'accuracy': self.accuracy,
            'last_updated': self.last_updated
        }


@dataclass
class TaskCharacteristics:
    """Характеристики задания для адаптации BKT параметров"""
    task_type: str  # 'true_false', 'single', 'multiple'
    difficulty: str  # 'beginner', 'intermediate', 'advanced'
    
    def get_difficulty_multiplier(self) -> float:
        """Получить множитель сложности для адаптации параметров BKT"""
        multipliers = {
            'beginner': 1.2,     # Легче изучать, меньше ошибок
            'intermediate': 1.0,  # Базовая сложность
            'advanced': 0.8      # Сложнее изучать, больше ошибок
        }
        return multipliers.get(self.difficulty, 1.0)
    
    def get_guess_probability(self) -> float:
        """Получить базовую вероятность угадывания для типа задания"""
        base_guess = {
            'true_false': 0.5,    # 50% шанс угадать (2 варианта)
            'single': 0.25,       # 25% шанс угадать (обычно 4 варианта)
            'multiple': 0.1       # 10% шанс угадать (множественный выбор сложнее)
        }
        return base_guess.get(self.task_type, 0.25)
    
    def get_slip_adjustment(self) -> float:
        """Получить корректировку вероятности ошибки для типа задания"""
        slip_adjustments = {
            'true_false': 0.8,    # Меньше ошибок (простой формат)
            'single': 1.0,        # Базовый уровень ошибок
            'multiple': 1.3       # Больше ошибок (сложный формат)
        }
        return slip_adjustments.get(self.task_type, 1.0)


class BKTModel:
    """Базовая модель Bayesian Knowledge Tracing"""
    
    def __init__(self):
        # Параметры модели для каждого навыка
        self.skill_parameters: Dict[int, BKTParameters] = {}
        
        # Состояния студентов по навыкам
        self.student_states: Dict[int, Dict[int, StudentSkillState]] = {}
        
        # Граф зависимостей навыков (опционально)
        self.skills_graph: Optional[Dict[int, List[int]]] = None
        
        # Метаданные модели
        self.is_trained = False
        self.training_data_size = 0
    
    def set_skill_parameters(self, skill_id: int, parameters: BKTParameters):
        """Установить параметры для навыка"""
        self.skill_parameters[skill_id] = parameters
    
    def get_skill_parameters(self, skill_id: int) -> Optional[BKTParameters]:
        """Получить параметры навыка"""
        return self.skill_parameters.get(skill_id)
    
    def set_skills_graph(self, graph: Dict[int, List[int]]):
        """
        Установить граф зависимостей навыков
        graph: {skill_id: [prerequisite_skill_ids]}
        """
        self.skills_graph = graph
    
    def initialize_student(self, student_id: int, skill_id: int) -> StudentSkillState:
        """Инициализировать состояние студента для навыка"""
        if student_id not in self.student_states:
            self.student_states[student_id] = {}
        
        # Получаем начальную вероятность
        params = self.get_skill_parameters(skill_id)
        if params:
            initial_mastery = params.P_L0
        else:
            # Используем значения по умолчанию
            initial_mastery = 0.1
        
        # Учитываем граф навыков (если доступен)
        if self.skills_graph and skill_id in self.skills_graph:
            initial_mastery = self._adjust_initial_mastery_by_prerequisites(
                student_id, skill_id, initial_mastery
            )
        
        state = StudentSkillState(
            skill_id=skill_id,
            current_mastery=initial_mastery,
            attempts_count=0,
            correct_attempts=0
        )
        
        self.student_states[student_id][skill_id] = state
        return state
    
    def _adjust_initial_mastery_by_prerequisites(
        self, 
        student_id: int, 
        skill_id: int, 
        base_mastery: float
    ) -> float:
        """Скорректировать начальную вероятность на основе пререквизитов"""
        if not self.skills_graph or skill_id not in self.skills_graph:
            return base_mastery
        
        prerequisite_ids = self.skills_graph[skill_id]
        if not prerequisite_ids:
            return base_mastery
        
        # Получаем освоение пререквизитов
        prereq_masteries = []
        for prereq_id in prerequisite_ids:
            if (student_id in self.student_states and 
                prereq_id in self.student_states[student_id]):
                prereq_masteries.append(
                    self.student_states[student_id][prereq_id].current_mastery
                )
        
        if not prereq_masteries:
            return base_mastery
          # Простая эвристика: среднее освоение пререквизатов влияет на начальное освоение
        avg_prereq_mastery = np.mean(prereq_masteries)
        
        # Корректируем базовую вероятность
        adjustment = (avg_prereq_mastery - 0.5) * 0.3  # Влияние до 30%
        adjusted_mastery = base_mastery + adjustment
        
        return max(0.0, min(1.0, float(adjusted_mastery)))
    
    def update_student_state(
        self, 
        student_id: int, 
        skill_id: int, 
        is_correct: bool,
        task_characteristics: Optional[TaskCharacteristics] = None
    ) -> StudentSkillState:
        """Обновить состояние студента после попытки"""
        
        # Инициализируем состояние если нужно
        if (student_id not in self.student_states or 
            skill_id not in self.student_states[student_id]):
            self.initialize_student(student_id, skill_id)
        
        state = self.student_states[student_id][skill_id]
        params = self.get_skill_parameters(skill_id)
        
        if not params:
            # Используем параметры по умолчанию
            params = BKTParameters(P_L0=0.1, P_T=0.3, P_G=0.2, P_S=0.1)
        
        # Адаптируем параметры с учетом характеристик задания
        if task_characteristics:
            adjusted_params = self._adjust_parameters_for_task(params, task_characteristics)
        else:
            adjusted_params = params
        
        # Обновляем статистику
        state.attempts_count += 1
        if is_correct:
            state.correct_attempts += 1
        
        # Обновляем вероятность освоения по формулам BKT
        current_mastery = state.current_mastery
        
        # Формула обновления по Байесу
        if is_correct:
            # P(L_t | correct) = P(L_{t-1}) * (1 - P_S) / [P(L_{t-1}) * (1 - P_S) + (1 - P(L_{t-1})) * P_G]
            numerator = current_mastery * (1 - adjusted_params.P_S)
            denominator = (current_mastery * (1 - adjusted_params.P_S) + 
                          (1 - current_mastery) * adjusted_params.P_G)
        else:
            # P(L_t | incorrect) = P(L_{t-1}) * P_S / [P(L_{t-1}) * P_S + (1 - P(L_{t-1})) * (1 - P_G)]
            numerator = current_mastery * adjusted_params.P_S
            denominator = (current_mastery * adjusted_params.P_S + 
                          (1 - current_mastery) * (1 - adjusted_params.P_G))
        
        if denominator > 0:
            updated_mastery = numerator / denominator
        else:
            updated_mastery = current_mastery
        
        # Применяем вероятность изучения
        # P(L_t) = P(L_t | evidence) + (1 - P(L_t | evidence)) * P_T
        new_mastery = updated_mastery + (1 - updated_mastery) * adjusted_params.P_T
          # Ограничиваем значения
        state.current_mastery = max(0.0, min(1.0, new_mastery))
        
        return state
    
    def predict_performance(
        self, 
        student_id: int, 
        skill_id: int,
        task_characteristics: Optional[TaskCharacteristics] = None
    ) -> float:
        """Предсказать вероятность правильного ответа"""
        
        # Получаем текущее состояние
        if (student_id not in self.student_states or 
            skill_id not in self.student_states[student_id]):
            self.initialize_student(student_id, skill_id)
        
        state = self.student_states[student_id][skill_id]
        params = self.get_skill_parameters(skill_id)
        
        if not params:
            params = BKTParameters(P_L0=0.1, P_T=0.3, P_G=0.2, P_S=0.1)
        
        # Адаптируем параметры с учетом характеристик задания
        if task_characteristics:
            adjusted_params = self._adjust_parameters_for_task(params, task_characteristics)
        else:
            adjusted_params = params
        
        # P(correct) = P(G) * (1 - P(L_t)) + (1 - P(S)) * P(L_t)
        p_correct = (adjusted_params.P_G * (1 - state.current_mastery) + 
                    (1 - adjusted_params.P_S) * state.current_mastery)
        
        return p_correct
    
    def _adjust_parameters_for_task(
        self, 
        params: BKTParameters, 
        task_characteristics: TaskCharacteristics
    ) -> BKTParameters:
        """Адаптировать параметры BKT под конкретное задание"""
        
        # Получаем базовую вероятность угадывания для типа задания
        base_guess = task_characteristics.get_guess_probability()
        
        # Получаем множитель сложности
        difficulty_multiplier = task_characteristics.get_difficulty_multiplier()
        
        # Получаем корректировку для вероятности ошибки
        slip_adjustment = task_characteristics.get_slip_adjustment()
        
        # Адаптируем параметры
        adjusted_p_t = min(1.0, params.P_T * difficulty_multiplier)
        adjusted_p_g = base_guess  # Используем базовую вероятность угадывания для типа задания
        adjusted_p_s = min(1.0, params.P_S * slip_adjustment)
        
        # Создаем новый объект параметров
        return BKTParameters(
            P_L0=params.P_L0,  # P_L0 не меняется
            P_T=adjusted_p_t,
            P_G=adjusted_p_g,
            P_S=adjusted_p_s
        )
    
    def get_student_mastery(self, student_id: int, skill_id: int) -> float:
        """Получить текущую вероятность освоения навыка студентом"""
        if (student_id not in self.student_states or 
            skill_id not in self.student_states[student_id]):
            return 0.0
        
        return self.student_states[student_id][skill_id].current_mastery
    
    def get_student_profile(self, student_id: int) -> Dict[int, StudentSkillState]:
        """Получить полный профиль студента по всем навыкам"""
        if student_id not in self.student_states:
            return {}
        
        return {skill_id: state for skill_id, state in self.student_states[student_id].items()}
    
    def get_skill_difficulty_ranking(self) -> List[Tuple[int, float]]:
        """
        Получить ранжирование навыков по сложности
        Возвращает список (skill_id, difficulty_score)
        """
        difficulty_scores = []
        
        for skill_id, params in self.skill_parameters.items():
            # Простая метрика сложности: низкие P_L0 и P_T, высокие P_S
            difficulty = (1 - params.P_L0) * 0.4 + (1 - params.P_T) * 0.4 + params.P_S * 0.2
            difficulty_scores.append((skill_id, difficulty))
        
        # Сортируем по убыванию сложности
        difficulty_scores.sort(key=lambda x: x[1], reverse=True)
        return difficulty_scores
    
    def recommend_skills_for_student(
        self, 
        student_id: int, 
        max_recommendations: int = 5
    ) -> List[Tuple[int, float, str]]:
        """
        Рекомендовать навыки для изучения студентом
        Возвращает список (skill_id, current_mastery, recommendation_reason)
        """
        if student_id not in self.student_states:
            return []
        
        student_profile = self.student_states[student_id]
        recommendations = []
        
        for skill_id, state in student_profile.items():
            mastery = state.current_mastery
            
            # Рекомендуем навыки с частичным освоением (0.2 - 0.8)
            if 0.2 <= mastery <= 0.8:
                if mastery < 0.5:
                    reason = "Навык требует дополнительной практики"
                    priority = 1.0 - mastery  # Чем ниже освоение, тем выше приоритет
                else:
                    reason = "Навык близок к освоению"
                    priority = mastery  # Чем ближе к освоению, тем выше приоритет
                
                recommendations.append((skill_id, mastery, reason, priority))
        
        # Также рекомендуем неосвоенные навыки, если освоены пререквизиты
        if self.skills_graph:
            for skill_id in self.skill_parameters:
                if skill_id not in student_profile:
                    # Проверяем, освоены ли пререквизиты
                    prerequisites = self.skills_graph.get(skill_id, [])
                    if self._are_prerequisites_met(student_id, prerequisites):
                        recommendations.append((
                            skill_id, 
                            0.0, 
                            "Новый навык, готов к изучению", 
                            0.5
                        ))
        
        # Сортируем по приоритету и возвращаем топ
        recommendations.sort(key=lambda x: x[3], reverse=True)
        return [(skill_id, mastery, reason) for skill_id, mastery, reason, _ in recommendations[:max_recommendations]]
    
    def _are_prerequisites_met(
        self, 
        student_id: int, 
        prerequisite_ids: List[int], 
        mastery_threshold: float = 0.7    ) -> bool:
        """Проверить, освоены ли необходимые навыки"""
        if not prerequisite_ids:
            return True
        
        if student_id not in self.student_states:
            return False
        
        student_profile = self.student_states[student_id]
        
        for prereq_id in prerequisite_ids:
            if (prereq_id not in student_profile or 
                student_profile[prereq_id].current_mastery < mastery_threshold):
                return False
        
        return True
    
    def save_model(self, filepath: str):
        """Сохранить модель в файл"""
        model_data = {
            'skill_parameters': {
                skill_id: params.to_dict() 
                for skill_id, params in self.skill_parameters.items()
            },
            'student_states': {
                student_id: {
                    skill_id: state.to_dict()
                    for skill_id, state in skills.items()
                }
                for student_id, skills in self.student_states.items()
            },
            'skills_graph': self.skills_graph,
            'metadata': {
                'is_trained': self.is_trained,
                'training_data_size': self.training_data_size
            }
        }
        
        file_path = Path(filepath)
        
        if file_path.suffix == '.json':
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(model_data, f, ensure_ascii=False, indent=2)
        elif file_path.suffix == '.pkl':
            with open(file_path, 'wb') as f:
                pickle.dump(model_data, f)
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {file_path.suffix}")
    
    def load_model(self, filepath: str):
        """Загрузить модель из файла"""
        file_path = Path(filepath)
        
        if file_path.suffix == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                model_data = json.load(f)
        elif file_path.suffix == '.pkl':
            with open(file_path, 'rb') as f:
                model_data = pickle.load(f)
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {file_path.suffix}")
        
        # Восстанавливаем параметры навыков
        self.skill_parameters = {
            int(skill_id): BKTParameters.from_dict(params)
            for skill_id, params in model_data['skill_parameters'].items()
        }
        
        # Восстанавливаем состояния студентов
        self.student_states = {}
        for student_id, skills in model_data['student_states'].items():
            self.student_states[int(student_id)] = {}
            for skill_id, state_data in skills.items():
                state = StudentSkillState(
                    skill_id=int(skill_id),
                    current_mastery=state_data['current_mastery'],
                    attempts_count=state_data['attempts_count'],
                    correct_attempts=state_data['correct_attempts'],
                    last_updated=state_data.get('last_updated')
                )
                self.student_states[int(student_id)][int(skill_id)] = state
        
        # Восстанавливаем граф навыков
        if 'skills_graph' in model_data and model_data['skills_graph']:
            self.skills_graph = {
                int(skill_id): prereqs
                for skill_id, prereqs in model_data['skills_graph'].items()
            }
        
        # Восстанавливаем метаданные
        metadata = model_data.get('metadata', {})
        self.is_trained = metadata.get('is_trained', False)
        self.training_data_size = metadata.get('training_data_size', 0)
    
    def get_model_summary(self) -> Dict[str, Any]:
        """Получить сводку модели"""
        total_students = len(self.student_states)
        total_skills = len(self.skill_parameters)
        
        total_attempts = sum(
            sum(state.attempts_count for state in student_skills.values())
            for student_skills in self.student_states.values()
        )
        
        return {
            'total_students': total_students,
            'total_skills': total_skills,
            'total_attempts': total_attempts,
            'is_trained': self.is_trained,
            'training_data_size': self.training_data_size,
            'has_skills_graph': self.skills_graph is not None,
            'avg_attempts_per_student': total_attempts / total_students if total_students > 0 else 0,
            'skill_parameters_summary': {
                skill_id: {
                    'P_L0': params.P_L0,
                    'P_T': params.P_T,
                    'difficulty_estimate': (1 - params.P_L0) * 0.5 + (1 - params.P_T) * 0.5
                }
                for skill_id, params in self.skill_parameters.items()
            }
        }
    
    def adapt_parameters_for_task(self, skill_id: int, task_characteristics: TaskCharacteristics) -> BKTParameters:
        """
        Адаптировать параметры BKT для конкретного типа задания и уровня сложности
        
        Args:
            skill_id: ID навыка
            task_characteristics: Характеристики задания
            
        Returns:
            BKTParameters: Адаптированные параметры
        """
        base_params = self.get_skill_parameters(skill_id)
        
        # Получаем множители и корректировки
        difficulty_mult = task_characteristics.get_difficulty_multiplier()
        base_guess = task_characteristics.get_guess_probability()
        slip_adjustment = task_characteristics.get_slip_adjustment()
        
        # Адаптируем параметры
        adapted_params = BKTParameters(
            P_L0=base_params.P_L0,  # Начальное знание не зависит от типа задания
            P_T=base_params.P_T * difficulty_mult,  # Сложность влияет на скорость изучения
            P_G=base_guess,  # Вероятность угадывания зависит от типа задания
            P_S=min(0.9, base_params.P_S * slip_adjustment)  # Корректируем вероятность ошибки
        )
        
        return adapted_params
    
    def predict_with_task_type(self, student_id: int, skill_id: int, 
                              task_characteristics: TaskCharacteristics) -> float:
        """
        Предсказать вероятность правильного ответа с учётом типа задания
        
        Args:
            student_id: ID студента
            skill_id: ID навыка
            task_characteristics: Характеристики задания
            
        Returns:
            float: Вероятность правильного ответа
        """
        # Получаем адаптированные параметры
        adapted_params = self.adapt_parameters_for_task(skill_id, task_characteristics)
        
        # Получаем текущее состояние знания
        current_mastery = self.get_mastery_probability(student_id, skill_id)
        
        # Вычисляем вероятность правильного ответа
        P_correct = (current_mastery * (1 - adapted_params.P_S) + 
                    (1 - current_mastery) * adapted_params.P_G)
        
        return P_correct
