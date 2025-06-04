from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = "Создает тестовых пользователей"

    def handle(self, *args, **options):
        users = [
            ("methodist", "methodist"),
            ("student", "student"),
            ("expert", "expert"),
        ]
        for username, password in users:
            if not User.objects.filter(username=username).exists():
                User.objects.create_user(username=username, password=password)
                self.stdout.write(self.style.SUCCESS(f"Создан пользователь {username}"))
            else:
                self.stdout.write(f"Пользователь {username} уже существует")
