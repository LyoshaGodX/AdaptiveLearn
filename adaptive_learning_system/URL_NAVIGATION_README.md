# URL Navigation Guide - Система Адаптивного Обучения

## Общая структура роутинга

Проект использует модульную структуру URL-роутинга Django, где каждое приложение имеет свой собственный файл `urls.py`.

## Глобальные маршруты (adaptive_learning/urls.py)

### Основные маршруты
- `""` (корень) - `home_redirect` - автоматическое перенаправление на главную страницу в зависимости от роли пользователя:
  - **Методист** → `/methodist/` (граф навыков)
  - **Эксперт** → `/expert/` (главная страница эксперта)  
  - **Студент** → `/student/` (главная страница студента)
  - **Неавторизованный** → `/login/` (страница входа)
- `"admin/"` - панель администратора Django
- `"login/"` - `RoleBasedLoginView` - вход в систему с автоматическим перенаправлением по роли
- `"logout/"` - `CustomLogoutView` - выход из системы
- `"edit/"` - `edit_skills` - редактирование навыков (общий доступ)

### Включенные приложения
- `"methodist/"` - модуль методиста
- `"student/"` - модуль студента
- `"expert/"` - модуль эксперта
- `"skills/"` - управление навыками
- `"mlmodels/"` - машинное обучение и модели

## Маршруты приложения Student (`student/urls.py`)

### Основные страницы
- `""` - `student_home` - главная страница студента
- `"profile/"` - `student_profile` - профиль студента
- `"profile/edit/"` - `student_profile_edit` - редактирование профиля

### Курсы
- `"courses/"` - `student_courses` - список доступных курсов
- `"courses/enroll/<str:course_id>/"` - `student_course_enroll` - запись на курс
- `"courses/detail/<int:enrollment_id>/"` - `student_course_detail` - детали курса

## Маршруты приложения Methodist (`methodist/urls.py`)

### Управление навыками
- `""` - `methodist_skills` - граф навыков
- `"edit/"` - `methodist_edit` - редактирование навыков
- `"edit_skill/"` - `methodist_edit_skill` - редактирование конкретного навыка
- `"delete_skill/"` - `methodist_delete_skill` - удаление навыка
- `"update_skill_courses/"` - `methodist_update_skill_courses` - обновление курсов навыка

### Управление заданиями
- `"tasks/"` - `methodist_tasks` - список заданий
- `"tasks/create/"` - `methodist_task_create` - создание задания
- `"tasks/<int:task_id>/edit/"` - `methodist_task_edit` - редактирование задания
- `"tasks/<int:task_id>/delete/"` - `methodist_task_delete` - удаление задания

### Управление курсами
- `"courses/"` - `methodist_courses` - список курсов
- `"courses/create/"` - `methodist_course_create` - создание курса
- `"courses/<str:course_id>/edit/"` - `methodist_course_edit` - редактирование курса
- `"courses/<str:course_id>/delete/"` - `methodist_course_delete` - удаление курса

### Управление зачислением
- `"enrollment/"` - `methodist_enrollment` - управление зачислением
- `"enrollment/enroll/"` - `methodist_enroll_student` - зачисление студента
- `"enrollment/unenroll/"` - `methodist_unenroll_student` - отчисление студента
- `"enrollment/status/"` - `methodist_update_enrollment_status` - обновление статуса зачисления

### API для работы с навыками
- `"api/skills/<int:skill_id>/details/"` - детали навыка
- `"api/skills/<int:skill_id>/courses/"` - курсы навыка
- `"api/add_prerequisite/"` - добавление предпосылки
- `"api/remove_prerequisite/"` - удаление предпосылки
- `"api/remove_dependent/"` - удаление зависимости

### API для работы с курсами
- `"api/skills/"` - список навыков
- `"api/tasks/"` - список заданий
- `"api/course/<str:course_id>/"` - данные курса
- `"api/courses/<str:course_id>/skills/"` - навыки курса
- `"api/courses/<str:course_id>/tasks/"` - задания курса
- `"api/update_course_skills/"` - обновление навыков курса
- `"api/update_course_tasks/"` - обновление заданий курса

### API для управления зачислением
- `"api/student/<int:student_id>/enrollments/"` - зачисления студента
- `"api/course/<str:course_id>/enrollments/"` - зачисления на курс

### Тестовые маршруты (без аутентификации)
- `"test/api/skills/"` - тестовый список навыков
- `"test/api/tasks/"` - тестовый список заданий
- `"test/courses/create/"` - тестовое создание курса
- `"test/course/form/"` - тестовая форма курса

## Маршруты приложения Expert (`expert/urls.py`)

- `""` - `expert_home` - главная страница эксперта

## Маршруты приложения Skills (`skills/urls.py`)

### Основные страницы
- `""` - `skills_list` - список навыков
- `"edit/"` - `skills_edit` - редактирование навыков
- `"edit_skill/"` - `edit_skill` - редактирование навыка
- `"delete_skill/"` - `delete_skill` - удаление навыка
- `"update_skill_courses/"` - `update_skill_courses` - обновление курсов навыка

### API маршруты
- `"api/skills/<int:skill_id>/courses/"` - курсы навыка
- `"api/skills/<int:skill_id>/details/"` - детали навыка
- `"api/add_prerequisite/"` - добавление предпосылки
- `"api/remove_prerequisite/"` - удаление предпосылки
- `"api/remove_dependent/"` - удаление зависимости

## Маршруты приложения MLModels (`mlmodels/urls.py`)

### API для работы с моделями BKT
- `"api/student/<int:student_id>/profile/"` - профиль студента
- `"api/student/<int:student_id>/attempts/"` - попытки студента
- `"api/student/<int:student_id>/masteries/"` - мастерство студента
- `"api/progress/update/"` - обновление прогресса студента

## Дополнительная конфигурация

### Статические файлы
В режиме отладки (`DEBUG=True`) автоматически добавляются маршруты для:
- `STATIC_URL` - статические файлы
- `MEDIA_URL` - медиа файлы

### Настройки URL
- `APPEND_SLASH = False` - URL могут работать как с окончающим слешем, так и без него

## Схема навигации по ролям

### Студент
- Домашняя страница: `/student/`
- Профиль: `/student/profile/`
- Курсы: `/student/courses/`
- Запись на курс: `/student/courses/enroll/{course_id}/`

### Методист
- Граф навыков: `/methodist/`
- Управление заданиями: `/methodist/tasks/`
- Управление курсами: `/methodist/courses/`
- Управление зачислением: `/methodist/enrollment/`

### Эксперт
- Домашняя страница: `/expert/`

### Общие
- Вход: `/login/`
- Выход: `/logout/`
- Редактирование навыков: `/edit/`

## Примечания по безопасности

- Большинство маршрутов требуют аутентификации
- Тестовые маршруты (`/methodist/test/`) работают без аутентификации
- API маршруты могут требовать дополнительных прав доступа
- Роли пользователей определяют доступные разделы системы

## Определение ролей пользователей

Система использует два подхода для определения роли пользователя:

1. **Группы Django** (основной подход):
   - `methodist` - методисты системы
   - `expert` - эксперты-предметники
   - `student` - студенты
   - Супер-пользователи автоматически получают права методиста

2. **Fallback по имени пользователя** (для совместимости):
   - Если в имени пользователя содержится `methodist` → роль методиста
   - Если в имени пользователя содержится `expert` → роль эксперта
   - Остальные пользователи → роль студента

Для создания тестовых пользователей с группами используйте команду:
```bash
python manage.py create_test_users
```
