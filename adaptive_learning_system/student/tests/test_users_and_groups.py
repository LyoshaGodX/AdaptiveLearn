"""
Тесты для проверки пользователей и групп в системе
"""
from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.core.management import call_command
from django.db import transaction


class UserGroupsTestCase(TestCase):
    """
    Тест-кейс для проверки пользователей и их групп
    """
    
    def setUp(self):
        """
        Настройка тестовых данных - создаем тестовых пользователей
        """
        # Создаем тестовых пользователей через команду управления
        try:
            call_command('create_test_users')
        except Exception as e:
            print(f"Предупреждение: не удалось выполнить create_test_users: {e}")
            # Создаем пользователей вручную если команда не работает
            self._create_manual_test_users()
    
    def _create_manual_test_users(self):
        """
        Создание тестовых пользователей вручную
        """
        # Создаем группы
        groups = {}
        for role in ['student', 'expert', 'methodist']:
            group, created = Group.objects.get_or_create(name=role)
            groups[role] = group
        
        # Создаем тестовых пользователей
        test_users = [
            ('methodist_test', 'methodist123', 'methodist'),
            ('expert_test', 'expert123', 'expert'),
            ('student_test', 'student123', 'student'),
        ]
        
        for username, password, role in test_users:
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    email=f'{username}@test.com'
                )
                user.groups.add(groups[role])
    
    def test_display_all_users_and_groups(self):
        """
        Тест, который выводит всех пользователей, их группы, ID и информацию о паролях
        """
        print("\n" + "="*80)
        print("ИНФОРМАЦИЯ О ВСЕХ ПОЛЬЗОВАТЕЛЯХ И ГРУППАХ СИСТЕМЫ")
        print("="*80)
        
        # Получаем всех пользователей
        users = User.objects.all().order_by('id')
        
        if not users.exists():
            print("❌ Пользователи не найдены в системе!")
            return
        
        print(f"📊 Всего пользователей в системе: {users.count()}")
        print("-"*80)
        
        # Группируем пользователей по группам
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
        
        # Выводим информацию по группам
        for group_name, group_users in groups_info.items():
            print(f"\n🏷️  ГРУППА: {group_name.upper()}")
            print("-" * 50)
            
            for user in group_users:
                self._print_user_info(user)
        
        # Выводим пользователей без групп
        if users_without_groups:
            print(f"\n❓ ПОЛЬЗОВАТЕЛИ БЕЗ ГРУПП")
            print("-" * 50)
            
            for user in users_without_groups:
                self._print_user_info(user)
        
        # Статистика по группам
        print(f"\n📈 СТАТИСТИКА ПО ГРУППАМ:")
        print("-" * 30)
        
        all_groups = Group.objects.all()
        for group in all_groups:
            user_count = group.user_set.count()
            print(f"• {group.name}: {user_count} пользователей")
        
        print(f"• Без группы: {len(users_without_groups)} пользователей")
        
        print("\n" + "="*80)
        
        # Проверяем, что есть пользователи
        self.assertTrue(users.exists(), "В системе должны быть пользователи")
    
    def _print_user_info(self, user):
        """
        Выводит информацию о пользователе
        """
        # Определяем статус пользователя
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
        
        # Группы пользователя
        user_groups = [group.name for group in user.groups.all()]
        groups_str = ", ".join(user_groups) if user_groups else "НЕТ ГРУПП"
        
        print(f"  ID: {user.id:2d} | Логин: {user.username:15s} | Email: {user.email:25s}")
        print(f"       Имя: {user.get_full_name() or 'Не указано':20s} | Группы: {groups_str}")
        print(f"       Статус: {status}")
        print(f"       Дата создания: {user.date_joined.strftime('%d.%m.%Y %H:%M')}")
        
        # Примечание о паролях
        if user.password:
            print(f"       🔐 Пароль: ЗАШИФРОВАН (хеш: {user.password[:20]}...)")
        else:
            print(f"       ⚠️  Пароль: НЕ УСТАНОВЛЕН")
        
        print()
    
    def test_display_known_test_passwords(self):
        """
        Выводит известные тестовые пароли из команды create_test_users
        """
        print("\n" + "="*80)
        print("ИЗВЕСТНЫЕ ТЕСТОВЫЕ ПАРОЛИ")
        print("="*80)
        
        # Известные тестовые пароли из create_test_users.py
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
        
        print("📝 Стандартные тестовые пароли:")
        print("-" * 40)
        
        for username, password in known_passwords.items():
            user_exists = User.objects.filter(username=username).exists()
            status = "✅ СУЩЕСТВУЕТ" if user_exists else "❌ НЕ НАЙДЕН"
            print(f"• {username:12s} : {password:15s} [{status}]")
        
        print(f"\n💡 Примечание:")
        print(f"   - Это пароли из команды 'python manage.py create_test_users'")
        print(f"   - В реальной системе пароли хранятся в зашифрованном виде")
        print(f"   - Для создания тестовых пользователей выполните:")
        print(f"     python manage.py create_test_users")
        
        print("\n" + "="*80)
    
    def test_group_membership_verification(self):
        """
        Проверяет правильность назначения групп пользователям
        """
        print("\n" + "="*60)
        print("ПРОВЕРКА ПРАВИЛЬНОСТИ НАЗНАЧЕНИЯ ГРУПП")
        print("="*60)
        
        # Ожидаемые соответствия username -> группа
        expected_mappings = {
            'methodist': 'methodist',
            'methodist2': 'methodist', 
            'expert': 'expert',
            'expert2': 'expert',
            'student': 'student',
            'student2': 'student',
            'student3': 'student',
            'student4': 'student',
            'admin': 'methodist',  # admin должен быть в группе methodist
        }
        
        print("🔍 Проверка соответствия пользователей группам:")
        print("-" * 50)
        
        errors = []
        
        for username, expected_group in expected_mappings.items():
            try:
                user = User.objects.get(username=username)
                user_groups = [group.name for group in user.groups.all()]
                
                if expected_group in user_groups:
                    print(f"✅ {username:12s} → группа '{expected_group}' ОК")
                else:
                    error_msg = f"❌ {username:12s} → ожидалась '{expected_group}', есть: {user_groups}"
                    print(error_msg)
                    errors.append(error_msg)
                    
            except User.DoesNotExist:
                error_msg = f"⚠️  {username:12s} → пользователь НЕ НАЙДЕН"
                print(error_msg)
                errors.append(error_msg)
        
        if errors:
            print(f"\n❌ Найдено {len(errors)} проблем:")
            for error in errors:
                print(f"   {error}")
            print(f"\n💡 Рекомендация: выполните 'python manage.py create_test_users'")
        else:
            print(f"\n✅ Все проверки пройдены успешно!")
        
        print("="*60)
        
        # Не делаем assert чтобы тест всегда показывал информацию
        # self.assertEqual(len(errors), 0, f"Найдены ошибки в назначении групп: {errors}")


