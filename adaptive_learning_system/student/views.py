from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .decorators import student_required
from .models import StudentProfile, StudentCourseEnrollment
from skills.models import Course


@login_required
@student_required
def index(request):
    """Главная страница студента"""
    # Получаем или создаем профиль студента
    profile, created = StudentProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'full_name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
            'email': request.user.email or f"{request.user.username}@example.com"
        }
    )
      # Получаем записи на курсы
    enrollments = StudentCourseEnrollment.objects.filter(
        student=profile
    ).select_related('course').order_by('-enrolled_at')
    
    # Рассчитываем средний прогресс
    active_enrollments = enrollments.filter(status__in=['enrolled', 'in_progress'])
    if active_enrollments.exists():
        avg_progress = sum(e.progress_percentage for e in active_enrollments) / active_enrollments.count()
    else:
        avg_progress = 0
    
    context = {
        'profile': profile,
        'enrollments': enrollments,
        'active_enrollments': active_enrollments,
        'completed_enrollments': enrollments.filter(status='completed'),
        'avg_progress': round(avg_progress),
    }
    
    return render(request, 'student/index.html', context)


@login_required
@student_required  
def profile_view(request):
    """Просмотр профиля студента"""
    profile, created = StudentProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'full_name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
            'email': request.user.email or f"{request.user.username}@example.com"
        }
    )
    
    return render(request, 'student/profile.html', {'profile': profile})


@login_required
@student_required
def profile_edit(request):
    """Редактирование профиля студента"""
    profile, created = StudentProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'full_name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
            'email': request.user.email or f"{request.user.username}@example.com"
        }
    )
    
    if request.method == 'POST':
        # Обновляем данные профиля
        profile.full_name = request.POST.get('full_name', profile.full_name)
        profile.email = request.POST.get('email', profile.email)
        profile.organization = request.POST.get('organization', profile.organization)
        
        # Обрабатываем загрузку фото
        if 'profile_photo' in request.FILES:
            profile.profile_photo = request.FILES['profile_photo']
        
        profile.save()
        messages.success(request, 'Профиль успешно обновлен!')
        return redirect('student_profile')
    
    return render(request, 'student/profile_edit.html', {'profile': profile})


@login_required
@student_required
def courses_list(request):
    """Список доступных курсов"""
    profile, created = StudentProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'full_name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
            'email': request.user.email or f"{request.user.username}@example.com"
        }
    )
    
    # Получаем все курсы
    all_courses = Course.objects.all()
    
    # Получаем курсы, на которые уже записан студент
    enrolled_course_ids = StudentCourseEnrollment.objects.filter(
        student=profile
    ).values_list('course_id', flat=True)
    
    # Доступные для записи курсы
    available_courses = all_courses.exclude(id__in=enrolled_course_ids)
    
    # Курсы студента
    my_enrollments = StudentCourseEnrollment.objects.filter(
        student=profile
    ).select_related('course')
    
    context = {
        'available_courses': available_courses,
        'my_enrollments': my_enrollments,
        'profile': profile,
    }
    
    return render(request, 'student/courses.html', context)


@login_required
@student_required
def course_enroll(request, course_id):
    """Запись на курс"""
    profile, created = StudentProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'full_name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
            'email': request.user.email or f"{request.user.username}@example.com"
        }
    )
    
    course = get_object_or_404(Course, id=course_id)
    
    # Проверяем, не записан ли уже студент на этот курс
    existing_enrollment = StudentCourseEnrollment.objects.filter(
        student=profile,
        course=course
    ).first()
    
    if existing_enrollment:
        messages.warning(request, f'Вы уже записаны на курс "{course.name}"')
    else:
        # Создаем новую запись
        StudentCourseEnrollment.objects.create(
            student=profile,
            course=course,
            status='enrolled'
        )
        messages.success(request, f'Вы успешно записались на курс "{course.name}"!')
    
    return redirect('student_courses')


@login_required
@student_required
def course_detail(request, enrollment_id):
    """Детали курса для студента"""
    profile, created = StudentProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'full_name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
            'email': request.user.email or f"{request.user.username}@example.com"
        }
    )
    
    enrollment = get_object_or_404(
        StudentCourseEnrollment,
        id=enrollment_id,
        student=profile
    )
    
    # Получаем навыки курса
    course_skills = enrollment.course.skills.all().order_by('name')
    
    context = {
        'enrollment': enrollment,
        'course_skills': course_skills,
        'profile': profile,
    }
    
    return render(request, 'student/course_detail.html', context)
