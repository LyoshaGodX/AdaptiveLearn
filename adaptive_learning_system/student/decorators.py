from functools import wraps
from django.http import HttpResponseForbidden


def student_required(view_func):
    """
    Декоратор, который проверяет, является ли пользователь студентом.
    Поскольку это базовая роль, только проверяет аутентификацию.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Проверка, что пользователь аутентифицирован
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Вы должны войти в систему.")
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view
