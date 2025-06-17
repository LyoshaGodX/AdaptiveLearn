/**
 * Основной файл инициализации для страницы редактирования навыков
 * Импортирует функции из модульных файлов и инициализирует компоненты
 */

// Убедитесь, что skill-modal.js загружен до этого файла в HTML, либо импортируйте его здесь, если используете модули
// Например, если используете ES6-модули, раскомментируйте следующую строку:
// import './js/skill-modal.js';

// Когда DOM полностью загружен, инициализируем приложение
document.addEventListener('DOMContentLoaded', function() {
    // Проверяем наличие Vis.js
    if (typeof vis === 'undefined') {
        console.error('Vis.js не загружен!');
        return;
    }
    
    // Загружаем данные графа из контекста Django
    let graphData;
    try {
        const graphElement = document.getElementById('graph-data');
        if (!graphElement) {
            console.error('Элемент graph-data не найден!');
            return;
        }
        
        const rawData = graphElement.textContent;
        graphData = JSON.parse(rawData);
    } catch (e) {
        console.error('Ошибка парсинга данных графа:', e);
        graphData = { nodes: [], edges: [] };
    }
    
    // Загружаем данные курсов
    let coursesData = [];
    try {
        const coursesElement = document.getElementById('courses-data');
        if (coursesElement) {
            coursesData = JSON.parse(coursesElement.textContent);
        }
    } catch (e) {
        console.error('Ошибка парсинга данных курсов:', e);
    }
    
    // Загружаем данные навыков
    let skillsData = [];
    try {
        const skillsElement = document.getElementById('skills-data');
        if (skillsElement) {
            skillsData = JSON.parse(skillsElement.textContent);
        }
    } catch (e) {
        console.error('Ошибка парсинга данных навыков:', e);
    }
    
    // Получаем ID выбранного навыка
    const selectedSkillElement = document.getElementById('selected-skill-id');
    const selectedSkillId = selectedSkillElement ? selectedSkillElement.textContent.trim() : '';
      // Устанавливаем глобальные переменные для других скриптов
    window.allSkills = skillsData;
    window.courses = coursesData;
    window.selectedSkillId = selectedSkillId;
    
    // DEBUG: Логируем данные для отладки
    console.group('=== DEBUG: Данные, переданные из Django ===');
    console.log('Курсы:', coursesData);
    console.log('Все навыки:', skillsData);
    console.log('Выбранный навык ID:', selectedSkillId);
    if (selectedSkillId) {
        const selectedSkill = skillsData.find(s => s.id == selectedSkillId);
        if (selectedSkill) {
            console.log('Выбранный навык:', selectedSkill);
            console.log('Предпосылки выбранного навыка:', selectedSkill.prerequisites);
        }
    }
    console.groupEnd();
    
    // Проверяем контейнер графа
    const container = document.getElementById('skill-network');
    if (!container) {
        console.error('Контейнер skill-network не найден!');
        return;
    }
    
    // Инициализация графа навыков, если есть данные
    if (graphData && graphData.nodes && graphData.nodes.length > 0) {
        // Вызываем функцию из network.js
        if (typeof initializeSkillNetwork === 'function') {
            initializeSkillNetwork(graphData);
        } else {
            console.error('Функция initializeSkillNetwork не найдена!');
        }
    }
    
    // Инициализация обработчиков событий для модальных окон
    if (typeof initializeModalHandlers === 'function') {
        initializeModalHandlers();
    } else {
        // Попробуйте явно вызвать функцию из window, если она не определена в области видимости
        if (window.initializeModalHandlers) {
            window.initializeModalHandlers();
        }
    }
    
    // Инициализация обработчиков событий для удаления навыков
    if (typeof initializeDeleteHandlers === 'function') {
        initializeDeleteHandlers();
    }
});
