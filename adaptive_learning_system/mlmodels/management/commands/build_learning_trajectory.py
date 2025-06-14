"""
Django management команда для построения траектории обучения студента.

Использование:
    python manage.py build_learning_trajectory
    python manage.py build_learning_trajectory --mastered 15 --partial 10
    python manage.py build_learning_trajectory --export-only
"""

from django.core.management.base import BaseCommand
from mlmodels.tests.learning_trajectory_builder import LearningTrajectoryBuilder


class Command(BaseCommand):
    help = 'Строит траекторию обучения студента на основе графа навыков'

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
            '--export-only',
            action='store_true',
            help='Только экспорт данных без вывода отчета',
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
        
        builder = LearningTrajectoryBuilder()
        
        try:
            builder.initialize()            # Симулируем студента
            mastery, learning_steps = builder.simulate_student_learning(
                target_mastered_count=options['mastered'],
                target_partial_count=options['partial']
            )
            
            if not options['export_only']:
                # Полный отчет
                builder.print_student_report(mastery, learning_steps)
            
            # Экспорт данных
            builder.export_trajectory_data(mastery, learning_steps, options['output_dir'])
            
            self.stdout.write(
                self.style.SUCCESS('\n✨ Траектория обучения построена успешно!')
            )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка: {e}')
            )
            raise
