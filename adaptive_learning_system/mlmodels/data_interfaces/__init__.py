"""
Интерфейсы для работы с данными адаптивной системы обучения
"""

# Отложенные импорты
def get_database_interfaces():
    from .database_interface import DatabaseInterface
    return DatabaseInterface

def get_skills_graph():
    from .skills_graph import SkillsGraph
    return SkillsGraph

# Для обратной совместимости - делаем импорты доступными
def DatabaseInterface():
    return get_database_interfaces()

def SkillsGraph():
    return get_skills_graph()

__all__ = [
    'get_database_interfaces',
    'get_skills_graph',
    'DatabaseInterface', 
    'SkillsGraph'
]
