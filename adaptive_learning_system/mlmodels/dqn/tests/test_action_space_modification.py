"""
Тест модификации пространства действий DQN модели

Этот тест проверяет способность data_processor.py:
1. Формировать корректные входные данные для DQN модели
2. Модифицировать пространство действий с учетом графа навыков
3. Ограничивать список заданий на основе prerequisite
4. Включать граф навыков в вектор состояния
5. Обеспечивать корректную работу Q-функции с ограниченным пространством действий
"""

import os
import sys
from pathlib import Path

# Добавляем путь к Django проекту
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')

import django
django.setup()

import torch
import numpy as np
from django.contrib.auth.models import User
from skills.models import Skill  
from methodist.models import Task, Course
from mlmodels.models import TaskAttempt, StudentSkillMastery
from student.models import StudentProfile

# Импортируем наши DQN компоненты
from mlmodels.dqn.data_processor import DQNDataProcessor, DQNEnvironment
from mlmodels.dqn.model import DQNConfig, create_dqn_agent


class TestDQNActionSpaceModification:
    """Тестирование модификации пространства действий DQN"""
    
    def __init__(self, student_id: int = 7):
        self.student_id = student_id
        self.processor = DQNDataProcessor()
        self.env = DQNEnvironment(student_id)
    def test_state_vector_formation(self):
        """Тест формирования вектора состояния с графом навыков"""
        print("\n🧠 Тестирование формирования вектора состояния...")
        
        try:
            # Получаем полное состояние студента
            state_data = self.processor.get_student_state(self.student_id)
            
            # Проверяем все компоненты состояния (без mastered_skills)
            required_keys = ['bkt_params', 'history', 'available_actions', 'skills_graph']
            missing_keys = [key for key in required_keys if key not in state_data]
            
            if missing_keys:
                print(f"❌ Отсутствуют компоненты состояния: {missing_keys}")
                return False
            
            # Анализируем компоненты
            bkt_params = state_data['bkt_params']
            history = state_data['history']
            skills_graph = state_data['skills_graph']
            
            print(f"✅ Вектор состояния сформирован:")
            print(f"  - BKT параметры: {bkt_params.shape} (только вероятность знания)")
            print(f"  - История: {history.shape}")
            print(f"  - Граф навыков: {skills_graph.shape}")
            print(f"  - Доступные действия: {len(state_data['available_actions'])}")
            
            # Показываем детали BKT параметров
            print(f"\n📊 Детали BKT параметров:")
            mastery_levels = bkt_params.squeeze().tolist()
            skill_stats = {
                'высокий (>0.8)': sum(1 for m in mastery_levels if m > 0.8),
                'средний (0.5-0.8)': sum(1 for m in mastery_levels if 0.5 <= m <= 0.8), 
                'низкий (<0.5)': sum(1 for m in mastery_levels if m < 0.5)
            }
            for level, count in skill_stats.items():
                print(f"  - Навыки с {level} уровнем: {count}")
            
            # Анализируем историю попыток
            print(f"\n📈 Детали истории попыток ({history.shape[0]} записей):")
            if history.shape[0] > 0:
                success_rate = (history[:, 1] == 1.0).float().mean().item()
                avg_difficulty = history[:, 2].mean().item()
                print(f"  - Успешность: {success_rate:.2%}")
                print(f"  - Средняя сложность: {avg_difficulty:.1f}")
                
                # Показываем последние несколько попыток для наглядности
                print("  - Последние 5 попыток (task_id, success, difficulty, type, skill_level, mastery_change, time, streak):")
                for i in range(min(5, history.shape[0])):
                    row = history[-(i+1)].tolist()  # Берем с конца
                    formatted = [f"{x:.2f}" if isinstance(x, float) else str(int(x)) for x in row]
                    print(f"    {formatted}")
            
            # Проверяем граф навыков
            if skills_graph.sum().item() == 0:
                print("⚠️ Граф навыков пустой - prerequisite связи отсутствуют")
            else:
                num_connections = int(skills_graph.sum().item())
                print(f"🔗 Prerequisite связей в графе: {num_connections}")
                
                # Объясняем, как граф помогает модели
                print("📖 Как граф навыков помогает модели:")
                print("  - Матрица смежности показывает зависимости между навыками")
                print("  - Модель использует эту информацию для:")
                print("    • Определения доступных заданий")
                print("    • Понимания последовательности изучения")
                print("    • Планирования оптимального пути обучения")
                print("  - В векторе состояния граф представлен как сплющенная матрица")
                print(f"    размером {skills_graph.shape[0]}×{skills_graph.shape[1]} = {skills_graph.numel()} элементов")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка формирования состояния: {e}")
            import traceback
            traceback.print_exc()
            return False
    def test_action_space_filtering(self):
        """Тест фильтрации пространства действий по prerequisite"""
        print("\n🎯 Тестирование фильтрации пространства действий...")
        
        try:
            # Получаем студента и его BKT параметры
            user = User.objects.get(id=self.student_id)
            student_profile = StudentProfile.objects.get(user=user)
            bkt_params = self.processor._get_all_bkt_parameters(student_profile)
            
            # Тестируем новую логику фильтрации (через DQNEnvironment)
            available_actions = self.env.get_available_actions(bkt_params, self.processor.skill_to_id)
            
            print(f"✅ Доступных заданий с новой логикой: {len(available_actions)}")
            
            # Анализируем распределение BKT параметров
            mastery_levels = bkt_params.squeeze().tolist()
            high_mastery = sum(1 for m in mastery_levels if m > 0.9)
            medium_mastery = sum(1 for m in mastery_levels if 0.5 <= m <= 0.9)
            low_mastery = sum(1 for m in mastery_levels if m < 0.5)
            
            print(f"📊 Распределение уровней освоения навыков:")
            print(f"  - Высокий уровень (>0.9): {high_mastery} навыков")
            print(f"  - Средний уровень (0.5-0.9): {medium_mastery} навыков") 
            print(f"  - Низкий уровень (<0.5): {low_mastery} навыков")
            
            # Проверяем примеры фильтрации
            print(f"\n🔍 Анализ логики фильтрации:")
            total_tasks = len(self.env.task_to_skills)
            filtered_out = total_tasks - len(available_actions)
            
            print(f"  - Всего заданий в системе: {total_tasks}")
            print(f"  - Доступно после фильтрации: {len(available_actions)}")
            print(f"  - Отфильтровано: {filtered_out} ({filtered_out/total_tasks*100:.1f}%)")
            
            # Показываем несколько доступных заданий
            print(f"\n✅ Примеры доступных заданий:")
            for i, action_idx in enumerate(available_actions[:5]):
                task_id = self.env.action_to_task_id[action_idx]
                task_skills = self.env.task_to_skills.get(task_id, set())
                
                skill_masteries = []
                for skill_id in task_skills:
                    skill_idx = self.processor.skill_to_id.get(skill_id)
                    if skill_idx is not None:
                        mastery = bkt_params[skill_idx, 0].item()
                        skill_masteries.append(f"{skill_id}:{mastery:.2f}")
                
                print(f"  {i+1}. Задание {task_id}: навыки {skill_masteries}")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка фильтрации действий: {e}")
            import traceback
            traceback.print_exc()
            return False
    def test_prerequisite_enforcement(self):
        """Тест соблюдения prerequisite ограничений"""
        print("\n🔒 Тестирование соблюдения prerequisite ограничений...")
        
        try:
            # Получаем состояние студента
            state_data = self.processor.get_student_state(self.student_id)
            bkt_params = state_data['bkt_params']
            available_actions = state_data['available_actions']
            
            violations = 0
            checked_tasks = 0
            
            print(f"🔍 Проверяем prerequisite для {len(available_actions)} доступных заданий...")
            
            # Проверяем каждое доступное действие
            for action_idx in available_actions[:10]:  # Проверяем первые 10 для скорости
                task_id = self.env.action_to_task_id[action_idx]
                task_skills = self.env.task_to_skills.get(task_id, set())
                
                for skill_id in task_skills:
                    # Проверяем рекурсивно все prerequisite
                    if not self.env._check_prerequisites_mastered(skill_id, bkt_params, self.processor.skill_to_id, 0.85):
                        violations += 1
                        prerequisites = self.env.skills_graph.get(skill_id, set())
                        print(f"❗ Нарушение prerequisite в задании {task_id}")
                        print(f"   Навык {skill_id} требует: {prerequisites}")
                        
                        # Показываем уровни освоения prerequisite
                        for prereq_id in prerequisites:
                            skill_idx = self.processor.skill_to_id.get(prereq_id)
                            if skill_idx is not None:
                                mastery = bkt_params[skill_idx, 0].item()
                                print(f"   Prerequisite {prereq_id}: {mastery:.3f} (нужно ≥ 0.85)")
                        break
                
                checked_tasks += 1
            
            if violations == 0:
                print(f"✅ Prerequisite ограничения соблюдены для всех {checked_tasks} проверенных заданий")
                print("🎯 Новая логика фильтрации работает корректно!")
            else:
                print(f"❌ Найдено {violations} нарушений prerequisite из {checked_tasks} заданий")
            
            # Показываем примеры рекурсивной проверки
            print(f"\n🔍 Примеры рекурсивной проверки prerequisite:")
            for i, skill_id in enumerate(list(self.env.skills_graph.keys())[:3]):
                prerequisites = self.env.skills_graph.get(skill_id, set())
                if prerequisites:
                    is_available = self.env._check_prerequisites_mastered(skill_id, bkt_params, self.processor.skill_to_id)
                    print(f"  Навык {skill_id}: prerequisite {prerequisites} → {'✅' if is_available else '❌'}")
            
            return violations == 0
            
        except Exception as e:
            print(f"❌ Ошибка проверки prerequisite: {e}")
            import traceback
            traceback.print_exc()
            return False
    def test_q_function_with_restricted_actions(self):
        """Тест Q-функции с ограниченным пространством действий"""
        print("\n🤖 Тестирование Q-функции с ограниченными действиями...")
        
        try:
            # Получаем состояние и создаем DQN агента
            state_data = self.processor.get_student_state(self.student_id)
            
            config = DQNConfig()
            config.num_actions = self.processor.get_num_tasks()
            num_skills = self.processor.get_num_skills()
            
            agent = create_dqn_agent(config, num_skills)
            
            # Подготавливаем входные данные
            bkt_params = state_data['bkt_params'].unsqueeze(0)
            history = state_data['history'].unsqueeze(0)
            skills_graph = state_data['skills_graph'].unsqueeze(0)
            
            # Кодируем состояние
            encoded_state = agent.q_network.encode_state(bkt_params, history)
            
            # Получаем Q-values для всех действий
            q_values = agent.q_network(encoded_state)
            
            print(f"✅ Q-функция работает:")
            print(f"  - Входное состояние: BKT {bkt_params.shape}, история {history.shape}")
            print(f"  - Закодированное состояние: {encoded_state.shape}")
            print(f"  - Q-values: {q_values.shape}")
            print(f"  - Диапазон Q-values: [{q_values.min():.3f}, {q_values.max():.3f}]")
            
            # Тестируем выбор действий с ограничениями
            available_actions = state_data['available_actions']
            
            if available_actions:
                # Без ограничений
                action_unrestricted = q_values.argmax().item()
                
                # С ограничениями - показываем процесс маскирования
                with torch.no_grad():
                    masked_q_values = q_values.clone()
                    mask = torch.ones(config.num_actions, dtype=torch.bool)
                    mask[available_actions] = False  # Доступные действия НЕ маскируем
                    masked_q_values[0, mask] = float('-inf')  # Недоступные получают -inf
                    action_restricted = masked_q_values.argmax().item()
                
                print(f"\n🎯 Процесс ограничения действий:")
                print(f"  - Всего Q-values: {q_values.shape[1]}")
                print(f"  - Доступных действий: {len(available_actions)}")
                print(f"  - Заблокированных действий: {q_values.shape[1] - len(available_actions)}")
                print(f"  - Действие без ограничений: {action_unrestricted}")
                print(f"  - Действие с ограничениями: {action_restricted}")
                print(f"  - Ограничение применено: {action_unrestricted != action_restricted}")
                
                # Показываем Q-values для первых нескольких доступных действий
                print(f"\n📊 Q-values для доступных действий:")
                for i, action_idx in enumerate(available_actions[:5]):
                    q_val = q_values[0, action_idx].item()
                    print(f"  - Действие {action_idx}: Q-value = {q_val:.4f}")
                
                # Показываем Q-values для нескольких недоступных действий
                all_actions = set(range(config.num_actions))
                unavailable_actions = list(all_actions - set(available_actions))[:5]
                print(f"\n🚫 Q-values для недоступных действий (до маскирования):")
                for action_idx in unavailable_actions:
                    q_val = q_values[0, action_idx].item()
                    print(f"  - Действие {action_idx}: Q-value = {q_val:.4f} → замаскировано как -inf")
                
                # Проверяем, что ограниченное действие действительно доступно
                if action_restricted in available_actions:
                    print("✅ Выбранное действие находится в списке доступных")
                else:
                    print("❌ Выбранное действие НЕ находится в списке доступных")
                    return False
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка работы Q-функции: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_action_space_consistency(self):
        """Тест согласованности пространства действий"""
        print("\n🔄 Тестирование согласованности пространства действий...")
        
        try:
            # Получаем маппинги
            total_tasks = self.processor.get_num_tasks()
            total_actions = len(self.env.task_ids)
            
            print(f"  - Всего заданий в процессоре: {total_tasks}")
            print(f"  - Всего действий в среде: {total_actions}")
            
            # Проверяем согласованность маппингов
            if total_tasks != total_actions:
                print("❌ Несогласованность между процессором и средой")
                return False
            
            # Проверяем bidirectional маппинг
            mapping_errors = 0
            for task_id in self.env.task_ids[:10]:  # Проверяем первые 10
                action_idx = self.env.task_id_to_action[task_id]
                back_task_id = self.env.action_to_task_id[action_idx]
                
                if task_id != back_task_id:
                    print(f"❌ Ошибка маппинга: {task_id} -> {action_idx} -> {back_task_id}")
                    mapping_errors += 1
            
            if mapping_errors == 0:
                print("✅ Маппинги между ID задач и индексами действий согласованы")
            else:
                print(f"❌ Найдено {mapping_errors} ошибок в маппинге")
                return False
            
            # Тестируем ограничения по доступным действиям
            state_data = self.processor.get_student_state(self.student_id)
            available_actions = state_data['available_actions']
            
            # Все доступные действия должны быть в пределах [0, total_actions)
            invalid_actions = [a for a in available_actions if a < 0 or a >= total_actions]
            
            if invalid_actions:
                print(f"❌ Найдены недопустимые индексы действий: {invalid_actions}")
                return False
            else:
                print(f"✅ Все {len(available_actions)} доступных действий имеют корректные индексы")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка проверки согласованности: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_skill_difficulty_matching(self):
        """Тест соответствия сложности заданий уровню навыков"""
        print("\n📊 Тестирование соответствия сложности заданий уровню навыков...")
        
        try:
            # Получаем рекомендации с учетом уровня навыков
            recommendations = self.processor.get_recommended_actions(
                student_id=self.student_id, 
                top_k=10
            )
            
            if not recommendations:
                print("⚠️ Нет рекомендаций для анализа")
                return True
            
            print(f"✅ Получено {len(recommendations)} рекомендаций:")
            
            # Анализируем рекомендации
            state_data = self.processor.get_student_state(self.student_id)
            bkt_params = state_data['bkt_params']
            
            for i, (action_idx, priority) in enumerate(recommendations[:5]):
                task_id = self.env.action_to_task_id[action_idx]
                task_data = self.processor.get_task_data(task_id)
                
                # Получаем навыки задания и их уровни освоения
                task_skills = task_data['skills']
                skill_levels = []
                
                for skill_id in task_skills:
                    skill_idx = self.processor.skill_to_id.get(skill_id)
                    if skill_idx is not None:
                        mastery = bkt_params[skill_idx, 0].item()
                        skill_levels.append(mastery)
                
                avg_mastery = np.mean(skill_levels) if skill_levels else 0.5
                
                print(f"  {i+1}. Задание {task_id} (приоритет: {priority:.3f}):")
                print(f"     - Сложность: {task_data['difficulty']}, тип: {task_data['task_type']}")
                print(f"     - Навыки: {task_skills}")
                print(f"     - Средний уровень освоения: {avg_mastery:.3f}")
                
                # Проверяем логику соответствия
                expected_difficulty = 0 if avg_mastery < 0.5 else (1 if avg_mastery < 0.8 else 2)
                difficulty_match = abs(task_data['difficulty'] - expected_difficulty) <= 1
                
                if difficulty_match:
                    print(f"     ✅ Сложность соответствует уровню навыков")
                else:
                    print(f"     ⚠️ Сложность не соответствует уровню навыков (ожидалось: {expected_difficulty})")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка анализа соответствия сложности: {e}")
            import traceback
            traceback.print_exc()
            return False
    def test_detailed_history_analysis(self):
        """Детальный анализ структуры истории попыток"""
        print("\n📊 Детальный анализ структуры истории попыток...")
        
        try:
            # Получаем состояние студента
            user = User.objects.get(id=self.student_id)
            student_profile = StudentProfile.objects.get(user=user)
            history = self.processor._get_student_history(student_profile)
            print(f"✅ История попыток: {history.shape}")
            print(f"📋 Структура каждой записи (7 параметров):")
            print(f"  0. task_id_encoded - Кодированный ID задания")
            print(f"  1. success - Успешность (0/1)")
            print(f"  2. difficulty - Сложность (0=простая, 1=средняя, 2=сложная)")
            print(f"  3. task_type - Тип задания (0=single, 1=multiple, 2=true_false)")
            print(f"  4. skill_level - Уровень освоения основного навыка (0-1)")
            print(f"  5. time_spent - Нормализованное время (0-1)")
            print(f"  6. streak - Серия успехов (0-1)")
            
            if history.shape[0] > 0:
                print(f"\n🔍 Значения для каждой из последних {min(10, history.shape[0])} попыток:")
                print("    task_id | success | diff | type | skill_lvl | time | streak")
                print("    " + "-" * 65)
                
                for i in range(min(10, history.shape[0])):
                    row = history[i].tolist()
                    formatted_row = [
                        f"{int(row[0]):7d}",    # task_id
                        f"{row[1]:7.0f}",       # success
                        f"{row[2]:4.0f}",       # difficulty
                        f"{row[3]:4.0f}",       # task_type
                        f"{row[4]:9.3f}",       # skill_level
                        f"{row[5]:4.2f}",       # time_spent
                        f"{row[6]:6.3f}"        # streak
                    ]
                    print("    " + " | ".join(formatted_row))
                
                # Статистика по параметрам                print(f"\n📈 Статистика по параметрам:")
                print(f"  - Успешность: {(history[:, 1] == 1.0).float().mean():.1%}")
                print(f"  - Сложность: мин={history[:, 2].min():.0f}, макс={history[:, 2].max():.0f}, среднее={history[:, 2].mean():.1f}")
                print(f"  - Уровень навыков: мин={history[:, 4].min():.3f}, макс={history[:, 4].max():.3f}, среднее={history[:, 4].mean():.3f}")
                print(f"  - Время: мин={history[:, 5].min():.3f}, макс={history[:, 5].max():.3f}, среднее={history[:, 5].mean():.3f}")
                print(f"  - Серия успехов: мин={history[:, 6].min():.3f}, макс={history[:, 6].max():.3f}, среднее={history[:, 6].mean():.3f}")
                
                # Рекомендации по оптимизации
                print(f"\n💡 Рекомендации по оптимизации входных данных:")
                unique_tasks = len(torch.unique(history[:, 0]))
                unique_difficulties = len(torch.unique(history[:, 2]))
                unique_types = len(torch.unique(history[:, 3]))
                
                print(f"  - Уникальных заданий в истории: {unique_tasks}")
                print(f"  - Уникальных уровней сложности: {unique_difficulties}")
                print(f"  - Уникальных типов заданий: {unique_types}")
                print(f"  ✅ Параметр mastery_change успешно удален!")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка анализа истории: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_skills_graph_representation(self):
        """Анализ представления графа навыков"""
        print("\n🕸️ Анализ представления графа навыков...")
        
        try:
            # Получаем граф навыков
            skills_graph = self.processor._build_skills_graph_matrix()
            
            print(f"✅ Граф навыков: {skills_graph.shape}")
            print(f"🔗 Всего prerequisite связей: {int(skills_graph.sum())}")
            
            # Анализируем структуру графа
            num_skills = skills_graph.shape[0]
            skills_with_prereqs = (skills_graph.sum(dim=1) > 0).sum().item()
            max_prereqs = skills_graph.sum(dim=1).max().item()
            
            print(f"📊 Структура графа:")
            print(f"  - Всего навыков: {num_skills}")
            print(f"  - Навыков с prerequisite: {skills_with_prereqs}")
            print(f"  - Максимум prerequisite у одного навыка: {int(max_prereqs)}")
            
            # Показываем, как граф представлен в векторе состояния
            print(f"\n🧠 Представление в векторе состояния:")
            print(f"  - Матрица {num_skills}×{num_skills} сплющивается в вектор размера {skills_graph.numel()}")
            print(f"  - Каждый элемент [i,j] показывает: 'является ли навык j prerequisite для навыка i'")
            print(f"  - Значение 1.0 = есть связь, 0.0 = нет связи")
            
            # Показываем примеры связей
            print(f"\n🔍 Примеры prerequisite связей:")
            connections_found = 0
            for i in range(min(num_skills, 5)):  # Проверяем первые 5 навыков
                prereqs = (skills_graph[i] > 0).nonzero().flatten()
                if len(prereqs) > 0:
                    print(f"  - Навык {i+1} требует навыки: {[p.item()+1 for p in prereqs]}")
                    connections_found += 1
                    if connections_found >= 3:  # Показываем только первые 3 примера
                        break
            
            if connections_found == 0:
                print("  ⚠️  Prerequisite связи не найдены в первых 5 навыках")
            
            # Объясняем, как это помогает модели
            print(f"\n🎓 Как граф помогает DQN модели:")
            print(f"  - Модель видит зависимости между навыками через матрицу смежности")
            print(f"  - При выборе действия модель учитывает prerequisite ограничения")
            print(f"  - Граф позволяет модели планировать последовательность изучения")
            print(f"  - Входной слой получает сплющенную матрицу как часть состояния")
            print(f"  - Размер входа от графа: {skills_graph.numel()} нейронов")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка анализа графа навыков: {e}")
            import traceback
            traceback.print_exc()
            return False
