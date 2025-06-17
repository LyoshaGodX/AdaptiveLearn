"""
Утилиты для работы с пользователями и группами
Можно использовать в Django shell для быстрого вывода информации
"""
from django.contrib.auth.models import User, Group
from django.db.models import Count


def print_all_users():
    """
    Выводит информацию о всех пользователях системы
    """
    print("\n" + "="*80)
    print("ВСЕ ПОЛЬЗОВАТЕЛИ СИСТЕМЫ")
    print("="*80)
    
    users = User.objects.all().select_related().prefetch_related('groups')
    
    if not users.exists():
        print("❌ Пользователи не найдены!")
        return
    
    for user in users:
        groups = [g.name for g in user.groups.all()]
        groups_str = ', '.join(groups) if groups else 'БЕЗ ГРУППЫ'
        
        print(f"ID: {user.id:2d} | {user.username:15s} | {user.email:25s} | Группы: {groups_str}")
        if user.is_superuser:
            print("     🔑 СУПЕРПОЛЬЗОВАТЕЛЬ")
        if user.is_staff:
            print("     👤 АДМИНИСТРАТОР")
        if not user.is_active:
            print("     ❌ НЕАКТИВЕН")
        print()


def print_users_by_groups():
    """
    Выводит пользователей, сгруппированных по группам
    """
    print("\n" + "="*80)
    print("ПОЛЬЗОВАТЕЛИ ПО ГРУППАМ")
    print("="*80)
    
    groups = Group.objects.all().prefetch_related('user_set')
    
    for group in groups:
        users = group.user_set.all()
        print(f"\n🏷️  ГРУППА: {group.name.upper()} ({users.count()} пользователей)")
        print("-" * 50)
        
        for user in users:
            status = "АКТИВЕН" if user.is_active else "НЕАКТИВЕН"
            super_flag = " 🔑" if user.is_superuser else ""
            print(f"  ID: {user.id:2d} | {user.username:15s} | {status}{super_flag}")
    
    # Пользователи без групп
    users_without_groups = User.objects.filter(groups__isnull=True)
    if users_without_groups.exists():
        print(f"\n❓ БЕЗ ГРУППЫ ({users_without_groups.count()} пользователей)")
        print("-" * 50)
        for user in users_without_groups:
            print(f"  ID: {user.id:2d} | {user.username:15s}")


def print_test_credentials():
    """
    Выводит известные тестовые учетные данные
    """
    print("\n" + "="*60)
    print("ТЕСТОВЫЕ УЧЕТНЫЕ ДАННЫЕ")
    print("="*60)
    
    test_accounts = [
        ('methodist', 'methodist123', 'methodist'),
        ('methodist2', 'methodist123', 'methodist'),
        ('expert', 'expert123', 'expert'),
        ('expert2', 'expert123', 'expert'),
        ('student', 'student123', 'student'),
        ('student2', 'student123', 'student'),
        ('student3', 'student123', 'student'),
        ('student4', 'student123', 'student'),
        ('admin', 'admin123', 'methodist'),
    ]
    
    print("Логин          | Пароль        | Группа    | Статус")
    print("-" * 60)
    
    for username, password, expected_group in test_accounts:
        try:
            user = User.objects.get(username=username)
            user_groups = [g.name for g in user.groups.all()]
            
            if expected_group in user_groups:
                status = "✅ ОК"
            else:
                status = f"❌ Группа: {user_groups}"
                
        except User.DoesNotExist:
            status = "⚠️  НЕ НАЙДЕН"
        
        print(f"{username:15s}| {password:14s}| {expected_group:10s}| {status}")
    
    print("\n💡 Для создания пользователей: python manage.py create_test_users")


def get_user_login_url_mapping():
    """
    Возвращает маппинг пользователей на их домашние страницы
    """
    mapping = {}
    users = User.objects.all().select_related().prefetch_related('groups')
    
    for user in users:
        groups = [g.name for g in user.groups.all()]
        
        if 'methodist' in groups or user.is_superuser:
            home_url = '/methodist/'
        elif 'expert' in groups:
            home_url = '/expert/'
        elif 'student' in groups:
            home_url = '/student/'
        else:
            # Fallback по имени пользователя
            username = user.username.lower()
            if 'methodist' in username or user.is_superuser:
                home_url = '/methodist/'
            elif 'expert' in username:
                home_url = '/expert/'
            else:
                home_url = '/student/'
        
        mapping[user.username] = {
            'id': user.id,
            'groups': groups,
            'home_url': home_url,
            'is_active': user.is_active,
            'is_superuser': user.is_superuser
        }
    
    return mapping


def print_navigation_mapping():
    """
    Выводит маппинг пользователей на их домашние страницы
    """
    print("\n" + "="*80)
    print("МАППИНГ ПОЛЬЗОВАТЕЛЕЙ НА ДОМАШНИЕ СТРАНИЦЫ")
    print("="*80)
    
    mapping = get_user_login_url_mapping()
    
    print("Пользователь    | ID | Группы         | Домашняя страница | Статус")
    print("-" * 80)
    
    for username, info in mapping.items():
        groups_str = ', '.join(info['groups']) if info['groups'] else 'БЕЗ ГРУППЫ'
        status = "АКТИВЕН" if info['is_active'] else "НЕАКТИВЕН"
        if info['is_superuser']:
            status += " 🔑"
        
        print(f"{username:16s}| {info['id']:2d} | {groups_str:15s}| {info['home_url']:18s}| {status}")


# Функции для использования в Django shell
def show_all():
    """Показать всю информацию о пользователях"""
    print_all_users()
    print_users_by_groups()
    print_test_credentials()
    print_navigation_mapping()


if __name__ == "__main__":
    print("Этот файл предназначен для использования в Django shell")
    print("Пример использования:")
    print("  from student.tests.user_utils import show_all")
    print("  show_all()")
