"""
Кастомные фильтры для шаблонов студента
"""
from django import template

register = template.Library()

@register.filter
def mul(value, multiplier):
    """
    Умножает значение на множитель
    Использование: {{ value|mul:100 }}
    """
    try:
        return float(value) * float(multiplier)
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(value):
    """
    Конвертирует значение от 0 до 1 в проценты
    Использование: {{ value|percentage }}
    """
    try:
        return f"{float(value) * 100:.0f}"
    except (ValueError, TypeError):
        return "0"

@register.filter
def mastery_level(value):
    """
    Определяет уровень освоения навыка
    """
    try:
        val = float(value)
        if val >= 0.8:
            return "excellent"
        elif val >= 0.6:
            return "good"
        elif val >= 0.4:
            return "fair"
        else:
            return "poor"
    except (ValueError, TypeError):
        return "poor"

@register.filter
def progress_color(value):
    """
    Определяет цвет прогресс-бара
    """
    try:
        val = float(value)
        if val >= 80:
            return "success"
        elif val >= 50:
            return "primary"
        elif val >= 25:
            return "warning"
        else:
            return "danger"
    except (ValueError, TypeError):
        return "secondary"
