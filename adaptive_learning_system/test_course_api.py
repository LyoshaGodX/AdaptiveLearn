#!/usr/bin/env python
"""
Скрипт для тестирования API эндпоинтов управления курсами
"""

import requests
import json
from requests.auth import HTTPBasicAuth

# Базовые настройки
BASE_URL = 'http://127.0.0.1:8000'
API_BASE = f'{BASE_URL}/methodist/api'

# Настройки аутентификации (замените на реальные данные)
USERNAME = 'admin'  # Замените на имя пользователя методиста
PASSWORD = 'admin'  # Замените на пароль

class CourseAPITester:
    def __init__(self):
        self.session = requests.Session()
        # Здесь можно добавить аутентификацию если нужно
        
    def test_skills_api(self):
        """Тестирование API получения навыков"""
        print("=== Тестирование API навыков ===")
        try:
            response = self.session.get(f'{API_BASE}/skills/')
            if response.status_code == 200:
                skills = response.json()
                print(f"✓ Получено навыков: {len(skills)}")
                if skills:
                    print(f"Пример навыка: {skills[0]['name']}")
            else:
                print(f"✗ Ошибка: {response.status_code}")
        except Exception as e:
            print(f"✗ Исключение: {e}")
    
    def test_tasks_api(self):
        """Тестирование API получения заданий"""
        print("\n=== Тестирование API заданий ===")
        try:
            response = self.session.get(f'{API_BASE}/tasks/')
            if response.status_code == 200:
                tasks = response.json()
                print(f"✓ Получено заданий: {len(tasks)}")
                if tasks:
                    print(f"Пример задания: {tasks[0]['title']}")
            else:
                print(f"✗ Ошибка: {response.status_code}")
        except Exception as e:
            print(f"✗ Исключение: {e}")
    
    def test_course_data_api(self, course_id):
        """Тестирование API получения данных курса"""
        print(f"\n=== Тестирование API курса {course_id} ===")
        try:
            response = self.session.get(f'{API_BASE}/course/{course_id}/')
            if response.status_code == 200:
                course = response.json()
                print(f"✓ Курс: {course['name']}")
                print(f"  Навыков: {len(course['skills'])}")
                print(f"  Заданий: {len(course['tasks'])}")
            elif response.status_code == 404:
                print(f"✗ Курс {course_id} не найден")
            else:
                print(f"✗ Ошибка: {response.status_code}")
        except Exception as e:
            print(f"✗ Исключение: {e}")
    
    def test_all(self):
        """Запуск всех тестов"""
        print("Начинаем тестирование API эндпоинтов...")
        
        self.test_skills_api()
        self.test_tasks_api()
        
        # Тестируем с примерными ID курсов
        test_course_ids = ['C1', 'C2', 'C3', 'C4', 'C5']
        for course_id in test_course_ids:
            self.test_course_data_api(course_id)
        
        print("\n=== Тестирование завершено ===")

if __name__ == '__main__':
    tester = CourseAPITester()
    tester.test_all()
