# DQN модель для рекомендации заданий

Deep Q-Network (DQN) модель для адаптивной системы обучения, которая использует Reinforcement Learning для рекомендации оптимальных заданий студентам.

## Основные особенности

### ✅ Что учитывает модель DQN:

1. **📊 BKT параметры** - Модель получает актуальные BKT параметры (know, learn, guess, slip) для всех навыков студента
2. **📈 История попыток** - Учитывается последовательность попыток студента с результатами и временными характеристиками
3. **🎯 Параметры заданий** - Сложность, тип задания, связанные навыки
4. **🔗 Граф навыков** - Строгое соблюдение prerequisite ограничений при выборе доступных заданий

### 🏗️ Архитектура

```
Состояние студента = BKT параметры + История попыток
                     ↓
            StudentStateEncoder (LSTM + FC)
                     ↓
                Q-Network (FC слои)
                     ↓
          Q-values для каждого задания
                     ↓
    Выбор действия с учётом available_actions
```

## Структура проекта

```
mlmodels/dqn/
├── __init__.py              # Инициализация модуля
├── model.py                 # DQN модель, агент, конфигурация
├── data_processor.py        # Обработка данных из Django моделей
├── environment.py           # Среда для обучения RL агента
├── trainer.py               # Тренер для обучения DQN
├── train_dqn.py            # Основной скрипт обучения
├── test_dqn.py             # Тестирование компонентов
└── README.md               # Документация
```

## Компоненты системы

### 1. DQNConfig
Конфигурация модели с параметрами:
- Размерности эмбеддингов и скрытых слоёв
- RL параметры (gamma, epsilon, learning_rate)
- Веса компонентов награды

### 2. DQNAgent
Основной RL агент с:
- Q-network и target network
- Experience replay buffer
- Epsilon-greedy exploration
- Double DQN обучение

### 3. DQNDataProcessor
Обработчик данных, который:
- Извлекает BKT параметры из реальной базы
- Формирует историю попыток студента
- Определяет доступные действия с учётом prerequisite
- Кодирует состояние для DQN

### 4. DQNEnvironment
Среда для обучения, которая:
- Моделирует взаимодействие студент-задание
- Вычисляет награды за рекомендации
- Обновляет состояние студента
- Генерирует синтетические эпизоды

## Использование

### Быстрый старт

```bash
# Тестирование компонентов
python -m mlmodels.dqn.train_dqn --test_only

# Обучение на 500 эпизодах
python -m mlmodels.dqn.train_dqn --episodes 500

# Оценка обученной модели
python -m mlmodels.dqn.train_dqn --evaluate_only checkpoints/best_model.pth
```

### Программное использование

```python
from mlmodels.dqn.model import DQNConfig, create_dqn_agent
from mlmodels.dqn.data_processor import DQNDataProcessor
from mlmodels.dqn.trainer import DQNTrainer

# Создание и обучение
config = DQNConfig()
trainer = DQNTrainer(config)
trainer.train(num_episodes=1000)

# Получение рекомендаций
processor = DQNDataProcessor()
state_data = processor.get_student_state(student_id=123)

# Агент выбирает лучшее задание
agent = trainer.agent
recommended_task = agent.select_action(
    state=state_data['encoded_state'],
    available_actions=state_data['available_actions']
)
```

## Учёт ограничений

### Граф навыков и prerequisite

Модель строго соблюдает иерархию навыков:

```python
# Пример: для изучения "Интегралы" нужно освоить "Производные"
skills_graph = {
    'derivatives': set(),  # Базовый навык
    'integrals': {'derivatives'},  # Требует производные
    'differential_equations': {'derivatives', 'integrals'}  # Требует оба
}

# Доступные задания фильтруются автоматически
available_tasks = env.get_available_actions(mastered_skills)
```

### Система наград

Награда учитывает несколько факторов:

```python
reward = base_reward(success) + 
         skill_improvement_bonus(bkt_changes) +
         difficulty_match_bonus(optimal_difficulty) -
         prerequisite_penalty(violations)
```

## Мониторинг обучения

Во время обучения сохраняются:
- 📈 Графики loss, rewards, success rate
- 💾 Чекпоинты модели каждые N эпизодов
- 📊 JSON файлы с метриками
- 🎯 Лучшая модель по валидационной награде

## Тестирование

```bash
# Полное тестирование всех компонентов
python -m mlmodels.dqn.test_dqn

# Тесты проверяют:
# - Создание и работу компонентов
# - Кодирование состояния студента
# - Соблюдение prerequisite ограничений
# - Вычисление наград
# - Создание эпизодов обучения
# - Полный цикл обучения
```

## Отличия от DKN

| Аспект | DKN (Supervised) | DQN (Reinforcement Learning) |
|--------|------------------|------------------------------|
| **Подход** | Предсказание успеха | Оптимизация долгосрочного обучения |
| **Цель** | Точность предсказания | Максимизация наград |
| **Обучение** | Статические датасеты | Интерактивные эпизоды |
| **Адаптация** | Переобучение на новых данных | Непрерывное обучение |
| **Explore/Exploit** | Нет | Epsilon-greedy балансировка |

## Требования к данным

Минимальные требования для обучения:
- 5+ студентов с попытками
- 3+ навыка с prerequisite связями  
- 10+ заданий разной сложности
- BKT модель для расчета параметров

## Конфигурация

Основные параметры в `DQNConfig`:

```python
config = DQNConfig()
config.num_actions = 270        # Количество заданий
config.gamma = 0.99            # Дисконт фактор
config.epsilon_start = 1.0     # Начальная exploration
config.learning_rate = 0.001   # Скорость обучения
config.batch_size = 32         # Размер батча
config.memory_size = 10000     # Размер replay buffer
```

## Мониторинг производительности

Ключевые метрики:
- **Episode Reward** - общая награда за эпизод
- **Success Rate** - доля успешных рекомендаций
- **Epsilon** - текущий уровень exploration
- **Loss** - ошибка Q-network
- **Episode Length** - длина эпизодов обучения

## Интеграция с Django

Модель полностью интегрирована с Django моделями:
- `User` и `StudentProfile` - студенты
- `Skill` - навыки с prerequisite
- `Task` - задания с параметрами
- `TaskAttempt` - попытки студентов
- `StudentSkillMastery` - прогресс BKT

## Производительность

Рекомендуемые настройки для различных сценариев:

### Быстрое тестирование
```python
config.num_episodes = 100
config.batch_size = 16
config.memory_size = 1000
```

### Полноценное обучение
```python
config.num_episodes = 2000
config.batch_size = 32
config.memory_size = 10000
```

### Продакшн
```python
config.num_episodes = 5000+
config.batch_size = 64
config.memory_size = 50000
```