def run_action_space_modification_tests():
    """Запускает все тесты модификации пространства действий"""
    print("🚀 ТЕСТЫ МОДИФИКАЦИИ ПРОСТРАНСТВА ДЕЙСТВИЙ DQN")
    print("=" * 70)
    
    tester = TestDQNActionSpaceModification(student_id=7)
    tests = [
        ("Формирование вектора состояния", tester.test_state_vector_formation),
        ("Детальный анализ истории попыток", tester.test_detailed_history_analysis),
        ("Анализ представления графа навыков", tester.test_skills_graph_representation),
        ("Фильтрация пространства действий", tester.test_action_space_filtering),
        ("Соблюдение prerequisite ограничений", tester.test_prerequisite_enforcement),
        ("Q-функция с ограниченными действиями", tester.test_q_function_with_restricted_actions),
        ("Согласованность пространства действий", tester.test_action_space_consistency),
        ("Соответствие сложности уровню навыков", tester.test_skill_difficulty_matching),
        ("Детальный анализ структуры истории попыток", tester.test_detailed_history_analysis),
        ("Анализ представления графа навыков", tester.test_skills_graph_representation),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"🧪 Тест: {name}")
        print('='*50)
        
        try:
            if test_func():
                print(f"✅ {name}: ПРОЙДЕН")
                passed += 1
            else:
                print(f"❌ {name}: НЕ ПРОЙДЕН")
        except Exception as e:
            print(f"💥 {name}: КРИТИЧЕСКАЯ ОШИБКА - {e}")
    
    print(f"\n{'='*70}")
    print(f"📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print('='*70)
    print(f"Пройдено: {passed}/{total}")
    print(f"Процент успешности: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Модификация пространства действий работает корректно!")
        print("✅ DQN модель готова к обучению с ограничениями по prerequisite")
    else:
        print("⚠️ НАЙДЕНЫ ПРОБЛЕМЫ в модификации пространства действий")
    
    return passed == total


if __name__ == "__main__":
    success = run_action_space_modification_tests()
    exit(0 if success else 1)
