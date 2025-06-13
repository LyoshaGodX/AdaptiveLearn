"""
Тестовый скрипт для применения BKT через программный интерфейс
Демонстрирует использование обученной модели optimized_bkt_model
"""

import os
import sys
import django
from pathlib import Path

# Настройка Django
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adaptive_learning.settings')
django.setup()

from mlmodels.interfaces.student_assessment_interface import StudentAssessmentInterface
from student.models import StudentProfile
from mlmodels.models import TaskAttempt, StudentSkillMastery
from datetime import datetime


def main():
    print('🎯 ТЕСТИРОВАНИЕ BKT ПРОГРАММНОГО ИНТЕРФЕЙСА')
    print('='*60)
    
    # 1. Получаем студента
    try:
        student = StudentProfile.objects.get(user__username='student2')
        print(f'👤 Студент найден: {student.full_name}')
    except StudentProfile.DoesNotExist:
        print('❌ Студент student2 не найден')
        return
    
    # 2. Проверяем состояние ДО применения BKT
    print(f'\n📊 СОСТОЯНИЕ ДО ПРИМЕНЕНИЯ BKT:')
    attempts_count = TaskAttempt.objects.filter(student=student).count()
    bkt_before = StudentSkillMastery.objects.filter(student=student).count()
    
    print(f'   📝 Попыток в БД: {attempts_count}')
    print(f'   🧠 BKT записей: {bkt_before}')
    
    if attempts_count == 0:
        print('   ⚠️ У студента нет попыток для обработки!')
        return
    
    # 3. Создаем интерфейс BKT
    print(f'\n🚀 СОЗДАНИЕ BKT ИНТЕРФЕЙСА:')
    try:
        interface = StudentAssessmentInterface()
        print(f'   ✅ Интерфейс создан')
        print(f'   📁 Использует модель: optimized_bkt_model/bkt_model_optimized.pkl')
        print(f'   🧠 Модель загружена: {interface.bkt_model is not None}')
    except Exception as e:
        print(f'   ❌ Ошибка создания интерфейса: {e}')
        return
      # 4. Применяем BKT к студенту
    print(f'\n🧠 ПРИМЕНЕНИЕ BKT К СТУДЕНТУ:')
    try:
        # Получаем попытки студента и конвертируем в нужный формат
        from mlmodels.interfaces.student_assessment_interface import AttemptData
        
        attempts = TaskAttempt.objects.filter(student=student).order_by('completed_at')
        attempt_data_list = []
          print(f'   📝 Конвертируем {attempts.count()} попыток в формат AttemptData...')
        
        for attempt in attempts:
            # Получаем курс для попытки
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
                    difficulty='medium',  # Default difficulty
                    timestamp=attempt.completed_at,
                    attempt_number=1
                )
                attempt_data_list.append(attempt_data)
        
        print(f'   📊 Подготовлено {len(attempt_data_list)} записей для BKT')
        
        start_time = datetime.now()
        result = interface.process_attempt_history(student.id, attempt_data_list)
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        print(f'   ✅ BKT успешно применен!')
        print(f'   ⏱️ Время обработки: {processing_time:.2f} сек')
        print(f'   📊 Обработано попыток: {result.get("processed_attempts", "N/A")}')
        print(f'   🎯 Навыков обработано: {len(result.get("skills", {}))}')
        print(f'   📚 Курсов обработано: {len(result.get("courses", {}))}')
        
    except Exception as e:
        print(f'   ❌ Ошибка применения BKT: {e}')
        import traceback
        traceback.print_exc()
        return
    
    # 5. Проверяем состояние ПОСЛЕ применения BKT
    print(f'\n📊 СОСТОЯНИЕ ПОСЛЕ ПРИМЕНЕНИЯ BKT:')
    bkt_after = StudentSkillMastery.objects.filter(student=student).count()
    
    print(f'   📝 Попыток в БД: {attempts_count}')
    print(f'   🧠 BKT записей: {bkt_after}')
    
    if bkt_after > bkt_before:
        print(f'   ✅ Создано новых BKT записей: {bkt_after - bkt_before}')
    else:
        print(f'   ⚠️ Новые BKT записи не созданы')
    
    # 6. Анализируем результаты BKT
    print(f'\n🔍 АНАЛИЗ РЕЗУЛЬТАТОВ BKT:')
    masteries = StudentSkillMastery.objects.filter(student=student).order_by('-current_mastery_prob')
    
    if masteries.exists():
        print(f'   📈 Топ навыков по освоению:')
        for i, mastery in enumerate(masteries[:5], 1):
            prob_percent = mastery.current_mastery_prob * 100
            print(f'     {i}. 🎯 {mastery.skill.name}: {prob_percent:.1f}%')
            print(f'        📊 P(L0)={mastery.initial_mastery_prob:.3f}, '
                  f'P(T)={mastery.transition_prob:.3f}, '
                  f'P(G)={mastery.guess_prob:.3f}, '
                  f'P(S)={mastery.slip_prob:.3f}')
            print(f'        📝 {mastery.correct_attempts}/{mastery.attempts_count} правильных')
    else:
        print(f'   ❌ BKT данные не найдены')
    
    # 7. Проверяем обученные параметры
    print(f'\n🎓 ПРОВЕРКА ИСПОЛЬЗОВАНИЯ ОБУЧЕННЫХ ПАРАМЕТРОВ:')
    check_trained_parameters_usage(masteries)
    
    # 8. Тестируем другие методы интерфейса
    print(f'\n🔧 ТЕСТИРОВАНИЕ ДОПОЛНИТЕЛЬНЫХ МЕТОДОВ:')
    test_additional_methods(interface, student.id, result)
    
    print(f'\n🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!')


