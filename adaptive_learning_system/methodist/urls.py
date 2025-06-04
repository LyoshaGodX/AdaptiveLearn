from django.urls import path
from . import views

urlpatterns = [
    path('', views.skill_graph, name='methodist_skills'),
    path('edit/', views.edit_skills, name='methodist_edit'),
]
