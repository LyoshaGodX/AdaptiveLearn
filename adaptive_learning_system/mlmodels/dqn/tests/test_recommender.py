"""
Тест DQN рекомендательной системы

Этот тест проверяет работу рекомендательной системы DQN:
1. Получение и анализ состояния студента
2. Генерация рекомендаций от DQN модели
3. Детальное отображение всей информации
4. Объяснение логики рекомендаций
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
from datetime import datetime

# Импортируем рекомендательную систему
from mlmodels.dqn.recommender import DQNRecommender


class TestDQNRecommender:
    """Тестирование DQN рекомендательной системы"""
    
    def __init__(self, student_id: int = 7):
        self.student_id = student_id
        self.recommender = DQNRecommender()  # Без загрузки модели - используем случайную
        
    def test_full_recommendation_pipeline(self):
        """Полный тест рекомендательной системы"""
        print("\n🎯 ПОЛНЫЙ ТЕСТ DQN РЕКОМЕНДАТЕЛЬНОЙ СИСТЕМЫ")
        print("=" * 80)
        
        try:
            # Получаем рекомендации
            print(f"🔍 Получаем рекомендации для студента ID: {self.student_id}")
            result = self.recommender.get_recommendations(self.student_id, top_k=50)
            
            # Отображаем результаты
            self._display_student_state(result.student_state)
            self._display_model_info(result.model_info)
            self._display_recommendations(result.recommendations, result.student_state)
            self._display_detailed_analysis(result)
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка в тесте рекомендательной системы: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _display_student_state(self, state):
        """Отображает состояние студента"""
        print(f"\n👤 СОСТОЯНИЕ СТУДЕНТА {state.student_id}")
        print("-" * 50)
        
        print(f"🧠 Навыки ({state.total_skills}):")
        print(f"  - Высокий уровень (>80%): {state.high_mastery_skills}")
        print(f"  - Средний уровень (50-80%): {state.medium_mastery_skills}")
        print(f"  - Низкий уровень (<50%): {state.low_mastery_skills}")
        
        print(f"\n📈 История попыток:")
        print(f"  - Всего попыток: {state.total_attempts}")
        if state.total_attempts > 0:
            print(f"  - Успешность: {state.success_rate:.1%}")
            print(f"  - Средняя сложность: {state.avg_difficulty:.1f}")
        else:
            print("  - Нет данных о попытках")
        
        print(f"\n🎯 Доступные задания:")
        print(f"  - Всего заданий в системе: {state.total_tasks}")
        print(f"  - Доступно для рекомендации: {state.available_tasks}")
        print(f"  - Отфильтровано (prerequisite): {state.filtered_tasks} ({state.filtered_tasks/state.total_tasks*100:.1f}%)")
        
        print(f"\n🔢 Размерности векторов:")
        print(f"  - BKT параметры: {state.bkt_params.shape}")
        print(f"  - История: {state.history.shape}")
        print(f"  - Граф навыков: {state.skills_graph.shape}")
    
    def _display_model_info(self, model_info):
        """Отображает информацию о модели"""
        print(f"\n🤖 ИНФОРМАЦИЯ О DQN МОДЕЛИ")
        print("-" * 50)
        print(f"  - Тип модели: {model_info['model_type']}")
        print(f"  - Путь к модели: {model_info['model_path'] or 'Случайная модель'}")
        print(f"  - Количество навыков: {model_info['num_skills']}")
        print(f"  - Количество заданий: {model_info['num_tasks']}")
        print(f"  - Размерность состояния: BKT {model_info['state_dim']}, история {model_info['history_dim']}")
        print(f"  - Размерность графа: {model_info['graph_dim']}")
    
    def _display_recommendations(self, recommendations, student_state):
        """Отображает рекомендации"""
        print(f"\n🎯 РЕКОМЕНДАЦИИ DQN ({len(recommendations)} заданий)")
        print("-" * 50)
        
        if not recommendations:
            print("❌ Нет доступных рекомендаций")
            return
        
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. ЗАДАНИЕ {rec.task_id}")
            print(f"   🎲 Q-value: {rec.q_value:.4f}")
            print(f"   🎯 Уверенность: {rec.confidence:.1%}")
            print(f"   📊 Сложность: {rec.difficulty}")
            print(f"   📝 Тип: {rec.task_type}")
            print(f"   ⏱️ Время: ~{rec.estimated_time // 60} мин")
            print(f"   🔗 Соответствие навыкам: {rec.skill_match_score:.1%}")
            print(f"   💡 Причина: {rec.reason}")
            
            if rec.skills:
                print(f"   🧠 Развиваемые навыки: {rec.skills}")
                # Показываем уровень освоения каждого навыка
                for skill_id in rec.skills:
                    skill_idx = self.recommender.data_processor.skill_to_id.get(skill_id)
                    if skill_idx is not None and skill_idx < len(student_state.bkt_params):
                        mastery = student_state.bkt_params[skill_idx, 0].item()
                        status = "🟢" if mastery > 0.8 else "🟡" if mastery > 0.5 else "🔴"
                        print(f"      {status} Навык {skill_id}: {mastery:.1%}")
    
    def _display_detailed_analysis(self, result):
        """Детальный анализ рекомендаций"""
        print(f"\n🔬 ДЕТАЛЬНЫЙ АНАЛИЗ")
        print("-" * 50)
        
        if not result.recommendations:
            return
        
        # Анализ Q-values
        q_values = [rec.q_value for rec in result.recommendations]
        print(f"📊 Статистика Q-values:")
        print(f"  - Диапазон: [{min(q_values):.4f}, {max(q_values):.4f}]")
        print(f"  - Среднее: {np.mean(q_values):.4f}")
        print(f"  - Стандартное отклонение: {np.std(q_values):.4f}")
        
        # Анализ сложности
        difficulties = [rec.difficulty for rec in result.recommendations]
        difficulty_count = {d: difficulties.count(d) for d in set(difficulties)}
        print(f"\n📈 Распределение по сложности:")
        for diff, count in difficulty_count.items():
            print(f"  - {diff}: {count} заданий")
        
        # Анализ навыков
        all_skills = []
        for rec in result.recommendations:
            all_skills.extend(rec.skills)
        
        if all_skills:
            unique_skills = list(set(all_skills))
            print(f"\n🧠 Навыки в рекомендациях:")
            print(f"  - Всего уникальных навыков: {len(unique_skills)}")
            print(f"  - Навыки: {sorted(unique_skills)}")
            
            # Показываем уровень освоения рекомендуемых навыков
            print(f"\n📊 Уровень освоения рекомендуемых навыков:")
            for skill_id in sorted(unique_skills)[:5]:  # Показываем первые 5
                skill_idx = self.recommender.data_processor.skill_to_id.get(skill_id)
                if skill_idx is not None and skill_idx < len(result.student_state.bkt_params):
                    mastery = result.student_state.bkt_params[skill_idx, 0].item()
                    bar_length = int(mastery * 20)
                    bar = "█" * bar_length + "░" * (20 - bar_length)
                    print(f"  Навык {skill_id:2d}: {bar} {mastery:.1%}")
        
        # Рекомендации по улучшению
        print(f"\n💡 РЕКОМЕНДАЦИИ ПО СИСТЕМЕ:")
        print(f"  - Доступно {result.student_state.available_tasks} из {result.student_state.total_tasks} заданий")
        if result.student_state.available_tasks < 10:
            print(f"  ⚠️  Мало доступных заданий - возможно, стоит пересмотреть фильтрацию")
        
        if result.student_state.total_attempts == 0:
            print(f"  💡 Студент новый - рекомендации основаны только на начальных BKT параметрах")
        elif result.student_state.success_rate < 0.5:
            print(f"  📉 Низкая успешность - модель должна рекомендовать более простые задания")
        elif result.student_state.success_rate > 0.8:
            print(f"  📈 Высокая успешность - модель может предложить более сложные вызовы")
    
    def test_individual_explanations(self):
        """Тест индивидуальных объяснений рекомендаций"""
        print(f"\n📝 ИНДИВИДУАЛЬНЫЕ ОБЪЯСНЕНИЯ РЕКОМЕНДАЦИЙ")
        print("-" * 50)
        
        try:
            result = self.recommender.get_recommendations(self.student_id, top_k=3)
            
            for i, rec in enumerate(result.recommendations, 1):
                print(f"\n{i}. ОБЪЯСНЕНИЕ РЕКОМЕНДАЦИИ:")
                explanation = self.recommender.explain_recommendation(rec, result.student_state)
                print(explanation)
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка в объяснениях: {e}")
            return False
    
    def test_edge_cases(self):
        """Тест крайних случаев"""
        print(f"\n🧪 ТЕСТ КРАЙНИХ СЛУЧАЕВ")
        print("-" * 50)
        
        tests_passed = 0
        total_tests = 3
        
        # Тест 1: Несуществующий студент
        print(f"\n1. Тест несуществующего студента:")
        try:
            result = self.recommender.get_recommendations(99999, top_k=3)
            print(f"❌ Должна была возникнуть ошибка для несуществующего студента")
        except Exception as e:
            print(f"✅ Корректно обработана ошибка: {type(e).__name__}")
            tests_passed += 1
        
        # Тест 2: Запрос 0 рекомендаций
        print(f"\n2. Тест запроса 0 рекомендаций:")
        try:
            result = self.recommender.get_recommendations(self.student_id, top_k=0)
            if len(result.recommendations) == 0:
                print(f"✅ Корректно возвращен пустой список")
                tests_passed += 1
            else:
                print(f"❌ Должен был вернуться пустой список")
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
        
        # Тест 3: Запрос большого количества рекомендаций
        print(f"\n3. Тест запроса большого количества рекомендаций:")
        try:
            result = self.recommender.get_recommendations(self.student_id, top_k=1000)
            max_possible = result.student_state.available_tasks
            actual = len(result.recommendations)
            if actual <= max_possible:
                print(f"✅ Вернулось {actual} рекомендаций (максимум доступных: {max_possible})")
                tests_passed += 1
            else:
                print(f"❌ Вернулось больше рекомендаций ({actual}) чем доступно ({max_possible})")
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
        
        print(f"\n📊 Результат крайних случаев: {tests_passed}/{total_tests}")
        return tests_passed == total_tests


def run_recommender_tests():
    """Запускает все тесты рекомендательной системы"""
    print("🚀 ТЕСТЫ DQN РЕКОМЕНДАТЕЛЬНОЙ СИСТЕМЫ")
    print("=" * 80)
    print(f"🕐 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = TestDQNRecommender(student_id=7)
    
    tests = [
        ("Полный тест рекомендательной системы", tester.test_full_recommendation_pipeline),
        ("Индивидуальные объяснения", tester.test_individual_explanations),
        ("Крайние случаи", tester.test_edge_cases),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"🧪 Тест: {name}")
        print('='*60)
        
        try:
            if test_func():
                print(f"✅ {name}: ПРОЙДЕН")
                passed += 1
            else:
                print(f"❌ {name}: НЕ ПРОЙДЕН")
        except Exception as e:
            print(f"💥 {name}: КРИТИЧЕСКАЯ ОШИБКА - {e}")
    
    print(f"\n{'='*80}")
    print(f"📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ РЕКОМЕНДАТЕЛЬНОЙ СИСТЕМЫ")
    print('='*80)
    print(f"Пройдено: {passed}/{total}")
    print(f"Процент успешности: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Рекомендательная система работает корректно!")
    else:
        print("⚠️ НАЙДЕНЫ ПРОБЛЕМЫ в рекомендательной системе")
    
    return passed == total


if __name__ == "__main__":
    success = run_recommender_tests()
    exit(0 if success else 1)
