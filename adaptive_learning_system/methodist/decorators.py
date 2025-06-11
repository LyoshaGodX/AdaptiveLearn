from functools import wraps
from django.http import HttpResponseForbidden


def methodist_required(view_func):
    """
    Декоратор, который проверяет, является ли пользователь методистом.
    Если нет, возвращает страницу с ошибкой 403 Forbidden.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Проверка, что пользователь аутентифицирован
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Вы должны войти в систему.")
        
        # Проверка, что пользователь является методистом
        username = request.user.username.lower()
        if 'methodist' not in username and not request.user.is_superuser:
            return HttpResponseForbidden("Доступ запрещен. Требуются права методиста.")
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view
