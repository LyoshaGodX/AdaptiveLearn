# База данных системы адаптивного обучения

## Обзор архитектуры

Система адаптивного обучения использует Django ORM и SQLite базу данных. База данных организована в несколько основных модулей:

- **Student** - модели студентов и их профилей
- **Skills** - модели курсов и навыков  
- **Methodist** - модели заданий и ответов
- **MLModels** - модели машинного обучения (BKT, DQN, аналитика)

---

## 📚 Модуль Student (Студенты)

### 1. StudentProfile
**Описание**: Профиль студента - расширение стандартной модели User Django

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | AutoField | Первичный ключ |
| `user` | OneToOneField(User) | Связь с пользователем Django |
| `full_name` | CharField(255) | ФИО студента |
| `email` | EmailField | Контактный email |
| `organization` | CharField(255) | Учебное заведение (опционально) |
| `profile_photo` | ImageField | Фото профиля (опционально) |
| `created_at` | DateTimeField | Дата создания |
| `updated_at` | DateTimeField | Дата обновления |
| `is_active` | BooleanField | Активность профиля |

**Связи:**
- `user` → User (один-к-одному)
- `course_enrollments` ← StudentCourseEnrollment (один-ко-многим)
- `skill_masteries` ← StudentSkillMastery (один-ко-многим)
- `task_attempts` ← TaskAttempt (один-ко-многим)
- `dqn_recommendations` ← DQNRecommendation (один-ко-многим)
- `current_recommendation` ← StudentCurrentRecommendation (один-к-одному)

### 2. StudentCourseEnrollment
**Описание**: Запись студентов на курсы

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | AutoField | Первичный ключ |
| `student` | ForeignKey(StudentProfile) | Студент |
| `course` | ForeignKey(Course) | Курс |
| `enrolled_at` | DateTimeField | Дата записи |
| `status` | CharField(20) | Статус: enrolled/in_progress/completed/suspended/dropped |
| `progress_percentage` | PositiveIntegerField | Прогресс (0-100%) |
| `completed_at` | DateTimeField | Дата завершения (опционально) |
| `final_grade` | DecimalField(5,2) | Итоговая оценка (опционально) |
| `instructor_notes` | TextField | Комментарии преподавателя (опционально) |

**Связи:**
- `student` → StudentProfile
- `course` → Course

**Ограничения:**
- Уникальность: student + course

---

## 🎯 Модуль Skills (Навыки и курсы)

### 3. Course
**Описание**: Модель курса

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | CharField(10) | Первичный ключ (строка) |
| `name` | CharField(255) | Название курса |
| `description` | TextField | Описание курса |
| `duration_hours` | PositiveIntegerField | Длительность в часах (опционально) |

**Связи:**
- `skills` ← Skill (многие-ко-многим)
- `tasks` ← Task (многие-ко-многим)
- `student_enrollments` ← StudentCourseEnrollment (один-ко-многим)

### 4. Skill
**Описание**: Модель навыка

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | AutoField | Первичный ключ |
| `name` | CharField(255) | Название навыка (уникальное) |
| `description` | TextField | Описание навыка (опционально) |
| `is_base` | BooleanField | Является ли базовым навыком |

**Связи:**
- `courses` ↔ Course (многие-ко-многим)
- `prerequisites` ↔ Skill (многие-ко-многим, самоссылка)
- `dependent_skills` ← Skill (обратная связь к prerequisites)
- `tasks` ← Task (многие-ко-многим)
- `student_masteries` ← StudentSkillMastery (один-ко-многим)

---

## 📝 Модуль Methodist (Задания)

### 5. Task
**Описание**: Модель задания

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | AutoField | Первичный ключ |
| `title` | CharField(255) | Название задания |
| `task_type` | CharField(20) | Тип: single/multiple/true_false |
| `difficulty` | CharField(20) | Сложность: beginner/intermediate/advanced |
| `question_text` | TextField | Формулировка задачи |
| `created_at` | DateTimeField | Дата создания |
| `updated_at` | DateTimeField | Дата обновления |
| `is_active` | BooleanField | Активность задания |

**Связи:**
- `skills` ↔ Skill (многие-ко-многим)
- `courses` ↔ Course (многие-ко-многим)
- `answers` ← TaskAnswer (один-ко-многим)
- `student_attempts` ← TaskAttempt (один-ко-многим)
- `dqn_recommendations` ← DQNRecommendation (один-ко-многим)

### 6. TaskAnswer
**Описание**: Варианты ответов для заданий с выбором

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | AutoField | Первичный ключ |
| `task` | ForeignKey(Task) | Задание |
| `text` | TextField | Текст ответа |
| `is_correct` | BooleanField | Правильность ответа |
| `order` | IntegerField | Порядок отображения |

