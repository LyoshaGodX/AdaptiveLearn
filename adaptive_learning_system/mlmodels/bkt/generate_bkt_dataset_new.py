"""
Генерация синтетического датасета для оптимизации параметров BKT модели
Создает выборку из 200 студентов с различными стратегиями обучения
"""

import os
import sys
import django
from pathlib import Path

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

import random
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json
from datetime import datetime, timedelta

from strategies import (
    StudentStrategy, BeginnerStrategy, IntermediateStrategy, 
    AdvancedStrategy, GiftedStrategy, StruggleStrategy,
    StudentStrategyFactory
)
from generator import SyntheticDataGenerator

# Импортируем Django модели напрямую
from skills.models import Course, Skill, Task
from student.models import Student

@dataclass
class DatasetConfig:
    """Конфигурация для генерации датасета"""
    num_students: int = 200
    courses_per_student: Tuple[int, int] = (1, 3)  # Минимум и максимум курсов на студента
    noise_level: float = 0.15  # Уровень шума в данных (0-1)
    time_span_days: int = 365  # Период времени для генерации данных (дни)
    min_attempts_per_task: int = 1  # Минимум попыток на задание
    max_attempts_per_task: int = 3  # Максимум попыток на задание
    
    # Распределение стратегий студентов
    strategy_distribution: Optional[Dict[str, float]] = None
    
    def __post_init__(self):
        if self.strategy_distribution is None:
            self.strategy_distribution = {
                'beginner': 0.25,      # 25% начинающих
                'intermediate': 0.35,   # 35% средних  
                'advanced': 0.25,      # 25% продвинутых
                'gifted': 0.10,        # 10% одаренных
                'struggle': 0.05       # 5% испытывающих трудности
            }

