from django.db import models
from django.contrib.auth.models import User
from skills.models import Skill, Course
from methodist.models import Task
from student.models import StudentProfile
import json
import os
import logging

logger = logging.getLogger(__name__)


class StudentSkillMastery(models.Model):
    """
    Модель для отслеживания освоения навыков студентами.
    Используется для BKT модели.
    """
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='skill_masteries',
        verbose_name="Студент"
    )
    
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='student_masteries',
        verbose_name="Навык"
    )
    
    # BKT параметры
    initial_mastery_prob = models.FloatField(
        default=0.0,
        verbose_name="Начальная вероятность освоения P(L0)",
        help_text="Вероятность того, что студент уже знает навык"
    )
    
    current_mastery_prob = models.FloatField(
        default=0.0,
        verbose_name="Текущая вероятность освоения P(Lt)",
        help_text="Текущая вероятность освоения навыка"
    )
    
    transition_prob = models.FloatField(
        default=0.3,
        verbose_name="Вероятность перехода P(T)",
        help_text="Вероятность изучения навыка за одну попытку"
    )
    
    guess_prob = models.FloatField(
        default=0.2,
        verbose_name="Вероятность угадывания P(G)",
        help_text="Вероятность правильного ответа при неосвоенном навыке"
    )
    
    slip_prob = models.FloatField(
        default=0.1,
        verbose_name="Вероятность ошибки P(S)",
        help_text="Вероятность неправильного ответа при освоенном навыке"
    )
    
    # Метаданные
    last_updated = models.DateTimeField(
        auto_now=True,
        verbose_name="Последнее обновление"
    )
    
    attempts_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Количество попыток",
        help_text="Общее количество попыток решения заданий по этому навыку"
    )
    
    correct_attempts = models.PositiveIntegerField(
        default=0,
        verbose_name="Правильные попытки",
        help_text="Количество правильных ответов"
    )
    
    def __str__(self):
        return f"{self.student.full_name} - {self.skill.name} (P={self.current_mastery_prob:.3f})"
    
    @property
    def accuracy(self):
        """Точность решения заданий по навыку"""
        if self.attempts_count == 0:
            return 0.0
        return self.correct_attempts / self.attempts_count
    
    @property
    def is_mastered(self):
        """Считается ли навык освоенным (порог 0.8)"""
        return self.current_mastery_prob >= 0.8
    
    def update_mastery_probability(self, is_correct):
        """
        Обновляет вероятность освоения навыка на основе результата попытки
        Использует формулы BKT
        """
        # Обновляем статистику попыток
        self.attempts_count += 1
        if is_correct:
            self.correct_attempts += 1
        
        # Вычисляем вероятность правильного ответа
        p_correct = (self.guess_prob * (1 - self.current_mastery_prob) + 
                    (1 - self.slip_prob) * self.current_mastery_prob)
        
        # Обновляем вероятность освоения по Байесу
        if is_correct:
            # Формула (5) из документа
            numerator = self.current_mastery_prob * (1 - self.slip_prob)
            denominator = (self.current_mastery_prob * (1 - self.slip_prob) + 
                          (1 - self.current_mastery_prob) * self.guess_prob)
        else:
            # Аналогичная формула для неправильного ответа
            numerator = self.current_mastery_prob * self.slip_prob
            denominator = (self.current_mastery_prob * self.slip_prob + 
                          (1 - self.current_mastery_prob) * (1 - self.guess_prob))
        
        if denominator > 0:
            updated_prob = numerator / denominator
        else:
            updated_prob = self.current_mastery_prob
        
        # Применяем вероятность перехода (изучения)
        self.current_mastery_prob = updated_prob + (1 - updated_prob) * self.transition_prob        
        # Ограничиваем значения от 0 до 1
        self.current_mastery_prob = max(0.0, min(1.0, self.current_mastery_prob))
        
        self.save()
    
    class Meta:
        app_label = 'mlmodels'
        verbose_name = "Освоение навыка студентом"
        verbose_name_plural = "Освоение навыков студентами"
        unique_together = ['student', 'skill']
        ordering = ['-current_mastery_prob']


