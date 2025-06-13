"""
Утилиты для работы с новыми навыками в обученной BKT модели
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from typing import Dict, List, Optional, Tuple
import json
import pickle
from mlmodels.bkt.base_model import BKTModel, BKTParameters
from mlmodels.bkt.base_model import TaskCharacteristics

class NewSkillManager:
    """Менеджер для работы с новыми навыками в обученной BKT модели"""
    
    def __init__(self, bkt_model: BKTModel):
        self.bkt_model = bkt_model
        self.skill_type_templates = self._init_skill_templates()
        
    def _init_skill_templates(self) -> Dict[str, BKTParameters]:
        """Инициализировать шаблоны параметров по типам навыков"""
        return {
            'default': BKTParameters(P_L0=0.1, P_T=0.3, P_G=0.2, P_S=0.1),
            'mathematics': BKTParameters(P_L0=0.05, P_T=0.25, P_G=0.15, P_S=0.08),
            'programming': BKTParameters(P_L0=0.08, P_T=0.30, P_G=0.10, P_S=0.15),
            'language': BKTParameters(P_L0=0.15, P_T=0.35, P_G=0.25, P_S=0.12),
            'science': BKTParameters(P_L0=0.12, P_T=0.28, P_G=0.18, P_S=0.10),
            'art': BKTParameters(P_L0=0.20, P_T=0.40, P_G=0.30, P_S=0.15)
        }
    
    def add_new_skill(
        self, 
        skill_id: int, 
        skill_type: str = 'default',
        custom_parameters: Optional[BKTParameters] = None,
        prerequisites: Optional[List[int]] = None
    ) -> BKTParameters:
        """
        Добавить новый навык в модель
        
        Args:
            skill_id: ID нового навыка
            skill_type: Тип навыка ('default', 'mathematics', 'programming', etc.)
            custom_parameters: Пользовательские параметры (приоритет над skill_type)
            prerequisites: Список ID навыков-пререквизитов
            
        Returns:
            BKTParameters: Установленные параметры навыка
        """
        # Выбираем параметры
        if custom_parameters:
            parameters = custom_parameters
        elif skill_type in self.skill_type_templates:
            parameters = self.skill_type_templates[skill_type]
        else:
            parameters = self.skill_type_templates['default']
            
        # Устанавливаем параметры в модель
        self.bkt_model.skill_parameters[skill_id] = parameters
        
        # Добавляем пререквизиты в граф
        if prerequisites:
            if not hasattr(self.bkt_model, 'skills_graph') or self.bkt_model.skills_graph is None:
                self.bkt_model.skills_graph = {}
            self.bkt_model.skills_graph[skill_id] = prerequisites
            
        return parameters
    
    def get_recommended_parameters(
        self, 
        skill_id: int,
        skill_type: str = 'default',
        prerequisites: Optional[List[int]] = None
    ) -> BKTParameters:
        """
        Получить рекомендованные параметры для нового навыка
        
        Args:
            skill_id: ID навыка
            skill_type: Тип навыка
            prerequisites: Пререквизиты для наследования параметров
            
        Returns:
            BKTParameters: Рекомендованные параметры
        """
        if prerequisites:
            return self._inherit_from_prerequisites(prerequisites)
        elif skill_type in self.skill_type_templates:
            return self.skill_type_templates[skill_type]
        else:
            return self._get_average_parameters()
    
    def _inherit_from_prerequisites(self, prerequisites: List[int]) -> BKTParameters:
        """Наследовать параметры от пререквизитов"""
        available_prereqs = [
            skill_id for skill_id in prerequisites 
            if skill_id in self.bkt_model.skill_parameters
        ]
        
        if not available_prereqs:
            return self.skill_type_templates['default']
        
        # Берем средние параметры от пререквизитов
        prereq_params = [self.bkt_model.skill_parameters[skill_id] for skill_id in available_prereqs]
        
        avg_P_L0 = sum(p.P_L0 for p in prereq_params) / len(prereq_params)
        avg_P_T = sum(p.P_T for p in prereq_params) / len(prereq_params)
        avg_P_G = sum(p.P_G for p in prereq_params) / len(prereq_params)
        avg_P_S = sum(p.P_S for p in prereq_params) / len(prereq_params)
        
        # Немного снижаем начальное знание (новый навык сложнее)
        avg_P_L0 *= 0.8
        
        return BKTParameters(
            P_L0=max(0.01, min(0.3, avg_P_L0)),
            P_T=max(0.1, min(0.99, avg_P_T)),
            P_G=max(0.05, min(0.5, avg_P_G)),
            P_S=max(0.05, min(0.5, avg_P_S))
        )
    
    def _get_average_parameters(self) -> BKTParameters:
        """Получить средние параметры от всех обученных навыков"""
        if not self.bkt_model.skill_parameters:
            return self.skill_type_templates['default']
        
        params_list = list(self.bkt_model.skill_parameters.values())
        
        avg_P_L0 = sum(p.P_L0 for p in params_list) / len(params_list)
        avg_P_T = sum(p.P_T for p in params_list) / len(params_list)
        avg_P_G = sum(p.P_G for p in params_list) / len(params_list)
        avg_P_S = sum(p.P_S for p in params_list) / len(params_list)
        
        return BKTParameters(
            P_L0=avg_P_L0,
            P_T=avg_P_T,
            P_G=avg_P_G,
            P_S=avg_P_S
        )
    
    def predict_for_new_skill(
        self, 
        student_id: int, 
        skill_id: int,
        skill_type: str = 'default',
        prerequisites: Optional[List[int]] = None
    ) -> float:
        """
        Получить прогноз освоения нового навыка студентом
        
        Args:
            student_id: ID студента
            skill_id: ID нового навыка
            skill_type: Тип навыка
            prerequisites: Пререквизиты
            
        Returns:
            float: Прогноз освоения (0-1)
        """
        # Добавляем навык если его нет
        if skill_id not in self.bkt_model.skill_parameters:
            self.add_new_skill(skill_id, skill_type, prerequisites=prerequisites)
        
        # Инициализируем студента для навыка
        if (student_id not in self.bkt_model.student_states or 
            skill_id not in self.bkt_model.student_states[student_id]):
            self.bkt_model.initialize_student(student_id, skill_id)
        
        # Получаем прогноз
        return self.bkt_model.get_student_mastery(student_id, skill_id)
    
    def batch_add_skills(
        self, 
        skills_config: List[Dict]
    ) -> Dict[int, BKTParameters]:
        """
        Добавить несколько навыков одновременно
        
        Args:
            skills_config: Список конфигураций навыков
                          [{'skill_id': 1001, 'skill_type': 'mathematics', 'prerequisites': [1, 2]}, ...]
                          
        Returns:
            Dict[int, BKTParameters]: Словарь установленных параметров
        """
        results = {}
        
        for config in skills_config:
            skill_id = config['skill_id']
            skill_type = config.get('skill_type', 'default')
            prerequisites = config.get('prerequisites')
            custom_parameters = config.get('custom_parameters')
            
            if custom_parameters:
                params = BKTParameters(**custom_parameters)
            else:
                params = None
                
            results[skill_id] = self.add_new_skill(
                skill_id=skill_id,
                skill_type=skill_type,
                custom_parameters=params,
                prerequisites=prerequisites
            )
            
        return results
    
    def export_skill_templates(self, filepath: str):
        """Экспортировать шаблоны параметров в JSON"""
        templates_dict = {}
        for skill_type, params in self.skill_type_templates.items():
            templates_dict[skill_type] = params.to_dict()
            
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(templates_dict, f, indent=2, ensure_ascii=False)
    
    def load_skill_templates(self, filepath: str):
        """Загрузить шаблоны параметров из JSON"""
        with open(filepath, 'r', encoding='utf-8') as f:
            templates_dict = json.load(f)
            
        for skill_type, params_dict in templates_dict.items():
            self.skill_type_templates[skill_type] = BKTParameters.from_dict(params_dict)

def load_trained_model(model_path: str = "optimized_bkt_model/bkt_model_optimized.pkl") -> BKTModel:
    """Загрузить обученную BKT модель"""
    with open(model_path, 'rb') as f:
        return pickle.load(f)

# Пример использования
if __name__ == "__main__":
    # Загружаем обученную модель
    bkt_model = load_trained_model()
    
    # Создаем менеджер новых навыков
    skill_manager = NewSkillManager(bkt_model)
    
    # Добавляем новый навык по математике
    new_skill_id = 1001
    skill_manager.add_new_skill(
        skill_id=new_skill_id,
        skill_type='mathematics',
        prerequisites=[1, 2]  # Зависит от навыков 1 и 2
    )
    
    # Получаем прогноз для студента
    student_id = 999
    prediction = skill_manager.predict_for_new_skill(
        student_id=student_id,
        skill_id=new_skill_id
    )
    
    print(f"Прогноз освоения навыка {new_skill_id} студентом {student_id}: {prediction:.3f}")
    
    # Добавляем несколько навыков сразу
    skills_config = [
        {
            'skill_id': 1002,
            'skill_type': 'programming',
            'prerequisites': [5, 6]
        },
        {
            'skill_id': 1003,
            'skill_type': 'language',
            'custom_parameters': {
                'P_L0': 0.2,
                'P_T': 0.4,
                'P_G': 0.3,
                'P_S': 0.1
            }
        }
    ]
    
    results = skill_manager.batch_add_skills(skills_config)
    print(f"Добавлено навыков: {len(results)}")
    
    # Экспортируем шаблоны
    skill_manager.export_skill_templates("skill_templates.json")
    print("Шаблоны параметров экспортированы в skill_templates.json")
