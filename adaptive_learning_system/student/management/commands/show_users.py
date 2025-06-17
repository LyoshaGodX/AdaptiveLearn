"""
Скрипт для вывода реальных пользователей из основной базы данных
Используется как management команда Django
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group


class Command(BaseCommand):
    help = "Показывает всех реальных пользователей системы с их данными"

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*80)
        self.stdout.write("РЕАЛЬНЫЕ ПОЛЬЗОВАТЕЛИ В ОСНОВНОЙ БАЗЕ ДАННЫХ")
        self.stdout.write("="*80)
        
        users = User.objects.all().order_by('id')
        
        if not users.exists():
            self.stdout.write(self.style.ERROR("❌ Пользователи не найдены в базе данных!"))
            self.stdout.write("💡 Создайте пользователей командой: python manage.py create_test_users")
            return
        
        self.stdout.write(f"📊 Всего пользователей: {users.count()}")
        self.stdout.write("-"*80)
        
        # Группируем по группам
        groups_info = {}
        users_without_groups = []
        
        for user in users:
            user_groups = user.groups.all()
            
            if user_groups.exists():
                for group in user_groups:
                    if group.name not in groups_info:
                        groups_info[group.name] = []
                    groups_info[group.name].append(user)
            else:
                users_without_groups.append(user)
        
        # Выводим по группам
        for group_name, group_users in groups_info.items():
            self.stdout.write(f"\n🏷️  ГРУППА: {group_name.upper()}")
            self.stdout.write("-" * 50)
            
            for user in group_users:
                self._print_user_info(user)
        
        # Пользователи без групп
        if users_without_groups:
            self.stdout.write(f"\n❓ БЕЗ ГРУППЫ")
            self.stdout.write("-" * 50)
            
            for user in users_without_groups:
                self._print_user_info(user)
        
        # Известные тестовые пароли
        self.stdout.write(f"\n📝 ИЗВЕСТНЫЕ ТЕСТОВЫЕ ПАРОЛИ:")
        self.stdout.write("-" * 50)
        
        known_passwords = {
            'methodist': 'methodist123',
            'methodist2': 'methodist123',
            'expert': 'expert123',
            'expert2': 'expert123',
            'student': 'student123',
            'student2': 'student123',
            'student3': 'student123',
            'student4': 'student123',
            'admin': 'admin123',
        }
        
        for username, password in known_passwords.items():
            user_exists = User.objects.filter(username=username).exists()
            status = "✅ ЕСТЬ В БД" if user_exists else "❌ НЕ НАЙДЕН"
            self.stdout.write(f"• {username:12s} : {password:15s} [{status}]")
        
        self.stdout.write(f"\n💡 Примечания:")
        self.stdout.write(f"   - Пароли в БД хранятся в зашифрованном виде")
        self.stdout.write(f"   - Для входа используйте указанные пароли")
        self.stdout.write(f"   - Если пользователей нет, выполните: python manage.py create_test_users")
        
        self.stdout.write("="*80)
    
    def _print_user_info(self, user):
        """Выводит информацию о пользователе"""
        # Статус
        status_flags = []
        if user.is_superuser:
            status_flags.append("🔑 СУПЕР")
        if user.is_staff:
            status_flags.append("👤 АДМИН")
        if user.is_active:
            status_flags.append("✅ АКТИВЕН")
        else:
            status_flags.append("❌ НЕАКТИВЕН")
        
        status = " | ".join(status_flags)
        
        # Группы
        user_groups = [group.name for group in user.groups.all()]
        groups_str = ", ".join(user_groups) if user_groups else "НЕТ ГРУПП"
        
        # Полное имя
        full_name = user.get_full_name() or "Не указано"
        
        self.stdout.write(f"  ID: {user.id:2d} | Логин: {user.username:15s} | Email: {user.email:25s}")
        self.stdout.write(f"       Имя: {full_name:20s} | Группы: {groups_str}")
        self.stdout.write(f"       Статус: {status}")
        self.stdout.write(f"       Создан: {user.date_joined.strftime('%d.%m.%Y %H:%M')}")
        self.stdout.write("")
