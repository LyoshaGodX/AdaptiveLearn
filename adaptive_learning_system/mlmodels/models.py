from django.db import models
from django.contrib.auth.models import User
from skills.models import Skill, Course
from methodist.models import Task
from student.models import StudentProfile
import json


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
    time_spent = models.PositiveIntegerField(        null=True,
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
    
    # LLM объяснение для рекомендации
    llm_explanation = models.TextField(
        blank=True,
        verbose_name="LLM объяснение",
        help_text="Объяснение рекомендации, которая привела к этой попытке, сгенерированное LLM"    )
    
    def __str__(self):
        status = "✓" if self.is_correct else "✗"
        return f"{status} {self.student.full_name} - {self.task.title}"    @property
    def duration_minutes(self):
        """Время решения в минутах"""
        if self.time_spent:
            return round(self.time_spent / 60, 2)
        return None
    
    def save(self, *args, **kwargs):
        # Автоматически вычисляем время решения
        if self.started_at and self.completed_at and not self.time_spent:
            delta = self.completed_at - self.started_at
            self.time_spent = int(delta.total_seconds())
        
        super().save(*args, **kwargs)
        
        # Автоматически применяем BKT при сохранении попытки
        self.update_skill_masteries()
        
        # ВАЖНО: Генерация DQN рекомендации перенесена в асинхронный вызов 
        # в student.views.create_recommendation_async() чтобы не блокировать UI
    
    def update_skill_masteries(self):
        """Обновляет вероятности освоения связанных навыков"""
        for skill in self.task.skills.all():
            # Получаем обученные параметры BKT для этого навыка
            trained_params = self._get_trained_bkt_parameters(skill)
            
            mastery, created = StudentSkillMastery.objects.get_or_create(
                student=self.student,
                skill=skill,
                defaults=trained_params
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
                        'guess_prob': skill_params.get('P_G', 0.2),                        'slip_prob': skill_params.get('P_S', 0.1),
                    }
            
        except Exception as e:
            pass
        
        # Возвращаем дефолтные параметры если не удалось загрузить обученные
        return {
            'initial_mastery_prob': 0.1,
            'current_mastery_prob': 0.1,
            'transition_prob': 0.3,
            'guess_prob': 0.2,            'slip_prob': 0.1,
        }
    
    def _create_new_dqn_recommendation(self):
        """Создает новую DQN рекомендацию после выполнения задания"""
        try:
            # Импортируем здесь, чтобы избежать циклических импортов
            from mlmodels.dqn.recommendation_manager_fixed import recommendation_manager_fixed
            
            # Автоматически связываем эту попытку с текущей рекомендацией
            recommendation_manager_fixed.link_attempt_to_recommendation(
                attempt_id=self.id,
                recommendation_id=None  # Найдет текущую рекомендацию автоматически
            )
              # Генерируем новую рекомендацию для студента
            new_rec = recommendation_manager_fixed.generate_and_save_recommendation(
                student_id=self.student.user.id,  # ID пользователя, а не StudentProfile
                set_as_current=True
            )
            
        except Exception as e:
            pass
    
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


# =============================================================================
# МОДЕЛИ ДЛЯ СИСТЕМЫ DQN С ПОДКРЕПЛЕНИЕМ
# =============================================================================

class DQNRecommendation(models.Model):
    """
    Модель для хранения рекомендаций DQN.
    Связывает студента с рекомендованным заданием.
    """
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='dqn_recommendations',
        verbose_name="Студент"
    )
    
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='dqn_recommendations',
        verbose_name="Рекомендованное задание"
    )
    
    # Информация о рекомендации
    q_value = models.FloatField(
        verbose_name="Q-value",
        help_text="Значение Q-функции для данной рекомендации"
    )
    
    confidence = models.FloatField(
        verbose_name="Уверенность",
        help_text="Уверенность модели в рекомендации (0-1)"
    )
    
    reason = models.CharField(
        max_length=500,
        verbose_name="Причина рекомендации",
        help_text="Объяснение почему было рекомендовано это задание"
    )
    
    # Контекст на момент рекомендации
    student_state_snapshot = models.JSONField(
        verbose_name="Снимок состояния студента",
        help_text="Состояние студента на момент генерации рекомендации"
    )
    
    # Метаданные
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Время создания"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активная рекомендация",
        help_text="Является ли рекомендация текущей для студента"
    )
      # Связь с попыткой (если студент выполнил задание)
    attempt = models.OneToOneField(
        'TaskAttempt',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dqn_recommendation',
        verbose_name="Связанная попытка"
    )
    
    # === ПОЛЯ ДЛЯ LLM ОБЪЯСНЕНИЙ ===
    
    # Граф навыков и зависимости
    prerequisite_skills_snapshot = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Снимок prerequisite навыков",
        help_text="Список prerequisite навыков с их BKT вероятностями на момент рекомендации"
    )
    
    dependent_skills_snapshot = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Снимок зависимых навыков", 
        help_text="Список навыков, которые зависят от рекомендуемого, с их BKT вероятностями"
    )
    
    # Контекст выбора задания
    target_skill_info = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Информация о целевом навыке",
        help_text="Подробная информация о навыке, для которого рекомендуется задание"
    )
    
    alternative_tasks_considered = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Рассмотренные альтернативы",
        help_text="Список других заданий по тому же навыку с их Q-values"
    )
    
    student_progress_context = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Контекст прогресса студента",
        help_text="История попыток студента по данному навыку и связанным навыкам"
    )
    
    # LLM генерация
    llm_explanation = models.TextField(
        blank=True,
        verbose_name="LLM объяснение",
        help_text="Сгенерированное LLM объяснение рекомендации на естественном языке"
    )
    
    llm_explanation_generated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Время генерации LLM объяснения"
    )
    
    def __str__(self):
        return f"DQN: {self.student.full_name} -> Задание {self.task.id} (Q={self.q_value:.4f})"
    
    class Meta:
        app_label = 'mlmodels'
        verbose_name = "DQN рекомендация"
        verbose_name_plural = "DQN рекомендации"
        ordering = ['-created_at']


