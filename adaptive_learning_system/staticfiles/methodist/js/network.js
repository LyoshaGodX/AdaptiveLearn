/**
 * Модуль для визуализации графа навыков при помощи Vis.js
 */

/**
 * Инициализирует интерактивный граф навыков
 * @param {Object} graphData - Данные графа в формате Cytoscape
 */
function initializeSkillNetwork(graphData) {
    // Создаем данные для Vis.js
    const nodesArray = [];
    const edgesArray = [];
    
    // Получаем выбранный навык
    const selectedSkillElement = document.getElementById('selected-skill-id');
    const selectedSkillId = selectedSkillElement ? parseInt(selectedSkillElement.textContent.trim()) : null;
    
    // Преобразуем данные из формата Cytoscape в формат Vis.js
    graphData.nodes.forEach(function(node, idx) {
        const isBase = node.data.is_base;
        const isSelected = node.data.skill_id === selectedSkillId;
        
        nodesArray.push({
            id: node.data.id,
            label: node.data.name,
            title: node.data.name,
            skillId: node.data.skill_id,
            isBase: isBase,
            shape: 'box',
            color: {
                background: isSelected ? '#ff9800' : (isBase ? '#4285f4' : '#34a853'),
                border: isSelected ? '#e65100' : (isBase ? '#2054a5' : '#1a682f'),
                highlight: {
                    background: '#ff9800',
                    border: '#e65100'
                }
            },
            font: {
                color: 'white',
                size: isSelected ? 16 : 14,
                face: 'Arial',
                strokeWidth: 1,
                strokeColor: '#333'
            },
            borderWidth: isSelected ? 3 : 2,
            margin: 10,
            shapeProperties: {
                borderRadius: 5
            },
            widthConstraint: {
                minimum: 80,
                maximum: 200
            },
            shadow: true
        });
    });
    
    graphData.edges.forEach(function(edge, idx) {
        edgesArray.push({
            id: edge.data.id,
            from: edge.data.source,
            to: edge.data.target,
            arrows: 'to',
            width: 2,
            color: {
                color: '#666',
                highlight: '#f57c00',
                hover: '#f39c12'
            },
            smooth: {
                type: 'dynamic',
                roundness: 0.5
            }
        });
    });
    
    // Создаем наборы данных Vis.js
    const nodes = new vis.DataSet(nodesArray);
    const edges = new vis.DataSet(edgesArray);
    
    // Настройки графа
    const options = {
        nodes: {
            shape: 'box',
            margin: 10,
            borderWidth: 2,
            shadow: true,
            shapeProperties: {
                borderRadius: 5
            },
            font: {
                color: 'white',
                size: 14,
                face: 'Arial'
            },
            widthConstraint: {
                minimum: 80,
                maximum: 200
            }
        },
        edges: {
            width: 2,
            selectionWidth: 3,
            hoverWidth: 2,
            shadow: true,
            arrows: {
                to: {
                    enabled: true,
                    scaleFactor: 0.8, 
                    type: 'arrow'
                }
            },
            smooth: {
                enabled: true,
                type: 'dynamic'
            },
            color: {
                color: '#666',
                highlight: '#f5b041',
                hover: '#f39c12'
            }
        },
        layout: {
            improvedLayout: true
        },
        physics: {
            enabled: true,
            solver: 'forceAtlas2Based',
            barnesHut: {
                gravitationalConstant: -2000,
                centralGravity: 0.3,
                springLength: 150,
                springConstant: 0.04,
                damping: 0.09,
                avoidOverlap: 1
            },
            forceAtlas2Based: {
                gravitationalConstant: -50,
                centralGravity: 0.01,
                springLength: 150,
                springConstant: 0.08,
                damping: 0.4,
                avoidOverlap: 1
            },
            stabilization: {
                enabled: true,
                iterations: 200,
                updateInterval: 25
            }
        },        interaction: {
            hover: true,
            navigationButtons: false,
            keyboard: {
                enabled: true,
                bindToWindow: false
            },
            multiselect: false,
            tooltipDelay: 200,
            hideEdgesOnDrag: true,
            hideEdgesOnZoom: true,
            dragNodes: true,
            dragView: true,
            zoomView: true        }
    };
    
    // Получаем контейнер для графа
    const container = document.getElementById('skill-network');
    
    if (container) {
        // Создаем сеть
        const network = new vis.Network(container, { nodes, edges }, options);

        // После стабилизации отключаем physics, чтобы граф не "плавал"
        network.once('stabilizationIterationsDone', function() {
            network.setOptions({ physics: { enabled: false } });
            
            // Скрываем индикатор загрузки
            const loadingIndicator = document.getElementById('loading-indicator');            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }
        });

        // Обработчики курсора при наведении
        network.on('hoverNode', function() {
            document.body.style.cursor = 'pointer';
        });
        
        network.on('blurNode', function() {
            document.body.style.cursor = 'default';
        });
    } else {
        console.error('Контейнер skill-network не найден! Граф не может быть создан.');
    }
}

// Экспортируем функцию в глобальную область видимости
window.initializeSkillNetwork = initializeSkillNetwork;
