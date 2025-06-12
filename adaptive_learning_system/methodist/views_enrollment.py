from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q, Count
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .decorators import methodist_required
from skills.models import Course
from student.models import StudentProfile, StudentCourseEnrollment
import json


@login_required
@methodist_required
def enrollment_management(request):
    """
    Страница управления зачислением студентов на курсы
    """
    # Получаем всех студентов с их профилями
    students = StudentProfile.objects.select_related('user').filter(
        is_active=True
    ).order_by('full_name')
    
    # Получаем все курсы
    courses = Course.objects.annotate(
        enrolled_count=Count('student_enrollments')
    ).order_by('name')
    
    # Фильтры для поиска
    student_search = request.GET.get('student_search', '')
    course_search = request.GET.get('course_search', '')
    
    if student_search:
        students = students.filter(
            Q(full_name__icontains=student_search) |
            Q(user__username__icontains=student_search) |
            Q(email__icontains=student_search)
        )
    
    if course_search:
        courses = courses.filter(
            Q(name__icontains=course_search) |
            Q(description__icontains=course_search)
        )
    
    # Получаем все записи на курсы для отображения
    all_enrollments = StudentCourseEnrollment.objects.select_related(
        'student__user', 'course'
    ).order_by('-enrolled_at')
    
    # Статистика
    total_students = StudentProfile.objects.filter(is_active=True).count()
    total_courses = Course.objects.count()
    total_enrollments = StudentCourseEnrollment.objects.count()
    active_enrollments = StudentCourseEnrollment.objects.filter(
        status__in=['enrolled', 'in_progress']
    ).count()
    
    context = {
        'students': students,
        'courses': courses,
        'all_enrollments': all_enrollments[:20],  # Показываем последние 20 записей
        'student_search': student_search,
        'course_search': course_search,
        'stats': {
            'total_students': total_students,
            'total_courses': total_courses,
            'total_enrollments': total_enrollments,
            'active_enrollments': active_enrollments,
        }
    }
    
    return render(request, 'methodist/enrollment_management.html', context)


@require_POST
@login_required
@methodist_required
def enroll_student(request):
    """
    API для записи студента на курс
    """
    try:
        student_id = request.POST.get('student_id')
        course_id = request.POST.get('course_id')
        
        if not student_id or not course_id:
            return JsonResponse({
                'success': False,
                'error': 'Не указан студент или курс'
            }, status=400)
        
        # Получаем студента и курс
        student = get_object_or_404(StudentProfile, id=student_id)
        course = get_object_or_404(Course, id=course_id)
        
        # Проверяем, не записан ли уже студент на этот курс
        existing_enrollment = StudentCourseEnrollment.objects.filter(
            student=student,
            course=course
        ).first()
        
        if existing_enrollment:
            return JsonResponse({
                'success': False,
                'error': f'Студент {student.full_name} уже записан на курс "{course.name}"'
            })
        
        # Создаем новую запись
        enrollment = StudentCourseEnrollment.objects.create(
            student=student,
            course=course,
            status='enrolled'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Студент {student.full_name} успешно записан на курс "{course.name}"',
            'enrollment': {
                'id': enrollment.id,
                'student_name': student.full_name,
                'course_name': course.name,
                'enrolled_at': enrollment.enrolled_at.strftime('%d.%m.%Y %H:%M'),
                'status': enrollment.get_status_display()
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при записи студента: {str(e)}'
        }, status=500)


@require_POST
@login_required
@methodist_required
def unenroll_student(request):
    """
    API для отчисления студента с курса
    """
    try:
        enrollment_id = request.POST.get('enrollment_id')
        
        if not enrollment_id:
            return JsonResponse({
                'success': False,
                'error': 'Не указана запись на курс'
            }, status=400)
        
        # Получаем запись на курс
        enrollment = get_object_or_404(StudentCourseEnrollment, id=enrollment_id)
        
        student_name = enrollment.student.full_name
        course_name = enrollment.course.name
        
        # Удаляем запись
        enrollment.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Студент {student_name} отчислен с курса "{course_name}"'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при отчислении студента: {str(e)}'
        }, status=500)


@login_required
@methodist_required
def get_student_enrollments(request, student_id):
    """
    API для получения курсов студента
    """
    try:
        student = get_object_or_404(StudentProfile, id=student_id)
        
        enrollments = StudentCourseEnrollment.objects.filter(
            student=student
        ).select_related('course').order_by('-enrolled_at')
        
        enrollments_data = []
        for enrollment in enrollments:
            enrollments_data.append({
                'id': enrollment.id,
                'course_id': enrollment.course.id,
                'course_name': enrollment.course.name,
                'status': enrollment.get_status_display(),
                'progress': enrollment.progress_percentage,
                'enrolled_at': enrollment.enrolled_at.strftime('%d.%m.%Y'),
            })
        
        return JsonResponse({
            'success': True,
            'student_name': student.full_name,
            'enrollments': enrollments_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@methodist_required
def get_course_enrollments(request, course_id):
    """
    API для получения студентов курса
    """
    try:
        course = get_object_or_404(Course, id=course_id)
        
        enrollments = StudentCourseEnrollment.objects.filter(
            course=course
        ).select_related('student__user').order_by('-enrolled_at')
        
        enrollments_data = []
        for enrollment in enrollments:
            enrollments_data.append({
                'id': enrollment.id,
                'student_id': enrollment.student.id,
                'student_name': enrollment.student.full_name,
                'student_username': enrollment.student.user.username,
                'status': enrollment.get_status_display(),
                'progress': enrollment.progress_percentage,
                'enrolled_at': enrollment.enrolled_at.strftime('%d.%m.%Y'),
            })
        
        return JsonResponse({
            'success': True,
            'course_name': course.name,
            'enrollments': enrollments_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@methodist_required
def update_enrollment_status(request):
    """
    API для обновления статуса записи на курс
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Метод не поддерживается'})
    
    try:
        enrollment_id = request.POST.get('enrollment_id')
        new_status = request.POST.get('status')
        
        if not enrollment_id or not new_status:
            return JsonResponse({
                'success': False,
                'error': 'Не указана запись или новый статус'
            })
        
        enrollment = get_object_or_404(StudentCourseEnrollment, id=enrollment_id)
        
        # Проверяем валидность статуса
        valid_statuses = dict(StudentCourseEnrollment.STATUS_CHOICES).keys()
        if new_status not in valid_statuses:
            return JsonResponse({
                'success': False,
                'error': 'Недопустимый статус'
            })
        
        old_status = enrollment.get_status_display()
        enrollment.status = new_status
        enrollment.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Статус изменен с "{old_status}" на "{enrollment.get_status_display()}"'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при обновлении статуса: {str(e)}'
        }, status=500)