class StudentCurrentRecommendation(models.Model):
    """
    Модель для хранения текущей рекомендации студента.
    У каждого студента может быть только одна активная рекомендация.
    """
    student = models.OneToOneField(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='current_recommendation',
        verbose_name="Студент"
    )
    
    recommendation = models.ForeignKey(
        DQNRecommendation,
        on_delete=models.CASCADE,
        related_name='current_for_students',
        verbose_name="Текущая рекомендация"
    )
      # Метаданные
    set_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Время установки"
    )
    
    times_viewed = models.PositiveIntegerField(
        default=0,
        verbose_name="Количество просмотров",
        help_text="Сколько раз студент видел эту рекомендацию"
    )
    
    # LLM объяснение рекомендации
    llm_explanation = models.TextField(
        blank=True,
        verbose_name="LLM объяснение",
        help_text="Объяснение рекомендации на естественном языке, сгенерированное LLM"
    )
    
    def __str__(self):
        return f"Текущая рекомендация: {self.student.full_name} -> Задание {self.recommendation.task.id}"
    
    def increment_views(self):
        """Увеличивает счетчик просмотров"""
        self.times_viewed += 1
        self.save()
    
    class Meta:
        app_label = 'mlmodels'
        verbose_name = "Текущая рекомендация студента"
        verbose_name_plural = "Текущие рекомендации студентов"


