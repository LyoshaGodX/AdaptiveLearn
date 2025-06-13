"""
Интерфейс для создания и работы с ориентированным графом навыков.
Поддерживает экспорт в различные форматы и анализ зависимостей.
"""

from typing import List, Dict, Any, Optional, Tuple, Set
import networkx as nx
from django.db.models import QuerySet
from skills.models import Skill, Course
from mlmodels.data_interfaces.database_interface import SkillDataInterface, CourseDataInterface
import json
import pickle
from pathlib import Path


class SkillsGraphInterface:
    """Интерфейс для работы с графом навыков"""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self._loaded = False
    
    def build_graph_from_database(self, course_id: Optional[str] = None) -> nx.DiGraph:
        """
        Построить граф навыков из базы данных.
        Если указан course_id, строится граф только для навыков курса.
        """
        self.graph.clear()
        
        if course_id:
            skills = CourseDataInterface.get_course_skills(course_id)
        else:
            skills = SkillDataInterface.get_all_skills()
        
        # Добавляем узлы (навыки)
        for skill in skills:
            self.graph.add_node(
                skill.id,
                name=skill.name,
                description=skill.description or "",
                is_base=skill.is_base,
                courses=[course.id for course in skill.courses.all()],
                tasks_count=skill.tasks.filter(is_active=True).count()
            )
        
        # Добавляем рёбра (зависимости)
        skill_ids = set(skills.values_list('id', flat=True))
        for skill in skills:
            for prereq in skill.prerequisites.filter(id__in=skill_ids):
                # Ребро от пререквизита к навыку
                self.graph.add_edge(
                    prereq.id, 
                    skill.id,
                    relationship='prerequisite'
                )
        
        self._loaded = True
        return self.graph
    
    def get_graph(self) -> nx.DiGraph:
        """Получить текущий граф"""
        if not self._loaded:
            self.build_graph_from_database()
        return self.graph
    
    def get_base_skills(self) -> List[int]:
        """Получить ID базовых навыков (без входящих рёбер)"""
        graph = self.get_graph()
        return [
            node for node in graph.nodes()
            if graph.in_degree(node) == 0 or graph.nodes[node].get('is_base', False)
        ]
    
    def get_leaf_skills(self) -> List[int]:
        """Получить ID навыков-листьев (без исходящих рёбер)"""
        graph = self.get_graph()
        return [node for node in graph.nodes() if graph.out_degree(node) == 0]
    
    def get_skill_prerequisites(self, skill_id: int) -> List[int]:
        """Получить все прямые пререквизиты навыка"""
        graph = self.get_graph()
        if skill_id in graph:
            return list(graph.predecessors(skill_id))
        return []
    
    def get_skill_dependents(self, skill_id: int) -> List[int]:
        """Получить все навыки, зависящие от данного"""
        graph = self.get_graph()
        if skill_id in graph:
            return list(graph.successors(skill_id))
        return []
    
    def get_all_prerequisites(self, skill_id: int) -> Set[int]:
        """
        Получить все навыки, которые нужно освоить перед данным
        (транзитивное замыкание пререквизитов)
        """
        graph = self.get_graph()
        if skill_id not in graph:
            return set()
        
        # Используем обход в ширину для поиска всех предшественников
        all_prereqs = set()
        to_visit = set(graph.predecessors(skill_id))
        
        while to_visit:
            current = to_visit.pop()
            if current not in all_prereqs:
                all_prereqs.add(current)
                to_visit.update(graph.predecessors(current))
        
        return all_prereqs
    
    def get_all_dependents(self, skill_id: int) -> Set[int]:
        """
        Получить все навыки, которые зависят от данного
        (транзитивное замыкание зависимостей)
        """
        graph = self.get_graph()
        if skill_id not in graph:
            return set()
        
        all_deps = set()
        to_visit = set(graph.successors(skill_id))        
        while to_visit:
            current = to_visit.pop()
            if current not in all_deps:
                all_deps.add(current)
                to_visit.update(graph.successors(current))
        
        return all_deps
    
    def get_learning_path(self, from_skill_id: int, to_skill_id: int) -> List[int]:
        """
        Найти кратчайший путь обучения от одного навыка к другому
        """
        graph = self.get_graph()
        try:
            path = nx.shortest_path(graph, from_skill_id, to_skill_id)
            return list(path) if isinstance(path, (list, tuple)) else []
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []
    
    def get_topological_order(self) -> List[int]:
        """
        Получить топологический порядок навыков
        (порядок изучения без нарушения зависимостей)
        """
        graph = self.get_graph()
        try:
            return list(nx.topological_sort(graph))
        except nx.NetworkXError:
            # Граф содержит циклы
            return list(graph.nodes())
    
    def find_cycles(self) -> List[List[int]]:
        """Найти циклы в графе навыков"""
        graph = self.get_graph()
        try:
            cycles = list(nx.simple_cycles(graph))
            return cycles
        except:
            return []
    
    def validate_graph(self) -> Dict[str, Any]:
        """
        Валидация графа навыков
        Проверяет наличие циклов и другие проблемы
        """
        graph = self.get_graph()
        
        validation_result = {
            'is_valid': True,
            'issues': [],
            'statistics': {
                'total_nodes': graph.number_of_nodes(),
                'total_edges': graph.number_of_edges(),
                'base_skills_count': len(self.get_base_skills()),
                'leaf_skills_count': len(self.get_leaf_skills()),
            }
        }
        
        # Проверка на циклы
        cycles = self.find_cycles()
        if cycles:
            validation_result['is_valid'] = False
            validation_result['issues'].append({
                'type': 'cycles',
                'description': f"Найдено {len(cycles)} циклов в графе",
                'details': cycles
            })
        
        # Проверка на изолированные узлы
        isolated_nodes = list(nx.isolates(graph))
        if isolated_nodes:
            validation_result['issues'].append({
                'type': 'isolated_nodes',
                'description': f"Найдено {len(isolated_nodes)} изолированных навыков",
                'details': isolated_nodes
            })
        
        # Проверка связности
        if not nx.is_weakly_connected(graph):
            validation_result['issues'].append({
                'type': 'disconnected',
                'description': "Граф не является связным",
                'details': list(nx.weakly_connected_components(graph))
            })
        
        return validation_result
    
    def get_skill_complexity(self, skill_id: int) -> Dict[str, Any]:
        """
        Вычислить сложность навыка на основе его позиции в графе
        """
        graph = self.get_graph()
        if skill_id not in graph:
            return {}
        
        prereqs = self.get_all_prerequisites(skill_id)
        dependents = self.get_all_dependents(skill_id)
        
        # Простые метрики сложности
        depth = len(prereqs)  # Глубина зависимостей
        breadth = len(dependents)  # Количество зависящих навыков
        
        # Централизованность в графе
        try:
            betweenness = nx.betweenness_centrality(graph)[skill_id]
            closeness = nx.closeness_centrality(graph)[skill_id]
            pagerank = nx.pagerank(graph)[skill_id]
        except:
            betweenness = closeness = pagerank = 0
        
        return {
            'skill_id': skill_id,
            'depth': depth,
            'breadth': breadth,
            'direct_prerequisites': len(self.get_skill_prerequisites(skill_id)),
            'direct_dependents': len(self.get_skill_dependents(skill_id)),
            'betweenness_centrality': betweenness,
            'closeness_centrality': closeness,
            'pagerank_score': pagerank,
            'complexity_score': depth * 0.4 + breadth * 0.3 + betweenness * 0.3
        }
    
    def export_to_dot(self, filepath: str, course_id: Optional[str] = None) -> bool:
        """
        Экспорт графа в формат DOT для визуализации с Graphviz
        """
        try:
            graph = self.get_graph()
            
            # Создаем DOT представление
            dot_lines = ['digraph skills_graph {']
            dot_lines.append('  rankdir=TB;')
            dot_lines.append('  node [shape=box];')
            
            # Добавляем узлы
            for node_id in graph.nodes():
                node_data = graph.nodes[node_id]
                label = node_data.get('name', f'Skill {node_id}')
                
                # Стиль для базовых навыков
                if node_data.get('is_base', False):
                    style = 'filled, color=lightblue'
                else:
                    style = 'filled, color=lightgray'
                
                dot_lines.append(f'  {node_id} [label="{label}", style="{style}"];')
            
            # Добавляем рёбра
            for edge in graph.edges():
                dot_lines.append(f'  {edge[0]} -> {edge[1]};')
            
            dot_lines.append('}')
            
            # Записываем в файл
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(dot_lines))
            
            return True
        except Exception as e:
            print(f"Ошибка при экспорте в DOT: {e}")
            return False
    
    def export_to_json(self, filepath: str) -> bool:
        """
        Экспорт графа в JSON формат
        """
        try:
            graph = self.get_graph()
            
            # Подготавливаем данные для JSON
            graph_data = {
                'nodes': [
                    {
                        'id': node_id,
                        **graph.nodes[node_id]
                    }
                    for node_id in graph.nodes()
                ],
                'edges': [
                    {
                        'source': edge[0],
                        'target': edge[1],
                        **graph.edges[edge]
                    }
                    for edge in graph.edges()
                ],
                'metadata': {
                    'total_nodes': graph.number_of_nodes(),
                    'total_edges': graph.number_of_edges(),
                    'is_dag': nx.is_directed_acyclic_graph(graph)
                }
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"Ошибка при экспорте в JSON: {e}")
            return False
    
    def export_to_pickle(self, filepath: str) -> bool:
        """
        Сохранить граф в формате pickle для быстрой загрузки
        """
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(self.graph, f)
            return True
        except Exception as e:
            print(f"Ошибка при экспорте в pickle: {e}")
            return False
    
    def load_from_pickle(self, filepath: str) -> bool:
        """
        Загрузить граф из файла pickle
        """
        try:
            with open(filepath, 'rb') as f:
                self.graph = pickle.load(f)
            self._loaded = True
            return True
        except Exception as e:
            print(f"Ошибка при загрузке из pickle: {e}")
            return False
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """
        Получить подробную статистику графа
        """
        graph = self.get_graph()
        
        stats = {
            'basic_stats': {
                'nodes_count': graph.number_of_nodes(),
                'edges_count': graph.number_of_edges(),
                'density': nx.density(graph),
                'is_dag': nx.is_directed_acyclic_graph(graph),
                'is_connected': nx.is_weakly_connected(graph)
            },
            'node_types': {
                'base_skills': len(self.get_base_skills()),
                'leaf_skills': len(self.get_leaf_skills()),
                'intermediate_skills': graph.number_of_nodes() - len(self.get_base_skills()) - len(self.get_leaf_skills())
            },
            'complexity_metrics': {},
            'cycles': self.find_cycles()
        }
        
        # Метрики сложности
        if graph.number_of_nodes() > 0:
            try:
                # Средние метрики
                in_degrees = [graph.in_degree(n) for n in graph.nodes()]
                out_degrees = [graph.out_degree(n) for n in graph.nodes()]
                
                stats['complexity_metrics'] = {
                    'avg_in_degree': sum(in_degrees) / len(in_degrees),
                    'max_in_degree': max(in_degrees),
                    'avg_out_degree': sum(out_degrees) / len(out_degrees),
                    'max_out_degree': max(out_degrees),
                    'avg_clustering': nx.average_clustering(graph.to_undirected()),
                }
            except:
                stats['complexity_metrics'] = {'error': 'Не удалось вычислить метрики'}
        
        return stats
    
    def suggest_learning_sequence(
        self, 
        target_skills: List[int], 
        mastered_skills: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Предложить последовательность изучения для достижения целевых навыков
        """
        if mastered_skills is None:
            mastered_skills = []
        
        graph = self.get_graph()
        mastered_set = set(mastered_skills)
        
        # Находим все необходимые навыки
        required_skills = set()
        for target in target_skills:
            required_skills.add(target)
            required_skills.update(self.get_all_prerequisites(target))
        
        # Исключаем уже освоенные
        to_learn = required_skills - mastered_set
          # Упорядочиваем топологически
        subgraph = graph.subgraph(to_learn)
        try:
            learning_order = list(nx.topological_sort(subgraph))
        except (nx.NetworkXError, nx.NetworkXUnfeasible):
            # Если есть циклы, просто возвращаем навыки в произвольном порядке
            learning_order = list(to_learn)
        
        # Формируем детальную последовательность
        sequence = []
        for i, skill_id in enumerate(learning_order):
            skill_data = graph.nodes[skill_id]
            
            # Проверяем готовность к изучению
            prereqs = set(self.get_skill_prerequisites(skill_id))
            completed_prereqs = prereqs & (mastered_set | set(learning_order[:i]))
            is_ready = len(prereqs - completed_prereqs) == 0
            
            sequence.append({
                'position': i + 1,
                'skill_id': skill_id,
                'skill_name': skill_data.get('name', f'Skill {skill_id}'),
                'is_target': skill_id in target_skills,
                'is_ready': is_ready,
                'prerequisites': list(prereqs),
                'missing_prerequisites': list(prereqs - completed_prereqs),
                'tasks_count': skill_data.get('tasks_count', 0)
            })
        
        return sequence
