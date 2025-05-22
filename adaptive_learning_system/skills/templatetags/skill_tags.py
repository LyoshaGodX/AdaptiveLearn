from django import template
from django.templatetags.static import static
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def vis_network_debug_script():
    """
    Вставляет тег <script> для загрузки сценария отладки сети Vis.js
    """
    url = static('skills/network_debug_helper.js')
    return mark_safe(f'<script src="{url}"></script>')
