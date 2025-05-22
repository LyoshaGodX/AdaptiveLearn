from django.contrib import admin
from .models import Course, Skill

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name', 'description']

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_base']
    list_filter = ['is_base', 'courses']
    search_fields = ['name', 'description']
    filter_horizontal = ['courses', 'prerequisites']
