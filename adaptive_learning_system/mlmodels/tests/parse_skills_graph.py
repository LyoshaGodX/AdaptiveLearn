"""
Скрипт для парсинга и анализа графа навыков из базы данных.

Подключается к Django ORM и анализирует:
- Структуру графа навыков 
- Зависимости между навыками (prerequisites)
- Статистику по навыкам и их связям
- Визуализацию графа навыков

Использование:
    python manage.py shell
    exec(open('mlmodels/tests/parse_skills_graph.py').read())
    
Или запуск как Django команда:
    python parse_skills_graph.py
"""

import os
import sys
import django
from typing import Dict, Set, List, Tuple, Optional
from collections import defaultdict, deque
import json
from pathlib import Path

# Настройка Django
def setup_django():
    """Настройка Django окружения"""
    # Добавляем путь к проекту
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    # Настройка Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
    django.setup()

# Импорты Django моделей (после настройки)
setup_django()

from skills.models import Skill, Course
from methodist.models import Task
from mlmodels.models import StudentSkillMastery
from django.db.models import Count, Avg, Q


class SkillsGraphParser:
    """Парсер графа навыков с анализом и визуализацией"""
    
    def __init__(self):
        self.skills_graph = {}  # {skill_id: {prerequisite_ids}}
        self.reverse_graph = {}  # {skill_id: {dependent_skill_ids}}
        self.skill_info = {}  # {skill_id: skill_model}
        self.task_skills_mapping = {}  # {task_id: {skill_ids}}
        self.skill_tasks_mapping = {}  # {skill_id: {task_ids}}
        
    def parse_skills_graph(self) -> Dict[int, Set[int]]:
        """
        Парсит граф навыков из базы данных
        
        Returns:
            Dict[int, Set[int]]: Граф навыков {skill_id: {prerequisite_ids}}
        """
        print("🔍 Парсинг графа навыков из базы данных...")
        
        skills_graph = {}
        reverse_graph = defaultdict(set)
        
        # Получаем все навыки
        skills = Skill.objects.all().prefetch_related('prerequisites', 'courses')
        
        print(f"📊 Найдено навыков: {skills.count()}")
        
        for skill in skills:
            # Сохраняем информацию о навыке
            self.skill_info[skill.id] = skill
            
            # Получаем prerequisite навыки
            prerequisites = set()
            for prereq in skill.prerequisites.all():
                prerequisites.add(prereq.id)
                reverse_graph[prereq.id].add(skill.id)  # Обратная связь
            
            skills_graph[skill.id] = prerequisites
            
            # Инициализируем обратную связь если её нет
            if skill.id not in reverse_graph:
                reverse_graph[skill.id] = set()
        
        self.skills_graph = skills_graph
        self.reverse_graph = dict(reverse_graph)
        
        print(f"✅ Граф навыков построен. Всего связей: {sum(len(prereqs) for prereqs in skills_graph.values())}")
        
        return skills_graph
    
    def parse_task_skills_mapping(self) -> Dict[int, Set[int]]:
        """
        Парсит связи между заданиями и навыками
        
        Returns:
            Dict[int, Set[int]]: Маппинг {task_id: {skill_ids}}
        """
        print("🔍 Парсинг связей заданий и навыков...")
        
        task_skills = {}
        skill_tasks = defaultdict(set)
        
        # Получаем все задания с навыками
        tasks = Task.objects.all().prefetch_related('skills')
        
        print(f"📊 Найдено заданий: {tasks.count()}")
        
        for task in tasks:
            skills = set()
            for skill in task.skills.all():
                skills.add(skill.id)
                skill_tasks[skill.id].add(task.id)
            
            task_skills[task.id] = skills
        
        self.task_skills_mapping = task_skills
        self.skill_tasks_mapping = dict(skill_tasks)
        
        print(f"✅ Связи заданий и навыков построены.")
        
        return task_skills
    
    def analyze_graph_structure(self) -> Dict:
        """Анализирует структуру графа навыков"""
        print("\n📈 Анализ структуры графа навыков...")
        
        if not self.skills_graph:
            self.parse_skills_graph()
        
        analysis = {
            'total_skills': len(self.skills_graph),
            'total_prerequisites': sum(len(prereqs) for prereqs in self.skills_graph.values()),
            'skills_with_prerequisites': sum(1 for prereqs in self.skills_graph.values() if prereqs),
            'root_skills': [],  # Навыки без prerequisites
            'leaf_skills': [],  # Навыки, которые не являются prerequisites для других
            'max_depth': 0,
            'cycles': [],
            'skill_depths': {},
            'prerequisite_count_distribution': defaultdict(int),
            'dependent_count_distribution': defaultdict(int)
        }
        
        # Находим корневые навыки (без prerequisites)
        for skill_id, prereqs in self.skills_graph.items():
            if not prereqs:
                analysis['root_skills'].append(skill_id)
        
        # Находим листовые навыки (не являются prerequisites для других)
        for skill_id in self.skills_graph.keys():
            if not self.reverse_graph.get(skill_id, set()):
                analysis['leaf_skills'].append(skill_id)
        
        # Распределение по количеству prerequisites
        for prereqs in self.skills_graph.values():
            analysis['prerequisite_count_distribution'][len(prereqs)] += 1
        
        # Распределение по количеству зависимых навыков
        for dependents in self.reverse_graph.values():
            analysis['dependent_count_distribution'][len(dependents)] += 1
        
        # Вычисляем глубину навыков
        analysis['skill_depths'] = self._calculate_skill_depths()
        analysis['max_depth'] = max(analysis['skill_depths'].values()) if analysis['skill_depths'] else 0
        
        # Поиск циклов
        analysis['cycles'] = self._find_cycles()
        
        return analysis
    
    def _calculate_skill_depths(self) -> Dict[int, int]:
        """Вычисляет глубину каждого навыка в графе"""
        depths = {}
        visited = set()
        
        def dfs_depth(skill_id: int, current_path: Set[int]) -> int:
            if skill_id in current_path:
                return 0  # Цикл найден
            
            if skill_id in depths:
                return depths[skill_id]
            
            current_path.add(skill_id)
            prereqs = self.skills_graph.get(skill_id, set())
            
            if not prereqs:
                depth = 0  # Корневой навык
            else:
                max_prereq_depth = 0
                for prereq_id in prereqs:
                    prereq_depth = dfs_depth(prereq_id, current_path)
                    max_prereq_depth = max(max_prereq_depth, prereq_depth)
                depth = max_prereq_depth + 1
            
            current_path.remove(skill_id)
            depths[skill_id] = depth
            return depth
        
        for skill_id in self.skills_graph.keys():
            if skill_id not in depths:
                dfs_depth(skill_id, set())
        
        return depths
    
    def _find_cycles(self) -> List[List[int]]:
        """Находит циклы в графе навыков"""
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs_cycle(skill_id: int, path: List[int]) -> bool:
            if skill_id in rec_stack:
                # Цикл найден
                cycle_start = path.index(skill_id)
                cycle = path[cycle_start:] + [skill_id]
                cycles.append(cycle)
                return True
            
            if skill_id in visited:
                return False
            
            visited.add(skill_id)
            rec_stack.add(skill_id)
            path.append(skill_id)
            
            for prereq_id in self.skills_graph.get(skill_id, set()):
                if dfs_cycle(prereq_id, path):
                    return True
            
            rec_stack.remove(skill_id)
            path.pop()
            return False
        
        for skill_id in self.skills_graph.keys():
            if skill_id not in visited:
                dfs_cycle(skill_id, [])
        
        return cycles
    
    def get_skill_learning_path(self, target_skill_id: int) -> List[int]:
        """
        Получает оптимальный путь изучения для достижения целевого навыка
        
        Args:
            target_skill_id: ID целевого навыка
            
        Returns:
            List[int]: Упорядоченный список навыков для изучения
        """
        if not self.skills_graph:
            self.parse_skills_graph()
        
        learning_path = []
        visited = set()
        
        def dfs_path(skill_id: int):
            if skill_id in visited:
                return
            
            # Сначала изучаем все prerequisites
            for prereq_id in self.skills_graph.get(skill_id, set()):
                dfs_path(prereq_id)
            
            # Затем добавляем сам навык
            if skill_id not in visited:
                learning_path.append(skill_id)
                visited.add(skill_id)
        
        dfs_path(target_skill_id)
        return learning_path
    
    def analyze_student_progress(self) -> Dict:
        """Анализирует прогресс студентов по навыкам"""
        print("\n👨‍🎓 Анализ прогресса студентов...")
        
        # Статистика по освоению навыков
        skill_mastery_stats = {}
        
        for skill_id in self.skills_graph.keys():
            masteries = StudentSkillMastery.objects.filter(skill_id=skill_id)
            
            if masteries.exists():
                avg_mastery = masteries.aggregate(avg=Avg('current_mastery_prob'))['avg']
                count_students = masteries.count()
                mastered_count = masteries.filter(current_mastery_prob__gte=0.8).count()
            else:
                avg_mastery = 0.0
                count_students = 0
                mastered_count = 0
            
            skill_mastery_stats[skill_id] = {
                'average_mastery': avg_mastery or 0.0,
                'students_count': count_students,
                'mastered_count': mastered_count,
                'mastery_rate': mastered_count / count_students if count_students > 0 else 0.0
            }
        
        return skill_mastery_stats
    
    def generate_graph_visualization_data(self) -> Dict:
        """Генерирует данные для визуализации графа"""
        print("\n🎨 Генерация данных для визуализации...")
        
        if not self.skills_graph:
            self.parse_skills_graph()
        
        # Создаем узлы
        nodes = []
        for skill_id, skill in self.skill_info.items():
            depth = self._calculate_skill_depths().get(skill_id, 0)
            
            nodes.append({
                'id': skill_id,
                'name': skill.name,
                'description': skill.description or '',
                'course': skill.courses.first().name if skill.courses.exists() else 'Без курса',
                'depth': depth,
                'prerequisites_count': len(self.skills_graph.get(skill_id, set())),
                'dependents_count': len(self.reverse_graph.get(skill_id, set())),
                'tasks_count': len(self.skill_tasks_mapping.get(skill_id, set()))
            })
        
        # Создаем связи
        edges = []
        for skill_id, prereqs in self.skills_graph.items():
            for prereq_id in prereqs:
                edges.append({
                    'source': prereq_id,
                    'target': skill_id,
                    'type': 'prerequisite'
                })
        
        return {
            'nodes': nodes,
            'edges': edges,            'metadata': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'max_depth': max(node['depth'] for node in nodes) if nodes else 0
            }
        }
    
    def export_graph_data(self, output_dir: Optional[str] = None):
        """Экспортирует данные графа в различных форматах"""
        if output_dir is None:
            output_dir = str(Path(__file__).parent.parent.parent / 'temp_dir')
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        print(f"\n💾 Экспорт данных в {output_path}...")
        
        # Экспорт в JSON
        graph_data = {
            'skills_graph': {str(k): list(v) for k, v in self.skills_graph.items()},
            'reverse_graph': {str(k): list(v) for k, v in self.reverse_graph.items()},
            'task_skills_mapping': {str(k): list(v) for k, v in self.task_skills_mapping.items()},
            'skill_info': {
                str(k): {
                    'name': v.name,
                    'description': v.description or '',
                    'course_ids': list(v.courses.values_list('id', flat=True))
                } for k, v in self.skill_info.items()
            }
        }
        
        with open(output_path / 'skills_graph.json', 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)
        
        # Экспорт визуализации
        viz_data = self.generate_graph_visualization_data()
        with open(output_path / 'skills_graph_viz.json', 'w', encoding='utf-8') as f:
            json.dump(viz_data, f, ensure_ascii=False, indent=2)
        
        # Экспорт в DOT формат для Graphviz
        self._export_to_dot(output_path / 'skills_graph.dot')
        
        print(f"✅ Данные экспортированы в {output_path}")
    
    def _export_to_dot(self, output_path: Path):
        """Экспортирует граф в DOT формат для Graphviz"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('digraph SkillsGraph {\n')
            f.write('    rankdir=TB;\n')
            f.write('    node [shape=box, style=rounded];\n\n')
            
            # Узлы
            for skill_id, skill in self.skill_info.items():
                label = f"{skill.name}\\n({skill_id})"
                f.write(f'    {skill_id} [label="{label}"];\n')
            
            f.write('\n')
            
            # Связи
            for skill_id, prereqs in self.skills_graph.items():
                for prereq_id in prereqs:
                    f.write(f'    {prereq_id} -> {skill_id};\n')
            
            f.write('}\n')
    
    def print_analysis_report(self):
        """Выводит детальный отчет по анализу графа"""
        print("\n" + "="*80)
        print("📊 ОТЧЕТ ПО АНАЛИЗУ ГРАФА НАВЫКОВ")
        print("="*80)
        
        # Парсим данные
        self.parse_skills_graph()
        self.parse_task_skills_mapping()
        
        # Анализ структуры
        structure = self.analyze_graph_structure()
        
        print(f"\n🔢 ОСНОВНАЯ СТАТИСТИКА:")
        print(f"   • Всего навыков: {structure['total_skills']}")
        print(f"   • Всего prerequisite связей: {structure['total_prerequisites']}")
        print(f"   • Навыков с prerequisites: {structure['skills_with_prerequisites']}")
        print(f"   • Корневых навыков: {len(structure['root_skills'])}")
        print(f"   • Листовых навыков: {len(structure['leaf_skills'])}")
        print(f"   • Максимальная глубина: {structure['max_depth']}")
        
        # Циклы
        if structure['cycles']:
            print(f"\n⚠️  НАЙДЕНЫ ЦИКЛЫ ({len(structure['cycles'])}):")
            for i, cycle in enumerate(structure['cycles'], 1):
                cycle_names = [self.skill_info[sid].name for sid in cycle]
                print(f"   {i}. {' -> '.join(cycle_names)}")
        else:
            print(f"\n✅ Циклов не найдено")
        
        # Распределение по prerequisites
        print(f"\n📈 РАСПРЕДЕЛЕНИЕ ПО КОЛИЧЕСТВУ PREREQUISITES:")
        for count, skills_num in sorted(structure['prerequisite_count_distribution'].items()):
            print(f"   • {count} prerequisites: {skills_num} навыков")
        
        # Топ навыков по глубине
        print(f"\n🏔️  ТОП НАВЫКОВ ПО ГЛУБИНЕ:")
        sorted_by_depth = sorted(structure['skill_depths'].items(), key=lambda x: x[1], reverse=True)
        for skill_id, depth in sorted_by_depth[:5]:
            skill_name = self.skill_info[skill_id].name
            print(f"   • {skill_name} (глубина: {depth})")
        
        # Корневые навыки
        if structure['root_skills']:
            print(f"\n🌱 КОРНЕВЫЕ НАВЫКИ:")
            for skill_id in structure['root_skills'][:10]:  # Показываем первые 10
                skill_name = self.skill_info[skill_id].name
                tasks_count = len(self.skill_tasks_mapping.get(skill_id, set()))
                print(f"   • {skill_name} (заданий: {tasks_count})")
        
        # Анализ прогресса студентов
        student_progress = self.analyze_student_progress()
        
        print(f"\n👨‍🎓 ПРОГРЕСС СТУДЕНТОВ:")
        skills_with_students = [(sid, data) for sid, data in student_progress.items() 
                               if data['students_count'] > 0]
        
        if skills_with_students:
            # Топ по освоенности
            top_mastered = sorted(skills_with_students, 
                                key=lambda x: x[1]['mastery_rate'], reverse=True)[:5]
            
            print(f"   🏆 ТОП ОСВОЕННЫХ НАВЫКОВ:")
            for skill_id, data in top_mastered:
                skill_name = self.skill_info[skill_id].name
                print(f"     • {skill_name}: {data['mastery_rate']:.1%} "
                      f"({data['mastered_count']}/{data['students_count']} студентов)")
            
            # Навыки требующие внимания
            low_mastery = sorted(skills_with_students, 
                               key=lambda x: x[1]['mastery_rate'])[:5]
            
            print(f"\n   ⚠️  НАВЫКИ, ТРЕБУЮЩИЕ ВНИМАНИЯ:")
            for skill_id, data in low_mastery:
                skill_name = self.skill_info[skill_id].name
                print(f"     • {skill_name}: {data['mastery_rate']:.1%} "
                      f"({data['mastered_count']}/{data['students_count']} студентов)")
        else:
            print("   📝 Нет данных о прогрессе студентов")
        
        print("\n" + "="*80)


def main():
    """Основная функция скрипта"""
    try:
        print("🚀 Запуск анализа графа навыков...")
        
        parser = SkillsGraphParser()
        
        # Полный анализ и отчет
        parser.print_analysis_report()
        
        # Экспорт данных
        parser.export_graph_data()
        
        print("\n✨ Анализ завершен успешно!")
        
        return parser
        
    except Exception as e:
        print(f"❌ Ошибка при анализе: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Запуск как standalone скрипт
    parser = main()
