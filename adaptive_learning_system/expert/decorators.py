from functools import wraps
from django.http import HttpResponseForbidden


def expert_required(view_func):
    """
    Декоратор, который проверяет, является ли пользователь экспертом.
    Если нет, возвращает страницу с ошибкой 403 Forbidden.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Проверка, что пользователь аутентифицирован
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Вы должны войти в систему.")
        
        # Проверка, что пользователь является экспертом
        username = request.user.username.lower()
        if 'expert' not in username and not request.user.is_superuser:
            return HttpResponseForbidden("Доступ запрещен. Требуются права эксперта.")
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view
