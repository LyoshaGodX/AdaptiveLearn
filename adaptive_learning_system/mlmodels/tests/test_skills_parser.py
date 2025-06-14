"""
Простой тест парсинга графа навыков.

Быстрая проверка функциональности без полного анализа.

Использование:
    python manage.py shell
    exec(open('mlmodels/tests/test_skills_parser.py').read())
"""

import os
import sys
import django
from pathlib import Path

# Настройка Django
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

from skills.models import Skill, Course
from methodist.models import Task
from mlmodels.tests.parse_skills_graph import SkillsGraphParser


def test_basic_parsing():
    """Базовый тест парсинга"""
    print("🧪 Тестирование базового парсинга графа навыков...")
    
    parser = SkillsGraphParser()
    
    # Тест парсинга графа навыков
    skills_graph = parser.parse_skills_graph()
    print(f"✓ Граф навыков: {len(skills_graph)} навыков")
    
    # Тест парсинга связей заданий
    task_skills = parser.parse_task_skills_mapping()
    print(f"✓ Связи заданий: {len(task_skills)} заданий")
    
    # Простая статистика
    total_prereqs = sum(len(prereqs) for prereqs in skills_graph.values())
    skills_with_prereqs = sum(1 for prereqs in skills_graph.values() if prereqs)
    
    print(f"✓ Общее количество prerequisite связей: {total_prereqs}")
    print(f"✓ Навыков с prerequisites: {skills_with_prereqs}")
    
    # Примеры навыков
    print("\n📝 Примеры навыков:")
    for i, (skill_id, prereqs) in enumerate(list(skills_graph.items())[:5]):
        skill_name = parser.skill_info[skill_id].name
        prereq_count = len(prereqs)
        tasks_count = len(parser.skill_tasks_mapping.get(skill_id, set()))
        print(f"  {i+1}. {skill_name} (prerequisites: {prereq_count}, заданий: {tasks_count})")
    
    return parser


def test_analysis():
    """Тест анализа структуры"""
    print("\n🔍 Тестирование анализа структуры...")
    
    parser = test_basic_parsing()
    analysis = parser.analyze_graph_structure()
    
    print(f"✓ Максимальная глубина: {analysis['max_depth']}")
    print(f"✓ Корневых навыков: {len(analysis['root_skills'])}")
    print(f"✓ Листовых навыков: {len(analysis['leaf_skills'])}")
    print(f"✓ Циклов найдено: {len(analysis['cycles'])}")
    
    return parser


def test_learning_path():
    """Тест построения пути изучения"""
    print("\n🎯 Тестирование построения пути изучения...")
    
    parser = test_basic_parsing()
    
    # Берем первый навык с prerequisites
    target_skill = None
    for skill_id, prereqs in parser.skills_graph.items():
        if prereqs:
            target_skill = skill_id
            break
    
    if target_skill:
        path = parser.get_skill_learning_path(target_skill)
        skill_name = parser.skill_info[target_skill].name
        
        print(f"✓ Путь изучения для '{skill_name}' ({len(path)} шагов):")
        for i, skill_id in enumerate(path[-5:], 1):  # Показываем последние 5
            name = parser.skill_info[skill_id].name
            print(f"    {i}. {name}")
    else:
        print("⚠️  Не найдено навыков с prerequisites для тестирования")
    
    return parser


def test_export():
    """Тест экспорта данных"""
    print("\n💾 Тестирование экспорта данных...")
    
    parser = test_basic_parsing()
    
    # Экспорт в temp_dir
    temp_dir = Path(__file__).parent.parent.parent / 'temp_dir'
    parser.export_graph_data(str(temp_dir))
    
    # Проверяем созданные файлы
    expected_files = ['skills_graph.json', 'skills_graph_viz.json', 'skills_graph.dot']
    created_files = []
    
    for filename in expected_files:
        filepath = temp_dir / filename
        if filepath.exists():
            created_files.append(filename)
            print(f"✓ Создан файл: {filename} ({filepath.stat().st_size} bytes)")
    
    print(f"✓ Создано файлов: {len(created_files)}/{len(expected_files)}")
    
    return parser


def main():
    """Запуск всех тестов"""
    print("🚀 Запуск тестов парсера графа навыков...\n")
    
    try:
        # Основные тесты
        test_basic_parsing()
        test_analysis()
        test_learning_path()
        test_export()
        
        print("\n✅ Все тесты прошли успешно!")
        
    except Exception as e:
        print(f"\n❌ Ошибка в тестах: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
