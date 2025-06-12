from django.urls import path
from . import views
from . import views_courses
from . import views_enrollment

urlpatterns = [
    path('', views.skill_graph, name='methodist_skills'),
    path('edit/', views.edit_skills, name='methodist_edit'),
    path('edit_skill/', views.edit_skill, name='methodist_edit_skill'),
    path('delete_skill/', views.delete_skill, name='methodist_delete_skill'),
    path('update_skill_courses/', views.update_skill_courses, name='methodist_update_skill_courses'),
    
    # Управление заданиями
    path('tasks/', views.tasks_list, name='methodist_tasks'),
    path('tasks/create/', views.task_create, name='methodist_task_create'),
    path('tasks/<int:task_id>/edit/', views.task_edit, name='methodist_task_edit'),
    path('tasks/<int:task_id>/delete/', views.task_delete, name='methodist_task_delete'),
    
    # Управление курсами
    path('courses/', views_courses.courses_list, name='methodist_courses'),
    path('courses/create/', views_courses.course_create, name='methodist_course_create'),
    path('courses/<str:course_id>/edit/', views_courses.course_edit, name='methodist_course_edit'),
    path('courses/<str:course_id>/delete/', views_courses.course_delete, name='methodist_course_delete'),
    
    # Управление зачислением
    path('enrollment/', views_enrollment.enrollment_management, name='methodist_enrollment'),
    path('enrollment/enroll/', views_enrollment.enroll_student, name='methodist_enroll_student'),
    path('enrollment/unenroll/', views_enrollment.unenroll_student, name='methodist_unenroll_student'),
    path('enrollment/status/', views_enrollment.update_enrollment_status, name='methodist_update_enrollment_status'),    
    # API маршруты
    path('api/skills/<int:skill_id>/details/', views.api_skill_details, name='methodist_api_skill_details'),
    path('api/skills/<int:skill_id>/courses/', views.api_skill_courses, name='methodist_api_skill_courses'),
    path('api/add_prerequisite/', views.api_add_prerequisite, name='methodist_api_add_prerequisite'),
    path('api/remove_prerequisite/', views.api_remove_prerequisite, name='methodist_api_remove_prerequisite'),
    path('api/remove_dependent/', views.api_remove_dependent, name='methodist_api_remove_dependent'),
    
    # API для курсов
    path('api/skills/', views_courses.api_skills_list, name='methodist_api_skills_list'),
    path('api/tasks/', views_courses.api_tasks_list, name='methodist_api_tasks_list'),
    path('api/course/<str:course_id>/', views_courses.api_course_data, name='methodist_api_course_data'),
    path('api/courses/<str:course_id>/skills/', views_courses.api_course_skills, name='methodist_api_course_skills'),
    path('api/courses/<str:course_id>/tasks/', views_courses.api_course_tasks, name='methodist_api_course_tasks'),
    path('api/update_course_skills/', views_courses.api_update_course_skills, name='methodist_api_update_course_skills'),
    path('api/update_course_tasks/', views_courses.api_update_course_tasks, name='methodist_api_update_course_tasks'),
    
    # API для управления зачислением
    path('api/student/<int:student_id>/enrollments/', views_enrollment.get_student_enrollments, name='methodist_api_student_enrollments'),
    path('api/course/<str:course_id>/enrollments/', views_enrollment.get_course_enrollments, name='methodist_api_course_enrollments'),

    # Тестовые API (без аутентификации)
    path('test/api/skills/', views_courses.test_skills_list, name='test_api_skills_list'),
    path('test/api/tasks/', views_courses.test_tasks_list, name='test_api_tasks_list'),
    
    # Тестовые представления (без аутентификации)
    path('test/courses/create/', views_courses.test_course_create, name='test_course_create'),
    path('test/course/form/', views_courses.test_course_form, name='test_course_form'),
]
