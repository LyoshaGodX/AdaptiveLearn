"""
URL конфигурация для ML Models API
"""

from django.urls import path
from . import views

app_name = 'mlmodels'

urlpatterns = [
    # Основные API endpoints для работы с BKT моделью
    path('api/student/<int:student_id>/profile/', views.get_student_profile, name='student_profile'),
    path('api/student/<int:student_id>/attempts/', views.get_student_attempts, name='student_attempts'),
    path('api/student/<int:student_id>/masteries/', views.get_student_masteries, name='student_masteries'),
    path('api/progress/update/', views.update_student_progress, name='update_progress'),
]
