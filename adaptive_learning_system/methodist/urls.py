from django.urls import path
from . import views

urlpatterns = [
    path('', views.skill_graph, name='methodist_skills'),    path('edit/', views.edit_skills, name='methodist_edit'),
    path('edit_skill/', views.edit_skill, name='methodist_edit_skill'),
    path('delete_skill/', views.delete_skill, name='methodist_delete_skill'),
    path('update_skill_courses/', views.update_skill_courses, name='methodist_update_skill_courses'),
    
    # Управление заданиями
    path('tasks/', views.tasks_list, name='methodist_tasks'),
    path('tasks/create/', views.task_create, name='methodist_task_create'),
    path('tasks/<int:task_id>/edit/', views.task_edit, name='methodist_task_edit'),
    path('tasks/<int:task_id>/delete/', views.task_delete, name='methodist_task_delete'),
    
    # API маршруты
    path('api/skills/<int:skill_id>/details/', views.api_skill_details, name='methodist_api_skill_details'),
    path('api/skills/<int:skill_id>/courses/', views.api_skill_courses, name='methodist_api_skill_courses'),    path('api/add_prerequisite/', views.api_add_prerequisite, name='methodist_api_add_prerequisite'),
    path('api/remove_prerequisite/', views.api_remove_prerequisite, name='methodist_api_remove_prerequisite'),
    path('api/remove_dependent/', views.api_remove_dependent, name='methodist_api_remove_dependent'),
]