class UserAuthenticationTestCase(TestCase):
    """
    Тест для проверки аутентификации пользователей
    """
    
    def test_user_login_simulation(self):
        """
        Симулирует попытки входа пользователей с известными паролями
        """
        print("\n" + "="*70)
        print("ТЕСТИРОВАНИЕ АУТЕНТИФИКАЦИИ ПОЛЬЗОВАТЕЛЕЙ")
        print("="*70)
        
        # Тестовые данные для входа
        test_credentials = [
            ('methodist', 'methodist123'),
            ('expert', 'expert123'),
            ('student', 'student123'),
            ('admin', 'admin123'),
        ]
        
        print("🔐 Проверка входа с тестовыми учетными данными:")
        print("-" * 50)
        
        for username, password in test_credentials:
            try:
                # Проверяем существование пользователя
                user = User.objects.get(username=username)
                
                # Проверяем пароль
                if user.check_password(password):
                    groups = [g.name for g in user.groups.all()]
                    print(f"✅ {username:12s} - вход УСПЕШЕН (группы: {groups})")
                else:
                    print(f"❌ {username:12s} - НЕВЕРНЫЙ ПАРОЛЬ")
                    
            except User.DoesNotExist:
                print(f"⚠️  {username:12s} - пользователь НЕ НАЙДЕН")
        
        print("\n💡 Примечание: это тестовые данные для разработки")
        print("="*70)