class BKTDatasetGenerator:
    """Генератор синтетического датасета для обучения BKT модели"""
    
    def __init__(self, config: Optional[DatasetConfig] = None):
        self.config = config or DatasetConfig()
        self.synthetic_generator = SyntheticDataGenerator()
        
        # Для воспроизводимости результатов
        random.seed(42)
        np.random.seed(42)
        
        print(f"🎯 Инициализация генератора BKT датасета")
        print(f"   📊 Студентов: {self.config.num_students}")
        print(f"   📚 Курсов на студента: {self.config.courses_per_student[0]}-{self.config.courses_per_student[1]}")
        print(f"   🔊 Уровень шума: {self.config.noise_level}")
        print(f"   📅 Период: {self.config.time_span_days} дней")
    
    def _load_course_data(self) -> Dict:
        """Загрузить данные о курсах, навыках и заданиях из Django моделей"""
        print("📂 Загрузка данных о курсах...")
        
        courses = Course.objects.all()
        course_data = {}
        total_tasks = 0
        
        for course in courses:
            # Получаем навыки курса
            course_skills = course.skills.all()
            course_tasks = []
            
            # Получаем задания для каждого навыка
            for skill in course_skills:
                skill_tasks = Task.objects.filter(skill=skill)
                for task in skill_tasks:
                    course_tasks.append({
                        'id': task.id,
                        'skill_id': skill.id,
                        'task_type': task.task_type,
                        'difficulty': task.difficulty,
                        'title': task.title,
                        'content': task.content
                    })
            
            course_data[course.id] = {
                'course_info': {
                    'id': course.id,
                    'name': course.name,
                    'description': course.description
                },
                'skills': [{'id': skill.id, 'name': skill.name, 'description': skill.description} 
                          for skill in course_skills],
                'tasks': course_tasks
            }
            total_tasks += len(course_tasks)
            
            print(f"   ✅ {course.name}: {len(course_skills)} навыков, {len(course_tasks)} заданий")
        
        print(f"📊 Загружено: {len(courses)} курсов, всего {total_tasks} заданий")
        return course_data
    
    def _create_student_population(self) -> List[Tuple[int, StudentStrategy, List[str]]]:
        """Создать популяцию студентов с различными стратегиями и курсами"""
        print(f"👥 Создание популяции из {self.config.num_students} студентов...")
        
        # Создаем стратегии студентов
        strategies = StudentStrategyFactory.create_mixed_population(
            self.config.num_students, 
            self.config.strategy_distribution
        )
        
        # Загружаем список доступных курсов
        courses = Course.objects.all()
        course_ids = [course.id for course in courses]
        
        students = []
        strategy_stats = {}
        
        for student_id in range(1, self.config.num_students + 1):
            strategy = strategies[student_id - 1]
            strategy_name = strategy.__class__.__name__.replace('Strategy', '').lower()
            
            # Случайно выбираем количество курсов для студента
            num_courses = random.randint(*self.config.courses_per_student)
            
            # Случайно выбираем курсы для студента
            student_courses = random.sample(course_ids, min(num_courses, len(course_ids)))
            
            students.append((student_id, strategy, student_courses))
            
            # Статистика по стратегиям
            if strategy_name not in strategy_stats:
                strategy_stats[strategy_name] = 0
            strategy_stats[strategy_name] += 1
        
        print("📈 Распределение стратегий студентов:")
        for strategy, count in strategy_stats.items():
            percentage = (count / self.config.num_students) * 100
            print(f"   {strategy}: {count} студентов ({percentage:.1f}%)")
        
        return students
    
    def _add_noise_to_performance(self, base_success_prob: float) -> float:
        """Добавить шум к базовой вероятности успеха"""
        noise = np.random.normal(0, self.config.noise_level)
        noisy_prob = base_success_prob + noise
        return max(0.0, min(1.0, noisy_prob))  # Ограничиваем [0, 1]
    
    def _simulate_learning_progression(self, student_strategy: StudentStrategy, 
                                     tasks: List[Dict], skills: List[Dict]) -> List[Dict]:
        """Симулировать прогрессию обучения студента"""
        attempts = []
        skill_mastery = {skill['id']: 0.1 for skill in skills}  # Начальное освоение
        
        # Сортируем задания по сложности и навыкам
        sorted_tasks = sorted(tasks, key=lambda t: (t.get('difficulty', 'intermediate'), t['skill_id']))
        
        start_date = datetime.now() - timedelta(days=self.config.time_span_days)
        current_date = start_date
        
        for task in sorted_tasks:
            skill_id = task['skill_id']
            current_mastery = skill_mastery[skill_id]
            
            # Студент решает, стоит ли пытаться выполнить задание
            should_attempt = student_strategy.should_attempt_task(
                task_difficulty=task.get('difficulty', 'intermediate'),
                current_mastery=current_mastery
            )
            
            if should_attempt:
                # Количество попыток для этого задания
                num_attempts = random.randint(
                    self.config.min_attempts_per_task, 
                    self.config.max_attempts_per_task
                )
                
                for attempt_num in range(num_attempts):
                    # Базовая вероятность успеха
                    base_success_prob = student_strategy.get_success_probability(
                        task_difficulty=task.get('difficulty', 'intermediate'),
                        current_mastery=current_mastery
                    )
                    
                    # Добавляем шум
                    noisy_success_prob = self._add_noise_to_performance(base_success_prob)
                    
                    # Определяем результат попытки
                    if task.get('task_type') == 'multiple':
                        # Для multiple choice - небинарная оценка
                        if random.random() < noisy_success_prob:
                            answer_score = random.uniform(0.6, 1.0)  # Частично или полностью правильный
                        else:
                            answer_score = random.uniform(0.0, 0.4)  # Неправильный или частично правильный
                    else:
                        # Для остальных типов - бинарная оценка
                        answer_score = 1.0 if random.random() < noisy_success_prob else 0.0
                    
                    # Время выполнения (с учетом сложности и мастерства)
                    base_time = {
                        'beginner': 5,
                        'intermediate': 8, 
                        'advanced': 12
                    }.get(task.get('difficulty', 'intermediate'), 8)
                    
                    time_multiplier = 2.0 - current_mastery  # Чем выше мастерство, тем быстрее
                    solve_time = max(1, int(base_time * time_multiplier * random.uniform(0.5, 1.5)))
                    
                    # Записываем попытку
                    attempt = {
                        'student_id': task.get('student_id', 1),
                        'task_id': task['id'],
                        'skill_id': skill_id,
                        'course_id': task.get('course_id'),
                        'attempt_number': attempt_num + 1,
                        'answer_score': answer_score,
                        'is_correct': answer_score > 0.5,
                        'task_type': task.get('task_type', 'single'),
                        'difficulty': task.get('difficulty', 'intermediate'),
                        'solve_time_minutes': solve_time,
                        'timestamp': current_date,
                        'strategy': student_strategy.__class__.__name__.replace('Strategy', '').lower()
                    }
                    attempts.append(attempt)
                    
                    # Обновляем освоение навыка (простая симуляция обучения)
                    if answer_score > 0.5:
                        learning_rate = student_strategy.characteristics.learning_speed.value
                        skill_mastery[skill_id] = min(1.0, 
                            skill_mastery[skill_id] + learning_rate * answer_score * 0.1
                        )
                    
                    # Сдвигаем время на случайный интервал
                    current_date += timedelta(
                        minutes=random.randint(30, 180),  # 30 минут - 3 часа между попытками
                        hours=random.randint(0, 48)       # До 2 дней между заданиями
                    )
                    
                    # Если студент справился, переходим к следующему заданию
                    if answer_score > 0.7 and attempt_num > 0:
                        break
        
        return attempts
    
    def generate_dataset(self, output_dir: str = "bkt_training_data") -> Dict[str, str]:
        """Генерировать полный датасет для обучения BKT"""
        print("🚀 ГЕНЕРАЦИЯ СИНТЕТИЧЕСКОГО ДАТАСЕТА ДЛЯ BKT")
        print("=" * 60)
        
        # Создаем директорию для вывода
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Загружаем данные о курсах
        course_data = self._load_course_data()
        
        # Создаем популяцию студентов
        students = self._create_student_population()
        
        # Генерируем данные для каждого студента
        print(f"\n📚 Генерация данных для {len(students)} студентов...")
        all_attempts = []
        
        for i, (student_id, strategy, student_courses) in enumerate(students, 1):
            if i % 20 == 0:
                print(f"   Обработка студента {i}/{len(students)}")
            
            # Собираем все задания студента из его курсов
            student_tasks = []
            student_skills = []
            
            for course_id in student_courses:
                if course_id in course_data:
                    course_tasks = course_data[course_id]['tasks'].copy()
                    course_skills = course_data[course_id]['skills']
                    
                    # Добавляем информацию о студенте и курсе к заданиям
                    for task in course_tasks:
                        task['student_id'] = student_id
                        task['course_id'] = course_id
                    
                    student_tasks.extend(course_tasks)
                    student_skills.extend(course_skills)
            
            # Убираем дублирующие навыки
            unique_skills = []
            seen_skill_ids = set()
            for skill in student_skills:
                if skill['id'] not in seen_skill_ids:
                    unique_skills.append(skill)
                    seen_skill_ids.add(skill['id'])
            
            # Перемешиваем задания для создания случайной последовательности
            random.shuffle(student_tasks)
            
            # Симулируем обучение студента
            student_attempts = self._simulate_learning_progression(
                strategy, student_tasks, unique_skills
            )
            
            all_attempts.extend(student_attempts)
        
        print(f"✅ Сгенерировано {len(all_attempts)} попыток решения заданий")
        
        # Создаем DataFrame
        df = pd.DataFrame(all_attempts)
        
        # Статистика по датасету
        print(f"\n📊 СТАТИСТИКА ДАТАСЕТА:")
        print(f"   📝 Всего попыток: {len(df)}")
        print(f"   👥 Уникальных студентов: {df['student_id'].nunique()}")
        print(f"   📋 Уникальных заданий: {df['task_id'].nunique()}")
        print(f"   🎯 Уникальных навыков: {df['skill_id'].nunique()}")
        print(f"   📚 Уникальных курсов: {df['course_id'].nunique()}")
        print(f"   ✅ Общий процент успеха: {(df['is_correct'].sum() / len(df)) * 100:.1f}%")
        print(f"   ⏱️  Среднее время на задание: {df['solve_time_minutes'].mean():.1f} минут")
        
        # Статистика по стратегиям
        print(f"\n📈 СТАТИСТИКА ПО СТРАТЕГИЯМ:")
        strategy_stats = df.groupby('strategy').agg({
            'student_id': 'count',
            'is_correct': 'mean',
            'solve_time_minutes': 'mean'
        }).round(3)
        
        for strategy, stats in strategy_stats.iterrows():
            print(f"   {strategy}: {stats['student_id']} попыток, "
                  f"успех {stats['is_correct']*100:.1f}%, "
                  f"время {stats['solve_time_minutes']:.1f} мин")
        
        # Статистика по типам заданий
        print(f"\n🎯 СТАТИСТИКА ПО ТИПАМ ЗАДАНИЙ:")
        task_type_stats = df.groupby('task_type').agg({
            'student_id': 'count',
            'is_correct': 'mean',
            'answer_score': 'mean'
        }).round(3)
        
        for task_type, stats in task_type_stats.iterrows():
            print(f"   {task_type}: {stats['student_id']} попыток, "
                  f"успех {stats['is_correct']*100:.1f}%, "
                  f"средний балл {stats['answer_score']:.2f}")
        
        # Сохраняем датасет в различных форматах
        files_created = {}
        
        # CSV для общего использования
        csv_path = output_path / "bkt_training_dataset.csv"
        df.to_csv(csv_path, index=False)
        files_created['csv'] = str(csv_path)
        print(f"💾 Датасет сохранен в CSV: {csv_path}")
        
        # JSON для детального анализа
        json_path = output_path / "bkt_training_dataset.json"
        df.to_json(json_path, orient='records', date_format='iso', indent=2)
        files_created['json'] = str(json_path)
        print(f"💾 Датасет сохранен в JSON: {json_path}")
        
        # Parquet для быстрой обработки
        parquet_path = output_path / "bkt_training_dataset.parquet"
        df.to_parquet(parquet_path, index=False)
        files_created['parquet'] = str(parquet_path)
        print(f"💾 Датасет сохранен в Parquet: {parquet_path}")
        
        # Метаданные датасета
        metadata = {
            'generation_config': {
                'num_students': self.config.num_students,
                'courses_per_student': self.config.courses_per_student,
                'noise_level': self.config.noise_level,
                'time_span_days': self.config.time_span_days,
                'strategy_distribution': self.config.strategy_distribution
            },
            'dataset_stats': {
                'total_attempts': len(df),
                'unique_students': df['student_id'].nunique(),
                'unique_tasks': df['task_id'].nunique(),
                'unique_skills': df['skill_id'].nunique(),
                'unique_courses': df['course_id'].nunique(),
                'overall_success_rate': float(df['is_correct'].mean()),
                'average_solve_time': float(df['solve_time_minutes'].mean())
            },
            'strategy_stats': strategy_stats.to_dict('index'),
            'task_type_stats': task_type_stats.to_dict('index'),
            'generation_timestamp': datetime.now().isoformat()
        }
        
        metadata_path = output_path / "dataset_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        files_created['metadata'] = str(metadata_path)
        print(f"📋 Метаданные сохранены: {metadata_path}")
        
        print(f"\n✅ ГЕНЕРАЦИЯ ДАТАСЕТА ЗАВЕРШЕНА УСПЕШНО!")
        print(f"📂 Созданные файлы: {len(files_created)}")
        for file_type, file_path in files_created.items():
            print(f"   {file_type.upper()}: {file_path}")
        
        return files_created

def main():
    """Основная функция для генерации датасета"""
    print("🎓 ГЕНЕРАТОР СИНТЕТИЧЕСКОГО ДАТАСЕТА ДЛЯ BKT МОДЕЛИ")
    print("=" * 60)
    
    # Конфигурация генерации
    config = DatasetConfig(
        num_students=200,
        courses_per_student=(1, 3),
        noise_level=0.15,
        time_span_days=365,
        min_attempts_per_task=1,
        max_attempts_per_task=3
    )
    
    # Создаем генератор
    generator = BKTDatasetGenerator(config)
    
    # Генерируем датасет
    files = generator.generate_dataset("bkt_training_data")
    
    print(f"\n🎯 Готов к использованию для обучения BKT модели!")
    print(f"Используйте файл: {files['csv']} для обучения")

if __name__ == "__main__":
    main()
