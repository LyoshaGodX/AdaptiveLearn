"""
Django команда для управления экспертной обратной связью DQN

Позволяет экспертам:
- Просматривать историю рекомендаций студентов
- Добавлять обратную связь (положительную/отрицательную)
- Запускать обучение модели на основе обратной связи
- Просматривать статистику и историю обучения
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import datetime, timedelta

from mlmodels.dqn.recommendation_manager_fixed import recommendation_manager_fixed as recommendation_manager
from mlmodels.dqn.expert_feedback_manager import expert_feedback_manager
from mlmodels.models import DQNRecommendation, ExpertFeedback
from student.models import StudentProfile


class Command(BaseCommand):
    help = 'Интерфейс эксперта для работы с DQN обратной связью'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['history', 'feedback', 'train', 'stats'],
            help='Действие: history (история), feedback (обратная связь), train (обучение), stats (статистика)'
        )
        
        parser.add_argument(
            '--student',
            type=int,
            help='ID студента для просмотра истории'
        )
        
        parser.add_argument(
            '--recommendation',
            type=int,
            help='ID рекомендации для добавления обратной связи'
        )
        
        parser.add_argument(
            '--expert',
            type=int,
            default=1,
            help='ID эксперта (по умолчанию 1)'
        )
        
        parser.add_argument(
            '--feedback-type',
            choices=['positive', 'negative'],
            help='Тип обратной связи'
        )
        
        parser.add_argument(
            '--strength',
            choices=['low', 'medium', 'strong'],
            default='medium',
            help='Сила подкрепления (по умолчанию medium)'
        )
        
        parser.add_argument(
            '--comment',
            type=str,
            default='',
            help='Комментарий к обратной связи'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Лимит записей для вывода (по умолчанию 20)'
        )
        
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Количество дней для статистики (по умолчанию 30)'
        )
    
    def handle(self, *args, **options):
        action = options['action']
        
        try:
            if action == 'history':
                self._show_recommendation_history(options)
            elif action == 'feedback':
                self._add_expert_feedback(options)
            elif action == 'train':
                self._train_model(options)
            elif action == 'stats':
                self._show_statistics(options)
            
        except Exception as e:
            raise CommandError(f'Ошибка выполнения команды: {e}')
    
    def _show_recommendation_history(self, options):
        """Показывает историю рекомендаций"""
        student_id = options.get('student')
        limit = options.get('limit', 20)
        
        if not student_id:
            # Показываем общую статистику по всем студентам
            self.stdout.write(
                self.style.SUCCESS('📚 ОБЩАЯ ИСТОРИЯ РЕКОМЕНДАЦИЙ')
            )
            self.stdout.write('=' * 60)
            
            # Получаем последние рекомендации
            recommendations = DQNRecommendation.objects.select_related(
                'student', 'task'
            ).prefetch_related(
                'expertfeedback_set'            ).order_by('-created_at')[:limit]
            
            for i, rec in enumerate(recommendations, 1):
                feedback = rec.expertfeedback_set.first()
                feedback_info = ""
                
                if feedback:
                    feedback_type = "✅" if feedback.feedback_type == 'positive' else "❌"
                    feedback_info = f" | {feedback_type} {feedback.strength} ({feedback.reward_value:+.1f})"
                
                self.stdout.write(
                    f"{i:2d}. Студент {rec.student.id} | "
                    f"Задание {rec.task.id} | "
                    f"Q={rec.q_value:.3f} | "
                    f"{rec.created_at.strftime('%Y-%m-%d %H:%M')}"
                    f"{feedback_info}"
                )
            
        else:
            # Показываем историю конкретного студента
            try:
                student = StudentProfile.objects.get(id=student_id)
            except StudentProfile.DoesNotExist:
                raise CommandError(f'Студент с ID {student_id} не найден')
            
            self.stdout.write(
                self.style.SUCCESS(f'📚 ИСТОРИЯ РЕКОМЕНДАЦИЙ ДЛЯ СТУДЕНТА {student_id}')
            )
            self.stdout.write('=' * 60)
            
            history = recommendation_manager.get_recommendation_history(
                student_id, limit=limit
            )
            
            if not history:
                self.stdout.write(
                    self.style.WARNING('Нет истории рекомендаций для данного студента')
                )
                return
            
            for i, rec in enumerate(history, 1):
                attempts_info = ""
                if rec['has_attempts']:
                    attempts_info = f" | Попыток: {len(rec['attempts'])}, Успех: {rec['success_rate']:.1%}"
                
                self.stdout.write(
                    f"{i:2d}. [{rec['id']}] {rec['task_title']} | "
                    f"Q={rec['q_value']:.3f} | "
                    f"{rec['difficulty']} | "
                    f"{rec['created_at'].strftime('%Y-%m-%d %H:%M')}"
                    f"{attempts_info}"
                )
                
                # Показываем обратную связь если есть
                try:
                    feedback = ExpertFeedback.objects.get(recommendation_id=rec['id'])
                    feedback_type = "✅ Положительная" if feedback.feedback_type == 'positive' else "❌ Отрицательная"
                    self.stdout.write(
                        f"    💬 {feedback_type} ({feedback.strength}) = {feedback.reward_value:+.1f}"
                    )
                    if feedback.comment:
                        self.stdout.write(f"    📝 {feedback.comment}")
                except ExpertFeedback.DoesNotExist:
                    self.stdout.write("    ⚪ Нет экспертной обратной связи")
    
    def _add_expert_feedback(self, options):
        """Добавляет экспертную обратную связь"""
        recommendation_id = options.get('recommendation')
        expert_id = options.get('expert')
        feedback_type = options.get('feedback_type')
        strength = options.get('strength')
        comment = options.get('comment', '')
        
        if not recommendation_id:
            raise CommandError('Необходимо указать --recommendation')
        
        if not feedback_type:
            raise CommandError('Необходимо указать --feedback-type (positive/negative)')
        
        # Проверяем существование рекомендации
        try:
            recommendation = DQNRecommendation.objects.select_related(
                'student', 'task'
            ).get(id=recommendation_id)
        except DQNRecommendation.DoesNotExist:
            raise CommandError(f'Рекомендация с ID {recommendation_id} не найдена')
        
        # Показываем информацию о рекомендации
        self.stdout.write(
            self.style.SUCCESS(f'💬 ДОБАВЛЕНИЕ ОБРАТНОЙ СВЯЗИ')
        )
        self.stdout.write('=' * 60)
        self.stdout.write(f"Рекомендация: {recommendation.id}")
        self.stdout.write(f"Студент: {recommendation.student.id}")
        self.stdout.write(f"Задание: {recommendation.task.title}")
        self.stdout.write(f"Q-value: {recommendation.q_value:.4f}")
        self.stdout.write(f"Дата: {recommendation.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        self.stdout.write('-' * 60)
        
        # Добавляем обратную связь
        success = expert_feedback_manager.add_feedback(
            recommendation_id=recommendation_id,
            expert_id=expert_id,
            feedback_type=feedback_type,
            strength=strength,
            comment=comment
        )
        
        if success:
            reward = expert_feedback_manager.REWARD_MAPPING[strength][feedback_type]
            feedback_emoji = "✅" if feedback_type == 'positive' else "❌"
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'{feedback_emoji} Обратная связь добавлена: {feedback_type} ({strength}) = {reward:+.1f}'
                )
            )
            if comment:
                self.stdout.write(f"📝 Комментарий: {comment}")
        else:
            self.stdout.write(
                self.style.ERROR('❌ Не удалось добавить обратную связь')
            )
    
    def _train_model(self, options):
        """Запускает обучение модели"""
        self.stdout.write(
            self.style.SUCCESS('🚀 ОБУЧЕНИЕ МОДЕЛИ DQN НА ЭКСПЕРТНОЙ ОБРАТНОЙ СВЯЗИ')
        )
        self.stdout.write('=' * 60)
        
        # Подготавливаем данные
        self.stdout.write("📚 Подготовка обучающих данных...")
        training_data = expert_feedback_manager.prepare_training_data(min_feedback_count=3)
        
        if not training_data:
            self.stdout.write(
                self.style.WARNING('⚠️ Недостаточно данных для обучения (минимум 3 записи с обратной связью)')
            )
            return
        
        self.stdout.write(f"✅ Подготовлено {len(training_data)} обучающих примеров")
        
        # Показываем статистику данных
        positive_count = sum(1 for ex in training_data if ex['feedback_type'] == 'positive')
        negative_count = len(training_data) - positive_count
        avg_reward = sum(ex['reward'] for ex in training_data) / len(training_data)
        
        self.stdout.write(f"   - Положительных: {positive_count}")
        self.stdout.write(f"   - Отрицательных: {negative_count}")
        self.stdout.write(f"   - Средняя награда: {avg_reward:.3f}")
        
        # Запускаем обучение
        self.stdout.write("\n🎯 Запуск обучения...")
        model_path = expert_feedback_manager.train_model_with_feedback(
            training_examples=training_data,
            learning_rate=1e-4,
            batch_size=min(16, len(training_data)),
            epochs=50
        )
        
        if model_path:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Обучение завершено! Модель сохранена: {model_path}')
            )
        else:
            self.stdout.write(
                self.style.ERROR('❌ Ошибка при обучении модели')
            )
    
    def _show_statistics(self, options):
        """Показывает статистику"""
        days = options.get('days', 30)
        
        self.stdout.write(
            self.style.SUCCESS(f'📊 СТАТИСТИКА DQN ЗА ПОСЛЕДНИЕ {days} ДНЕЙ')
        )
        self.stdout.write('=' * 60)
        
        # Статистика обратной связи
        stats = expert_feedback_manager.get_feedback_stats(days=days)
        
        self.stdout.write("💬 Экспертная обратная связь:")
        self.stdout.write(f"   - Всего записей: {stats.total_feedback}")
        self.stdout.write(f"   - Положительных: {stats.positive_feedback}")
        self.stdout.write(f"   - Отрицательных: {stats.negative_feedback}")
        self.stdout.write(f"   - Средняя награда: {stats.avg_reward:.3f}")
        
        if stats.by_strength:
            self.stdout.write("   - По силе подкрепления:")
            for strength, count in stats.by_strength.items():
                self.stdout.write(f"     • {strength}: {count}")
        
        if stats.by_expert:
            self.stdout.write("   - По экспертам:")
            for expert_id, count in stats.by_expert.items():
                self.stdout.write(f"     • Эксперт {expert_id}: {count}")
        
        # Статистика рекомендаций
        since_date = timezone.now() - timedelta(days=days)
        total_recommendations = DQNRecommendation.objects.filter(
            created_at__gte=since_date
        ).count()
        
        recommendations_with_feedback = DQNRecommendation.objects.filter(
            created_at__gte=since_date,
            expertfeedback__isnull=False
        ).distinct().count()
        
        self.stdout.write(f"\n🎯 Рекомендации:")
        self.stdout.write(f"   - Всего создано: {total_recommendations}")
        self.stdout.write(f"   - С обратной связью: {recommendations_with_feedback}")
        
        if total_recommendations > 0:
            feedback_rate = recommendations_with_feedback / total_recommendations * 100
            self.stdout.write(f"   - Покрытие обратной связью: {feedback_rate:.1f}%")
        
        # История обучения
        training_history = expert_feedback_manager.get_training_history(limit=5)
        
        self.stdout.write(f"\n🤖 История обучения (последние 5):")
        if not training_history:
            self.stdout.write("   - Нет завершенных сессий обучения")
        else:
            for session in training_history:
                status_emoji = "✅" if session['status'] == 'completed' else "❌" if session['status'] == 'failed' else "⏳"
                self.stdout.write(
                    f"   {status_emoji} Сессия {session['id']}: "
                    f"{session['training_examples_count']} примеров, "
                    f"{session['epochs']} эпох"
                )
                if session['final_loss']:
                    self.stdout.write(f"      Финальная потеря: {session['final_loss']:.4f}")
