/**
 * Основной файл инициализации для страницы редактирования навыков
 * Импортирует функции из модульных файлов и инициализирует компоненты
 */

// Убедитесь, что skill-modal.js загружен до этого файла в HTML, либо импортируйте его здесь, если используете модули
// Например, если используете ES6-модули, раскомментируйте следующую строку:
// import './js/skill-modal.js';

// Когда DOM полностью загружен, инициализируем приложение
document.addEventListener('DOMContentLoaded', function() {
    // Загружаем данные графа из контекста Django
    let graphData;
    try {
        const rawData = document.getElementById('graph-data').textContent;
        graphData = JSON.parse(rawData);
    } catch (e) {
        graphData = { nodes: [], edges: [] };
    }
    
    // Получаем ID выбранного навыка
    const selectedSkillId = document.getElementById('selected-skill-id').textContent;
    
    // Инициализация графа навыков, если есть данные
    if (graphData && graphData.nodes && graphData.nodes.length > 0) {
        // Вызываем функцию из network.js
        if (typeof initializeSkillNetwork === 'function') {
            initializeSkillNetwork(graphData);
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