**Связи:**
- `task` → Task

---

## 🤖 Модуль MLModels (Машинное обучение)

### 7. StudentSkillMastery
**Описание**: Освоение навыков студентами (для BKT модели)

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | AutoField | Первичный ключ |
| `student` | ForeignKey(StudentProfile) | Студент |
| `skill` | ForeignKey(Skill) | Навык |
| `initial_mastery_prob` | FloatField | P(L0) - начальная вероятность освоения |
| `current_mastery_prob` | FloatField | P(Lt) - текущая вероятность освоения |
| `transition_prob` | FloatField | P(T) - вероятность перехода |
| `guess_prob` | FloatField | P(G) - вероятность угадывания |
| `slip_prob` | FloatField | P(S) - вероятность ошибки |
| `last_updated` | DateTimeField | Последнее обновление |
| `attempts_count` | PositiveIntegerField | Количество попыток |
| `correct_attempts` | PositiveIntegerField | Правильные попытки |

**Связи:**
- `student` → StudentProfile
- `skill` → Skill

**Ограничения:**
- Уникальность: student + skill

### 8. TaskAttempt
**Описание**: Попытки решения заданий студентами

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | AutoField | Первичный ключ |
| `student` | ForeignKey(StudentProfile) | Студент |
| `task` | ForeignKey(Task) | Задание |
| `is_correct` | BooleanField | Правильность ответа |
| `given_answer` | TextField | Данный ответ (опционально) |
| `correct_answer` | TextField | Правильный ответ (опционально) |
| `started_at` | DateTimeField | Время начала |
| `completed_at` | DateTimeField | Время завершения |
| `time_spent` | PositiveIntegerField | Время решения (секунды) |
| `metadata` | JSONField | Дополнительные данные |
| `llm_explanation` | TextField | LLM объяснение рекомендации |

**Связи:**
- `student` → StudentProfile
- `task` → Task
- `dqn_recommendation` ← DQNRecommendation (один-к-одному)

### 9. StudentLearningProfile
**Описание**: Профиль обучения студента (агрегированные характеристики)

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | AutoField | Первичный ключ |
| `student` | OneToOneField(StudentProfile) | Студент |
| `learning_speed` | FloatField | Скорость обучения (0-1) |
| `persistence_level` | FloatField | Уровень настойчивости (0-1) |
| `difficulty_preference` | CharField(20) | Предпочтения: easy/medium/hard/adaptive |
| `total_attempts` | PositiveIntegerField | Общее количество попыток |
| `total_correct` | PositiveIntegerField | Правильные ответы |
| `average_time_per_task` | FloatField | Среднее время на задание (мин) |
| `first_activity` | DateTimeField | Первая активность |
| `last_activity` | DateTimeField | Последняя активность |
| `last_updated` | DateTimeField | Последнее обновление |

**Связи:**
- `student` → StudentProfile (один-к-одному)

### 10. DQNRecommendation
**Описание**: Рекомендации DQN системы

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | AutoField | Первичный ключ |
| `student` | ForeignKey(StudentProfile) | Студент |
| `task` | ForeignKey(Task) | Рекомендованное задание |
| `q_value` | FloatField | Q-value рекомендации |
| `confidence` | FloatField | Уверенность модели (0-1) |
| `reason` | CharField(500) | Причина рекомендации |
| `student_state_snapshot` | JSONField | Снимок состояния студента |
| `created_at` | DateTimeField | Время создания |
| `is_active` | BooleanField | Активность рекомендации |
| `attempt` | OneToOneField(TaskAttempt) | Связанная попытка |
| `prerequisite_skills_snapshot` | JSONField | Снимок prerequisite навыков |
| `dependent_skills_snapshot` | JSONField | Снимок зависимых навыков |
| `target_skill_info` | JSONField | Информация о целевом навыке |
| `alternative_tasks_considered` | JSONField | Рассмотренные альтернативы |
| `student_progress_context` | JSONField | Контекст прогресса студента |
| `llm_explanation` | TextField | LLM объяснение |
| `llm_explanation_generated_at` | DateTimeField | Время генерации объяснения |

**Связи:**
- `student` → StudentProfile
- `task` → Task
- `attempt` → TaskAttempt (один-к-одному)
- `current_for_students` ← StudentCurrentRecommendation (один-ко-многим)
- `expert_feedback` ← ExpertFeedback (один-ко-многим)

