#!/usr/bin/env python
"""
Скрипт для обнаружения и устранения циклов в графе навыков
"""

import os
import sys
import django
from pathlib import Path

# Настройка Django
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

import networkx as nx
from skills.models import Skill
from mlmodels.data_interfaces.skills_graph import SkillsGraphInterface


def find_and_display_cycles():
    """Найти и отобразить все циклы в графе навыков"""
    print("🔍 АНАЛИЗ ЦИКЛОВ В ГРАФЕ НАВЫКОВ")
    print("=" * 50)
    
    # Строим граф навыков
    graph_interface = SkillsGraphInterface()
    graph_interface.build_graph_from_database()
    graph = graph_interface.get_graph()
    
    print(f"Граф содержит {graph.number_of_nodes()} навыков и {graph.number_of_edges()} связей")
    
    # Находим все циклы
    try:
        cycles = list(nx.simple_cycles(graph))
        print(f"\nНайдено циклов: {len(cycles)}")
        
        if cycles:
            print("\nДетали циклов:")
            for i, cycle in enumerate(cycles, 1):
                print(f"\nЦикл {i}: {' -> '.join(map(str, cycle))} -> {cycle[0]}")
                
                # Получаем названия навыков
                skill_names = []
                for skill_id in cycle:
                    try:
                        skill = Skill.objects.get(id=skill_id)
                        skill_names.append(f"{skill.name} (ID: {skill.id})")
                    except Skill.DoesNotExist:
                        skill_names.append(f"Навык {skill_id} (не найден)")
                
                print(f"  Навыки: {' -> '.join(skill_names)}")
                
                # Показываем связи в цикле
                print("  Связи в цикле:")
                for j in range(len(cycle)):
                    from_skill_id = cycle[j]
                    to_skill_id = cycle[(j + 1) % len(cycle)]
                    
                    from_skill = Skill.objects.get(id=from_skill_id)
                    to_skill = Skill.objects.get(id=to_skill_id)
                    
                    print(f"    {from_skill.name} -> {to_skill.name}")
        
        return cycles
        
    except Exception as e:
        print(f"Ошибка при поиске циклов: {e}")
        return []


def break_cycles_interactive(cycles):
    """Интерактивное устранение циклов"""
    print("\n🔧 УСТРАНЕНИЕ ЦИКЛОВ")
    print("=" * 50)
    
    if not cycles:
        print("Циклы не найдены!")
        return
    
    removed_edges = []
    
    for i, cycle in enumerate(cycles, 1):
        print(f"\n--- Цикл {i} ---")
        
        # Показываем все рёбра в цикле
        edges_in_cycle = []
        for j in range(len(cycle)):
            from_skill_id = cycle[j]
            to_skill_id = cycle[(j + 1) % len(cycle)]
            edges_in_cycle.append((from_skill_id, to_skill_id))
        
        print("Рёбра в цикле:")
        for idx, (from_id, to_id) in enumerate(edges_in_cycle):
            from_skill = Skill.objects.get(id=from_id)
            to_skill = Skill.objects.get(id=to_id)
            print(f"  {idx + 1}. {from_skill.name} -> {to_skill.name}")
        
        # Автоматически выбираем ребро для удаления
        # Стратегия: удаляем ребро с наименьшим приоритетом
        edge_to_remove = choose_edge_to_remove(edges_in_cycle)
        
        if edge_to_remove:
            from_id, to_id = edge_to_remove
            from_skill = Skill.objects.get(id=from_id)
            to_skill = Skill.objects.get(id=to_id)
            
            print(f"\n⚠️ Удаляем связь: {from_skill.name} -> {to_skill.name}")
            
            # Удаляем зависимость
            from_skill.prerequisites.remove(to_skill)
            removed_edges.append((from_skill.name, to_skill.name))
            
            print(f"✅ Связь удалена")
    
    print(f"\n🎉 Устранение циклов завершено!")
    print(f"Удалено связей: {len(removed_edges)}")
    
    if removed_edges:
        print("\nУдалённые связи:")
        for from_name, to_name in removed_edges:
            print(f"  - {from_name} -> {to_name}")


def choose_edge_to_remove(edges_in_cycle):
    """Выбрать ребро для удаления из цикла"""
    # Стратегия: удаляем ребро, которое ведёт к навыку с наибольшим количеством зависимостей
    # Это минимизирует влияние на структуру графа
    
    best_edge = None
    max_out_degree = -1
    
    for from_id, to_id in edges_in_cycle:
        to_skill = Skill.objects.get(id=to_id)
        out_degree = to_skill.prerequisites.count()  # Количество исходящих связей
        
        if out_degree > max_out_degree:
            max_out_degree = out_degree
            best_edge = (from_id, to_id)
    
    return best_edge


def verify_no_cycles():
    """Проверить, что циклы устранены"""
    print("\n🔍 ПРОВЕРКА РЕЗУЛЬТАТА")
    print("=" * 50)
    
    graph_interface = SkillsGraphInterface()
    graph_interface.build_graph_from_database()
    graph = graph_interface.get_graph()
    
    try:
        cycles = list(nx.simple_cycles(graph))
        if cycles:
            print(f"❌ Ещё остались циклы: {len(cycles)}")
            return False
        else:
            print("✅ Циклы устранены! Граф стал ациклическим.")
            
            # Проверяем топологическую сортировку
            try:
                topo_order = list(nx.topological_sort(graph))
                print(f"✅ Топологическая сортировка работает: {len(topo_order)} навыков упорядочены")
                
                # Показываем первые 10 навыков в порядке изучения
                print("\nРекомендуемый порядок изучения (первые 10):")
                for i, skill_id in enumerate(topo_order[:10], 1):
                    skill = Skill.objects.get(id=skill_id)
                    print(f"  {i}. {skill.name}")
                
                return True
            except nx.NetworkXUnfeasible:
                print("❌ Топологическая сортировка всё ещё не работает")
                return False
                
    except Exception as e:
        print(f"Ошибка при проверке: {e}")
        return False


def main():
    """Основная функция"""
    print("УСТРАНЕНИЕ ЦИКЛОВ В ГРАФЕ НАВЫКОВ")
    print("=" * 60)
    
    # 1. Найти циклы
    cycles = find_and_display_cycles()
    
    if not cycles:
        print("✅ Граф уже ациклический!")
        return
    
    # 2. Подтверждение
    print(f"\nНайдено {len(cycles)} циклов. Продолжить устранение? (y/N): ", end="")
    response = input().strip().lower()
    
    if response != 'y':
        print("Операция отменена.")
        return
    
    # 3. Устранить циклы
    break_cycles_interactive(cycles)
    
    # 4. Проверить результат
    verify_no_cycles()


if __name__ == "__main__":
    main()
