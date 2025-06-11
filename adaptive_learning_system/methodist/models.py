from django.db import models
from skills.models import Skill, Course


class TaskType(models.TextChoices):
    """Типы заданий"""
    SINGLE_CHOICE = 'single', 'Один вариант ответа'
    MULTIPLE_CHOICE = 'multiple', 'Множественный выбор'
    TRUE_FALSE = 'true_false', 'Верно/Неверно'


class DifficultyLevel(models.TextChoices):
    """Уровни сложности"""
    BEGINNER = 'beginner', 'Начальный'
    INTERMEDIATE = 'intermediate', 'Средний'
    ADVANCED = 'advanced', 'Продвинутый'


class Task(models.Model):
    """Модель задания"""
    title = models.CharField(max_length=255, verbose_name="Название задания")
    task_type = models.CharField(
        max_length=20,
        choices=TaskType.choices,
        default=TaskType.SINGLE_CHOICE,
        verbose_name="Тип задания"
    )
    difficulty = models.CharField(
        max_length=20,
        choices=DifficultyLevel.choices,
        default=DifficultyLevel.BEGINNER,
        verbose_name="Уровень сложности"    )
    question_text = models.TextField(verbose_name="Формулировка задачи")
    correct_answer = models.TextField(verbose_name="Правильный ответ")
    explanation = models.TextField(
        blank=True,
        null=True,
        verbose_name="Объяснение ответа"
    )
    skills = models.ManyToManyField(
        Skill,
        related_name="tasks",
        verbose_name="Связанные навыки"
    )
    courses = models.ManyToManyField(
        Course,
        related_name="tasks",
        verbose_name="Связанные курсы"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    is_active = models.BooleanField(default=True, verbose_name="Активное задание")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Задание"
        verbose_name_plural = "Задания"
        ordering = ["-created_at"]


class TaskAnswer(models.Model):
    """Модель вариантов ответов для заданий с выбором"""
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="Задание"
    )
    text = models.TextField(verbose_name="Текст ответа")
    is_correct = models.BooleanField(default=False, verbose_name="Правильный ответ")
    order = models.IntegerField(default=0, verbose_name="Порядок отображения")

    def __str__(self):
        return f"{self.task.title} - {self.text[:50]}"

    class Meta:
        verbose_name = "Вариант ответа"
        verbose_name_plural = "Варианты ответов"
        ordering = ["order"]