### 11. StudentCurrentRecommendation
**Описание**: Текущая рекомендация студента

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | AutoField | Первичный ключ |
| `student` | OneToOneField(StudentProfile) | Студент |
| `recommendation` | ForeignKey(DQNRecommendation) | Текущая рекомендация |
| `set_at` | DateTimeField | Время установки |
| `times_viewed` | PositiveIntegerField | Количество просмотров |
| `llm_explanation` | TextField | LLM объяснение |

**Связи:**
- `student` → StudentProfile (один-к-одному)
- `recommendation` → DQNRecommendation

### 12. ExpertFeedback
**Описание**: Экспертная разметка рекомендаций

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | AutoField | Первичный ключ |
| `recommendation` | ForeignKey(DQNRecommendation) | Рекомендация |
| `expert` | ForeignKey(User) | Эксперт |
| `feedback_type` | CharField(20) | Тип: positive/negative |
| `strength` | CharField(20) | Сила: low/medium/high |
| `reward_value` | FloatField | Численное значение награды |
| `comment` | TextField | Комментарий эксперта |
| `created_at` | DateTimeField | Время создания |
| `is_used_for_training` | BooleanField | Использовано для обучения |

**Связи:**
- `recommendation` → DQNRecommendation
- `expert` → User

**Ограничения:**
- Уникальность: recommendation + expert

### 13. DQNTrainingSession
**Описание**: Сессии дообучения DQN модели

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | AutoField | Первичный ключ |
| `name` | CharField(200) | Название сессии |
| `description` | TextField | Описание |
| `learning_rate` | FloatField | Скорость обучения |
| `batch_size` | PositiveIntegerField | Размер батча |
| `num_epochs` | PositiveIntegerField | Количество эпох |
| `feedback_count` | PositiveIntegerField | Количество размеченных данных |
| `status` | CharField(20) | Статус: pending/running/completed/failed |
| `started_at` | DateTimeField | Время начала |
| `completed_at` | DateTimeField | Время завершения |
| `initial_loss` | FloatField | Начальная потеря |
| `final_loss` | FloatField | Финальная потеря |
| `training_history` | JSONField | История обучения |
| `model_path` | CharField(500) | Путь к модели |
| `error_message` | TextField | Сообщение об ошибке |
| `created_by` | ForeignKey(User) | Создатель |
| `created_at` | DateTimeField | Время создания |

**Связи:**
- `created_by` → User

---

## 🔄 Диаграмма связей

```
User (Django) ─┬─ StudentProfile ─┬─ StudentCourseEnrollment ─ Course ─ Skill
               │                  ├─ StudentSkillMastery ────────────────┘
               │                  ├─ TaskAttempt ─ Task ─┬─ TaskAnswer
               │                  │                      └─ Skills (M2M)
               │                  ├─ StudentLearningProfile
               │                  ├─ DQNRecommendation ──┬─ Task
               │                  │                      └─ TaskAttempt
               │                  └─ StudentCurrentRecommendation
               │
               └─ ExpertFeedback ── DQNRecommendation
               └─ DQNTrainingSession
```

---

## 📊 Основные метрики и индексы

### Рекомендуемые индексы для производительности:
- `StudentProfile.user_id` (уникальный)
- `TaskAttempt.student_id, TaskAttempt.completed_at`
- `StudentSkillMastery.student_id, StudentSkillMastery.skill_id`
- `DQNRecommendation.student_id, DQNRecommendation.created_at`
- `StudentCurrentRecommendation.student_id` (уникальный)

### Вычисляемые поля:
- `StudentSkillMastery.accuracy` - точность решения по навыку
- `StudentSkillMastery.is_mastered` - освоен ли навык (P >= 0.8)
- `StudentLearningProfile.overall_accuracy` - общая точность
- `TaskAttempt.duration_minutes` - время решения в минутах

---

## 🛠 Автоматические процессы

### Сигналы Django:
1. **При создании User** → автоматическое создание StudentProfile (если username содержит 'student')
2. **При сохранении TaskAttempt** → автоматическое обновление BKT параметров в StudentSkillMastery
3. **При сохранении TaskAttempt** → автоматическая генерация новой DQN рекомендации

### Триггеры обновления:
- BKT вероятности обновляются при каждой попытке решения задания
- Профиль обучения пересчитывается при значительных изменениях в активности студента
- DQN рекомендации генерируются автоматически после выполнения заданий

---

## 📁 Файлы моделей

1. `student/models.py` - StudentProfile, StudentCourseEnrollment
2. `skills/models.py` - Course, Skill  
3. `methodist/models.py` - Task, TaskAnswer
4. `mlmodels/models.py` - все модели машинного обучения

---

*Данный документ содержит полное описание всех моделей базы данных системы адаптивного обучения по состоянию на 16 июня 2025 года.*
