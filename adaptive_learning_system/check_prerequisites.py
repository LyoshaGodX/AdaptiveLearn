"""
Проверочный скрипт перед тестированием BKT интерфейса
Проверяет все необходимые условия
"""

import os
import sys
import django
from pathlib import Path

# Настройка Django
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

from student.models import StudentProfile
from mlmodels.models import TaskAttempt, StudentSkillMastery
from mlmodels.interfaces.student_assessment_interface import StudentAssessmentInterface
import json


def check_prerequisites():
    """Проверяет все необходимые условия"""
    print('🔍 ПРОВЕРКА ПРЕДВАРИТЕЛЬНЫХ УСЛОВИЙ')
    print('='*50)
    
    all_checks_passed = True
    
    # 1. Проверка студента student2
    print('1️⃣ Проверка студента student2...')
    try:
        student = StudentProfile.objects.get(user__username='student2')
        print(f'   ✅ Студент найден: {student.full_name}')
        print(f'   📧 Email: {student.email}')
        print(f'   🆔 ID: {student.id}')
    except StudentProfile.DoesNotExist:
        print('   ❌ Студент student2 НЕ найден!')
        all_checks_passed = False
        return all_checks_passed
    
    # 2. Проверка истории попыток
    print(f'\n2️⃣ Проверка истории попыток...')
    attempts = TaskAttempt.objects.filter(student=student)
    attempts_count = attempts.count()
    
    if attempts_count > 0:
        print(f'   ✅ Найдено попыток: {attempts_count}')
        correct_count = attempts.filter(is_correct=True).count()
        accuracy = (correct_count / attempts_count) * 100 if attempts_count > 0 else 0
        print(f'   📊 Правильных: {correct_count}/{attempts_count} ({accuracy:.1f}%)')
        
        # Проверяем навыки в попытках
        skills_in_attempts = set()
        for attempt in attempts[:5]:  # Берем первые 5 для проверки
            skills_in_attempts.update(attempt.task.skills.values_list('id', flat=True))
        
        print(f'   🎯 Уникальных навыков в попытках: {len(skills_in_attempts)}')
        print(f'   📝 Примеры навыков: {list(skills_in_attempts)[:3]}')
    else:
        print('   ❌ У студента НЕТ попыток!')
        all_checks_passed = False
    
    # 3. Проверка отсутствия BKT параметров
    print(f'\n3️⃣ Проверка отсутствия BKT параметров...')
    bkt_records = StudentSkillMastery.objects.filter(student=student)
    bkt_count = bkt_records.count()
    
    if bkt_count == 0:
        print(f'   ✅ BKT параметры отсутствуют (как и должно быть)')
    else:
        print(f'   ⚠️ Найдено BKT записей: {bkt_count}')
        print(f'   💡 Это не критично, но означает, что BKT уже применялся')
        for record in bkt_records[:3]:
            print(f'      🎯 {record.skill.name}: P(Lt)={record.current_mastery_prob:.3f}')
    
    # 4. Проверка интерфейса и загрузки попыток по ID
    print(f'\n4️⃣ Проверка student_assessment_interface...')
    try:
        interface = StudentAssessmentInterface()
        print(f'   ✅ Интерфейс создан успешно')
        print(f'   🧠 BKT модель загружена: {interface.bkt_model is not None}')
        
        # Проверяем, что интерфейс может получать данные из БД
        # Для этого проверим, что метод process_attempt_history существует
        if hasattr(interface, 'process_attempt_history'):
            print(f'   ✅ Метод process_attempt_history доступен')
        else:
            print(f'   ❌ Метод process_attempt_history НЕ найден!')
            all_checks_passed = False
            
    except Exception as e:
        print(f'   ❌ Ошибка создания интерфейса: {e}')
        all_checks_passed = False
    
    # 5. Проверка оптимизированной модели BKT
    print(f'\n5️⃣ Проверка оптимизированной модели BKT...')
    
    # Проверяем файлы модели
    model_pkl = Path('optimized_bkt_model/bkt_model_optimized.pkl')
    model_json = Path('optimized_bkt_model/bkt_model_optimized.json')
    
    if model_pkl.exists():
        print(f'   ✅ Файл модели найден: {model_pkl}')
        print(f'   📏 Размер: {model_pkl.stat().st_size} байт')
    else:
        print(f'   ❌ Файл модели НЕ найден: {model_pkl}')
        all_checks_passed = False
    
    if model_json.exists():
        print(f'   ✅ Файл параметров найден: {model_json}')
        
        # Проверяем содержимое JSON
        try:
            with open(model_json, 'r', encoding='utf-8') as f:
                model_data = json.load(f)
            
            skill_params = model_data.get('skill_parameters', {})
            print(f'   📊 Параметров навыков: {len(skill_params)}')
            
            # Показываем пример параметров
            if skill_params:
                first_skill = list(skill_params.keys())[0]
                params = skill_params[first_skill]
                print(f'   💡 Пример (навык {first_skill}):')
                print(f'      P(L0)={params.get("P_L0", "N/A"):.3f}')
                print(f'      P(T)={params.get("P_T", "N/A"):.3f}')
                print(f'      P(G)={params.get("P_G", "N/A"):.3f}')
                print(f'      P(S)={params.get("P_S", "N/A"):.3f}')
            
        except Exception as e:
            print(f'   ⚠️ Ошибка чтения JSON: {e}')
    else:
        print(f'   ❌ Файл параметров НЕ найден: {model_json}')
        all_checks_passed = False
    
    # Итоговая проверка
    print(f'\n📋 ИТОГОВАЯ ПРОВЕРКА:')
    print('='*30)
    
    if all_checks_passed:
        print('✅ ВСЕ УСЛОВИЯ ВЫПОЛНЕНЫ!')
        print('🚀 Можно запускать test_bkt_interface.py')
        
        print(f'\n📊 КРАТКАЯ СВОДКА:')
        print(f'   👤 Студент: {student.full_name} (ID: {student.id})')
        print(f'   📝 Попыток: {attempts_count}')
        print(f'   🧠 BKT записей до: {bkt_count}')
        print(f'   🎯 Навыков в попытках: {len(skills_in_attempts)}')
        
    else:
        print('❌ НЕ ВСЕ УСЛОВИЯ ВЫПОЛНЕНЫ!')
        print('⚠️ Необходимо исправить проблемы перед запуском теста')
    
    return all_checks_passed


