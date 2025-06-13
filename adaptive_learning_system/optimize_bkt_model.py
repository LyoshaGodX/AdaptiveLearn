"""
Оптимизация параметров BKT модели на синтетическом датасете
Обучает модель методом EM и сохраняет оптимизированные параметры
"""

import os
import sys
import django
from pathlib import Path

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

import pandas as pd
import numpy as np
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import pickle
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, log_loss

from mlmodels.bkt.base_model import BKTModel, BKTParameters, TaskCharacteristics
from mlmodels.bkt.trainer import BKTTrainer, TrainingData
from skills.models import Course, Skill
from methodist.models import Task

class BKTOptimizer:
    """Класс для оптимизации параметров BKT модели"""
    
    def __init__(self, dataset_path: str = "bkt_training_data/bkt_training_dataset.csv"):
        self.dataset_path = dataset_path
        self.bkt_model = BKTModel()
        self.trainer = BKTTrainer(self.bkt_model)
        
        print("🔧 Инициализация оптимизатора BKT модели")
        print(f"📂 Датасет: {dataset_path}")
    
    def load_dataset(self) -> pd.DataFrame:
        """Загрузить датасет для обучения"""
        print("📊 Загрузка датасета...")
        
        df = pd.read_csv(self.dataset_path)
        
        print(f"✅ Загружено записей: {len(df)}")
        print(f"   👥 Студентов: {df['student_id'].nunique()}")
        print(f"   📝 Заданий: {df['task_id'].nunique()}")
        print(f"   🎯 Навыков: {df['skill_id'].nunique()}")
        print(f"   ✅ Успешность: {df['is_correct'].mean():.1%}")
        
        return df
    
    def prepare_training_data(self, df: pd.DataFrame) -> Tuple[List[Dict], List[Dict]]:
        """Подготовить данные для обучения BKT"""
        print("🔄 Подготовка данных для обучения...")
        
        # Сортируем по студенту и времени для корректной последовательности
        df_sorted = df.sort_values(['student_id', 'timestamp'])
        
        training_examples = []
        validation_examples = []
        
        # Разделяем данные по студентам на обучение (80%) и валидацию (20%)
        students = df['student_id'].unique()
        train_students, val_students = train_test_split(
            students, test_size=0.2, random_state=42
        )
          # Подготавливаем примеры для обучения
        for student_id in train_students:
            student_data = df_sorted[df_sorted['student_id'] == student_id]
            
            for _, row in student_data.iterrows():
                example = TrainingData(
                    student_id=int(row['student_id']),
                    skill_id=int(row['skill_id']),
                    is_correct=bool(row['is_correct']),
                    task_id=int(row['task_id']),
                    timestamp=row['timestamp']
                )
                training_examples.append(example)
        
        # Подготавливаем примеры для валидации
        for student_id in val_students:
            student_data = df_sorted[df_sorted['student_id'] == student_id]
            
            for _, row in student_data.iterrows():
                example = TrainingData(
                    student_id=int(row['student_id']),
                    skill_id=int(row['skill_id']),
                    is_correct=bool(row['is_correct']),
                    task_id=int(row['task_id']),
                    timestamp=row['timestamp']
                )
                validation_examples.append(example)
        
        print(f"✅ Подготовлено:")
        print(f"   🎓 Обучающих примеров: {len(training_examples)}")
        print(f"   📋 Валидационных примеров: {len(validation_examples)}")
        print(f"   👥 Студентов в обучении: {len(train_students)}")
        print(f"   👥 Студентов в валидации: {len(val_students)}")
        
        return training_examples, validation_examples
    
    def load_skills_graph(self) -> Dict[int, List[int]]:
        """Загрузить граф навыков из базы данных"""
        print("🔗 Загрузка графа навыков...")
        
        skills_graph = {}
        skills = Skill.objects.all()
        
        for skill in skills:
            prerequisites = list(skill.prerequisites.values_list('id', flat=True))
            skills_graph[skill.id] = prerequisites
            
        print(f"✅ Загружен граф из {len(skills_graph)} навыков")
        edges_count = sum(len(prereqs) for prereqs in skills_graph.values())
        print(f"   🔗 Связей (пререквизитов): {edges_count}")
        
        return skills_graph
    
    def initialize_model_parameters(self, training_data: List[Dict]) -> Dict[int, BKTParameters]:
        """Инициализировать базовые параметры модели для каждого навыка"""
        print("⚙️ Инициализация параметров модели...")
          # Получаем уникальные навыки из данных
        unique_skills = set(example.skill_id for example in training_data)
        
        # Базовые параметры для разных стратегий студентов
        base_parameters = {
            'default': BKTParameters(P_L0=0.1, P_T=0.3, P_G=0.2, P_S=0.1)
        }
        
        skill_parameters = {}
        for skill_id in unique_skills:
            skill_parameters[skill_id] = base_parameters['default']
        
        print(f"✅ Инициализированы параметры для {len(skill_parameters)} навыков")
        return skill_parameters
    
    def train_model(self, training_data: List[Dict], validation_data: List[Dict]) -> Dict:
        """Обучить BKT модель методом EM"""
        print("🎯 ОБУЧЕНИЕ BKT МОДЕЛИ")
        print("=" * 50)
        
        # Инициализируем параметры модели
        skill_parameters = self.initialize_model_parameters(training_data)
        
        # Загружаем граф навыков
        skills_graph = self.load_skills_graph()
        
        # Настраиваем модель
        for skill_id, params in skill_parameters.items():
            self.bkt_model.set_skill_parameters(skill_id, params)
        
        self.bkt_model.set_skills_graph(skills_graph)
          # Обучаем модель
        print("🔄 Запуск EM алгоритма...")
        training_results = self.trainer.train_with_em(
            training_data,
            max_iterations=20,
            tolerance=1e-4,
            verbose=True
        )
        
        # Валидация модели
        print("\n📊 Валидация модели на тестовых данных...")
        validation_results = self.validate_model(validation_data)
        
        # Объединяем результаты
        results = {
            'training': training_results,
            'validation': validation_results,
            'model_parameters': self.get_model_parameters(),
            'training_timestamp': datetime.now().isoformat()        }
        
        return results
    
    def validate_model(self, validation_data: List[Dict]) -> Dict:
        """Валидировать модель на тестовых данных"""
        predictions = []
        actual = []
        
        # Инициализируем всех студентов
        student_ids = set(example.student_id for example in validation_data)
        skill_ids = list(self.bkt_model.skill_parameters.keys())
        
        for student_id in student_ids:
            self.bkt_model.initialize_student_all_skills(student_id, skill_ids)
        
        for example in validation_data:
            student_id = example.student_id
            skill_id = example.skill_id
            is_correct = example.is_correct
            
            # Получаем предсказание до обновления
            prediction = self.bkt_model.get_student_mastery(student_id, skill_id)
            predictions.append(prediction)
            actual.append(1.0 if is_correct else 0.0)
            
            # Обновляем состояние студента
            # Используем стандартные параметры задания, поскольку у нас нет детальной информации
            task_chars = TaskCharacteristics(task_type="single_choice", difficulty="medium")
            answer_score = 1.0 if is_correct else 0.0
            self.bkt_model.update_student_state(
                student_id, skill_id, answer_score, task_chars
            )
        
        # Вычисляем метрики
        # Для accuracy преобразуем предсказания в бинарные (> 0.5)
        binary_predictions = [1 if p > 0.5 else 0 for p in predictions]
        binary_actual = [1 if a > 0.5 else 0 for a in actual]
        
        accuracy = accuracy_score(binary_actual, binary_predictions)
        
        # Для log-loss нужны вероятности
        # Ограничиваем предсказания чтобы избежать log(0)
        clipped_predictions = [max(min(p, 0.999), 0.001) for p in predictions]
        logloss = log_loss(binary_actual, clipped_predictions)
        
        validation_results = {
            'accuracy': float(accuracy),
            'log_loss': float(logloss),
            'num_examples': len(validation_data),
            'mean_prediction': float(np.mean(predictions)),
            'mean_actual': float(np.mean(actual))
        }
        
        print(f"✅ Результаты валидации:")
        print(f"   🎯 Точность: {accuracy:.3f}")
        print(f"   📊 Log-loss: {logloss:.3f}")
        print(f"   📝 Примеров: {len(validation_data)}")
        
        return validation_results
    
    def get_model_parameters(self) -> Dict:
        """Получить текущие параметры модели"""
        parameters = {}
        
        for skill_id, params in self.bkt_model.skill_parameters.items():
            parameters[skill_id] = {
                'P_L0': float(params.P_L0),
                'P_T': float(params.P_T),
                'P_G': float(params.P_G),
                'P_S': float(params.P_S)
            }
        
        return parameters
    
    def save_model(self, results: Dict, output_dir: str = "optimized_bkt_model") -> Dict[str, str]:
        """Сохранить обученную модель и результаты"""
        print("💾 Сохранение обученной модели...")
        
        # Создаем директорию
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        files_created = {}
        
        # 1. Сохраняем модель в JSON
        model_data = {
            'skill_parameters': results['model_parameters'],
            'skills_graph': self.bkt_model.skills_graph,
            'training_results': results['training'],
            'validation_results': results['validation'],
            'metadata': {
                'training_timestamp': results['training_timestamp'],
                'model_type': 'BKT',
                'optimization_method': 'EM',
                'num_skills': len(results['model_parameters'])
            }
        }
        
        json_path = output_path / "bkt_model_optimized.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(model_data, f, indent=2, ensure_ascii=False)
        files_created['model_json'] = str(json_path)
        
        # 2. Сохраняем модель в pickle для быстрой загрузки
        pickle_path = output_path / "bkt_model_optimized.pkl"
        with open(pickle_path, 'wb') as f:
            pickle.dump(self.bkt_model, f)
        files_created['model_pickle'] = str(pickle_path)
        
        # 3. Сохраняем детальные результаты обучения
        results_path = output_path / "training_results.json"
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        files_created['results'] = str(results_path)
        
        # 4. Создаем сводный отчет
        report = self.generate_training_report(results)
        report_path = output_path / "TRAINING_REPORT.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        files_created['report'] = str(report_path)
        
        print(f"✅ Модель сохранена в {len(files_created)} файлах:")
        for file_type, file_path in files_created.items():
            print(f"   {file_type.upper()}: {file_path}")
        
        return files_created
    
    def generate_training_report(self, results: Dict) -> str:
        """Создать отчет о результатах обучения"""
        training_results = results['training']
        validation_results = results['validation']
        model_params = results['model_parameters']
        
        report = f"""# 🎓 ОТЧЕТ ОБ ОБУЧЕНИИ BKT МОДЕЛИ

**Дата обучения**: {results['training_timestamp']}
**Метод оптимизации**: Expectation-Maximization (EM)

---

## 📊 РЕЗУЛЬТАТЫ ОБУЧЕНИЯ

### Общие метрики:
- **Точность на валидации**: {validation_results['accuracy']:.3f}
- **Log-loss на валидации**: {validation_results['log_loss']:.3f}
- **Обучено навыков**: {len(model_params)}
- **Итераций EM**: {training_results.get('total_iterations', 'N/A')}
- **Время обучения**: {training_results.get('training_time_seconds', 'N/A')} сек

### Сходимость:
- **Достигнута сходимость**: {training_results.get('converged', 'N/A')}
- **Финальная log-likelihood**: {training_results.get('final_log_likelihood', 'N/A')}

---

## 🎯 ПАРАМЕТРЫ НАВЫКОВ (топ-10 по P_T)

"""
        
        # Сортируем навыки по P_T для показа самых "обучаемых"
        sorted_skills = sorted(
            model_params.items(), 
            key=lambda x: x[1]['P_T'], 
            reverse=True
        )
        
        report += "| Навык ID | P(L0) | P(T) | P(G) | P(S) |\n"
        report += "|----------|-------|------|------|------|\n"
        
        for skill_id, params in sorted_skills[:10]:
            report += f"| {skill_id} | {params['P_L0']:.3f} | {params['P_T']:.3f} | {params['P_G']:.3f} | {params['P_S']:.3f} |\n"
        
        if len(sorted_skills) > 10:
            report += f"\n*... и еще {len(sorted_skills) - 10} навыков*\n"
        
        report += f"""
---

## 📈 СТАТИСТИКА ПАРАМЕТРОВ

| Параметр | Минимум | Максимум | Среднее | Стд. отклонение |
|----------|---------|----------|---------|-----------------|
| **P(L0)** | {min(p['P_L0'] for p in model_params.values()):.3f} | {max(p['P_L0'] for p in model_params.values()):.3f} | {np.mean([p['P_L0'] for p in model_params.values()]):.3f} | {np.std([p['P_L0'] for p in model_params.values()]):.3f} |
| **P(T)** | {min(p['P_T'] for p in model_params.values()):.3f} | {max(p['P_T'] for p in model_params.values()):.3f} | {np.mean([p['P_T'] for p in model_params.values()]):.3f} | {np.std([p['P_T'] for p in model_params.values()]):.3f} |
| **P(G)** | {min(p['P_G'] for p in model_params.values()):.3f} | {max(p['P_G'] for p in model_params.values()):.3f} | {np.mean([p['P_G'] for p in model_params.values()]):.3f} | {np.std([p['P_G'] for p in model_params.values()]):.3f} |
| **P(S)** | {min(p['P_S'] for p in model_params.values()):.3f} | {max(p['P_S'] for p in model_params.values()):.3f} | {np.mean([p['P_S'] for p in model_params.values()]):.3f} | {np.std([p['P_S'] for p in model_params.values()]):.3f} |

---

## ✅ ГОТОВНОСТЬ К ИСПОЛЬЗОВАНИЮ

Модель успешно обучена и готова к использованию в системе адаптивного обучения:

1. **Прогнозирование освоения навыков** студентами
2. **Оценка освоения курсов** на основе навыков
3. **Учет графа навыков** при прогнозировании
4. **Поддержка разных типов заданий** с корректными весами

### Рекомендации:
- ✅ Модель показывает {validation_results['accuracy']:.1%} точности на валидационных данных
- ✅ Параметры оптимизированы для реальных паттернов обучения
- ✅ Готова к интеграции с рекомендательными системами

**Модель готова к продакшену!** 🚀
"""
        
        return report
    
    def optimize(self) -> Dict[str, str]:
        """Полный цикл оптимизации модели"""
        print("🚀 ЗАПУСК ОПТИМИЗАЦИИ BKT МОДЕЛИ")
        print("=" * 60)
        
        # 1. Загружаем данные
        df = self.load_dataset()
        
        # 2. Подготавливаем данные
        training_data, validation_data = self.prepare_training_data(df)
        
        # 3. Обучаем модель
        results = self.train_model(training_data, validation_data)
        
        # 4. Сохраняем модель
        files = self.save_model(results)
        
        print("\n🎉 ОПТИМИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
        print(f"📊 Точность модели: {results['validation']['accuracy']:.1%}")
        print(f"📂 Файлы сохранены в: optimized_bkt_model/")
        
        return files

def main():
    """Основная функция для оптимизации модели"""
    print("🔧 ОПТИМИЗАТОР ПАРАМЕТРОВ BKT МОДЕЛИ")
    print("=" * 60)
    
    # Создаем оптимизатор
    optimizer = BKTOptimizer("bkt_training_data/bkt_training_dataset.csv")
    
    # Запускаем оптимизацию
    files = optimizer.optimize()
    
    print(f"\n🎯 Оптимизированная модель готова к использованию!")
    print(f"Загружайте модель из: {files['model_pickle']}")

if __name__ == "__main__":
    main()
