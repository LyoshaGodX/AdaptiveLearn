#!/usr/bin/env python3
"""
Тестовый скрипт для проверки градиентного окрашивания процентов освоения навыков
"""

def get_mastery_css_class(percentage):
    """
    Возвращает CSS класс для процента освоения навыка
    """
    if percentage >= 100:
        return 'skill-mastery-100'
    elif percentage >= 90:
        return 'skill-mastery-90'
    elif percentage >= 80:
        return 'skill-mastery-80'
    elif percentage >= 70:
        return 'skill-mastery-70'
    elif percentage >= 60:
        return 'skill-mastery-60'
    elif percentage >= 50:
        return 'skill-mastery-50'
    elif percentage >= 40:
        return 'skill-mastery-40'
    elif percentage >= 30:
        return 'skill-mastery-30'
    elif percentage >= 20:
        return 'skill-mastery-20'
    elif percentage >= 10:
        return 'skill-mastery-10'
    else:
        return 'skill-mastery-0'

def test_gradient_classes():
    """Тестируем функцию определения CSS классов"""
    
    print("=== Тест градиентного окрашивания процентов освоения ===\n")
    
    test_values = [0, 5, 15, 25, 35, 45, 55, 65, 75, 85, 95, 100]
    
    for percentage in test_values:
        css_class = get_mastery_css_class(percentage)
        print(f"{percentage:3d}% → {css_class}")
    
    print("\n=== Цвета по классам ===")
    color_map = {
        'skill-mastery-0': '#dc3545 (красный)',
        'skill-mastery-10': '#e74c3c (ярко-красный)',
        'skill-mastery-20': '#f39c12 (оранжевый)',
        'skill-mastery-30': '#f1c40f (желтый)',
        'skill-mastery-40': '#f39c12 (оранжево-желтый)',
        'skill-mastery-50': '#e67e22 (темно-оранжевый)',
        'skill-mastery-60': '#27ae60 (зеленовато-желтый)',
        'skill-mastery-70': '#2ecc71 (светло-зеленый)',
        'skill-mastery-80': '#27ae60 (зеленый)',
        'skill-mastery-90': '#16a085 (темно-зеленый)',
        'skill-mastery-100': '#0d7377 (темно-морской)',
    }
    
    for css_class, color in color_map.items():
        print(f"{css_class} → {color}")
    
    print("\n=== Тест завершен ===")

if __name__ == "__main__":
    test_gradient_classes()
