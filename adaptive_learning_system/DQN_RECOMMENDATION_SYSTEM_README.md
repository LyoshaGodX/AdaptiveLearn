# 🤖 DQN Рекомендательная система для адаптивного обучения

## 📋 Оглавление
- [Обзор системы](#обзор-системы)
- [Архитектура](#архитектура)
- [Модели базы данных](#модели-базы-данных)
- [Компоненты DQN](#компоненты-dqn)
- [Система буферизации](#система-буферизации)
- [Экспертное подкрепление](#экспертное-подкрепление)
- [Тестирование](#тестирование)
- [Использование](#использование)
- [Статус разработки](#статус-разработки)

## 🎯 Обзор системы

Система DQN (Deep Q-Network) для адаптивного обучения предназначена для генерации персонализированных рекомендаций заданий студентам на основе их текущего состояния обучения, истории попыток и графа навыков.

### Ключевые особенности:
- ✅ **Автоматическая генерация рекомендаций** после каждой попытки студента
- ✅ **Фильтрация по освоенности навыков** и prerequisite
- ✅ **Буферизация рекомендаций** (20 записей на студента)
- ✅ **Связывание попытка-рекомендация** для отслеживания эффективности
- ✅ **Экспертное подкрепление** для дообучения модели
- ✅ **BKT интеграция** для оценки освоения навыков

## 🏗️ Архитектура

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   StudentProfile│───▶│  TaskAttempt    │───▶│ DQNRecommendation│
│   (Студент)     │    │  (Попытка)      │    │ (Рекомендация)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│StudentSkillMastery│   │      BKT        │    │ ExpertFeedback  │
│   (BKT данные)  │    │  (Обновление)   │    │ (Экспертная     │
└─────────────────┘    └─────────────────┘    │  оценка)        │
                                              └─────────────────┘
```

## 💾 Модели базы данных

### 1. `DQNRecommendation` - Основная модель рекомендаций

```python
class DQNRecommendation(models.Model):
    # Связи
    student = ForeignKey(StudentProfile)         # Студент
    task = ForeignKey(Task)                      # Рекомендованное задание
    attempt = OneToOneField(TaskAttempt)         # Связанная попытка (если выполнена)
    
    # DQN данные
    q_value = FloatField()                       # Q-value модели
    confidence = FloatField()                    # Уверенность (0-1)
    reason = CharField(max_length=500)           # Причина рекомендации
    student_state_snapshot = JSONField()         # Снимок состояния студента
    
    # Метаданные
    created_at = DateTimeField(auto_now_add=True)
    is_active = BooleanField(default=True)
```

**Функции:**
- Хранение всех рекомендаций с полным контекстом
- Связывание с попытками для отслеживания эффективности
- Буферизация (максимум 20 записей на студента)

### 2. `StudentCurrentRecommendation` - Текущая рекомендация

```python
class StudentCurrentRecommendation(models.Model):
    student = OneToOneField(StudentProfile)      # Один студент - одна текущая рекомендация
    recommendation = ForeignKey(DQNRecommendation)  # Ссылка на рекомендацию
    set_at = DateTimeField(auto_now=True)        # Время установки
    times_viewed = PositiveIntegerField(default=0)  # Количество просмотров
```

**Функции:**
- Отслеживание активной рекомендации для каждого студента
- Статистика просмотров
- Быстрый доступ к текущей рекомендации

### 3. `ExpertFeedback` - Экспертное подкрепление

```python
class ExpertFeedback(models.Model):
    # Связи
    recommendation = ForeignKey(DQNRecommendation)  # Оцениваемая рекомендация
    expert = ForeignKey(User)                    # Эксперт
    
    # Подкрепление
    feedback_type = CharField(choices=[          # 'positive' / 'negative'
        ('positive', 'Положительное'),
        ('negative', 'Отрицательное'),
    ])
    strength = CharField(choices=[               # 'low' / 'medium' / 'high'
        ('low', 'Низкая'),
        ('medium', 'Средняя'), 
        ('high', 'Высокая'),
    ])
    reward_value = FloatField()                  # Численная награда (-1.0 до +1.0)
    comment = TextField(blank=True)              # Комментарий эксперта
    
    # Метаданные
    created_at = DateTimeField(auto_now_add=True)
    is_used_for_training = BooleanField(default=False)  # Использовано для обучения
```

**Автоматический расчет награды:**
```python
def calculate_reward_value(self):
    base_values = {'low': 0.1, 'medium': 0.5, 'high': 1.0}
    base_reward = base_values.get(self.strength, 0.5)
    return base_reward if self.feedback_type == 'positive' else -base_reward
```

## 🧠 Компоненты DQN

### 1. `DQNDataProcessor` - Обработка данных
- **Извлечение BKT параметров** студента
- **Формирование вектора состояния** для DQN
- **Фильтрация действий** по освоенности и prerequisite
- **Исключение переизученных заданий**

### 2. `DQNModel` - Нейронная сеть
- **Архитектура:** Полносвязная сеть с dropout
- **Вход:** Вектор состояния студента
- **Выход:** Q-values для доступных заданий

### 3. `DQNRecommender` - Генератор рекомендаций
- **Получение рекомендаций** на основе DQN
- **Ранжирование заданий** по Q-value
- **Формирование объяснений** рекомендаций

### 4. `DQNRecommendationManagerFixed` - Менеджер рекомендаций
- **Автоматическое создание** рекомендаций
- **Связывание попытка-рекомендация**
- **Управление буфером** (20 записей)
- **Обновление текущих рекомендаций**

## 🗃️ Система буферизации

### Механизм буфера попытка-рекомендация:

1. **Создание рекомендации** → сохранение в `DQNRecommendation`
2. **Выполнение попытки** → связывание через поле `attempt`
3. **Поддержание размера буфера** → удаление старых записей (>20)

```python
def _maintain_buffer_size(self, student: StudentProfile):
    """Поддерживает размер буфера рекомендаций (20 записей)"""
    recommendations = DQNRecommendation.objects.filter(
        student=student
    ).order_by('-created_at')
    
    if recommendations.count() > self.buffer_size:  # buffer_size = 20
        old_recommendations = recommendations[self.buffer_size:]
        old_ids = [rec.id for rec in old_recommendations]
        DQNRecommendation.objects.filter(id__in=old_ids).delete()
```

### Автоматическое связывание:

```python
# В TaskAttempt.save():
def _create_dqn_recommendation(self):
    # 1. Связать попытку с текущей рекомендацией
    recommendation_manager_fixed.link_attempt_to_recommendation(
        attempt_id=self.id,
        recommendation_id=None  # Автоматический поиск
    )
    
    # 2. Создать новую рекомендацию
    new_rec = recommendation_manager_fixed.generate_and_save_recommendation(
        student_id=self.student.user.id,
        set_as_current=True
    )
```

## 🏆 Экспертное подкрепление

### Возможности экспертной оценки:

#### ✅ **УЖЕ РЕАЛИЗОВАНО:**
1. **Модель `ExpertFeedback`** с полным функционалом
2. **Градация подкрепления:**
   - Тип: положительное/отрицательное
   - Сила: низкая/средняя/высокая
   - Автоматический расчет награды: -1.0 до +1.0
3. **Комментарии экспертов** с обоснованием
4. **Отслеживание использования** для обучения

#### 🚧 **НУЖНО РЕАЛИЗОВАТЬ:**
1. **Веб-интерфейс эксперта:**
   - Список рекомендаций для оценки
   - Форма подачи feedback
   - История экспертных оценок

2. **API для экспертной оценки:**
   ```python
   # Примерный API
   POST /api/expert/feedback/
   {
       "recommendation_id": 123,
       "feedback_type": "positive", 
       "strength": "high",
       "comment": "Отличная рекомендация для этого студента"
   }
   ```

3. **Интеграция с обучением DQN:**
   - Использование expert rewards
   - Дообучение модели на экспертных оценках

## 🧪 Тестирование

### Основные тесты:

1. **`test_recommendation_filtering.py`** - Тест фильтрации заданий
   - Проверка исключения освоенных навыков
   - Проверка фильтрации по prerequisite
   - Проверка исключения переизученных заданий

2. **`test_student_analysis.py`** - Анализ состояния студента  
   - BKT оценки навыков
   - Доступные навыки для изучения
   - Связи попытка-рекомендация
   - Текущие рекомендации

3. **`test_recommendation_execution.py`** - Выполнение рекомендаций
   - Симуляция выполнения попытки
   - Проверка автоматического создания рекомендаций

### Интеграционные тесты:
- **`test_automatic_recommendations.py`** - Автоматическая работа системы
- **`test_feedback_cycle.py`** - Цикл обратной связи
- **`create_test_attempt.py`** - Создание тестовых попыток

## 🚀 Использование

### Создание рекомендации:
```python
from mlmodels.dqn.recommendation_manager_fixed import recommendation_manager_fixed

# Создать рекомендацию для студента
recommendation = recommendation_manager_fixed.generate_and_save_recommendation(
    student_id=15,
    set_as_current=True
)
```

### Получение текущей рекомендации:
```python
from mlmodels.models import StudentCurrentRecommendation

current = StudentCurrentRecommendation.objects.get(student__user_id=15)
task = current.recommendation.task
```

### Добавление экспертной оценки:
```python
from mlmodels.models import ExpertFeedback, DQNRecommendation

feedback = ExpertFeedback.objects.create(
    recommendation_id=recommendation_id,
    expert=expert_user,
    feedback_type='positive',
    strength='high',
    comment='Отличная рекомендация!'
)
```

## 📊 Статус разработки

### ✅ **ПОЛНОСТЬЮ РЕАЛИЗОВАНО:**
- ✅ Модели базы данных
- ✅ DQN компоненты (model, data_processor, recommender)
- ✅ Автоматическое создание рекомендаций
- ✅ Система буферизации (20 записей)
- ✅ Связывание попытка-рекомендация
- ✅ Фильтрация по BKT и prerequisite
- ✅ Экспертное подкрепление (модель)
- ✅ Интеграция с BKT
- ✅ Комплексное тестирование

### 🚧 **В РАЗРАБОТКЕ:**
- 🚧 Веб-интерфейс для экспертов
- 🚧 Дообучение DQN на экспертных оценках
- 🚧 Расширенная аналитика рекомендаций

### 🎯 **ГОТОВО К ИСПОЛЬЗОВАНИЮ:**
Система полностью функциональна и готова к использованию в продакшене. 
Все основные компоненты работают автоматически при создании попыток студентов.

---

## 📝 Примечания для разработчиков

### Ключевые файлы:
- `mlmodels/models.py` - Модели БД
- `mlmodels/dqn/recommendation_manager_fixed.py` - Основная логика
- `mlmodels/dqn/data_processor.py` - Обработка данных
- `mlmodels/dqn/recommender.py` - Генерация рекомендаций
- `mlmodels/dqn/tests/` - Тесты системы

### Конфигурация:
- **Буфер:** 20 рекомендаций на студента
- **BKT порог освоения:** 0.85
- **Порог переизучения:** 3 правильных ответа подряд
- **DQN архитектура:** 128-64-32 нейронов + dropout

**Система готова к масштабированию и дальнейшему развитию!** 🎉