def check_trained_parameters_usage(masteries):
    """Проверяет, используются ли обученные параметры"""
    import json
    from pathlib import Path
    
    try:
        # Загружаем обученные параметры
        model_path = Path('optimized_bkt_model/bkt_model_optimized.json')
        if not model_path.exists():
            print(f'   ⚠️ Файл обученных параметров не найден: {model_path}')
            return
        
        with open(model_path, 'r', encoding='utf-8') as f:
            trained_data = json.load(f)
        
        trained_params = trained_data.get('skill_parameters', {})
        
        matches_count = 0
        total_skills = masteries.count()
        
        for mastery in masteries:
            skill_id = str(mastery.skill.id)
            if skill_id in trained_params:
                trained = trained_params[skill_id]
                
                # Проверяем совпадение параметров (с небольшой погрешностью)
                p_l0_match = abs(mastery.initial_mastery_prob - trained.get('P_L0', 0)) < 0.001
                p_t_match = abs(mastery.transition_prob - trained.get('P_T', 0)) < 0.001
                p_g_match = abs(mastery.guess_prob - trained.get('P_G', 0)) < 0.001
                p_s_match = abs(mastery.slip_prob - trained.get('P_S', 0)) < 0.001
                
                if p_l0_match and p_t_match and p_g_match and p_s_match:
                    matches_count += 1
        
        print(f'   📊 Навыков с обученными параметрами: {matches_count}/{total_skills}')
        
        if matches_count > 0:
            print(f'   ✅ Обученные параметры ИСПОЛЬЗУЮТСЯ!')
        else:
            print(f'   ❌ Обученные параметры НЕ используются!')
        
    except Exception as e:
        print(f'   ⚠️ Ошибка проверки параметров: {e}')


def test_additional_methods(interface, student_id, result):
    """Тестирует дополнительные методы интерфейса"""
    
    try:
        # Тест получения оценки студента
        assessment = interface.get_student_assessment(student_id)
        if assessment:
            print(f'   ✅ get_student_assessment: Данные получены')
        else:
            print(f'   ⚠️ get_student_assessment: Данные не найдены')
        
        # Тест рекомендаций
        if 'skills' in result and result['skills']:
            skill_ids = list(result['skills'].keys())
            if skill_ids:
                recommendations = interface.get_learning_recommendations(student_id, skill_ids[:3])
                print(f'   ✅ get_learning_recommendations: {len(recommendations)} рекомендаций')
            else:
                print(f'   ⚠️ get_learning_recommendations: Нет навыков для тестирования')
        
        # Тест предсказания освоения навыка
        if 'skills' in result and result['skills']:
            skill_id = list(result['skills'].keys())[0]
            prediction = interface.predict_skill_mastery(student_id, skill_id, num_attempts=5)
            print(f'   ✅ predict_skill_mastery: Предсказание {prediction:.3f}')
        
    except Exception as e:
        print(f'   ⚠️ Ошибка тестирования методов: {e}')


def print_detailed_statistics():
    """Выводит детальную статистику по студенту"""
    print(f'\n📋 ДЕТАЛЬНАЯ СТАТИСТИКА СТУДЕНТА:')
    
    try:
        student = StudentProfile.objects.get(user__username='student2')
        attempts = TaskAttempt.objects.filter(student=student).order_by('completed_at')
        masteries = StudentSkillMastery.objects.filter(student=student)
        
        print(f'👤 Студент: {student.full_name}')
        print(f'📝 Всего попыток: {attempts.count()}')
        print(f'✅ Правильных: {attempts.filter(is_correct=True).count()}')
        print(f'❌ Неправильных: {attempts.filter(is_correct=False).count()}')
        
        if attempts.exists():
            accuracy = attempts.filter(is_correct=True).count() / attempts.count() * 100
            print(f'🎯 Общая точность: {accuracy:.1f}%')
        
        print(f'🧠 BKT навыков: {masteries.count()}')
        
        if masteries.exists():
            avg_mastery = sum(m.current_mastery_prob for m in masteries) / masteries.count()
            print(f'📊 Средний уровень освоения: {avg_mastery:.3f}')
        
    except Exception as e:
        print(f'❌ Ошибка вывода статистики: {e}')


if __name__ == "__main__":
    main()
    print_detailed_statistics()
