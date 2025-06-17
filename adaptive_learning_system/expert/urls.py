from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='expert_home'),  # Главная страница теперь показывает DQN
    path('dqn/', views.dqn_management, name='expert_dqn'),  # Дублируем для прямого доступа
    path('bkt/', views.bkt_management, name='expert_bkt'),  # Для будущей реализации
    path('llm/', views.llm_management, name='expert_llm'),  # Для будущей реализации
    path('dqn/student/<int:student_id>/', views.dqn_student_detail, name='expert_dqn_student'),
    path('dqn/feedback/', views.save_expert_feedback, name='expert_save_feedback'),
    path('dqn/dataset/', views.view_feedback_dataset, name='expert_view_dataset'),
]