class TaskAttempt(models.Model):
    """
    Модель для записи попыток решения заданий студентами.
    Используется для анализа и обучения BKT модели.
    """
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='task_attempts',
        verbose_name="Студент"
    )
    
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='student_attempts',
        verbose_name="Задание"
    )
    
    # Результат попытки
    is_correct = models.BooleanField(
        verbose_name="Правильный ответ",
        help_text="True если ответ правильный"
    )
    
    # Детали ответа
    given_answer = models.TextField(
        blank=True,
        null=True,
        verbose_name="Данный ответ",
        help_text="Ответ, который дал студент"
    )
    
    correct_answer = models.TextField(
        blank=True,
        null=True,
        verbose_name="Правильный ответ",
        help_text="Правильный ответ на задание"
    )
    
    # Временные метки
    started_at = models.DateTimeField(
        verbose_name="Время начала"
    )
    
    completed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Время завершения"
    )
    
    # Время, затраченное на решение (в секундах)
    time_spent = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Время решения (сек)",
        help_text="Время, затраченное на решение задания в секундах"
    )
      # Дополнительные метаданные (JSON)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Дополнительные данные",
        help_text="Дополнительная информация о попытке в формате JSON"
    )
    
    def __str__(self):
        status = "✓" if self.is_correct else "✗"
        return f"{status} {self.student.full_name} - {self.task.title}"
    
    @property
    def duration_minutes(self):
        """Время решения в минутах"""
        if self.time_spent:            return round(self.time_spent / 60, 2)
        return None

    def save(self, *args, **kwargs):
        # Проверяем, создаётся ли новая попытка
        is_new_attempt = self.pk is None
        
        # Автоматически вычисляем время решения
        if self.started_at and self.completed_at and not self.time_spent:
            delta = self.completed_at - self.started_at
            self.time_spent = int(delta.total_seconds())
        
        super().save(*args, **kwargs)
        
        # Автоматически обновляем BKT при создании новой попытки
        if is_new_attempt:
            try:
                self.update_skill_masteries()
                logger.debug(f"BKT обновлен для студента {self.student.user.username} "
                           f"после попытки задания {self.task.title} "
                           f"(результат: {'правильно' if self.is_correct else 'неправильно'})")
            except Exception as e:
                logger.error(f"Ошибка при автоматическом обновлении BKT: {e}")
                # Не прерываем сохранение попытки из-за ошибки BKT
    
    def update_skill_masteries(self):
        """Обновляет вероятности освоения связанных навыков"""
        for skill in self.task.skills.all():
            # Получаем обученные параметры BKT для этого навыка
            trained_params = self._get_trained_bkt_parameters(skill)
            
            mastery, created = StudentSkillMastery.objects.get_or_create(
                student=self.student,
                skill=skill,                defaults=trained_params
            )
            mastery.update_mastery_probability(self.is_correct)

    def _get_trained_bkt_parameters(self, skill):
        """Получает обученные BKT параметры для навыка"""
        import json
        from pathlib import Path
        
        try:
            # Путь к обученной модели
            model_path = Path(__file__).parent.parent / 'optimized_bkt_model' / 'bkt_model_optimized.json'
            
            if model_path.exists():
                with open(model_path, 'r', encoding='utf-8') as f:
                    model_data = json.load(f)
                
                skill_params = model_data.get('skill_parameters', {}).get(str(skill.id))
                
                if skill_params:
                    return {
                        'initial_mastery_prob': skill_params.get('P_L0', 0.1),
                        'current_mastery_prob': skill_params.get('P_L0', 0.1),  # Начинаем с P_L0
                        'transition_prob': skill_params.get('P_T', 0.3),
                        'guess_prob': skill_params.get('P_G', 0.2),
                        'slip_prob': skill_params.get('P_S', 0.1),
                    }
                    
        except Exception as e:
            logger.warning(f"Ошибка загрузки обученных параметров BKT: {e}")
            logger.debug(f"Используются дефолтные параметры BKT для навыка {skill.name}")
        
        # Возвращаем дефолтные параметры если не удалось загрузить обученные
        return {
            'initial_mastery_prob': 0.1,
            'current_mastery_prob': 0.1,
            'transition_prob': 0.3,
            'guess_prob': 0.2,
            'slip_prob': 0.1,
        }
    
    class Meta:
        app_label = 'mlmodels'
        verbose_name = "Попытка решения задания"
        verbose_name_plural = "Попытки решения заданий"
        ordering = ['-completed_at']


