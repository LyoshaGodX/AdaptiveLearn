from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Остальные URL-шаблоны проекта
    path('', include('skills.urls')),
]

# Добавляем настройку для обработки URL как с окончающим слешем, так и без него
APPEND_SLASH = False
