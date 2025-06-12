from django.db import models
from django.contrib.auth.models import User
from skills.models import Course
from PIL import Image
import os


class StudentProfile(models.Model):
    """
    Профиль студента - расширение стандартной модели User Django
    """
    # Связь один-к-одному с базовой моделью User Django
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name='student_profile',
        verbose_name="Пользователь"
    )
    
    # Дополнительные поля профиля
    full_name = models.CharField(
        max_length=255, 
        verbose_name="ФИО",
        help_text="Полное имя студента"
    )
    
    email = models.EmailField(
        verbose_name="Email",
        help_text="Контактный email студента"
    )
    
    organization = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Организация",
        help_text="Учебное заведение или организация"
    )
    
    profile_photo = models.ImageField(
        upload_to='student_photos/',
        blank=True,
        null=True,
        verbose_name="Фото профиля",
        help_text="Загрузите фото профиля (рекомендуемый размер: 200x200px)"
    )
    
    # Метаинформация
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания профиля"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата последнего обновления"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активный профиль"
    )

    def __str__(self):
        return f"{self.full_name} ({self.user.username})"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Автоматическое изменение размера фото профиля
        if self.profile_photo:
            self.resize_profile_photo()
    
    def resize_profile_photo(self):
        """Изменяет размер фото профиля до 200x200px"""
        if self.profile_photo and os.path.exists(self.profile_photo.path):
            with Image.open(self.profile_photo.path) as img:
                if img.height > 200 or img.width > 200:
                    img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                    img.save(self.profile_photo.path)
    
    @property
    def has_photo(self):
        """Проверяет, есть ли у студента фото профиля"""
        return bool(self.profile_photo)
    
    class Meta:
        verbose_name = "Профиль студента"
        verbose_name_plural = "Профили студентов"
        ordering = ['full_name']


class StudentCourseEnrollment(models.Model):
    """
    Модель для записи студентов на курсы
    """
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='course_enrollments',
        verbose_name="Студент"
    )
    
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='student_enrollments',
        verbose_name="Курс"
    )
    
    # Дата записи на курс
    enrolled_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата записи на курс"
    )
    
    # Статус обучения
    STATUS_CHOICES = [
        ('enrolled', 'Записан'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершен'),
        ('suspended', 'Приостановлен'),
        ('dropped', 'Отчислен'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='enrolled',
        verbose_name="Статус обучения"
    )
    
    # Прогресс по курсу (в процентах)
    progress_percentage = models.PositiveIntegerField(
        default=0,
        verbose_name="Прогресс (%)",
        help_text="Процент выполнения курса (0-100)"
    )
    
    # Дата завершения курса
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Дата завершения курса"
    )
    
    # Итоговая оценка
    final_grade = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Итоговая оценка",
        help_text="Оценка по курсу (например, 4.75)"
    )
    
    # Комментарии преподавателя
    instructor_notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Комментарии преподавателя"
    )

    def __str__(self):
        return f"{self.student.full_name} - {self.course.name} ({self.get_status_display()})"
    
    @property
    def is_active(self):
        """Проверяет, активна ли запись на курс"""
        return self.status in ['enrolled', 'in_progress']
    
    @property
    def is_completed(self):
        """Проверяет, завершен ли курс"""
        return self.status == 'completed'
    
    def mark_completed(self, grade=None):
        """Отмечает курс как завершенный"""
        self.status = 'completed'
        self.progress_percentage = 100
        self.completed_at = models.timezone.now()
        if grade:
            self.final_grade = grade
        self.save()
    
    class Meta:
        verbose_name = "Запись на курс"
        verbose_name_plural = "Записи на курсы"
        unique_together = ['student', 'course']  # Один студент может быть записан на курс только один раз
        ordering = ['-enrolled_at']


# Сигналы для автоматического создания профиля студента
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_student_profile(sender, instance, created, **kwargs):
    """
    Автоматически создает профиль студента при создании нового пользователя,
    если имя пользователя содержит 'student'
    """
    if created and 'student' in instance.username.lower():
        StudentProfile.objects.create(
            user=instance,
            full_name=f"{instance.first_name} {instance.last_name}".strip() or instance.username,
            email=instance.email or f"{instance.username}@example.com"
        )

@receiver(post_save, sender=User)
def save_student_profile(sender, instance, **kwargs):
    """
    Сохраняет профиль студента при сохранении пользователя
    """
    if hasattr(instance, 'student_profile'):
        instance.student_profile.save()
