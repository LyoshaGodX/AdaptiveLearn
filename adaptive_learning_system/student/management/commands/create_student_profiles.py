from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from student.models import StudentProfile, StudentCourseEnrollment
from skills.models import Course


class Command(BaseCommand):
    help = "Создает профили для существующих студентов и записывает их на курсы"

    def handle(self, *args, **options):
        # Создаем профили для существующих студентов
        students = User.objects.filter(username__icontains='student')
        created_profiles = 0
        
        for user in students:
            profile, created = StudentProfile.objects.get_or_create(
                user=user,
                defaults={
                    'full_name': f"{user.first_name} {user.last_name}".strip() or user.username.title(),
                    'email': user.email or f"{user.username}@example.com",
                    'organization': 'Тестовый университет',
                }
            )
            
            if created:
                created_profiles += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Создан профиль для {user.username}: {profile.full_name}")
                )
            else:
                self.stdout.write(f"Профиль для {user.username} уже существует")
        
        self.stdout.write(
            self.style.SUCCESS(f"Создано {created_profiles} новых профилей студентов")
        )
        
        # Записываем студентов на случайные курсы для демонстрации
        courses = list(Course.objects.all()[:3])  # Берем первые 3 курса
        
        if not courses:
            self.stdout.write(
                self.style.WARNING("Курсы не найдены. Пропускаем запись студентов на курсы.")
            )
            return
        
        enrolled_count = 0
        for profile in StudentProfile.objects.all():
            # Записываем каждого студента на 1-2 курса
            import random
            selected_courses = random.sample(courses, min(2, len(courses)))
            
            for course in selected_courses:
                enrollment, created = StudentCourseEnrollment.objects.get_or_create(
                    student=profile,
                    course=course,
                    defaults={
                        'status': 'in_progress',
                        'progress_percentage': random.randint(10, 80),
                    }
                )
                
                if created:
                    enrolled_count += 1
                    self.stdout.write(
                        f"Записан {profile.full_name} на курс {course.name}"
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f"Создано {enrolled_count} записей на курсы")
        )