class ExpertFeedback(models.Model):
    """
    Модель для хранения экспертной разметки рекомендаций.
    Используется для обучения DQN с подкреплением.
    """
    
    FEEDBACK_CHOICES = [
        ('positive', 'Положительное'),
        ('negative', 'Отрицательное'),
    ]
    
    STRENGTH_CHOICES = [
        ('low', 'Низкая'),
        ('medium', 'Средняя'),
        ('high', 'Высокая'),
    ]
    
    recommendation = models.ForeignKey(
        DQNRecommendation,
        on_delete=models.CASCADE,
        related_name='expert_feedback',
        verbose_name="Рекомендация"
    )
    
    expert = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='expert_feedbacks',
        verbose_name="Эксперт"
    )
    
    # Тип подкрепления
    feedback_type = models.CharField(
        max_length=20,
        choices=FEEDBACK_CHOICES,
        verbose_name="Тип подкрепления"
    )
    
    strength = models.CharField(
        max_length=20,
        choices=STRENGTH_CHOICES,
        verbose_name="Сила подкрепления"
    )
    
    # Численное значение награды
    reward_value = models.FloatField(
        verbose_name="Численное значение награды",
        help_text="Вычисляется автоматически на основе типа и силы"
    )
    
    # Комментарий эксперта
    comment = models.TextField(
        blank=True,
        verbose_name="Комментарий эксперта",
        help_text="Объяснение решения о подкреплении"
    )
    
    # Метаданные
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Время создания"
    )
    
    is_used_for_training = models.BooleanField(
        default=False,
        verbose_name="Использовано для обучения",
        help_text="Была ли эта разметка использована для дообучения модели"
    )
    
    def save(self, *args, **kwargs):
        """Автоматически вычисляет численное значение награды"""
        if not self.reward_value:
            self.reward_value = self.calculate_reward_value()
        super().save(*args, **kwargs)
    
    def calculate_reward_value(self):
        """Вычисляет численное значение награды на основе типа и силы"""
        # Базовые значения
        base_values = {
            'low': 0.1,
            'medium': 0.5,
            'high': 1.0,
        }
        
        base_reward = base_values.get(self.strength, 0.5)
        
        # Применяем знак в зависимости от типа
        if self.feedback_type == 'positive':
            return base_reward
        else:  # negative
            return -base_reward
    
    def __str__(self):
        sign = "+" if self.feedback_type == 'positive' else "-"
        return f"Feedback: {self.recommendation} ({sign}{self.strength}, {self.reward_value:+.2f})"
    
    class Meta:
        app_label = 'mlmodels'
        verbose_name = "Экспертная разметка"
        verbose_name_plural = "Экспертные разметки"
        ordering = ['-created_at']
        unique_together = ['recommendation', 'expert']


class DQNTrainingSession(models.Model):
    """
    Модель для отслеживания сессий дообучения DQN модели.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Ожидание'),
        ('running', 'Выполняется'),
        ('completed', 'Завершено'),
        ('failed', 'Ошибка'),
    ]
    
    # Основная информация
    name = models.CharField(
        max_length=200,
        verbose_name="Название сессии"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="Описание"
    )
    
    # Параметры обучения
    learning_rate = models.FloatField(
        default=0.001,
        verbose_name="Скорость обучения"
    )
    
    batch_size = models.PositiveIntegerField(
        default=32,
        verbose_name="Размер батча"
    )
    
    num_epochs = models.PositiveIntegerField(
        default=100,
        verbose_name="Количество эпох"
    )
    
    # Данные для обучения
    feedback_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Количество размеченных данных"
    )
    
    # Статус и результаты
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Статус"
    )
    
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Время начала"
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Время завершения"
    )
    
    # Метрики обучения
    initial_loss = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Начальная потеря"
    )
    
    final_loss = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Финальная потеря"
    )
    
    training_history = models.JSONField(
        null=True,
        blank=True,
        verbose_name="История обучения",
        help_text="Метрики по эпохам"
    )
    
    # Результаты
    model_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Путь к сохраненной модели"
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name="Сообщение об ошибке"
    )
    
    # Метаданные
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='dqn_training_sessions',
        verbose_name="Создал"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Время создания"
    )
    
    def __str__(self):
        return f"DQN Training: {self.name} ({self.status})"
    
    @property
    def duration(self):
        """Длительность обучения"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def improvement(self):
        """Улучшение потери"""
        if self.initial_loss and self.final_loss:
            return self.initial_loss - self.final_loss
        return None
    
    class Meta:
        app_label = 'mlmodels'
        verbose_name = "Сессия обучения DQN"
        verbose_name_plural = "Сессии обучения DQN"
        ordering = ['-created_at']
