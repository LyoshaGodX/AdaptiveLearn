from django.db import models

class Course(models.Model):
    """Модель курса"""
    id = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=255, verbose_name="Название курса")
    description = models.TextField(verbose_name="Описание")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Курс"
        verbose_name_plural = "Курсы"

class Skill(models.Model):
    """Модель навыка"""
    name = models.CharField(max_length=255, unique=True, verbose_name="Название навыка")
    description = models.TextField(blank=True, null=True, verbose_name="Описание навыка")
    is_base = models.BooleanField(default=False, verbose_name="Базовый навык")
    courses = models.ManyToManyField(Course, related_name="skills", verbose_name="Связанные курсы")
    prerequisites = models.ManyToManyField("self", symmetrical=False, blank=True, verbose_name="Необходимые навыки", related_name="dependent_skills")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Навык"
        verbose_name_plural = "Навыки"
        ordering = ["name"]
