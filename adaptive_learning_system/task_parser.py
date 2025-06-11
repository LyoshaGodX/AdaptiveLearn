#!/usr/bin/env python
"""
Парсер текстового формата заданий для LLM
Преобразует простой текстовый формат в JSON для импорта
"""

import re
import json
import os
from datetime import datetime
from typing import List, Dict, Any

class TaskParser:
    """Парсер заданий из текстового формата"""
    
    def __init__(self):
        self.tasks = []
        self.errors = []
        
    def parse_text_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Парсит файл с заданиями в текстовом формате"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return self.parse_text_content(content)
            
        except Exception as e:
            self.errors.append(f"Ошибка чтения файла {file_path}: {e}")
            return []
    
    def parse_text_content(self, content: str) -> List[Dict[str, Any]]:
        """Парсит содержимое с заданиями"""
        self.tasks = []
        self.errors = []
        
        # Разделяем на блоки заданий
        task_blocks = self._split_into_task_blocks(content)
        
        for i, block in enumerate(task_blocks, 1):
            try:
                task = self._parse_single_task(block, i)
                if task:
                    self.tasks.append(task)
            except Exception as e:
                self.errors.append(f"Ошибка парсинга задания {i}: {e}")
        
        return self.tasks
    
    def _split_into_task_blocks(self, content: str) -> List[str]:
        """Разделяет текст на блоки заданий"""
        # Ищем начало заданий по ключевому слову "ЗАДАНИЕ:"
        blocks = []
        lines = content.split('\n')
        current_block = []
        
        for line in lines:
            if line.strip().startswith('ЗАДАНИЕ:') and current_block:
                # Новое задание началось, сохраняем предыдущее
                blocks.append('\n'.join(current_block))
                current_block = [line]
            elif line.strip().startswith('ЗАДАНИЕ:'):
                # Первое задание
                current_block = [line]
            elif current_block:
                # Продолжение текущего задания
                current_block.append(line)
        
        # Добавляем последний блок
        if current_block:
            blocks.append('\n'.join(current_block))
        
        return blocks
    
    def _parse_single_task(self, block: str, task_num: int) -> Dict[str, Any]:
        """Парсит одно задание"""
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        
        task = {
            'title': '',
            'task_type': 'single',
            'difficulty': 'beginner',
            'question_text': '',
            'correct_answer': '',
            'explanation': '',
            'is_active': True,
            'skills': [],
            'courses': [],
            'answers': []
        }
        
        current_section = None
        question_lines = []
        explanation_lines = []
        variants = []
        
        for line in lines:
            if line.startswith('ЗАДАНИЕ:'):
                task['title'] = line.replace('ЗАДАНИЕ:', '').strip()
            elif line.startswith('ТИП:'):
                task_type = line.replace('ТИП:', '').strip().lower()
                if task_type in ['single', 'multiple', 'true_false']:
                    task['task_type'] = task_type
            elif line.startswith('СЛОЖНОСТЬ:'):
                difficulty = line.replace('СЛОЖНОСТЬ:', '').strip().lower()
                if difficulty in ['beginner', 'intermediate', 'advanced']:
                    task['difficulty'] = difficulty
            elif line.startswith('НАВЫКИ:'):
                skills_text = line.replace('НАВЫКИ:', '').strip()
                task['skills'] = [s.strip() for s in skills_text.split(',')]
            elif line.startswith('КУРСЫ:'):
                courses_text = line.replace('КУРСЫ:', '').strip()
                task['courses'] = [c.strip() for c in courses_text.split(',')]
            elif line.startswith('ВОПРОС:'):
                current_section = 'question'
                continue
            elif line.startswith('ВАРИАНТЫ:'):
                current_section = 'variants'
                continue
            elif line.startswith('ПРАВИЛЬНЫЙ:') or line.startswith('ПРАВИЛЬНЫЕ:'):
                correct_text = line.replace('ПРАВИЛЬНЫЙ:', '').replace('ПРАВИЛЬНЫЕ:', '').strip()
                task['correct_answer'] = correct_text
                current_section = None
            elif line.startswith('УТВЕРЖДЕНИЕ:'):
                current_section = 'question'
                continue
            elif line.startswith('ОБЪЯСНЕНИЕ:'):
                current_section = 'explanation'
                continue
            elif current_section == 'question':
                question_lines.append(line)            elif current_section == 'variants':
                if line and (line.startswith(('A)', 'B)', 'C)', 'D)', 'E)', 'F)')) or re.match(r'^\d+\)', line)):
                    variants.append(line)
            elif current_section == 'explanation':
                explanation_lines.append(line)
        
        # Собираем вопрос
        task['question_text'] = '\n'.join(question_lines).strip()
        
        # Собираем объяснение
        task['explanation'] = '\n'.join(explanation_lines).strip()
        
        # Обрабатываем варианты ответов
        if variants:
            task['answers'] = self._process_variants(variants, task['correct_answer'], task['task_type'])
        elif task['task_type'] == 'true_false':
            # Для true_false создаем стандартные варианты
            task['answers'] = [
                {'text': 'Верно', 'is_correct': task['correct_answer'].lower() in ['верно', 'true'], 'order': 0},
                {'text': 'Неверно', 'is_correct': task['correct_answer'].lower() in ['неверно', 'false'], 'order': 1}
            ]
        
        return task
    
    def _process_variants(self, variants: List[str], correct_answer: str, task_type: str) -> List[Dict[str, Any]]:
        """Обрабатывает варианты ответов"""
        answers = []
        correct_letters = []
        
        # Извлекаем правильные ответы
        if task_type == 'multiple':
            # Для множественного выбора: "A, C, E" или "A,C,E"
            correct_letters = [letter.strip() for letter in correct_answer.replace(',', ' ').split()]
        else:
            # Для одиночного выбора: "B"
            correct_letters = [correct_answer.strip()]
        
        for i, variant in enumerate(variants):
            # Извлекаем букву/цифру и текст
            match = re.match(r'^([A-F]|\d+)\)\s*(.+)$', variant)
            if match:
                letter = match.group(1)
                text = match.group(2).strip()
                
                is_correct = letter in correct_letters
                
                answers.append({
                    'text': text,
                    'is_correct': is_correct,
                    'order': i
                })
        
        return answers
    
    def save_as_json(self, output_file: str) -> str:
        """Сохраняет распарсенные задания в JSON"""
        data = {
            'metadata': {
                'export_date': datetime.now().isoformat(),
                'total_tasks': len(self.tasks),
                'version': '1.0',
                'format': 'JSON',
                'description': 'Tasks parsed from text format for LLM'
            },
            'tasks': self.tasks
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return output_file
    
    def validate_tasks(self) -> List[str]:
        """Валидирует распарсенные задания"""
        validation_errors = []
        
        for i, task in enumerate(self.tasks, 1):
            errors = []
            
            # Проверяем обязательные поля
            if not task.get('title'):
                errors.append("отсутствует название")
            if not task.get('question_text'):
                errors.append("отсутствует текст вопроса")
            if task.get('task_type') not in ['single', 'multiple', 'true_false']:
                errors.append(f"неверный тип задания: {task.get('task_type')}")
            if task.get('difficulty') not in ['beginner', 'intermediate', 'advanced']:
                errors.append(f"неверный уровень сложности: {task.get('difficulty')}")
            
            # Проверяем варианты ответов
            answers = task.get('answers', [])
            if task.get('task_type') in ['single', 'multiple'] and not answers:
                errors.append("отсутствуют варианты ответов")
            
            correct_answers = [a for a in answers if a.get('is_correct')]
            if task.get('task_type') == 'single' and len(correct_answers) != 1:
                errors.append(f"для single должен быть 1 правильный ответ, найдено {len(correct_answers)}")
            elif task.get('task_type') == 'multiple' and len(correct_answers) == 0:
                errors.append("для multiple должен быть хотя бы 1 правильный ответ")
            elif task.get('task_type') == 'true_false' and len(correct_answers) != 1:
                errors.append(f"для true_false должен быть 1 правильный ответ, найдено {len(correct_answers)}")
            
            if errors:
                validation_errors.append(f"Задание {i} ({task.get('title', 'без названия')}): {'; '.join(errors)}")
        
        return validation_errors
    
    def get_statistics(self) -> Dict[str, Any]:
        """Возвращает статистику по задачам"""
        if not self.tasks:
            return {}
        
        stats = {
            'total_tasks': len(self.tasks),
            'by_type': {},
            'by_difficulty': {},
            'skills_used': set(),
            'courses_used': set()
        }
        
        for task in self.tasks:
            # По типам
            task_type = task.get('task_type', 'unknown')
            stats['by_type'][task_type] = stats['by_type'].get(task_type, 0) + 1
            
            # По сложности
            difficulty = task.get('difficulty', 'unknown')
            stats['by_difficulty'][difficulty] = stats['by_difficulty'].get(difficulty, 0) + 1
            
            # Навыки и курсы
            for skill in task.get('skills', []):
                stats['skills_used'].add(skill)
            for course in task.get('courses', []):
                stats['courses_used'].add(course)
        
        # Преобразуем sets в lists для JSON
        stats['skills_used'] = list(stats['skills_used'])
        stats['courses_used'] = list(stats['courses_used'])
        
        return stats

def main():
    """Основная функция для использования как скрипт"""
    import sys
    
    if len(sys.argv) < 2:
        print("Использование: python task_parser.py <input_file.txt> [output_file.json]")
        print("\nПример:")
        print("  python task_parser.py tasks.txt")
        print("  python task_parser.py tasks.txt output.json")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not output_file:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"parsed_tasks_{base_name}_{timestamp}.json"
    
    # Если путь не абсолютный, используем temp_dir
    temp_dir = os.path.join(os.path.dirname(__file__), '..', 'temp_dir')
    if not os.path.isabs(input_file):
        input_file = os.path.join(temp_dir, input_file)
    if not os.path.isabs(output_file):
        output_file = os.path.join(temp_dir, output_file)
    
    print("="*50)
    print("ПАРСЕР ЗАДАНИЙ ИЗ ТЕКСТОВОГО ФОРМАТА")
    print("="*50)
    
    parser = TaskParser()
    
    print(f"Читаем файл: {input_file}")
    tasks = parser.parse_text_file(input_file)
    
    if parser.errors:
        print(f"\n⚠️  Ошибки парсинга:")
        for error in parser.errors:
            print(f"  - {error}")
    
    print(f"\n📊 Распарсено заданий: {len(tasks)}")
    
    if tasks:
        # Валидация
        validation_errors = parser.validate_tasks()
        if validation_errors:
            print(f"\n❌ Ошибки валидации:")
            for error in validation_errors:
                print(f"  - {error}")
        else:
            print("✅ Все задания прошли валидацию")
        
        # Статистика
        stats = parser.get_statistics()
        print(f"\n📈 Статистика:")
        print(f"  Всего заданий: {stats['total_tasks']}")
        print(f"  По типам: {stats['by_type']}")
        print(f"  По сложности: {stats['by_difficulty']}")
        print(f"  Навыков: {len(stats['skills_used'])}")
        print(f"  Курсов: {len(stats['courses_used'])}")
        
        # Сохранение
        output_path = parser.save_as_json(output_file)
        print(f"\n💾 Результат сохранен: {output_path}")
        
        if validation_errors:
            print(f"\n⚠️  Внимание: найдены ошибки валидации. Проверьте задания перед импортом!")
        else:
            print(f"\n✅ Файл готов для импорта:")
            print(f"     python import_tasks.py {os.path.basename(output_file)} --dry-run")

if __name__ == '__main__':
    main()
