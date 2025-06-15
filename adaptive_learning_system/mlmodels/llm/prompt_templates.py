"""
Шаблоны промптов для генерации объяснений рекомендаций

Содержит специализированные промпты для различных образовательных сценариев
"""

from typing import Dict, Any, List


class PromptTemplates:
    """Шаблоны промптов для LLM"""
    
    @staticmethod
    def recommendation_explanation_prompt(
        student_name: str,
        task_title: str,
        task_difficulty: str,
        task_type: str,
        target_skill: str,
        target_skill_mastery: float,
        prerequisite_skills: List[Dict[str, Any]],
        dependent_skills: List[Dict[str, Any]],
        student_progress: Dict[str, Any]
    ) -> str:
        """
        Создает улучшенный промпт для объяснения рекомендации задания
        
        Args:
            student_name: Имя студента
            task_title: Название задания
            task_difficulty: Сложность задания (beginner/intermediate/advanced)
            task_type: Тип задания (true_false/single/multiple)
            target_skill: Целевой навык
            target_skill_mastery: Вероятность освоения целевого навыка (0-1)
            prerequisite_skills: Список prerequisite навыков с их освоенностью
            dependent_skills: Список навыков, зависящих от целевого
            student_progress: Общий прогресс студента
            
        Returns:
            Готовый промпт для LLM
        """
        
        # Формируем информацию о prerequisite навыках (освоенных)
        mastered_prereqs = [skill for skill in prerequisite_skills if skill.get('mastery_probability', 0) > 0.7]
        partially_mastered_prereqs = [skill for skill in prerequisite_skills if 0.3 < skill.get('mastery_probability', 0) <= 0.7]
        
        # Формируем информацию о зависимых навыках
        dependent_skills_names = [skill.get('skill_name', 'неизвестный навык') for skill in dependent_skills[:2]]  # Берем первые 2
        
        # Определяем статус студента по сложности
        total_success = student_progress.get('total_success_rate', 0)
        if total_success > 0.8:
            student_status = "справляешься уверенно"
        elif total_success > 0.6:
            student_status = "в целом делаешь успехи"
        else:
            student_status = "испытываешь трудности с более сложными заданиями"
        
        # Обоснование типа задания
        task_type_reasoning = {
            'true_false': "нужно освоиться с более простыми вариантами ответа",
            'single': "хорошо знаешь тему, но нужно закрепить точные знания", 
            'multiple': "нужна насмотренность и понимание множественных аспектов темы"
        }.get(task_type, "подходит для твоего уровня")
        
        # Название типа задания
        task_type_name = {
            'true_false': "Правда/Ложь",
            'single': "выбор одного ответа",
            'multiple': "выбор нескольких ответов"
        }.get(task_type, task_type)
        
        # Формируем контекст освоенных prerequisite навыков
        mastered_skills_text = ""
        if mastered_prereqs:
            skills_list = [f"'{skill.get('skill_name', 'неизвестный')}' ({skill.get('mastery_probability', 0):.0%})" 
                          for skill in mastered_prereqs[:2]]
            mastered_skills_text = f"Ты делаешь успехи в заданиях по навыкам {' и '.join(skills_list)}"
        
        # Формируем контекст зависимых навыков
        dependent_context = ""
        if dependent_skills_names:
            dependent_context = f"для полноценного понимания {dependent_skills_names[0]}"
            if len(dependent_skills_names) > 1:
                dependent_context += f" и {dependent_skills_names[1]}"
        
        prompt = f"""Ты - ИИ-ассистент адаптивной системы обучения программированию. 

ВАЖНЫЙ КОНТЕКСТ СИСТЕМЫ:
В системе существует 30 навыков программирования, выстроенных в ориентированный ациклический граф зависимостей. Каждый навык имеет навыки-предпосылки (которые нужно освоить сначала) и зависимые навыки (которые откроются после его освоения).

ДАННЫЕ О СТУДЕНТЕ И ЗАДАНИИ:
Студент: {student_name}
Рекомендованное задание: "{task_title}"
Тип задания: {task_type_name}
Сложность: {task_difficulty}
Целевой навык: задание нацелено на развитие навыка "{target_skill}", который сейчас развит на {target_skill_mastery:.0%}

КОНТЕКСТ НАВЫКОВ:
Навыки-предпосылки (уже освоенные):
{chr(10).join([f"- {skill.get('skill_name', 'неизвестный')}: развит на {skill.get('mastery_probability', 0):.0%}" for skill in mastered_prereqs]) if mastered_prereqs else "- Специальных предпосылок не требуется"}

{f"Навыки, которые откроются после освоения '{target_skill}':" if dependent_skills_names else ""}
{chr(10).join([f"- {name}" for name in dependent_skills_names]) if dependent_skills_names else ""}

ПРОГРЕСС СТУДЕНТА:
- Общий процент успешных решений: {total_success:.0%}
- Статус: {student_status}

АЛГОРИТМИЧЕСКИЙ ШАБЛОН ОБЪЯСНЕНИЯ:
{mastered_skills_text + ', но ' if mastered_skills_text else ''}{dependent_context + ' ' if dependent_context else ''}необходимо решить следующее задание по теме "{target_skill}". Задание сложности {task_difficulty} выбрано, так как ты {student_status}. Тип задания "{task_type_name}" выбран, потому что тебе {task_type_reasoning}.

ТРЕБОВАНИЯ К ОТВЕТУ:
- Используй обращение на "ты"
- Будь конкретным и используй цифры (проценты освоения)
- Объясни логику выбора типа и сложности задания
- Покажи связь с графом навыков
- БЕЗ технических терминов ("BKT", "алгоритм DQN", "вероятность")
- Создай понятное и мотивирующее объяснение

ПРИМЕРЫ ХОРОШИХ ОБЪЯСНЕНИЙ:
- "Ты отлично освоил Основы Python (85%), теперь пора изучить Циклы для перехода к Функциям. Задание среднее, так как справляешься уверенно. Тип 'выбор ответа' поможет закрепить теорию."
- "Успехи в Переменных (70%) готовят тебя к Условиям. Простое задание 'Правда/Ложь' подойдет, пока осваиваешься с базовыми концепциями."

ОТВЕТ:"""
        
        return prompt
    
    @staticmethod
    def skill_progress_prompt(
        skill_name: str,
        current_mastery: float,
        attempts_count: int,
        success_rate: float
    ) -> str:
        """Промпт для объяснения прогресса по навыку"""
        
        prompt = f"""Опиши прогресс студента по навыку "{skill_name}" в 1-2 предложениях.

ДАННЫЕ:
- Текущий уровень освоения: {current_mastery:.1%}
- Количество попыток: {attempts_count}
- Процент успеха: {success_rate:.1%}

Будь ободряющим и конкретным."""
        
        return prompt
    
    @staticmethod
    def motivation_prompt(
        student_name: str,
        recent_successes: int,
        recent_failures: int
    ) -> str:
        """Промпт для мотивационного сообщения"""
        
        total = recent_successes + recent_failures
        if total == 0:
            context = "начинает изучение"
        elif recent_successes > recent_failures:
            context = "показывает хороший прогресс"
        else:
            context = "сталкивается с трудностями, но продолжает учиться"
        
        prompt = f"""Создай короткое мотивационное сообщение для студента {student_name}, который {context}.

Последние результаты: {recent_successes} успехов, {recent_failures} ошибок.

Сообщение должно:
- Ободрять и мотивировать
- Подчеркивать важность практики
- Использовать обращение на "ты"

ОТВЕТ:"""
        
        return prompt
    
    @staticmethod
    def difficulty_explanation_prompt(
        task_difficulty: str,
        student_skill_level: float,
        reason: str
    ) -> str:
        """Промпт для объяснения выбора сложности задания"""
        
        skill_desc = "высокий" if student_skill_level > 0.8 else "средний" if student_skill_level > 0.5 else "начальный"
        
        prompt = f"""Объясни студенту, почему выбрано задание сложности "{task_difficulty}".

КОНТЕКСТ:
- Уровень навыка студента: {skill_desc} ({student_skill_level:.1%})
- Причина выбора: {reason}

Создай объяснение, которое:
- Связывает сложность с уровнем студента
- Объясняет пользу такого выбора
- Звучит ободряюще

ОТВЕТ:"""
        
        return prompt
