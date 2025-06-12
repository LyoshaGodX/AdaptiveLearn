from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='student_home'),
    path('profile/', views.profile_view, name='student_profile'),
    path('profile/edit/', views.profile_edit, name='student_profile_edit'),
    path('courses/', views.courses_list, name='student_courses'),
    path('courses/enroll/<str:course_id>/', views.course_enroll, name='student_course_enroll'),
    path('courses/detail/<int:enrollment_id>/', views.course_detail, name='student_course_detail'),
]
