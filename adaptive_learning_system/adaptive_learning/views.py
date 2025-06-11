from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse


def home_redirect(request):
    """
    Перенаправляет пользователя на соответствующую домашнюю страницу в зависимости от его статуса аутентификации.
    Если пользователь авторизован, перенаправляет на страницу студента.
    Если пользователь не авторизован, перенаправляет на страницу входа.
    """
    if request.user.is_authenticated:
        return redirect('student_home')
    else:
        return redirect('login')


class RoleBasedLoginView(LoginView):
    """
    Кастомное представление для входа с перенаправлением на страницу соответствующей роли
    """
    def get_success_url(self):
        user = self.request.user
        username = user.username.lower()
        
        # Проверяем роль по имени пользователя (как это делают декораторы)
        if 'methodist' in username or user.is_superuser:
            return reverse('methodist_skills')
        elif 'expert' in username:
            return reverse('expert_home')
        else:
            # По умолчанию для студентов или пользователей без специальной роли
            return reverse('student_home')


class CustomLogoutView(LogoutView):
    """
    Кастомное представление для выхода, которое принимает GET запросы
    """
    http_method_names = ['get', 'post', 'options']
    
    def get(self, request, *args, **kwargs):
        """Обрабатываем GET запрос как POST для совместимости со ссылками"""
        return self.post(request, *args, **kwargs)