class StudentLearningProfile(models.Model):
    """
    Профиль обучения студента - агрегированные характеристики
    для использования в рекомендательной системе
    """
    student = models.OneToOneField(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='learning_profile',
        verbose_name="Студент"
    )
    
    # Общие характеристики обучения
    learning_speed = models.FloatField(
        default=0.5,
        verbose_name="Скорость обучения",
        help_text="Средняя скорость освоения новых навыков (0-1)"
    )
    
    persistence_level = models.FloatField(
        default=0.5,
        verbose_name="Уровень настойчивости",
        help_text="Склонность к продолжению работы при трудностях (0-1)"
    )
    
    difficulty_preference = models.CharField(
        max_length=20,
        choices=[
            ('easy', 'Легкие задания'),
            ('medium', 'Средние задания'),
            ('hard', 'Сложные задания'),
            ('adaptive', 'Адаптивная сложность'),
        ],
        default='adaptive',
        verbose_name="Предпочитаемая сложность"
    )
    
    # Статистика обучения
    total_attempts = models.PositiveIntegerField(
        default=0,
        verbose_name="Общее количество попыток"
    )
    
    total_correct = models.PositiveIntegerField(
        default=0,
        verbose_name="Общее количество правильных ответов"
    )
    
    average_time_per_task = models.FloatField(
        default=0.0,
        verbose_name="Среднее время на задание (мин)"
    )
    
    # Даты активности
    first_activity = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Первая активность"
    )
    
    last_activity = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Последняя активность"
    )
    
    # Обновление профиля
    last_updated = models.DateTimeField(
        auto_now=True,
        verbose_name="Последнее обновление"
    )
    
    def __str__(self):
        return f"Профиль обучения: {self.student.full_name}"
    
    @property
    def overall_accuracy(self):
        """Общая точность ответов"""
        if self.total_attempts == 0:
            return 0.0
        return self.total_correct / self.total_attempts
    
    @property
    def mastered_skills_count(self):
        """Количество освоенных навыков"""
        return self.student.skill_masteries.filter(
            current_mastery_prob__gte=0.8
        ).count()
    
    def update_profile(self):
        """Обновляет профиль на основе попыток студента"""
        attempts = self.student.task_attempts.all()
        
        if attempts.exists():
            self.total_attempts = attempts.count()
            self.total_correct = attempts.filter(is_correct=True).count()
            
            # Вычисляем среднее время
            time_data = attempts.filter(time_spent__isnull=False)
            if time_data.exists():
                avg_seconds = time_data.aggregate(
                    avg_time=models.Avg('time_spent')
                )['avg_time']
                self.average_time_per_task = avg_seconds / 60 if avg_seconds else 0
            
            # Обновляем даты активности
            self.first_activity = attempts.order_by('completed_at').first().completed_at
            self.last_activity = attempts.order_by('completed_at').last().completed_at
            
            # Вычисляем скорость обучения на основе динамики точности
            self.calculate_learning_speed()
            
            self.save()
    
    def calculate_learning_speed(self):
        """Вычисляет скорость обучения на основе прогресса"""
        # Простая эвристика: анализируем последние 10 попыток
        recent_attempts = self.student.task_attempts.order_by('-completed_at')[:10]
        
        if len(recent_attempts) >= 5:
            # Сравниваем точность первой и второй половины
            mid = len(recent_attempts) // 2
            first_half = recent_attempts[mid:]
            second_half = recent_attempts[:mid]
            
            first_accuracy = sum(1 for att in first_half if att.is_correct) / len(first_half)
            second_accuracy = sum(1 for att in second_half if att.is_correct) / len(second_half)            
            # Нормализуем скорость обучения
            improvement = second_accuracy - first_accuracy
            self.learning_speed = max(0.1, min(1.0, 0.5 + improvement))
    
    class Meta:
        app_label = 'mlmodels'
        verbose_name = "Профиль обучения студента"
        verbose_name_plural = "Профили обучения студентов"
