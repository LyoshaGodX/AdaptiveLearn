"""
Интерфейсы для работы с данными курсов, заданий и навыков.
Предоставляет удобные методы для извлечения и анализа данных.
"""

from typing import List, Dict, Any, Optional, Tuple
from django.db.models import QuerySet, Count, Avg, Q
from skills.models import Skill, Course
from methodist.models import Task, TaskAnswer
from student.models import StudentProfile, StudentCourseEnrollment
from mlmodels.models import StudentSkillMastery, TaskAttempt, StudentLearningProfile
import networkx as nx
import json


class CourseDataInterface:
    """Интерфейс для работы с данными курсов"""
    
    @staticmethod
    def get_all_courses() -> QuerySet[Course]:
        """Получить все курсы"""
        return Course.objects.all()
    
    @staticmethod
    def get_course_by_id(course_id: str) -> Optional[Course]:
        """Получить курс по ID"""
        try:
            return Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return None
    
    @staticmethod
    def get_course_skills(course_id: str) -> QuerySet[Skill]:
        """Получить все навыки курса"""
        course = CourseDataInterface.get_course_by_id(course_id)
        if course:
            return course.skills.all()
        return Skill.objects.none()
    
    @staticmethod
    def get_course_tasks(course_id: str) -> QuerySet[Task]:
        """Получить все задания курса"""
        course = CourseDataInterface.get_course_by_id(course_id)
        if course:
            return course.tasks.filter(is_active=True)
        return Task.objects.none()
    
    @staticmethod
    def get_course_students(course_id: str) -> QuerySet[StudentProfile]:
        """Получить всех студентов курса"""
        course = CourseDataInterface.get_course_by_id(course_id)
        if course:
            enrollments = course.student_enrollments.filter(
                status__in=['enrolled', 'in_progress']
            )
            return StudentProfile.objects.filter(
                course_enrollments__in=enrollments
            ).distinct()
        return StudentProfile.objects.none()
    
    @staticmethod
    def get_course_statistics(course_id: str) -> Dict[str, Any]:
        """Получить статистику по курсу"""
        course = CourseDataInterface.get_course_by_id(course_id)
        if not course:
            return {}
        
        skills = course.skills.all()
        tasks = course.tasks.filter(is_active=True)
        students = CourseDataInterface.get_course_students(course_id)
        
        return {
            'course_id': course_id,
            'course_name': course.name,
            'skills_count': skills.count(),
            'tasks_count': tasks.count(),
            'students_count': students.count(),
            'skills': [
                {                    'id': skill.id,
                    'name': skill.name,
                    'is_base': skill.is_base,
                    'tasks_count': skill.tasks.filter(is_active=True).count()
                }
                for skill in skills
            ],
            'difficulty_distribution': {
                diff: tasks.filter(difficulty=diff).count()
                for diff in tasks.values_list('difficulty', flat=True).distinct()
            },
            'task_types_distribution': {
                task_type: tasks.filter(task_type=task_type).count()
                for task_type in tasks.values_list('task_type', flat=True).distinct()
            }
        }


