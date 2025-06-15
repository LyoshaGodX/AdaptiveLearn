"""
Django management команда для создания студента с попытками решения заданий.

Использование:
    python manage.py create_student_with_attempts
    python manage.py create_student_with_attempts --mastered 15 --partial 10
    python manage.py create_student_with_attempts --recreate
"""

from django.core.management.base import BaseCommand
from mlmodels.tests.create_student_with_attempts import StudentCreatorWithAttempts
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Создает студента с попытками решения заданий для симуляции обучения'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mastered',
            type=int,
            help='Количество полностью освоенных навыков',
            default=12
        )
        parser.add_argument(
            '--partial',
            type=int,
            help='Количество частично освоенных навыков',
            default=8
        )
        parser.add_argument(
            '--recreate',
            action='store_true',
            help='Пересоздать студента если он уже существует',
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            help='Директория для экспорта данных',
            default=None
        )
        parser.add_argument(
            '--seed',
            type=int,
            help='Seed для воспроизводимости результатов',
            default=None
        )

    def handle(self, *args, **options):
        import random
        
        # Устанавливаем seed для воспроизводимости
        if options['seed']:
            random.seed(options['seed'])
            self.stdout.write(f"🎲 Установлен seed: {options['seed']}")
        
        # Проверяем существование студента
        username = "alex_klementev"
        if User.objects.filter(username=username).exists() and not options['recreate']:
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️ Студент {username} уже существует. '
                    'Используйте --recreate для пересоздания.'
                )
            )
            return
        
        creator = StudentCreatorWithAttempts()
        
        try:
            # Настраиваем параметры траектории
            creator.trajectory_builder.target_mastered_count = options['mastered']
            creator.trajectory_builder.target_partial_count = options['partial']
            
            # Создаем студента
            student_profile = creator.create_student()
            
            # Генерируем целевые уровни
            target_mastery = creator.generate_target_mastery_from_trajectory()
            
            # Создаем попытки
            attempts = creator.create_all_task_attempts()
            
            # Анализируем результаты
            analysis = creator.analyze_resulting_mastery()
            
            # Выводим отчет
            creator.print_detailed_report(analysis)
            
            # Экспортируем данные
            creator.export_student_data(analysis, options['output_dir'])
            
            self.stdout.write(
                self.style.SUCCESS(f'\n✨ Студент {student_profile.full_name} успешно создан!')
            )
            self.stdout.write(
                self.style.SUCCESS(f'📊 Создано попыток: {len(attempts)}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'📈 Освоено навыков: {analysis["mastered_count"]} полностью, {analysis["partial_count"]} частично')
            )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка: {e}')
            )
            raise
