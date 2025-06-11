from django import template
from django.templatetags.static import static
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def vis_network_debug_script():
    """
    Вставляет тег <script> для загрузки сценария отладки сети Vis.js
    """
    url = static('methodist/network_debug_helper.js')
    return mark_safe(f'<script src="{url}"></script>')

@register.simple_tag(takes_context=True)
def get_user_role(context):
    """
    Определяет роль пользователя на основе его имени пользователя.
    Возвращает: 'student', 'expert', 'methodist' или 'anonymous'
    """
    user = context['user']
    if not user.is_authenticated:
        return 'anonymous'
    
    username = user.username.lower()
    if 'student' in username:
        return 'student'
    elif 'expert' in username:
        return 'expert'
    elif 'methodist' in username:
        return 'methodist'
    else:
        return 'student'  # По умолчанию роль - студент
