#!/usr/bin/env python
import csv
import os

# Получаем путь к temp_dir
temp_dir = os.path.join(os.path.dirname(__file__), '..', 'temp_dir')
csv_file = os.path.join(temp_dir, 'tasks_fixed.csv')

print(f"Путь к файлу: {csv_file}")
print(f"Файл существует: {os.path.exists(csv_file)}")

try:
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        print(f"Заголовки: {reader.fieldnames}")
        
        data = list(reader)
        print(f"Количество строк данных: {len(data)}")
        
        if data:
            print(f"Первая строка: {data[0]}")
            print(f"Поля первой строки: {list(data[0].keys())}")
            
except Exception as e:
    print(f"Ошибка: {e}")
