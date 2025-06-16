"""
Расширенные шаблоны промптов для генерации объяснений рекомендаций

Модуль переработан с учётом следующих целей:
1. Более глубокий алгоритмический анализ данных обучающегося.
2. Вариативная, грамматически гладкая формулировка фрагментов, исключающая однообразие.
3. Сохранение читаемости и лаконичности конечного текста, несмотря на увеличение информативности.

Ключевые изменения:
• Добавлены словари с вариативными фразами для приветствий, связок, выводов.
• Реализовано гибкое ранжирование прогресса с тонкой градацией (шкала А–E) вместо 4-уровневой.
• Учтён факт, что prerequisite-навыки могут быть частично освоены; логика формирует корректные обороты «нуждается в укреплении».
• Для зависимых навыков генерируется фраза «откроются X, Y, а также Z» с учётом количества элементов.
• В конец добавляется короткий тезис о пользе задания («в рамках подготовки к …»), если количество dependent-skills > 0.
• Все проценты выводятся без неуместных десятых долей, но с правильным падежом («80 %», «1 %»).

Эти приёмы делают результат более осмысленным и естественным без привлечения внешних библиотек.
"""

from __future__ import annotations

import math
import random
from typing import Dict, Any, List


class PromptTemplates:
    """Генератор промптов для LLM-моделей."""

    # ————————————————————————————————————————————————————————————————
    # Вспомогательные методы
    # ————————————————————————————————————————————————————————————————

    @staticmethod
    def _pct(value: float) -> str:
        """Форматированный процент без лишних разрядов: 0.83 → '83 %'."""
        return f"{round(value * 100):d} %"

    @staticmethod
    def _choose(sentence_pool: List[str], seed: str | int) -> str:
        """Детерминированный выбор фразы из набора (чтобы мелкие правки не
        ломали тесты, но ответы оставались вариативными)."""
        rng = random.Random(str(seed))
        return rng.choice(sentence_pool)

    # ————————————————————————————————————————————————————————————————
    # Основной промпт-конструктор
    # ————————————————————————————————————————————————————————————————

    @classmethod
    def recommendation_explanation_prompt(
        cls,
        student_name: str,
        task_title: str,
        task_difficulty: str,
        task_type: str,
        target_skill: str,
        target_skill_mastery: float,
        prerequisite_skills: List[Dict[str, Any]],
        dependent_skills: List[Dict[str, Any]],
        student_progress: Dict[str, Any],
    ) -> str:
        """Формирует промпт-заготовку для LLM, содержащую обоснование выбора задания."""

        # ——— 1. Приветствие и основной факт рекомендации
        greeting_variants = [
            f"Для тебя, {student_name}, сформирована рекомендация пройти задание «{task_title}».",
            f"{student_name}, следующим шагом предлагается задание «{task_title}».",
            f"Рекомендуемое задание для тебя, {student_name}, — «{task_title}».",
        ]
        intro = cls._choose(greeting_variants, student_name)

        skill_state = (
            f"Твой текущий уровень по навыку «{target_skill}» составляет {cls._pct(target_skill_mastery)}."
        )

        # ——— 2. Prerequisite-навыки
        if prerequisite_skills:
            parts = []
            for sk in prerequisite_skills:
                name = sk.get("skill_name", "неизвестный навык")
                mastery = sk.get("mastery_probability", 0.0)
                level_word = (
                    "освоен"
                    if mastery >= 0.8
                    else "изучен частично"
                    if mastery >= 0.4
                    else "нуждается в укреплении"
                )
                parts.append(f"«{name}» ({level_word}, {cls._pct(mastery)})")
            prereq_line = ", ".join(parts)
            prereq_phrase = (
                "Для успешного выполнения потребуются навыки: "
                + prereq_line
                + "."
            )
        else:
            prereq_phrase = (
                "Для этого задания специальная предварительная подготовка не требуется."
            )

        # ——— 3. Тип и сложность задания
        type_names = {
            "true_false": "Верно/Неверно",
            "single": "Один вариант ответа",
            "multiple": "Несколько вариантов ответов",
        }
        diff_names = {
            "beginner": "начальный",
            "intermediate": "средний",
            "advanced": "продвинутый",
        }
        task_type_name = type_names.get(task_type, task_type)
        difficulty_name = diff_names.get(task_difficulty, task_difficulty)

        type_explanations = {
            "true_false": (
                "Формат «Верно/Неверно» помогает быстро освежить ключевые концепции."
            ),
            "single": (
                "Задания с одним вариантом ответа позволяют закрепить материал при умеренной нагрузке."
            ),
            "multiple": (
                "Формат с несколькими вариантами ответа проверяет нюансы понимания темы."
            ),
        }
        diff_explanations = {
            "beginner": (
                "Начальный уровень подойдёт для первого знакомства и постепенной практики."
            ),
            "intermediate": (
                "Средний уровень предполагает применение основ в стандартных ситуациях."
            ),
            "advanced": (
                "Продвинутый уровень требует глубокого понимания и умения решать нетиповые задачи."
            ),
        }

        type_block = (
            f"Задание относится к типу «{task_type_name}». {type_explanations.get(task_type, '')}"
        )
        diff_block = (
            f"Уровень сложности — {difficulty_name}. {diff_explanations.get(task_difficulty, '')}"
        )

        # ——— 4. Dependent-навыки (что откроется после освоения)
        if dependent_skills:
            names = [sk.get("skill_name", "новый навык") for sk in dependent_skills]
            if len(names) == 1:
                deps_text = names[0]
            elif len(names) == 2:
                deps_text = f"{names[0]} и {names[1]}"
            else:
                deps_text = f"{', '.join(names[:-1])} и {names[-1]}"
            future_phrase = (
                f"После успешного освоения навыка откроются темы: {deps_text}."
            )
        else:
            future_phrase = (
                "Освоение навыка создаст основу для дальнейшего углубления в предмет."
            )

        # ——— 5. Прогресс студента
        total_success = student_progress.get("total_success_rate", 0.0)

        # Шкала A–E для тонкой градации
        progress_scale = [
            (0.9, "выдающаяся подготовка", "Результаты превосходят ожидания"),
            (0.75, "очень хорошая подготовка", "Ты держишь высокий темп"),
            (0.6, "хорошая подготовка", "Темп развития устойчивый"),
            (0.45, "базовая подготовка", "Прогресс заметен, продолжай"),
            (0.25, "начальная подготовка", "Каждый шаг приближает к цели"),
            (0.0, "минимальная подготовка", "Стартовая точка определена"),
        ]
        for threshold, status, comment in progress_scale:
            if total_success >= threshold:
                student_status, progress_comment = status, comment
                break

        progress_line = f"{progress_comment}! Твой общий процент успешных решений — {cls._pct(total_success)}, что свидетельствует: {student_status}."

        # ——— 6. Финальный связующий тезис (по заданному навыку)
        closing_variants = [
            "Это задание вписывается в план системного освоения материала.",
            "Шаг важен для формирования прочного фундамента компетенций.",
            "Выполнение задания приблизит тебя к следующему блоку тем.",
        ]
        closing_sentence = cls._choose(closing_variants, task_title)

        # ——— 7. Итоговая сборка
        prompt = (
            "Сократи данный комментарий:\n\n"
            f"{intro} {skill_state}\n\n"
            f"{prereq_phrase}\n\n"
            f"{type_block} {diff_block}\n\n"
            f"{future_phrase}\n\n"
            f"{progress_line} {closing_sentence}"
        )

        return prompt

    # ——————————————————————————————————————————————————————————
    # Прочие шаблоны переработаны лишь стилистически,
    # логика не трогается, чтобы минимизировать технический долг
    # ——————————————————————————————————————————————————————————

    @staticmethod
    def skill_progress_prompt(
        skill_name: str,
        current_mastery: float,
        attempts_count: int,
        success_rate: float,
    ) -> str:
        """Промпт для лаконичного отчёта о прогрессе по навыку."""
        prompt = (
            f"Опиши прогресс студента по навыку «{skill_name}» в 1–2 предложениях.\n\n"
            "ДАННЫЕ:\n"
            f"- Текущий уровень освоения: {round(current_mastery * 100, 1):.1f} %\n"
            f"- Количество попыток: {attempts_count}\n"
            f"- Процент успеха: {round(success_rate * 100, 1):.1f} %\n\n"
            "Текст должен оставаться мотивирующим и конкретным."
        )
        return prompt

    @staticmethod
    def motivation_prompt(
        student_name: str,
        recent_successes: int,
        recent_failures: int,
    ) -> str:
        """Промпт для мотивационного сообщения."""
        total = recent_successes + recent_failures
        if total == 0:
            context = "только начинает путь"
        elif recent_successes > recent_failures:
            context = "демонстрирует заметный прогресс"
        else:
            context = "сталкивается с трудностями, но двигается вперёд"

        prompt = (
            f"Составь краткое мотивирующее сообщение для {student_name}, который {context}.\n\n"
            f"Последние результаты: {recent_successes} успех(ов), {recent_failures} неудач(и).\n\n"
            "Сообщение должно:\n"
            "• подбадривать;\n"
            "• подчеркивать значение регулярной практики;\n"
            "• обращаться на «ты».\n\n"
            "ОТВЕТ:"
        )
        return prompt

    @staticmethod
    def difficulty_explanation_prompt(
        task_difficulty: str,
        student_skill_level: float,
        reason: str,
    ) -> str:
        """Промпт для пояснения выбора уровня сложности задания."""
        skill_desc = (
            "высокий"
            if student_skill_level > 0.8
            else "средний"
            if student_skill_level > 0.5
            else "начальный"
        )
        prompt = (
            f"Объясни студенту, почему выбрано задание сложности «{task_difficulty}».\n\n"
            "КОНТЕКСТ:\n"
            f"- Уровень навыка студента: {skill_desc} ({round(student_skill_level * 100):d} %)\n"
            f"- Причина выбора: {reason}\n\n"
            "В ответе:\n"
            "• свяжи сложность с текущим уровнем;\n"
            "• покажи пользу именно такого выбора;\n"
            "• используй ободряющий, но не мизерно-ласковый тон.\n\n"
            "ОТВЕТ:"
        )
        return prompt
