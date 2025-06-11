from django.core.management.base import BaseCommand
from skills.models import Skill as SkillsSkill, Course as SkillsCourse
from methodist.models import Skill, Course

class Command(BaseCommand):
    help = 'Переносит данные из приложения skills в methodist'

    def handle(self, *args, **options):
        self.stdout.write("Начинаем перенос данных из skills в methodist...")
        
        # Переносим курсы
        self.stdout.write("Переносим курсы...")
        for course in SkillsCourse.objects.all():
            new_course, created = Course.objects.get_or_create(
                id=course.id,
                defaults={
                    'name': course.name,
                    'description': course.description
                }
            )
            status = "создан" if created else "уже существует"
            self.stdout.write(f"  Курс '{course.name}' - {status}")
        
        # Переносим навыки
        self.stdout.write("Переносим навыки...")
        skill_mapping = {}
        for skill in SkillsSkill.objects.all():
            new_skill, created = Skill.objects.get_or_create(
                name=skill.name,
                defaults={
                    'description': skill.description,
                    'is_base': skill.is_base
                }
            )
            skill_mapping[skill.id] = new_skill
            status = "создан" if created else "уже существует"
            self.stdout.write(f"  Навык '{skill.name}' - {status}")
        
        # Устанавливаем связи с курсами
        self.stdout.write("Устанавливаем связи навыков с курсами...")
        for old_skill in SkillsSkill.objects.all():
            new_skill = skill_mapping[old_skill.id]
            for course in old_skill.courses.all():
                try:
                    new_course = Course.objects.get(id=course.id)
                    new_skill.courses.add(new_course)
                    self.stdout.write(f"  '{new_skill.name}' -> '{new_course.name}'")
                except Course.DoesNotExist:
                    self.stdout.write(f"  Ошибка: курс {course.id} не найден")
        
        # Устанавливаем связи предпосылок
        self.stdout.write("Устанавливаем связи предпосылок...")
        for old_skill in SkillsSkill.objects.all():
            new_skill = skill_mapping[old_skill.id]
            for prereq in old_skill.prerequisites.all():
                if prereq.id in skill_mapping:
                    new_prereq = skill_mapping[prereq.id]
                    new_skill.prerequisites.add(new_prereq)
                    self.stdout.write(f"  '{new_prereq.name}' -> '{new_skill.name}'")
        
        self.stdout.write(self.style.SUCCESS("Перенос данных завершен успешно!"))
        
        # Выводим статистику
        courses_count = Course.objects.count()
        skills_count = Skill.objects.count()
        self.stdout.write(f"Итого перенесено: {courses_count} курсов, {skills_count} навыков")
