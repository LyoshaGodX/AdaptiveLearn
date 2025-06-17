from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse


def home_redirect(request):
    """
    Перенаправляет пользователя на соответствующую домашнюю страницу в зависимости от его роли.
    Если пользователь не авторизован, перенаправляет на страницу входа.
    """
    if not request.user.is_authenticated:
        return redirect('login')
    
    user = request.user
    username = user.username.lower()
    
    # Проверяем роль пользователя по группам (приоритет)
    if user.groups.filter(name='methodist').exists() or user.is_superuser:
        return redirect('methodist_skills')
    elif user.groups.filter(name='expert').exists():
        return redirect('expert_home')
    elif user.groups.filter(name='student').exists():
        return redirect('student_home')
    
    # Fallback: проверяем роль по имени пользователя (для совместимости)
    if 'methodist' in username or user.is_superuser:
        return redirect('methodist_skills')
    elif 'expert' in username:
        return redirect('expert_home')
    else:
        # По умолчанию для пользователей без группы или со студенческим именем
        return redirect('student_home')


class RoleBasedLoginView(LoginView):
    """
    Кастомное представление для входа с перенаправлением на страницу соответствующей роли
    """
    def get_success_url(self):
        user = self.request.user
        username = user.username.lower()
        
        # Проверяем роль пользователя по группам (приоритет)
        if user.groups.filter(name='methodist').exists() or user.is_superuser:
            return reverse('methodist_skills')
        elif user.groups.filter(name='expert').exists():
            return reverse('expert_home')
        elif user.groups.filter(name='student').exists():
            return reverse('student_home')
        
        # Fallback: проверяем роль по имени пользователя (для совместимости)
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
