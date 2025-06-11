from django.urls import path
from . import views

urlpatterns = [
    path('', views.skills_list, name='skills_list'),
    path('edit/', views.skills_edit, name='skills_edit'),
    path('edit_skill/', views.edit_skill, name='edit_skill'),
    path('delete_skill/', views.delete_skill, name='delete_skill'),
    path('update_skill_courses/', views.update_skill_courses, name='update_skill_courses'),
    
    # API маршруты - заменяем импорт api_views на обычный импорт views
    path('api/skills/<int:skill_id>/courses/', views.api_skill_courses, name='api_skill_courses'),
    path('api/skills/<int:skill_id>/details/', views.api_skill_details, name='api_skill_details'),    path('api/add_prerequisite/', views.api_add_prerequisite, name='api_add_prerequisite'),
    path('api/remove_prerequisite/', views.api_remove_prerequisite, name='api_remove_prerequisite'),
    path('api/remove_dependent/', views.api_remove_dependent, name='api_remove_dependent'),
]
