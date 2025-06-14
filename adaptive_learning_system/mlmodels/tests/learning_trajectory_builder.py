"""
Скрипт для построения траектории обучения студента на основе графа навыков.

Симулирует логичное освоение навыков с учетом prerequisites:
- Студент не может освоить навык без освоения всех prerequisite навыков
- Все предки освоенного навыка должны быть освоены (уровень >0.9)
- Генерирует реалистичную траекторию обучения

Использование:
    python manage.py shell
    exec(open('mlmodels/tests/learning_trajectory_builder.py').read())
"""

import os
import sys
import django
from typing import Dict, Set, List, Tuple, Optional
from collections import defaultdict, deque
import json
import random
from pathlib import Path

# Настройка Django
def setup_django():
    """Настройка Django окружения"""
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
    django.setup()

setup_django()

from skills.models import Skill, Course
from methodist.models import Task
from mlmodels.tests.parse_skills_graph import SkillsGraphParser
from mlmodels.models import StudentSkillMastery, StudentProfile
from student.models import StudentProfile as StudentUser


class LearningTrajectoryBuilder:
    """Построитель траектории обучения на основе графа навыков"""
    
    def __init__(self):
        self.graph_parser = SkillsGraphParser()
        self.skills_graph = {}  # {skill_id: {prerequisite_ids}}
        self.reverse_graph = {}  # {skill_id: {dependent_skill_ids}}
        self.skill_depths = {}  # {skill_id: depth_level}
        self.skill_info = {}
        
        # Параметры симуляции
        self.default_mastery = 0.1  # Дефолтный уровень освоения
        self.mastery_threshold = 0.9  # Порог полного освоения
        self.partial_mastery_level = 0.6  # Уровень частичного освоения
        
    def initialize(self):
        """Инициализация графа навыков и анализ структуры"""
        print("🔄 Инициализация графа навыков...")
        
        # Парсим граф навыков
        self.skills_graph = self.graph_parser.parse_skills_graph()
        self.reverse_graph = self.graph_parser.reverse_graph
        self.skill_info = self.graph_parser.skill_info
        
        # Анализируем структуру
        analysis = self.graph_parser.analyze_graph_structure()
        self.skill_depths = analysis['skill_depths']
        
        print(f"✅ Граф навыков инициализирован:")
        print(f"   • Навыков: {len(self.skills_graph)}")
        print(f"   • Связей: {sum(len(prereqs) for prereqs in self.skills_graph.values())}")
        print(f"   • Максимальная глубина: {max(self.skill_depths.values()) if self.skill_depths else 0}")
        
    def get_root_skills(self) -> List[int]:
        """Получает корневые навыки (без prerequisites)"""
        return [skill_id for skill_id, prereqs in self.skills_graph.items() if not prereqs]
    
    def get_available_skills(self, current_mastery: Dict[int, float]) -> List[int]:
        """
        Получает навыки, доступные для изучения (все prerequisites освоены)
        
        Args:
            current_mastery: Текущий уровень освоения навыков {skill_id: mastery_level}
            
        Returns:
            List[int]: Список доступных для изучения навыков
        """
        available = []
        
        for skill_id, prereqs in self.skills_graph.items():
            # Пропускаем уже освоенные навыки
            if current_mastery.get(skill_id, self.default_mastery) >= self.mastery_threshold:
                continue
                
            # Проверяем, что все prerequisites освоены
            all_prereqs_mastered = True
            for prereq_id in prereqs:
                if current_mastery.get(prereq_id, self.default_mastery) < self.mastery_threshold:
                    all_prereqs_mastered = False
                    break
            
            if all_prereqs_mastered:
                available.append(skill_id)
        
        return available
    
    def validate_mastery_consistency(self, mastery: Dict[int, float]) -> Tuple[bool, List[str]]:
        """
        Проверяет логическую согласованность освоения навыков
        
        Args:
            mastery: Уровень освоения навыков {skill_id: mastery_level}
            
        Returns:
            Tuple[bool, List[str]]: (является_ли_согласованным, список_ошибок)
        """
        errors = []
        
        for skill_id, skill_mastery in mastery.items():
            if skill_mastery >= self.mastery_threshold:
                # Для освоенного навыка проверяем, что все prerequisites тоже освоены
                prereqs = self.skills_graph.get(skill_id, set())
                for prereq_id in prereqs:
                    prereq_mastery = mastery.get(prereq_id, self.default_mastery)
                    if prereq_mastery < self.mastery_threshold:
                        skill_name = self.skill_info[skill_id].name
                        prereq_name = self.skill_info[prereq_id].name
                        errors.append(
                            f"Навык '{skill_name}' освоен ({skill_mastery:.2f}), "
                            f"но prerequisite '{prereq_name}' не освоен ({prereq_mastery:.2f})"                        )
        
        return len(errors) == 0, errors
    
    def simulate_student_learning(self, target_mastered_count: int = 10, 
                                 target_partial_count: int = 5) -> Tuple[Dict[int, float], List[Dict]]:
        """
        Симулирует логичное освоение навыков студентом
        
        Args:
            target_mastered_count: Количество полностью освоенных навыков
            target_partial_count: Количество частично освоенных навыков
            
        Returns:
            Dict[int, float]: Уровень освоения навыков {skill_id: mastery_level}
        """
        print(f"\n🎯 Симуляция обучения студента:")
        print(f"   • Цель: {target_mastered_count} полностью освоенных навыков")
        print(f"   • Цель: {target_partial_count} частично освоенных навыков")
        
        # Инициализируем все навыки дефолтным уровнем
        mastery = {skill_id: self.default_mastery for skill_id in self.skills_graph.keys()}
        
        mastered_count = 0
        partial_count = 0
        learning_steps = []
        
        # Сначала осваиваем корневые навыки
        root_skills = self.get_root_skills()
        print(f"   • Корневых навыков: {len(root_skills)}")
        
        # Стратегия освоения: идем по глубинам от корней
        skills_by_depth = defaultdict(list)
        for skill_id, depth in self.skill_depths.items():
            skills_by_depth[depth].append(skill_id)
        
        max_depth = max(skills_by_depth.keys()) if skills_by_depth else 0
        
        for depth in range(max_depth + 1):
            if mastered_count >= target_mastered_count and partial_count >= target_partial_count:
                break
                
            available_at_depth = []
            for skill_id in skills_by_depth[depth]:
                # Проверяем доступность
                prereqs = self.skills_graph.get(skill_id, set())
                if all(mastery.get(p, self.default_mastery) >= self.mastery_threshold for p in prereqs):
                    available_at_depth.append(skill_id)
            
            if not available_at_depth:
                continue
                
            # Перемешиваем для случайности
            random.shuffle(available_at_depth)
            
            for skill_id in available_at_depth:
                if mastered_count >= target_mastered_count and partial_count >= target_partial_count:
                    break
                
                # Решаем, полностью или частично осваивать
                if mastered_count < target_mastered_count:
                    # Полное освоение с некоторой вероятностью
                    if random.random() < 0.7:  # 70% шанс полного освоения
                        new_mastery = random.uniform(self.mastery_threshold, 1.0)
                        mastery[skill_id] = new_mastery
                        mastered_count += 1
                        learning_steps.append({
                            'step': len(learning_steps) + 1,
                            'skill_id': skill_id,
                            'skill_name': self.skill_info[skill_id].name,
                            'mastery_level': new_mastery,
                            'type': 'full_mastery',
                            'depth': depth
                        })
                        continue
                
                if partial_count < target_partial_count:
                    # Частичное освоение
                    new_mastery = random.uniform(0.4, 0.8)
                    mastery[skill_id] = new_mastery
                    partial_count += 1
                    learning_steps.append({
                        'step': len(learning_steps) + 1,
                        'skill_id': skill_id,
                        'skill_name': self.skill_info[skill_id].name,
                        'mastery_level': new_mastery,
                        'type': 'partial_mastery',
                        'depth': depth
                    })
        
        # Проверяем согласованность
        is_consistent, errors = self.validate_mastery_consistency(mastery)
        
        print(f"\n📊 Результат симуляции:")
        print(f"   • Полностью освоено: {mastered_count} навыков")
        print(f"   • Частично освоено: {partial_count} навыков")
        print(f"   • Шагов обучения: {len(learning_steps)}")
        print(f"   • Согласованность: {'✅ OK' if is_consistent else '❌ Ошибки'}")
        
        if not is_consistent:
            print("   🚨 Ошибки согласованности:")
            for error in errors[:3]:  # Показываем первые 3 ошибки
                print(f"     - {error}")
        
        return mastery, learning_steps
    
    def get_learning_recommendations(self, current_mastery: Dict[int, float], 
                                   limit: int = 10) -> List[Dict]:
        """
        Получает рекомендации по изучению навыков
        
        Args:
            current_mastery: Текущий уровень освоения
            limit: Максимальное количество рекомендаций
            
        Returns:
            List[Dict]: Список рекомендованных навыков с метаданными
        """
        available_skills = self.get_available_skills(current_mastery)
        
        recommendations = []
        for skill_id in available_skills[:limit]:
            skill = self.skill_info[skill_id]
            
            # Считаем количество зависимых навыков
            dependents = self.reverse_graph.get(skill_id, set())
            unlocked_dependents = 0
            for dep_id in dependents:
                dep_prereqs = self.skills_graph.get(dep_id, set())
                other_prereqs_ready = all(
                    current_mastery.get(p, self.default_mastery) >= self.mastery_threshold 
                    for p in dep_prereqs if p != skill_id
                )
                if other_prereqs_ready:
                    unlocked_dependents += 1
            
            # Количество заданий по навыку
            tasks_count = len(self.graph_parser.skill_tasks_mapping.get(skill_id, set()))
            
            recommendations.append({
                'skill_id': skill_id,
                'skill_name': skill.name,
                'skill_description': skill.description or '',
                'current_mastery': current_mastery.get(skill_id, self.default_mastery),
                'depth': self.skill_depths.get(skill_id, 0),
                'prerequisites_count': len(self.skills_graph.get(skill_id, set())),
                'unlocks_count': unlocked_dependents,
                'tasks_count': tasks_count,
                'priority_score': self._calculate_priority_score(
                    skill_id, current_mastery, unlocked_dependents, tasks_count
                )
            })
        
        # Сортируем по приоритету
        recommendations.sort(key=lambda x: x['priority_score'], reverse=True)
        
        return recommendations
    
    def _calculate_priority_score(self, skill_id: int, current_mastery: Dict[int, float],
                                 unlocks_count: int, tasks_count: int) -> float:
        """Вычисляет приоритет изучения навыка"""
        score = 0.0
        
        # Базовый приоритет по глубине (меньше глубина = выше приоритет)
        depth = self.skill_depths.get(skill_id, 0)
        score += max(0, 10 - depth) * 0.3
        
        # Приоритет по количеству разблокируемых навыков
        score += unlocks_count * 0.4
        
        # Приоритет по количеству заданий (больше заданий = больше практики)
        score += min(tasks_count, 10) * 0.2
        
        # Бонус за текущий уровень (ближе к порогу = выше приоритет)
        current_level = current_mastery.get(skill_id, self.default_mastery)
        if current_level > 0.3:
            score += (current_level - 0.1) * 0.1
        
        return score
    
    def generate_student_profile_report(self, mastery: Dict[int, float], 
                                      learning_steps: List[Dict]) -> Dict:
        """Генерирует подробный отчет о профиле студента"""
        
        # Категоризация навыков
        mastered_skills = []
        partial_skills = []
        unlearned_skills = []
        
        for skill_id, level in mastery.items():
            skill_data = {
                'skill_id': skill_id,
                'skill_name': self.skill_info[skill_id].name,
                'mastery_level': level,
                'depth': self.skill_depths.get(skill_id, 0)
            }
            
            if level >= self.mastery_threshold:
                mastered_skills.append(skill_data)
            elif level >= 0.3:
                partial_skills.append(skill_data)
            else:
                unlearned_skills.append(skill_data)
        
        # Статистика по глубинам
        depth_stats = defaultdict(lambda: {'mastered': 0, 'partial': 0, 'unlearned': 0})
        for skill_id, level in mastery.items():
            depth = self.skill_depths.get(skill_id, 0)
            if level >= self.mastery_threshold:
                depth_stats[depth]['mastered'] += 1
            elif level >= 0.3:
                depth_stats[depth]['partial'] += 1
            else:
                depth_stats[depth]['unlearned'] += 1
        
        # Рекомендации
        recommendations = self.get_learning_recommendations(mastery)
        
        return {
            'summary': {
                'total_skills': len(mastery),
                'mastered_count': len(mastered_skills),
                'partial_count': len(partial_skills),
                'unlearned_count': len(unlearned_skills),
                'learning_steps': len(learning_steps)
            },
            'skills_by_level': {
                'mastered': sorted(mastered_skills, key=lambda x: x['depth']),
                'partial': sorted(partial_skills, key=lambda x: x['depth']),
                'unlearned': sorted(unlearned_skills, key=lambda x: x['depth'])
            },
            'depth_statistics': dict(depth_stats),
            'learning_trajectory': learning_steps,
            'recommendations': recommendations,
            'next_available_skills': self.get_available_skills(mastery)
        }
    
    def print_student_report(self, mastery: Dict[int, float], learning_steps: List[Dict]):
        """Выводит подробный отчет о студенте"""
        
        report = self.generate_student_profile_report(mastery, learning_steps)
        
        print("\n" + "="*80)
        print("👨‍🎓 ПРОФИЛЬ СТУДЕНТА - ТРАЕКТОРИЯ ОБУЧЕНИЯ")
        print("="*80)
        
        # Общая статистика
        summary = report['summary']
        print(f"\n📊 ОБЩАЯ СТАТИСТИКА:")
        print(f"   • Всего навыков: {summary['total_skills']}")
        print(f"   • Полностью освоено: {summary['mastered_count']} ({summary['mastered_count']/summary['total_skills']*100:.1f}%)")
        print(f"   • Частично освоено: {summary['partial_count']} ({summary['partial_count']/summary['total_skills']*100:.1f}%)")
        print(f"   • Не изучено: {summary['unlearned_count']} ({summary['unlearned_count']/summary['total_skills']*100:.1f}%)")
        print(f"   • Шагов обучения: {summary['learning_steps']}")
        
        # Статистика по глубинам
        print(f"\n📈 РАСПРЕДЕЛЕНИЕ ПО ГЛУБИНАМ:")
        for depth in sorted(report['depth_statistics'].keys()):
            stats = report['depth_statistics'][depth]
            total = stats['mastered'] + stats['partial'] + stats['unlearned']
            print(f"   Глубина {depth}: {stats['mastered']}✅ {stats['partial']}🟡 {stats['unlearned']}⚪ (всего: {total})")
        
        # Освоенные навыки
        mastered = report['skills_by_level']['mastered']
        if mastered:
            print(f"\n✅ ПОЛНОСТЬЮ ОСВОЕННЫЕ НАВЫКИ ({len(mastered)}):")
            for skill in mastered[:10]:  # Показываем первые 10
                print(f"   • {skill['skill_name']} (уровень: {skill['mastery_level']:.2f}, глубина: {skill['depth']})")
        
        # Частично освоенные навыки
        partial = report['skills_by_level']['partial']
        if partial:
            print(f"\n🟡 ЧАСТИЧНО ОСВОЕННЫЕ НАВЫКИ ({len(partial)}):")
            for skill in partial[:5]:  # Показываем первые 5
                print(f"   • {skill['skill_name']} (уровень: {skill['mastery_level']:.2f}, глубина: {skill['depth']})")
        
        # Траектория обучения
        print(f"\n🛤️  ТРАЕКТОРИЯ ОБУЧЕНИЯ:")
        for step in learning_steps[-10:]:  # Показываем последние 10 шагов
            icon = "✅" if step['type'] == 'full_mastery' else "🟡"
            print(f"   {step['step']:2d}. {icon} {step['skill_name']} "
                  f"(уровень: {step['mastery_level']:.2f}, глубина: {step['depth']})")
        
        # Рекомендации
        recommendations = report['recommendations']
        if recommendations:
            print(f"\n🎯 РЕКОМЕНДАЦИИ ДЛЯ ИЗУЧЕНИЯ (топ-10):")
            for i, rec in enumerate(recommendations[:10], 1):
                priority = rec['priority_score']
                unlocks = rec['unlocks_count']
                tasks = rec['tasks_count']
                print(f"   {i:2d}. {rec['skill_name']} "
                      f"(приоритет: {priority:.1f}, разблокирует: {unlocks}, заданий: {tasks})")
        
        # Доступные навыки
        available = report['next_available_skills']
        print(f"\n🔓 ДОСТУПНЫХ ДЛЯ ИЗУЧЕНИЯ: {len(available)} навыков")
        if len(available) != len(recommendations):
            print(f"   (показано {min(len(recommendations), 10)} в рекомендациях)")
        
        print("\n" + "="*80)
    
    def export_trajectory_data(self, mastery: Dict[int, float], 
                              learning_steps: List[Dict], output_dir: Optional[str] = None):
        """Экспортирует данные траектории в JSON"""
        
        if output_dir is None:
            output_dir = str(Path(__file__).parent.parent.parent / 'temp_dir')
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        report = self.generate_student_profile_report(mastery, learning_steps)
        
        # Подготавливаем данные для экспорта
        export_data = {
            'student_profile': {
                'mastery_levels': {str(k): v for k, v in mastery.items()},
                'summary': report['summary'],
                'depth_statistics': report['depth_statistics']
            },
            'learning_trajectory': learning_steps,
            'recommendations': report['recommendations'],
            'skills_info': {
                str(k): {
                    'name': v.name,
                    'description': v.description or '',
                    'depth': self.skill_depths.get(k, 0)
                } for k, v in self.skill_info.items()
            },
            'graph_structure': {
                'skills_graph': {str(k): list(v) for k, v in self.skills_graph.items()},
                'skill_depths': {str(k): v for k, v in self.skill_depths.items()}
            }
        }
        
        # Экспорт в JSON
        with open(output_path / 'student_learning_trajectory.json', 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Данные траектории экспортированы в {output_path / 'student_learning_trajectory.json'}")


def main():
    """Основная функция демонстрации"""
    try:
        print("🚀 Построение траектории обучения студента...")
        
        builder = LearningTrajectoryBuilder()
        builder.initialize()
        
        # Симулируем студента
        print(f"\n🎭 Создание симуляции студента...")
        mastery, learning_steps = builder.simulate_student_learning(
            target_mastered_count=12,  # 12 полностью освоенных навыков
            target_partial_count=8     # 8 частично освоенных навыков
        )
        
        # Выводим подробный отчет
        builder.print_student_report(mastery, learning_steps)
        
        # Экспортируем данные
        builder.export_trajectory_data(mastery, learning_steps)
        
        print("\n✨ Построение траектории завершено!")
        
        return builder, mastery, learning_steps
        
    except Exception as e:
        print(f"❌ Ошибка при построении траектории: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None


if __name__ == "__main__":
    builder, mastery, learning_steps = main()
