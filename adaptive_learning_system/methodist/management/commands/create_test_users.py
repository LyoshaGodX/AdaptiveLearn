from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group

class Command(BaseCommand):
    help = "Создает тестовых пользователей разных ролей"

    def handle(self, *args, **options):
        # Создаем группы для ролей, если они не существуют
        roles = ['student', 'expert', 'methodist']
        groups = {}
        
        for role in roles:
            group, created = Group.objects.get_or_create(name=role)
            groups[role] = group
            if created:
                self.stdout.write(self.style.SUCCESS(f"Создана группа {role}"))
            else:
                self.stdout.write(f"Группа {role} уже существует")
        
        # Список тестовых пользователей
        # Формат: (username, password, first_name, last_name, email, role)
        users = [
            # Методисты
            ("methodist", "methodist123", "Мария", "Иванова", "methodist@example.com", "methodist"),
            ("methodist2", "methodist123", "Александр", "Петров", "methodist2@example.com", "methodist"),
            
            # Эксперты
            ("expert", "expert123", "Елена", "Смирнова", "expert@example.com", "expert"),
            ("expert2", "expert123", "Дмитрий", "Кузнецов", "expert2@example.com", "expert"),
            
            # Студенты
            ("student", "student123", "Иван", "Соколов", "student@example.com", "student"),
            ("student2", "student123", "Анна", "Козлова", "student2@example.com", "student"),
            ("student3", "student123", "Сергей", "Морозов", "student3@example.com", "student"),
            ("student4", "student123", "Ольга", "Новикова", "student4@example.com", "student"),
            
            # Администратор
            ("admin", "admin123", "Администратор", "Системы", "admin@example.com", "methodist"),
        ]
        
        # Создаем пользователей и добавляем их в соответствующие группы
        for username, password, first_name, last_name, email, role in users:
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    email=email
                )
                
                # Делаем admin суперпользователем
                if username == "admin":
                    user.is_staff = True
                    user.is_superuser = True
                    user.save()
                
                # Добавляем пользователя в соответствующую группу
                user.groups.add(groups[role])
                
                self.stdout.write(self.style.SUCCESS(f"Создан пользователь {username} с ролью {role}"))
            else:
                user = User.objects.get(username=username)
                self.stdout.write(f"Пользователь {username} уже существует")
                
                # Обновляем данные существующего пользователя
                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                
                # Добавляем пользователя в соответствующую группу, если он ещё не в ней
                if not user.groups.filter(name=role).exists():
                    user.groups.add(groups[role])
                    self.stdout.write(f"Пользователь {username} добавлен в группу {role}")
                
                user.save()
        
        self.stdout.write(self.style.SUCCESS("Создание тестовых пользователей завершено успешно!"))
