from django.contrib import admin
from .models import Task, TaskAnswer

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'task_type', 'difficulty', 'is_active', 'created_at']
    list_filter = ['task_type', 'difficulty', 'is_active', 'courses', 'skills']
    search_fields = ['title', 'question_text']
    filter_horizontal = ['courses', 'skills']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(TaskAnswer)
class TaskAnswerAdmin(admin.ModelAdmin):
    list_display = ['task', 'text', 'is_correct', 'order']
    list_filter = ['is_correct', 'task__task_type']
    search_fields = ['text', 'task__title']
