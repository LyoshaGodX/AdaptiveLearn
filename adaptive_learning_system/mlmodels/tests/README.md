# Анализ Графа Навыков

Набор скриптов для парсинга, анализа и визуализации графа навыков из базы данных Django.

## Файлы

### `parse_skills_graph.py`
Основной скрипт для анализа графа навыков. Содержит класс `SkillsGraphParser` с полным функционалом.

**Возможности:**
- Парсинг графа навыков из базы данных
- Анализ структуры графа (глубина, циклы, статистика)
- Анализ прогресса студентов по навыкам  
- Построение путей изучения для навыков
- Экспорт в различные форматы (JSON, DOT, визуализация)
- Детальные отчеты

### `test_skills_parser.py`
Быстрые тесты для проверки функциональности парсера.

### `analyze_skills_graph.py`
Django management команда для удобного запуска анализа.

## Использование

### 1. Через Django shell
```python
python manage.py shell
exec(open('mlmodels/tests/parse_skills_graph.py').read())
```

### 2. Через management команду
```bash
# Полный анализ
python manage.py analyze_skills_graph

# Только экспорт данных
python manage.py analyze_skills_graph --export-only

# Экспорт в конкретную папку
python manage.py analyze_skills_graph --output-dir /path/to/output

# Путь изучения для конкретного навыка
python manage.py analyze_skills_graph --target-skill 123
```

### 3. Быстрый тест
```python
python manage.py shell
exec(open('mlmodels/tests/test_skills_parser.py').read())
```

### 4. Программное использование
```python
from mlmodels.tests.parse_skills_graph import SkillsGraphParser

parser = SkillsGraphParser()

# Парсинг графа
skills_graph = parser.parse_skills_graph()
task_skills = parser.parse_task_skills_mapping()

# Анализ
analysis = parser.analyze_graph_structure()
student_progress = parser.analyze_student_progress()

# Путь изучения
path = parser.get_skill_learning_path(skill_id=123)

# Экспорт
parser.export_graph_data('/path/to/output')
```

## Выходные данные

### Экспорт файлы
- `skills_graph.json` - граф навыков в JSON формате
- `skills_graph_viz.json` - данные для визуализации
- `skills_graph.dot` - граф в DOT формате для Graphviz

### Отчет включает
- Общая статистика графа (количество навыков, связей)
- Структурный анализ (корневые навыки, листовые, глубина)
- Обнаружение циклов в зависимостях
- Статистика прогресса студентов
- Топ навыков по различным метрикам

## Структура данных

### Граф навыков
```json
{
  "skill_id": [prerequisite_id1, prerequisite_id2, ...]
}
```

### Обратный граф  
```json
{
  "prerequisite_id": [dependent_skill_id1, dependent_skill_id2, ...]
}
```

### Связи заданий и навыков
```json
{
  "task_id": [skill_id1, skill_id2, ...],
  "skill_id": [task_id1, task_id2, ...]
}
```

## Визуализация

Сгенерированный DOT файл можно визуализировать с помощью Graphviz:

```bash
dot -Tpng skills_graph.dot -o skills_graph.png
```

## Анализ циклов

Скрипт автоматически обнаруживает циклы в зависимостях навыков, что может указывать на проблемы в структуре курса.

## Пути изучения

Для любого навыка можно построить оптимальный путь изучения, учитывающий все prerequisite зависимости.

## Примеры использования

### Найти все базовые навыки
```python
parser = SkillsGraphParser()
parser.parse_skills_graph()
root_skills = [skill_id for skill_id, prereqs in parser.skills_graph.items() if not prereqs]
```

### Найти навыки определенной глубины
```python
analysis = parser.analyze_graph_structure()
depth_2_skills = [skill_id for skill_id, depth in analysis['skill_depths'].items() if depth == 2]
```

### Получить статистику по курсу
```python
course_skills = Skill.objects.filter(courses__id=course_id).values_list('id', flat=True)
course_graph = {k: v for k, v in parser.skills_graph.items() if k in course_skills}
```
