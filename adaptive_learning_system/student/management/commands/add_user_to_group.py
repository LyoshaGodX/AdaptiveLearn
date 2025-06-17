"""
Команда для добавления пользователя в группу
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group


class Command(BaseCommand):
    help = "Добавляет пользователя в указанную группу"

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Имя пользователя')
        parser.add_argument('group_name', type=str, help='Название группы (student, expert, methodist)')

    def handle(self, *args, **options):
        username = options['username']
        group_name = options['group_name']
        
        try:
            # Получаем пользователя
            user = User.objects.get(username=username)
            self.stdout.write(f"✅ Найден пользователь: {user.username} (ID: {user.id})")
            self.stdout.write(f"   Имя: {user.get_full_name() or 'Не указано'}")
            self.stdout.write(f"   Email: {user.email}")
            
            # Получаем или создаем группу
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(f"✅ Создана группа: {group_name}")
            else:
                self.stdout.write(f"✅ Найдена группа: {group_name}")
            
            # Проверяем, не состоит ли уже в группе
            if user.groups.filter(name=group_name).exists():
                self.stdout.write(self.style.WARNING(f"⚠️  Пользователь {username} уже состоит в группе {group_name}"))
                return
            
            # Добавляем в группу
            user.groups.add(group)
            
            self.stdout.write(self.style.SUCCESS(f"🎉 Пользователь {username} успешно добавлен в группу {group_name}"))
            
            # Показываем текущие группы пользователя
            current_groups = [g.name for g in user.groups.all()]
            self.stdout.write(f"📋 Текущие группы пользователя: {', '.join(current_groups)}")
            
            # Показываем, куда будет перенаправлен пользователь
            if group_name == 'methodist':
                redirect_url = '/methodist/'
            elif group_name == 'expert':
                redirect_url = '/expert/'
            elif group_name == 'student':
                redirect_url = '/student/'
            else:
                redirect_url = '/student/ (по умолчанию)'
            
            self.stdout.write(f"🏠 При входе пользователь будет перенаправлен на: {redirect_url}")
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ Пользователь {username} не найден"))
            
            # Показываем доступных пользователей
            users = User.objects.all()
            if users.exists():
                self.stdout.write(f"\n📋 Доступные пользователи:")
                for user in users:
                    groups = [g.name for g in user.groups.all()]
                    groups_str = ', '.join(groups) if groups else 'БЕЗ ГРУППЫ'
                    self.stdout.write(f"  • {user.username} (ID: {user.id}) - группы: {groups_str}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Ошибка: {str(e)}"))
