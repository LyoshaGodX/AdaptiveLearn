"""
Template filters для обработки Markdown в заданиях
"""
import markdown
import bleach
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Разрешенные HTML теги и атрибуты для безопасности
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'b', 'em', 'i', 'u', 'del', 'strike', 's',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 
    'blockquote', 
    'a', 'img',
    'code', 'pre',
    'hr',
    'table', 'thead', 'tbody', 'tr', 'th', 'td'
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target'],
    'img': ['src', 'alt', 'title', 'width', 'height', 'style'],
    'code': ['class'],
    'pre': ['class'],
    'blockquote': ['class'],
    '*': ['class', 'style']
}

@register.filter(name='markdown')
def markdown_filter(text):
    """
    Конвертирует Markdown текст в HTML с расширениями
    """
    if not text:
        return ''
    
    # Настройка Markdown с расширениями
    md = markdown.Markdown(
        extensions=[
            'markdown.extensions.extra',      # Таблицы, footnotes, etc.
            'markdown.extensions.codehilite', # Подсветка кода
            'markdown.extensions.toc',        # Оглавление
            'markdown.extensions.nl2br',      # Переводы строк -> <br>
            'markdown.extensions.sane_lists', # Улучшенные списки
        ],
        extension_configs={
            'markdown.extensions.codehilite': {
                'css_class': 'highlight',
                'use_pygments': False,  # Используем CSS классы вместо inline стилей
            },
            'markdown.extensions.toc': {
                'anchorlink': True,
            }
        }
    )
    
    # Конвертируем Markdown в HTML
    html = md.convert(text)    # Очищаем HTML для безопасности
    clean_html = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )
    
    # Добавляем CSS классы для стилизации
    clean_html = clean_html.replace('<img', '<img class="markdown-img"')
    clean_html = clean_html.replace('<code>', '<code class="markdown-code">')
    clean_html = clean_html.replace('<pre>', '<pre class="markdown-pre">')
    clean_html = clean_html.replace('<blockquote>', '<blockquote class="markdown-blockquote">')
    clean_html = clean_html.replace('<a ', '<a class="markdown-link" ')
    clean_html = clean_html.replace('<table>', '<table class="markdown-table">')
    
    return mark_safe(clean_html)

@register.filter(name='markdown_inline')
def markdown_inline_filter(text):
    """
    Упрощенная версия Markdown для инлайн элементов (варианты ответов)
    Поддерживает только базовое форматирование без блочных элементов
    """
    if not text:
        return ''
    
    # Настройка Markdown только с инлайн элементами
    md = markdown.Markdown(
        extensions=[
            'markdown.extensions.nl2br',      # Переводы строк -> <br>
        ]
    )
    
    # Конвертируем Markdown в HTML
    html = md.convert(text)
    
    # Разрешаем только инлайн теги для ответов
    inline_tags = ['strong', 'b', 'em', 'i', 'u', 'del', 'code', 'a', 'br']
    inline_attributes = {
        'a': ['href', 'title', 'target'],
        'code': ['class'],
    }
    
    # Очищаем HTML для безопасности
    clean_html = bleach.clean(
        html,
        tags=inline_tags,
        attributes=inline_attributes,
        strip=True
    )
    
    # Добавляем CSS классы
    clean_html = clean_html.replace('<code>', '<code class="markdown-code-inline">')
    clean_html = clean_html.replace('<a ', '<a class="markdown-link-inline" ')
    
    return mark_safe(clean_html)
