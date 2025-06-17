"""
Команда для сброса пароля пользователя
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Сбрасывает пароль пользователя"

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Имя пользователя')
        parser.add_argument('new_password', type=str, help='Новый пароль')

    def handle(self, *args, **options):
        username = options['username']
        new_password = options['new_password']
        
        try:
            # Получаем пользователя
            user = User.objects.get(username=username)
            
            self.stdout.write(f"✅ Найден пользователь: {user.username} (ID: {user.id})")
            self.stdout.write(f"   Имя: {user.get_full_name() or 'Не указано'}")
            self.stdout.write(f"   Email: {user.email}")
            
            # Получаем группы
            groups = [g.name for g in user.groups.all()]
            groups_str = ', '.join(groups) if groups else 'БЕЗ ГРУППЫ'
            self.stdout.write(f"   Группы: {groups_str}")
            
            # Сбрасываем пароль
            user.set_password(new_password)
            user.save()
            
            self.stdout.write(self.style.SUCCESS(f"🎉 Пароль для пользователя {username} успешно изменен!"))
            self.stdout.write(f"🔑 Новые учетные данные:")
            self.stdout.write(f"   Логин: {username}")
            self.stdout.write(f"   Пароль: {new_password}")
            
            # Показываем URL для входа
            if 'methodist' in groups:
                redirect_url = '/methodist/'
            elif 'expert' in groups:
                redirect_url = '/expert/'
            elif 'student' in groups:
                redirect_url = '/student/'
            else:
                redirect_url = '/student/ (по умолчанию)'
            
            self.stdout.write(f"🏠 После входа пользователь будет перенаправлен на: {redirect_url}")
            
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