class SkillDataInterface:
    """Интерфейс для работы с данными навыков"""
    
    @staticmethod
    def get_all_skills() -> QuerySet[Skill]:
        """Получить все навыки"""
        return Skill.objects.all()
    
    @staticmethod
    def get_skill_by_id(skill_id: int) -> Optional[Skill]:
        """Получить навык по ID"""
        try:
            return Skill.objects.get(id=skill_id)
        except Skill.DoesNotExist:
            return None
    
    @staticmethod
    def get_base_skills() -> QuerySet[Skill]:
        """Получить базовые навыки (без пререквизитов)"""
        return Skill.objects.filter(is_base=True)
    
    @staticmethod
    def get_skill_prerequisites(skill_id: int) -> QuerySet[Skill]:
        """Получить пререквизиты навыка"""
        skill = SkillDataInterface.get_skill_by_id(skill_id)
        if skill:
            return skill.prerequisites.all()
        return Skill.objects.none()
    
    @staticmethod
    def get_skill_dependents(skill_id: int) -> QuerySet[Skill]:
        """Получить навыки, зависящие от данного"""
        skill = SkillDataInterface.get_skill_by_id(skill_id)
        if skill:
            return skill.dependent_skills.all()
        return Skill.objects.none()
    
    @staticmethod
    def get_skill_tasks(skill_id: int) -> QuerySet[Task]:
        """Получить задания для навыка"""
        skill = SkillDataInterface.get_skill_by_id(skill_id)
        if skill:
            return skill.tasks.filter(is_active=True)
        return Task.objects.none()
    
    @staticmethod
    def get_skill_courses(skill_id: int) -> QuerySet[Course]:
        """Получить курсы, содержащие навык"""
        skill = SkillDataInterface.get_skill_by_id(skill_id)
        if skill:
            return skill.courses.all()
        return Course.objects.none()
    
    @staticmethod
    def build_skills_dependency_path(from_skill_id: int, to_skill_id: int) -> List[int]:
        """
        Построить путь зависимостей между навыками
        Возвращает список ID навыков от начального к конечному
        """
        graph = SkillDataInterface.build_skills_graph()
        
        try:
            path = nx.shortest_path(graph, from_skill_id, to_skill_id)
            return list(path) if path else []
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
    
    @staticmethod
    def get_skills_learning_order(course_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Получить рекомендуемый порядок изучения навыков
        Если указан course_id, возвращает порядок только для навыков курса
        """
        if course_id:
            skills = CourseDataInterface.get_course_skills(course_id)
        else:
            skills = SkillDataInterface.get_all_skills()
        
        # Строим граф для данных навыков
        graph = nx.DiGraph()
        skill_ids = list(skills.values_list('id', flat=True))
        
        for skill in skills:
            graph.add_node(skill.id, name=skill.name, is_base=skill.is_base)
            
            # Добавляем связи пререквизитов
            for prereq in skill.prerequisites.filter(id__in=skill_ids):
                graph.add_edge(prereq.id, skill.id)
        
        # Топологическая сортировка для определения порядка
        try:
            ordered_skills = list(nx.topological_sort(graph))
        except nx.NetworkXError:
            # Граф содержит циклы, используем простой порядок
            ordered_skills = skill_ids
        
        result = []
        for skill_id in ordered_skills:
            skill = skills.get(id=skill_id)
            result.append({
                'id': skill.id,
                'name': skill.name,
                'is_base': skill.is_base,
                'prerequisites_count': skill.prerequisites.count(),
                'dependents_count': skill.dependent_skills.count(),
                'tasks_count': skill.tasks.filter(is_active=True).count()
            })
        
        return result


class TaskDataInterface:
    """Интерфейс для работы с данными заданий"""
    
    @staticmethod
    def get_all_tasks() -> QuerySet[Task]:
        """Получить все активные задания"""
        return Task.objects.filter(is_active=True)
    
    @staticmethod
    def get_task_by_id(task_id: int) -> Optional[Task]:
        """Получить задание по ID"""
        try:
            return Task.objects.get(id=task_id, is_active=True)
        except Task.DoesNotExist:
            return None
    
    @staticmethod
    def get_tasks_by_skill(skill_id: int) -> QuerySet[Task]:
        """Получить задания для навыка"""
        return Task.objects.filter(skills=skill_id, is_active=True)
    
    @staticmethod
    def get_tasks_by_difficulty(difficulty: str) -> QuerySet[Task]:
        """Получить задания по уровню сложности"""
        return Task.objects.filter(difficulty=difficulty, is_active=True)
    
    @staticmethod
    def get_tasks_by_type(task_type: str) -> QuerySet[Task]:
        """Получить задания по типу"""
        return Task.objects.filter(task_type=task_type, is_active=True)
    
    @staticmethod
    def get_task_answers(task_id: int) -> QuerySet[TaskAnswer]:
        """Получить варианты ответов для задания"""
        return TaskAnswer.objects.filter(task_id=task_id).order_by('order')
    
    @staticmethod
    def get_task_correct_answers(task_id: int) -> QuerySet[TaskAnswer]:
        """Получить правильные ответы для zadania"""
        return TaskAnswer.objects.filter(task_id=task_id, is_correct=True)
    
    @staticmethod
    def get_task_statistics(task_id: int) -> Dict[str, Any]:
        """Получить статистику по заданию"""
        task = TaskDataInterface.get_task_by_id(task_id)
        if not task:
            return {}
        
        attempts = TaskAttempt.objects.filter(task=task)
        
        stats = {
            'task_id': task_id,
            'task_title': task.title,
            'task_type': task.task_type,
            'difficulty': task.difficulty,
            'total_attempts': attempts.count(),
            'correct_attempts': attempts.filter(is_correct=True).count(),
            'unique_students': attempts.values('student').distinct().count(),
        }
        
        if stats['total_attempts'] > 0:
            stats['success_rate'] = stats['correct_attempts'] / stats['total_attempts']
            
            # Статистика времени
            time_data = attempts.filter(time_spent__isnull=False)
            if time_data.exists():
                avg_time = time_data.aggregate(avg=Avg('time_spent'))['avg']
                stats['average_time_seconds'] = round(avg_time, 2) if avg_time else 0
                stats['average_time_minutes'] = round(avg_time / 60, 2) if avg_time else 0
        else:
            stats['success_rate'] = 0
            stats['average_time_seconds'] = 0
            stats['average_time_minutes'] = 0
        
        return stats
    
    @staticmethod
    def get_recommended_tasks_for_student(
        student_id: int, 
        skill_id: Optional[int] = None,
        difficulty: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Получить рекомендуемые задания для студента
        на основе его текущего уровня освоения навыков
        """
        try:
            student = StudentProfile.objects.get(id=student_id)
        except StudentProfile.DoesNotExist:
            return []
        
        # Получаем освоение навыков студентом
        masteries = StudentSkillMastery.objects.filter(student=student)
        mastery_dict = {m.skill_id: m.current_mastery_prob for m in masteries}
        
        # Базовый запрос заданий
        tasks_query = Task.objects.filter(is_active=True)
        
        if skill_id:
            tasks_query = tasks_query.filter(skills=skill_id)
        
        if difficulty:
            tasks_query = tasks_query.filter(difficulty=difficulty)
        
        # Исключаем задания, которые студент уже выполнил правильно
        completed_tasks = TaskAttempt.objects.filter(
            student=student, 
            is_correct=True
        ).values_list('task_id', flat=True)
        
        tasks_query = tasks_query.exclude(id__in=completed_tasks)
        
        recommended_tasks = []
        
        for task in tasks_query[:limit * 2]:  # Берем больше для фильтрации
            # Вычисляем релевантность задания
            task_skills = task.skills.all()
            skill_relevance = 0
            
            for skill in task_skills:
                mastery_prob = mastery_dict.get(skill.id, 0.0)
                
                # Задание релевантно, если навык частично освоен (0.2-0.8)
                if 0.2 <= mastery_prob <= 0.8:
                    skill_relevance += 1 - abs(mastery_prob - 0.5) * 2
                elif mastery_prob < 0.2:
                    skill_relevance += 0.3  # Базовые задания для неосвоенных навыков
            
            if skill_relevance > 0:
                recommended_tasks.append({
                    'task_id': task.id,
                    'title': task.title,
                    'difficulty': task.difficulty,
                    'task_type': task.task_type,
                    'relevance_score': skill_relevance,
                    'skills': [
                        {
                            'id': skill.id,
                            'name': skill.name,
                            'mastery_prob': mastery_dict.get(skill.id, 0.0)
                        }
                        for skill in task_skills
                    ]
                })
        
        # Сортируем по релевантности и возвращаем топ
        recommended_tasks.sort(key=lambda x: x['relevance_score'], reverse=True)
        return recommended_tasks[:limit]


class StudentDataInterface:
    """Интерфейс для работы с данными студентов"""
    
    @staticmethod
    def get_student_skill_masteries(student_id: int) -> QuerySet[StudentSkillMastery]:
        """Получить освоение навыков студентом"""
        return StudentSkillMastery.objects.filter(student_id=student_id)
    
    @staticmethod
    def get_student_attempts(student_id: int) -> QuerySet[TaskAttempt]:
        """Получить попытки решения заданий студентом"""
        return TaskAttempt.objects.filter(student_id=student_id)
    
    @staticmethod
    def get_student_learning_profile(student_id: int) -> Optional[StudentLearningProfile]:
        """Получить профиль обучения студента"""
        try:
            return StudentLearningProfile.objects.get(student_id=student_id)
        except StudentLearningProfile.DoesNotExist:
            return None
    
    @staticmethod
    def get_student_progress_summary(student_id: int) -> Dict[str, Any]:
        """Получить сводку прогресса студента"""
        try:
            student = StudentProfile.objects.get(id=student_id)
        except StudentProfile.DoesNotExist:
            return {}
        
        masteries = StudentDataInterface.get_student_skill_masteries(student_id)
        attempts = StudentDataInterface.get_student_attempts(student_id)
        
        # Статистика по навыкам
        total_skills = masteries.count()
        mastered_skills = masteries.filter(current_mastery_prob__gte=0.8).count()
        in_progress_skills = masteries.filter(
            current_mastery_prob__gte=0.2,
            current_mastery_prob__lt=0.8
        ).count()
        
        # Статистика по попыткам
        total_attempts = attempts.count()
        correct_attempts = attempts.filter(is_correct=True).count()
        
        # Курсы студента
        enrollments = student.course_enrollments.filter(
            status__in=['enrolled', 'in_progress']
        )
        
        return {
            'student_id': student_id,
            'student_name': student.full_name,
            'skills_stats': {
                'total_skills': total_skills,
                'mastered_skills': mastered_skills,
                'in_progress_skills': in_progress_skills,
                'not_started_skills': total_skills - mastered_skills - in_progress_skills,
                'mastery_rate': mastered_skills / total_skills if total_skills > 0 else 0
            },
            'attempts_stats': {
                'total_attempts': total_attempts,
                'correct_attempts': correct_attempts,
                'success_rate': correct_attempts / total_attempts if total_attempts > 0 else 0
            },
            'active_courses': [
                {
                    'course_id': enrollment.course.id,
                    'course_name': enrollment.course.name,
                    'progress_percentage': enrollment.progress_percentage,
                    'status': enrollment.status
                }
                for enrollment in enrollments
            ]
        }
