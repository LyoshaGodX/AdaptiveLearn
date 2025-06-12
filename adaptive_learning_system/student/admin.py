from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import StudentProfile, StudentCourseEnrollment


class StudentProfileInline(admin.StackedInline):
    """
    Inline для отображения профиля студента в админке пользователя
    """
    model = StudentProfile
    can_delete = False
    verbose_name_plural = 'Профиль студента'
    fields = ('full_name', 'email', 'organization', 'profile_photo', 'is_active')


class UserAdmin(BaseUserAdmin):
    """
    Расширенная админка пользователя с профилем студента
    """
    inlines = (StudentProfileInline,)
    
    def get_inline_instances(self, request, obj=None):
        """
        Показываем inline профиля только для студентов
        """
        if obj and 'student' in obj.username.lower():
            return super().get_inline_instances(request, obj)
        return []


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    """
    Админка для профилей студентов
    """
    list_display = ('full_name', 'user_username', 'email', 'organization', 'is_active', 'created_at')
    list_filter = ('is_active', 'organization', 'created_at')
    search_fields = ('full_name', 'user__username', 'email', 'organization')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'full_name', 'email')
        }),
        ('Дополнительная информация', {
            'fields': ('organization', 'profile_photo')
        }),
        ('Статус', {
            'fields': ('is_active',)
        }),
        ('Метаинформация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_username(self, obj):
        """Отображает имя пользователя"""
        return obj.user.username
    user_username.short_description = 'Имя пользователя'
    user_username.admin_order_field = 'user__username'


@admin.register(StudentCourseEnrollment)
class StudentCourseEnrollmentAdmin(admin.ModelAdmin):
    """
    Админка для записей студентов на курсы
    """
    list_display = ('student_name', 'course_name', 'status', 'progress_percentage', 'enrolled_at', 'completed_at')
    list_filter = ('status', 'course', 'enrolled_at', 'completed_at')
    search_fields = ('student__full_name', 'student__user__username', 'course__name')
    readonly_fields = ('enrolled_at',)
    fieldsets = (
        ('Основная информация', {
            'fields': ('student', 'course', 'status')
        }),
        ('Прогресс', {
            'fields': ('progress_percentage', 'final_grade')
        }),
        ('Даты', {
            'fields': ('enrolled_at', 'completed_at')
        }),
        ('Дополнительно', {
            'fields': ('instructor_notes',),
            'classes': ('collapse',)
        }),
    )
    
    def student_name(self, obj):
        """Отображает имя студента"""
        return obj.student.full_name
    student_name.short_description = 'Студент'
    student_name.admin_order_field = 'student__full_name'
    
    def course_name(self, obj):
        """Отображает название курса"""
        return obj.course.name
    course_name.short_description = 'Курс'
    course_name.admin_order_field = 'course__name'


# Перерегистрируем User с новой админкой
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
