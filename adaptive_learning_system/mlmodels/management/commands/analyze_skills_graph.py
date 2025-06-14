"""
Django management команда для запуска анализа графа навыков.

Использование:
    python manage.py analyze_skills_graph
"""

from django.core.management.base import BaseCommand
from mlmodels.tests.parse_skills_graph import SkillsGraphParser


class Command(BaseCommand):
    help = 'Анализирует граф навыков и выводит статистику'

    def add_arguments(self, parser):
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
            '--target-skill',
            type=int,
            help='ID навыка для построения пути изучения',
            default=None
        )

    def handle(self, *args, **options):
        parser = SkillsGraphParser()
        
        try:
            if options['export_only']:
                # Только экспорт
                parser.parse_skills_graph()
                parser.parse_task_skills_mapping()
                parser.export_graph_data(options['output_dir'])
                self.stdout.write(
                    self.style.SUCCESS('✅ Данные графа навыков экспортированы')
                )
            else:
                # Полный анализ
                parser.print_analysis_report()
                parser.export_graph_data(options['output_dir'])
                
                # Путь изучения для конкретного навыка
                if options['target_skill']:
                    path = parser.get_skill_learning_path(options['target_skill'])
                    self.stdout.write(f"\n🎯 Путь изучения для навыка {options['target_skill']}:")
                    for i, skill_id in enumerate(path, 1):
                        skill_name = parser.skill_info[skill_id].name
                        self.stdout.write(f"  {i}. {skill_name} (ID: {skill_id})")
                
                self.stdout.write(
                    self.style.SUCCESS('\n✨ Анализ графа навыков завершен')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка: {e}')
            )
            raise
