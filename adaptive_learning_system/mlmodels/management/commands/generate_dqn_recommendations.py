"""
Django команда для генерации DQN рекомендаций для студентов
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction

from mlmodels.models import DQNRecommendation, StudentCurrentRecommendation
from student.models import StudentProfile
from mlmodels.dqn.recommendation_manager_fixed import recommendation_manager_fixed as recommendation_manager


class Command(BaseCommand):
    help = 'Генерирует DQN рекомендации для студентов'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--student-id',
            type=int,
            help='ID конкретного студента для генерации рекомендации'
        )
        
        parser.add_argument(
            '--all',
            action='store_true',
            help='Генерировать рекомендации для всех студентов'
        )
    
    def handle(self, *args, **options):
        verbosity = options.get('verbosity', 1)
        
        if options.get('student_id'):
            self.generate_for_student(options['student_id'], verbosity)
        elif options.get('all'):
            self.generate_for_all_students(verbosity)
        else:
            raise CommandError('Укажите --student-id ID или --all для всех студентов')
    
    def generate_for_student(self, student_id, verbosity):
        """Генерирует рекомендацию для конкретного студента"""
        try:
            student = StudentProfile.objects.get(id=student_id)
            if verbosity >= 1:
                self.stdout.write(f'Генерируем рекомендацию для студента: {student.full_name}')
              # Генерируем рекомендацию через менеджер
            recommendation_result = recommendation_manager.generate_and_save_recommendation(
                student_id=student.user.id,  # ID пользователя, а не StudentProfile
                set_as_current=True
            )            
            if recommendation_result and recommendation_result.recommendation:
                recommendation = recommendation_result.recommendation
                # Сохраняем как текущую рекомендацию
                with transaction.atomic():
                    # Удаляем старую текущую рекомендацию
                    StudentCurrentRecommendation.objects.filter(student=student).delete()
                    
                    # Создаем новую
                    StudentCurrentRecommendation.objects.create(
                        student=student,
                        recommendation=recommendation
                    )
                
                if verbosity >= 1:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Рекомендация успешно создана: {recommendation.task.title} '
                            f'(уверенность: {recommendation.confidence:.2%})'
                        )
                    )
            else:
                if verbosity >= 1:
                    self.stdout.write(
                        self.style.WARNING(f'Не удалось создать рекомендацию для студента {student.full_name}')
                    )
                
        except StudentProfile.DoesNotExist:
            raise CommandError(f'Студент с ID {student_id} не найден')
        except Exception as e:
            if verbosity >= 1:
                self.stdout.write(
                    self.style.ERROR(f'Ошибка при генерации рекомендации: {str(e)}')
                )
    
    def generate_for_all_students(self, verbosity):
        """Генерирует рекомендации для всех студентов"""
        students = StudentProfile.objects.all()
        
        if verbosity >= 1:
            self.stdout.write(f'Найдено студентов: {students.count()}')
        
        success_count = 0
        error_count = 0
        
        for student in students:
            try:
                if verbosity >= 2:
                    self.stdout.write(f'Обрабатываем студента: {student.full_name}')
                
                recommendation_result = recommendation_manager.generate_and_save_recommendation(
                    student_id=student.user.id,
                    set_as_current=True
                )
                
                if recommendation_result and recommendation_result.recommendation:
                    recommendation = recommendation_result.recommendation
                    with transaction.atomic():
                        StudentCurrentRecommendation.objects.filter(student=student).delete()
                        StudentCurrentRecommendation.objects.create(
                            student=student,
                            recommendation=recommendation
                        )
                    success_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                error_count += 1
                if verbosity >= 2:
                    self.stdout.write(
                        self.style.ERROR(f'Ошибка для студента {student.full_name}: {str(e)}')
                    )
        
        if verbosity >= 1:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Генерация завершена. Успешно: {success_count}, Ошибок: {error_count}'
                )
            )
