from django.core.management.base import BaseCommand
from methodist.models import Skill, Course
from skills.models import Skill as SkillsSkill, Course as SkillsCourse

class Command(BaseCommand):
    help = 'Проверяет данные в базе данных для приложений skills и methodist'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== ПРОВЕРКА ДАННЫХ В БАЗЕ ==='))
        
        # Проверка данных в приложении skills
        self.stdout.write('\n--- Данные в приложении SKILLS ---')
        skills_courses = SkillsCourse.objects.all()
        skills_skills = SkillsSkill.objects.all()
        
        self.stdout.write(f'Курсов в skills: {skills_courses.count()}')
        for course in skills_courses:
            self.stdout.write(f'  - Курс: {course.id} - {course.name}')
        
        self.stdout.write(f'Навыков в skills: {skills_skills.count()}')
        for skill in skills_skills[:10]:  # Показываем первые 10
            prereqs = skill.prerequisites.all()
            courses = skill.courses.all()
            self.stdout.write(f'  - Навык: {skill.id} - {skill.name} (базовый: {skill.is_base})')
            if prereqs.exists():
                self.stdout.write(f'    Предпосылки: {[p.name for p in prereqs]}')
            if courses.exists():
                self.stdout.write(f'    Курсы: {[c.name for c in courses]}')
        
        if skills_skills.count() > 10:
            self.stdout.write(f'  ... и еще {skills_skills.count() - 10} навыков')
        
        # Проверка данных в приложении methodist
        self.stdout.write('\n--- Данные в приложении METHODIST ---')
        methodist_courses = Course.objects.all()
        methodist_skills = Skill.objects.all()
        
        self.stdout.write(f'Курсов в methodist: {methodist_courses.count()}')
        for course in methodist_courses:
            self.stdout.write(f'  - Курс: {course.id} - {course.name}')
        
        self.stdout.write(f'Навыков в methodist: {methodist_skills.count()}')
        for skill in methodist_skills[:10]:  # Показываем первые 10
            prereqs = skill.prerequisites.all()
            courses = skill.courses.all()
            self.stdout.write(f'  - Навык: {skill.id} - {skill.name} (базовый: {skill.is_base})')
            if prereqs.exists():
                self.stdout.write(f'    Предпосылки: {[p.name for p in prereqs]}')
            if courses.exists():
                self.stdout.write(f'    Курсы: {[c.name for c in courses]}')
        
        if methodist_skills.count() > 10:
            self.stdout.write(f'  ... и еще {methodist_skills.count() - 10} навыков')
        
        # Проверка связей
        self.stdout.write('\n--- ПРОВЕРКА СВЯЗЕЙ ---')
        total_prereq_relations_skills = sum(skill.prerequisites.count() for skill in skills_skills)
        total_prereq_relations_methodist = sum(skill.prerequisites.count() for skill in methodist_skills)
        
        self.stdout.write(f'Связей предпосылок в skills: {total_prereq_relations_skills}')
        self.stdout.write(f'Связей предпосылок в methodist: {total_prereq_relations_methodist}')
        
        total_course_relations_skills = sum(skill.courses.count() for skill in skills_skills)
        total_course_relations_methodist = sum(skill.courses.count() for skill in methodist_skills)
        
        self.stdout.write(f'Связей навык-курс в skills: {total_course_relations_skills}')
        self.stdout.write(f'Связей навык-курс в methodist: {total_course_relations_methodist}')
        
        # Сравнение данных
        self.stdout.write('\n--- СРАВНЕНИЕ ---')
        if skills_courses.count() == methodist_courses.count():
            self.stdout.write(self.style.SUCCESS('✓ Количество курсов совпадает'))
        else:
            self.stdout.write(self.style.ERROR('✗ Количество курсов НЕ совпадает'))
        
        if skills_skills.count() == methodist_skills.count():
            self.stdout.write(self.style.SUCCESS('✓ Количество навыков совпадает'))
        else:
            self.stdout.write(self.style.ERROR('✗ Количество навыков НЕ совпадает'))
        
        if total_prereq_relations_skills == total_prereq_relations_methodist:
            self.stdout.write(self.style.SUCCESS('✓ Количество связей предпосылок совпадает'))
        else:
            self.stdout.write(self.style.ERROR('✗ Количество связей предпосылок НЕ совпадает'))
        
        if total_course_relations_skills == total_course_relations_methodist:
            self.stdout.write(self.style.SUCCESS('✓ Количество связей навык-курс совпадает'))
        else:
            self.stdout.write(self.style.ERROR('✗ Количество связей навык-курс НЕ совпадает'))
        
        # Проверка импорта данных
        self.stdout.write('\n--- РЕКОМЕНДАЦИИ ---')
        if methodist_skills.count() == 0:
            self.stdout.write(self.style.WARNING('⚠ В приложении methodist нет навыков!'))
            self.stdout.write('Попробуйте импортировать данные командой:')
            self.stdout.write('python manage.py import_skills_dot')
        elif methodist_skills.count() < skills_skills.count():
            self.stdout.write(self.style.WARNING('⚠ В приложении methodist меньше навыков, чем в skills!'))
            self.stdout.write('Возможно, миграция данных прошла не полностью.')
        else:
            self.stdout.write(self.style.SUCCESS('✓ Данные в приложении methodist присутствуют'))
        
        self.stdout.write(self.style.SUCCESS('\n=== ПРОВЕРКА ЗАВЕРШЕНА ==='))
