"""
Модуль для обучения BKT модели на синтетических и реальных данных.
Поддерживает различные методы оптимизации параметров.
"""

from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pandas as pd
from scipy.optimize import minimize, differential_evolution
from sklearn.metrics import log_loss, accuracy_score
import warnings
from dataclasses import dataclass

from mlmodels.bkt.base_model import BKTModel, BKTParameters, StudentSkillState


@dataclass
class TrainingData:
    """Структура для обучающих данных"""
    student_id: int
    skill_id: int
    is_correct: bool
    timestamp: Optional[str] = None
    task_id: Optional[int] = None


class BKTTrainer:
    """Класс для обучения BKT модели"""
    
    def __init__(self, model: BKTModel):
        self.model = model
        self.training_history = []
        
    def prepare_training_data(self, data: pd.DataFrame) -> List[TrainingData]:
        """
        Подготовить данные для обучения из DataFrame
        
        Ожидаемые колонки:
        - student_id: ID студента
        - skill_id: ID навыка
        - is_correct: результат (True/False)
        - timestamp (опционально): время попытки
        - task_id (опционально): ID задания
        """
        training_data = []
        
        required_columns = ['student_id', 'skill_id', 'is_correct']
        for col in required_columns:
            if col not in data.columns:
                raise ValueError(f"Отсутствует обязательная колонка: {col}")
        
        for _, row in data.iterrows():
            training_data.append(TrainingData(
                student_id=int(row['student_id']),
                skill_id=int(row['skill_id']),
                is_correct=bool(row['is_correct']),
                timestamp=row.get('timestamp'),
                task_id=row.get('task_id')
            ))
        
        # Сортируем по времени если доступно
        if training_data and training_data[0].timestamp:
            training_data.sort(key=lambda x: x.timestamp)
        
        return training_data
    
    def train_with_em(
        self, 
        training_data: List[TrainingData],
        max_iterations: int = 100,
        tolerance: float = 1e-6,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Обучение BKT модели методом Expectation-Maximization
        """
        if verbose:
            print(f"Начало обучения BKT модели методом EM на {len(training_data)} примерах")
        
        # Группируем данные по навыкам
        skill_data = {}
        for data_point in training_data:
            skill_id = data_point.skill_id
            if skill_id not in skill_data:
                skill_data[skill_id] = []
            skill_data[skill_id].append(data_point)
        
        # Обучаем параметры для каждого навыка отдельно
        training_results = {}
        
        for skill_id, skill_training_data in skill_data.items():
            if verbose:
                print(f"Обучение навыка {skill_id} на {len(skill_training_data)} примерах")
            
            # Инициализация параметров
            params = self._initialize_skill_parameters(skill_id, skill_training_data)
            
            # EM итерации
            for iteration in range(max_iterations):
                old_params = BKTParameters(params.P_L0, params.P_T, params.P_G, params.P_S)
                
                # E-step: вычисляем скрытые состояния
                hidden_states = self._e_step(skill_training_data, params)
                
                # M-step: обновляем параметры
                params = self._m_step(skill_training_data, hidden_states)
                
                # Проверяем сходимость
                if self._parameters_converged(old_params, params, tolerance):
                    if verbose:
                        print(f"Навык {skill_id}: сходимость достигнута на итерации {iteration + 1}")
                    break
            
            # Сохраняем обученные параметры
            self.model.set_skill_parameters(skill_id, params)
            
            # Вычисляем метрики качества
            accuracy, log_likelihood = self._evaluate_skill_model(skill_training_data, params)
            
            training_results[skill_id] = {
                'parameters': params.to_dict(),
                'iterations': iteration + 1,
                'accuracy': accuracy,
                'log_likelihood': log_likelihood,
                'data_points': len(skill_training_data)
            }
        
        self.model.is_trained = True
        self.model.training_data_size = len(training_data)
        
        if verbose:
            print("Обучение завершено")
        
        return training_results
    
    def _initialize_skill_parameters(
        self, 
        skill_id: int, 
        skill_data: List[TrainingData]
    ) -> BKTParameters:
        """Инициализация параметров навыка"""
        
        # Простая эвристическая инициализация на основе данных
        total_attempts = len(skill_data)
        correct_attempts = sum(1 for d in skill_data if d.is_correct)
        
        overall_accuracy = correct_attempts / total_attempts if total_attempts > 0 else 0.5
        
        # Эвристические начальные значения
        P_L0 = max(0.01, min(0.99, overall_accuracy * 0.3))  # Начальное знание
        P_T = max(0.01, min(0.99, 0.2 + overall_accuracy * 0.3))  # Вероятность изучения
        P_G = max(0.01, min(0.99, 0.1 + (1 - overall_accuracy) * 0.2))  # Угадывание
        P_S = max(0.01, min(0.99, 0.05 + (1 - overall_accuracy) * 0.15))  # Ошибка
        
        return BKTParameters(P_L0=P_L0, P_T=P_T, P_G=P_G, P_S=P_S)
    
    def _e_step(
        self, 
        skill_data: List[TrainingData], 
        params: BKTParameters
    ) -> List[float]:
        """
        E-step: вычисление скрытых состояний (вероятности знания на каждом шаге)
        """
        hidden_states = []
        
        # Группируем данные по студентам
        student_data = {}
        for data_point in skill_data:
            student_id = data_point.student_id
            if student_id not in student_data:
                student_data[student_id] = []
            student_data[student_id].append(data_point)
        
        # Для каждого студента вычисляем последовательность скрытых состояний
        for student_id, student_attempts in student_data.items():
            # Сортируем по времени если доступно
            if student_attempts[0].timestamp:
                student_attempts.sort(key=lambda x: x.timestamp)
            
            current_mastery = params.P_L0
            
            for attempt in student_attempts:
                hidden_states.append(current_mastery)
                
                # Обновляем вероятность знания после попытки
                current_mastery = self._update_mastery_probability(
                    current_mastery, attempt.is_correct, params
                )
        
        return hidden_states
    
    def _m_step(
        self, 
        skill_data: List[TrainingData], 
        hidden_states: List[float]
    ) -> BKTParameters:
        """
        M-step: обновление параметров на основе скрытых состояний
        """
        if len(hidden_states) != len(skill_data):
            raise ValueError("Размеры hidden_states и skill_data не совпадают")
        
        # Группируем данные по студентам для вычисления P_L0 и P_T
        student_data = {}
        state_index = 0
        
        for data_point in skill_data:
            student_id = data_point.student_id
            if student_id not in student_data:
                student_data[student_id] = []
            student_data[student_id].append((data_point, hidden_states[state_index]))
            state_index += 1
        
        # Вычисляем P_L0 (начальная вероятность знания)
        initial_masteries = []
        for student_attempts in student_data.values():
            if student_attempts:
                # Берем первое состояние студента
                initial_masteries.append(student_attempts[0][1])
        
        P_L0 = np.mean(initial_masteries) if initial_masteries else 0.1
        
        # Вычисляем P_T (вероятность изучения)
        transition_events = []
        for student_attempts in student_data.values():
            for i in range(len(student_attempts) - 1):
                current_data, current_state = student_attempts[i]
                next_data, next_state = student_attempts[i + 1]
                
                # Если студент не знал навык и затем узнал
                if current_state < 0.5 and next_state >= 0.5:
                    transition_events.append(1)
                elif current_state < 0.5:
                    transition_events.append(0)
        
        P_T = np.mean(transition_events) if transition_events else 0.3
        
        # Вычисляем P_G и P_S
        guess_events = []  # Правильные ответы при незнании
        slip_events = []   # Неправильные ответы при знании
        
        for i, (data_point, mastery_state) in enumerate(zip(skill_data, hidden_states)):
            if mastery_state < 0.5:  # Не знает
                guess_events.append(1 if data_point.is_correct else 0)
            else:  # Знает
                slip_events.append(0 if data_point.is_correct else 1)
        
        P_G = np.mean(guess_events) if guess_events else 0.2
        P_S = np.mean(slip_events) if slip_events else 0.1
          # Ограничиваем значения параметров
        P_L0 = max(0.01, min(0.99, float(P_L0)))
        P_T = max(0.01, min(0.99, float(P_T)))
        P_G = max(0.01, min(0.99, float(P_G)))
        P_S = max(0.01, min(0.99, float(P_S)))
        
        return BKTParameters(P_L0=P_L0, P_T=P_T, P_G=P_G, P_S=P_S)
    
    def _update_mastery_probability(
        self, 
        current_mastery: float, 
        is_correct: bool, 
        params: BKTParameters
    ) -> float:
        """Обновить вероятность знания после попытки"""
        
        if is_correct:
            numerator = current_mastery * (1 - params.P_S)
            denominator = (current_mastery * (1 - params.P_S) + 
                          (1 - current_mastery) * params.P_G)
        else:
            numerator = current_mastery * params.P_S
            denominator = (current_mastery * params.P_S + 
                          (1 - current_mastery) * (1 - params.P_G))
        
        if denominator > 0:
            updated_mastery = numerator / denominator
        else:
            updated_mastery = current_mastery
        
        # Применяем вероятность изучения
        new_mastery = updated_mastery + (1 - updated_mastery) * params.P_T
        
        return max(0.0, min(1.0, new_mastery))
    
    def _parameters_converged(
        self, 
        old_params: BKTParameters, 
        new_params: BKTParameters, 
        tolerance: float
    ) -> bool:
        """Проверить сходимость параметров"""
        
        changes = [
            abs(old_params.P_L0 - new_params.P_L0),
            abs(old_params.P_T - new_params.P_T),
            abs(old_params.P_G - new_params.P_G),
            abs(old_params.P_S - new_params.P_S)
        ]
        
        return max(changes) < tolerance
    
    def _evaluate_skill_model(
        self, 
        skill_data: List[TrainingData], 
        params: BKTParameters
    ) -> Tuple[float, float]:
        """Оценить качество модели для навыка"""
        
        predictions = []
        actuals = []
        log_likelihoods = []
        
        # Группируем по студентам
        student_data = {}
        for data_point in skill_data:
            student_id = data_point.student_id
            if student_id not in student_data:
                student_data[student_id] = []
            student_data[student_id].append(data_point)
        
        for student_attempts in student_data.values():
            current_mastery = params.P_L0
            
            for attempt in student_attempts:
                # Предсказываем вероятность правильного ответа
                p_correct = (params.P_G * (1 - current_mastery) + 
                           (1 - params.P_S) * current_mastery)
                
                predictions.append(p_correct)
                actuals.append(1 if attempt.is_correct else 0)
                
                # Вычисляем log-likelihood
                if attempt.is_correct:
                    log_likelihoods.append(np.log(max(1e-10, p_correct)))
                else:
                    log_likelihoods.append(np.log(max(1e-10, 1 - p_correct)))
                
                # Обновляем состояние
                current_mastery = self._update_mastery_probability(
                    current_mastery, attempt.is_correct, params
                )
          # Вычисляем метрики
        binary_predictions = [1 if p >= 0.5 else 0 for p in predictions]
        accuracy = accuracy_score(actuals, binary_predictions)
        avg_log_likelihood = np.mean(log_likelihoods)
        
        return float(accuracy), float(avg_log_likelihood)
    
    def train_with_optimization(
        self,
        training_data: List[TrainingData],
        method: str = 'differential_evolution',
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Обучение BKT модели методами численной оптимизации
        """
        if verbose:
            print(f"Обучение BKT модели методом {method}")
        
        # Группируем данные по навыкам
        skill_data = {}
        for data_point in training_data:
            skill_id = data_point.skill_id
            if skill_id not in skill_data:
                skill_data[skill_id] = []
            skill_data[skill_id].append(data_point)
        
        training_results = {}
        
        for skill_id, skill_training_data in skill_data.items():
            if verbose:
                print(f"Оптимизация параметров навыка {skill_id}")
            
            # Определяем функцию потерь
            def objective_function(params_array):
                P_L0, P_T, P_G, P_S = params_array
                
                # Ограничения на параметры
                if not (0.01 <= P_L0 <= 0.99 and 0.01 <= P_T <= 0.99 and 
                       0.01 <= P_G <= 0.99 and 0.01 <= P_S <= 0.99):
                    return 1e6
                
                params = BKTParameters(P_L0=P_L0, P_T=P_T, P_G=P_G, P_S=P_S)
                
                # Вычисляем отрицательный log-likelihood
                return -self._compute_log_likelihood(skill_training_data, params)
            
            # Границы параметров
            bounds = [(0.01, 0.99), (0.01, 0.99), (0.01, 0.99), (0.01, 0.99)]
            
            # Оптимизация
            if method == 'differential_evolution':                result = differential_evolution(
                    objective_function, 
                    bounds, 
                    maxiter=100
                )
            else:
                # Используем начальное приближение
                initial_params = self._initialize_skill_parameters(skill_id, skill_training_data)
                x0 = [initial_params.P_L0, initial_params.P_T, initial_params.P_G, initial_params.P_S]
                
                result = minimize(
                    objective_function,
                    x0,
                    bounds=bounds,
                    method='L-BFGS-B'
                )
            
            if result.success:
                P_L0, P_T, P_G, P_S = result.x
                optimized_params = BKTParameters(P_L0=P_L0, P_T=P_T, P_G=P_G, P_S=P_S)
                
                # Сохраняем параметры
                self.model.set_skill_parameters(skill_id, optimized_params)
                
                # Вычисляем метрики
                accuracy, log_likelihood = self._evaluate_skill_model(skill_training_data, optimized_params)
                
                training_results[skill_id] = {
                    'parameters': optimized_params.to_dict(),
                    'optimization_success': True,
                    'final_loss': result.fun,
                    'accuracy': accuracy,
                    'log_likelihood': log_likelihood,
                    'data_points': len(skill_training_data)
                }
            else:
                if verbose:
                    print(f"Оптимизация для навыка {skill_id} не удалась: {result.message}")
                
                training_results[skill_id] = {
                    'optimization_success': False,
                    'error_message': result.message,
                    'data_points': len(skill_training_data)
                }
        
        self.model.is_trained = True
        self.model.training_data_size = len(training_data)
        
        return training_results
    
    def _compute_log_likelihood(
        self, 
        skill_data: List[TrainingData], 
        params: BKTParameters
    ) -> float:
        """Вычислить log-likelihood данных при заданных параметрах"""
        
        log_likelihood = 0.0
        
        # Группируем по студентам
        student_data = {}
        for data_point in skill_data:
            student_id = data_point.student_id
            if student_id not in student_data:
                student_data[student_id] = []
            student_data[student_id].append(data_point)
        
        for student_attempts in student_data.values():
            current_mastery = params.P_L0
            
            for attempt in student_attempts:
                # Вычисляем вероятность наблюдения
                p_correct = (params.P_G * (1 - current_mastery) + 
                           (1 - params.P_S) * current_mastery)
                
                if attempt.is_correct:
                    log_likelihood += np.log(max(1e-10, p_correct))
                else:
                    log_likelihood += np.log(max(1e-10, 1 - p_correct))
                
                # Обновляем состояние
                current_mastery = self._update_mastery_probability(
                    current_mastery, attempt.is_correct, params
                )
        
        return log_likelihood
    
    def evaluate_model(
        self, 
        test_data: List[TrainingData]
    ) -> Dict[str, Any]:
        """Оценить качество обученной модели на тестовых данных"""
        
        if not self.model.is_trained:
            raise ValueError("Модель не обучена")
        
        # Группируем по навыкам
        skill_data = {}
        for data_point in test_data:
            skill_id = data_point.skill_id
            if skill_id not in skill_data:
                skill_data[skill_id] = []
            skill_data[skill_id].append(data_point)
        
        evaluation_results = {}
        overall_metrics = {
            'total_predictions': 0,
            'total_correct': 0,
            'total_log_likelihood': 0.0
        }
        
        for skill_id, skill_test_data in skill_data.items():
            params = self.model.get_skill_parameters(skill_id)
            if not params:
                continue
            
            accuracy, log_likelihood = self._evaluate_skill_model(skill_test_data, params)
            
            evaluation_results[skill_id] = {
                'accuracy': accuracy,
                'log_likelihood': log_likelihood,
                'test_examples': len(skill_test_data)
            }
            
            overall_metrics['total_predictions'] += len(skill_test_data)
            overall_metrics['total_correct'] += accuracy * len(skill_test_data)
            overall_metrics['total_log_likelihood'] += log_likelihood * len(skill_test_data)
        
        # Вычисляем общие метрики
        if overall_metrics['total_predictions'] > 0:
            overall_metrics['overall_accuracy'] = (
                overall_metrics['total_correct'] / overall_metrics['total_predictions']
            )
            overall_metrics['overall_log_likelihood'] = (
                overall_metrics['total_log_likelihood'] / overall_metrics['total_predictions']
            )
        
        return {
            'skill_results': evaluation_results,
            'overall_metrics': overall_metrics,
            'evaluated_skills': len(evaluation_results),
            'total_test_examples': len(test_data)
        }