def simulate_interface_workflow():
    """Имитирует работу интерфейса для проверки"""
    print(f'\n🧪 ИМИТАЦИЯ РАБОТЫ ИНТЕРФЕЙСА:')
    print('-'*40)
    
    try:
        student = StudentProfile.objects.get(user__username='student2')
        
        # Проверяем, что мы можем получить данные из БД
        from mlmodels.interfaces.student_assessment_interface import AttemptData
        attempts = TaskAttempt.objects.filter(student=student)
        
        print(f'   📝 Попыток из БД: {attempts.count()}')
        
        # Конвертируем первые несколько попыток
        attempt_data_list = []
        for attempt in attempts[:3]:  # Берем только первые 3 для теста
            course_id = None
            if attempt.task.courses.exists():
                course_id = attempt.task.courses.first().id
                
            for skill in attempt.task.skills.all():
                attempt_data = AttemptData(
                    student_id=student.id,
                    task_id=attempt.task.id,
                    skill_id=skill.id,
                    course_id=course_id,
                    is_correct=attempt.is_correct,
                    answer_score=1.0 if attempt.is_correct else 0.0,
                    task_type=attempt.task.task_type or 'single',
                    difficulty='medium',
                    timestamp=attempt.completed_at,
                    attempt_number=1
                )
                attempt_data_list.append(attempt_data)
        
        print(f'   📊 Конвертировано: {len(attempt_data_list)} записей AttemptData')
        print(f'   ✅ Формат данных корректный')
        
        # Проверяем навыки
        skill_ids = set(ad.skill_id for ad in attempt_data_list)
        print(f'   🎯 Навыков для обработки: {len(skill_ids)}')
        
    except Exception as e:
        print(f'   ❌ Ошибка имитации: {e}')
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if check_prerequisites():
        simulate_interface_workflow()
        print(f'\n🎉 ВСЕ ГОТОВО К ТЕСТИРОВАНИЮ!')
    else:
        print(f'\n⚠️ ИСПРАВЬТЕ ПРОБЛЕМЫ ПЕРЕД ТЕСТИРОВАНИЕМ!')
