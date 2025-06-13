"""
URL конфигурация для интерфейса оценки студентов
"""

from django.urls import path, include
from mlmodels.views.assessment_views import (
    StudentAssessmentView,
    StudentProgressView,
    SkillProgressView,
    CourseProgressView,
    LearningRecommendationsView,
    BulkStudentAssessmentView,
    ClassAnalyticsView,
    quick_assessment,
    quick_attempt_process,
    quick_progress,
    quick_recommendations
)

app_name = 'assessment'

urlpatterns = [
    # Основные API endpoints
    path('student/<int:student_id>/', StudentAssessmentView.as_view(), name='student_assessment'),
    path('student/<int:student_id>/progress/', StudentProgressView.as_view(), name='student_progress'),
    path('student/<int:student_id>/skill/<int:skill_id>/', SkillProgressView.as_view(), name='skill_progress'),
    path('student/<int:student_id>/course/<int:course_id>/', CourseProgressView.as_view(), name='course_progress'),
    path('student/<int:student_id>/recommendations/', LearningRecommendationsView.as_view(), name='recommendations'),
    
    # Массовые операции
    path('bulk/assess/', BulkStudentAssessmentView.as_view(), name='bulk_assessment'),
    path('analytics/class/', ClassAnalyticsView.as_view(), name='class_analytics'),
    
    # Быстрые функциональные endpoints
    path('quick/assess/<int:student_id>/', quick_assessment, name='quick_assessment'),
    path('quick/attempt/', quick_attempt_process, name='quick_attempt'),
    path('quick/progress/<int:student_id>/', quick_progress, name='quick_progress'),
    path('quick/recommendations/<int:student_id>/', quick_recommendations, name='quick_recommendations'),
]
