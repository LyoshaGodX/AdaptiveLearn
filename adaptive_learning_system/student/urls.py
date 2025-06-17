from django.urls import path
from . import views

urlpatterns = [
    path('', views.profile_view, name='student_home'),
    path('profile/', views.profile_view, name='student_profile'),
    path('learning/', views.learning_task_view, name='student_learning'),
    path('learning/<int:task_id>/', views.learning_task_view, name='student_learning_task'),
    path('profile/edit/', views.profile_edit, name='student_profile_edit'),
    path('courses/', views.courses, name='student_courses'),
    path('courses/enroll/<str:course_id>/', views.enroll_course, name='student_course_enroll'),
    path('courses/detail/<str:course_id>/', views.course_detail, name='student_course_detail'),
    path('api/profile/', views.get_profile_api, name='student_profile_api'),
    path('api/recommendation/status/', views.check_recommendation_status, name='check_recommendation_status'),
    path('api/new-task/', views.get_new_task, name='get_new_task'),
]
