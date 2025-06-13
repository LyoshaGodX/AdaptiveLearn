"""
URL configuration for adaptive_learning project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from methodist import views as methodist_views
from . import views as core_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("methodist/", include('methodist.urls')),
    path("student/", include('student.urls')),
    path("expert/", include('expert.urls')),
    path("skills/", include('skills.urls')),
    path("mlmodels/", include('mlmodels.urls')),
    path("", core_views.home_redirect, name='home'),
    path("login/", core_views.RoleBasedLoginView.as_view(), name='login'),
    path("logout/", core_views.CustomLogoutView.as_view(), name='logout'),
    path("edit/", methodist_views.edit_skills, name='edit_skills'),
]

# Добавляем обработку статических файлов в режиме отладки
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
