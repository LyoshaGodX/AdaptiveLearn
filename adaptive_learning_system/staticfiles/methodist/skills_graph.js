/**
 * Скрипт для отрисовки и управления графом навыков
 * Использует библиотеку Vis.js для визуализации сетевого графа
 */

document.addEventListener('DOMContentLoaded', function() {
    // Глобальные переменные для управления состоянием графа    
    let isUserInteracting = false; // Флаг взаимодействия пользователя с графом
    let autoFocusEnabled = true;  // Флаг разрешения автофокусировки
    
    // Получаем данные из контекста Django
    let graphData;
    try {
        const rawData = document.getElementById('graph-data').textContent;
        
        if (!rawData || rawData.trim() === '') {
            graphData = { nodes: [], edges: [] };
        } else {
            graphData = JSON.parse(rawData);
            
            // Проверяем структуру данных
            if (!graphData.nodes || !Array.isArray(graphData.nodes) || 
                !graphData.edges || !Array.isArray(graphData.edges)) {
                graphData = { nodes: [], edges: [] };
            }
        }
    } catch (e) {
        alert('Произошла ошибка при загрузке данных графа. Пожалуйста, обновите страницу.');
        return;
    }
    
    const selectedSkillId = document.getElementById('selected-skill-id').textContent;
    
    // Создаем данные для Vis.js
    const nodesArray = [];
    const edgesArray = [];
    
    // Преобразуем данные из формата Cytoscape в формат Vis.js
    graphData.nodes.forEach(function(node) {
        const isBase = node.data.is_base;
        nodesArray.push({
            id: node.data.id,
            label: node.data.name,
            title: node.data.name,
            skillId: node.data.skill_id,
            isBase: isBase,
            shape: 'box', // Все узлы - прямоугольники
            color: {
                background: isBase ? '#4285f4' : '#34a853',
                border: isBase ? '#2054a5' : '#1a682f',
                highlight: {
                    background: '#ff9800',
                    border: '#e65100'
                }
            },
            font: {
                color: 'white',
                size: 14,
                face: 'Arial',
                strokeWidth: 1,
                strokeColor: '#333'
            },
            borderWidth: 2,
            margin: 10, // Отступ внутри прямоугольника
            shapeProperties: {
                borderRadius: 5 // Закругление углов прямоугольника
            },
            shadow: true,
            widthConstraint: {
                minimum: 80, // Минимальная ширина узла
                maximum: 200 // Максимальная ширина узла
            }
        });
    });
    
    graphData.edges.forEach(function(edge) {
        edgesArray.push({
            from: edge.data.source,
            to: edge.data.target,
            arrows: 'to',
            color: {
                color: '#666',
                highlight: '#f5b041',
                hover: '#f39c12'
            },
            width: 2,
            smooth: {
                type: 'cubicBezier',
                roundness: 0.3
            }
        });
    });
    
    // Создаем наборы данных Vis.js
    const nodes = new vis.DataSet(nodesArray);
    const edges = new vis.DataSet(edgesArray);
    
    // Собираем данные для сети
    const data = {
        nodes: nodes,
        edges: edges
    };
    
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
            width: 1.5,
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
        }, 
        interaction: {
            hover: true,
            navigationButtons: true,
            keyboard: {
                enabled: true,
                bindToWindow: false
            },
            multiselect: true,
            tooltipDelay: 200,
            hideEdgesOnDrag: true,
            hideEdgesOnZoom: true,
            dragNodes: true,
            dragView: true,
            zoomView: true
        }
    };
    
    // Инициализация сети Vis.js
    const container = document.getElementById('network-container');
    const network = new vis.Network(container, data, options);
    
    // После стабилизации отключаем physics, чтобы граф не "плавал"
    network.once('stabilizationIterationsDone', function() {
        network.setOptions({ physics: { enabled: false } });
        
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
    });
    
    // Создаем обертки для методов фокусировки, чтобы контролировать их вызов
    const originalFit = network.fit;
    const originalFocus = network.focus;
    
    // Заменяем методы фокусировки своими, чтобы контролировать их вызов
    network.fit = function(options) {
        if (autoFocusEnabled && !isUserInteracting) {
            originalFit.call(this, options);
        }
    };
    
    network.focus = function(nodeId, options) {
        if (autoFocusEnabled && !isUserInteracting) {
            originalFocus.call(this, nodeId, options);
        }
    };
    
    // Индексы для быстрого поиска связанных навыков
    const dependentSkillsIndex = {};
    const prerequisiteSkillsIndex = {};
    
    // Заполняем индексы
    edges.forEach(edge => {
        const fromId = edge.from;
        const toId = edge.to;
        
        // Добавляем в индекс зависимых навыков
        if (!prerequisiteSkillsIndex[fromId]) {
            prerequisiteSkillsIndex[fromId] = [];
        }
        prerequisiteSkillsIndex[fromId].push(toId);
        
        // Добавляем в индекс требуемых навыков
        if (!dependentSkillsIndex[toId]) {
            dependentSkillsIndex[toId] = [];
        }
        dependentSkillsIndex[toId].push(fromId);
    });
    
    // Функция выделения навыка и его прямых зависимостей
    function highlightDependencies(nodeId) {
        // Проверяем существование узла
        const node = nodes.get(nodeId);
        if (!node) return false;
        
        // Временно включаем автофокусировку для этого действия
        const prevAutoFocus = autoFocusEnabled;
        const prevUserInteracting = isUserInteracting;
        
        autoFocusEnabled = true;
        isUserInteracting = false;
        
        network.unselectAll();
        
        // Выделяем центральный узел и его непосредственные связи
        const connectedNodes = new Set([nodeId]);
        const connectedEdges = new Set();
        
        // Получаем все связанные ребра
        const connectedEdgesIds = network.getConnectedEdges(nodeId);
        
        // Для каждого ребра проверяем, связан ли он с центральным узлом
        connectedEdgesIds.forEach(edgeId => {
            const edge = edges.get(edgeId);
            if (edge) {
                // Если ребро связано с центральным узлом, добавляем его и связанный узел
                if (edge.from === nodeId || edge.to === nodeId) {
                    connectedEdges.add(edgeId);
                    // Добавляем связанный узел (источник или цель)
                    const connectedNode = edge.from === nodeId ? edge.to : edge.from;
                    connectedNodes.add(connectedNode);
                }
            }
        });
        
        // Выделяем узлы и ребра
        network.selectNodes(Array.from(connectedNodes));
        network.selectEdges(Array.from(connectedEdges));
        
        // Выполняем однократную фокусировку на связанных узлах
        if (connectedNodes.size > 1) {
            // Если есть связанные узлы, показываем их все
            originalFit.call(network, {
                nodes: Array.from(connectedNodes),
                animation: {
                    duration: 600,
                    easingFunction: 'easeOutQuad'
                }
            });
        } else {
            // Если нет связанных узлов, фокусируемся только на выбранном узле
            originalFocus.call(network, nodeId, {
                scale: 1.2,
                offset: { x: 0, y: 0 },
                animation: {
                    duration: 600,
                    easingFunction: 'easeOutQuad'
                }
            });
        }
        
        // Восстанавливаем предыдущие настройки автофокусировки через задержку
        setTimeout(() => {
            autoFocusEnabled = prevAutoFocus;
            isUserInteracting = prevUserInteracting;
        }, 650);
        
        // Обновляем информационную панель
        updateSkillInfoPanel(nodeId);
        
        return true; // Успешное выделение
    }
    
    // Функция обновления информационной панели
    function updateSkillInfoPanel(nodeId) {
        const node = nodes.get(nodeId);
        const skillInfoPanel = document.getElementById('skill-info-panel');
        const skillInfoTitle = document.getElementById('skill-info-title');
        const skillInfoType = document.getElementById('skill-info-type');
        const skillInfoDeps = document.getElementById('skill-info-deps');
        const skillInfoDependent = document.getElementById('skill-info-dependent');
        
        if (node) {
            skillInfoTitle.textContent = node.label;
            skillInfoTitle.className = node.isBase ? 'font-bold text-lg mb-2 skill-label-base' : 'font-bold text-lg mb-2 skill-label-regular';
            
            skillInfoType.textContent = node.isBase ? 'Базовый навык' : 'Прикладной навык';
            
            // Получаем навыки, от которых зависит текущий (предпосылки)
            const prerequisites = dependentSkillsIndex[nodeId] || [];
            
            // Формируем список зависимостей с кликабельными ссылками
            if (prerequisites.length > 0) {
                skillInfoDeps.innerHTML = ''; // Очищаем содержимое
                prerequisites.forEach((id, index) => {
                    const depNode = nodes.get(id);
                    if (depNode) {
                        const depLink = document.createElement('a');
                        depLink.href = 'javascript:void(0)';
                        depLink.className = 'text-blue-600 hover:underline';
                        depLink.textContent = depNode.label;
                        depLink.onclick = function() {
                            highlightDependencies(id);
                        };
                        
                        skillInfoDeps.appendChild(depLink);
                        
                        if (index < prerequisites.length - 1) {
                            skillInfoDeps.appendChild(document.createTextNode(', '));
                        }
                    }
                });
            } else {
                skillInfoDeps.textContent = 'Нет зависимостей';
            }
            
            // Получаем навыки, зависящие от текущего
            const dependents = prerequisiteSkillsIndex[nodeId] || [];
            
            // Формируем список зависимых навыков с кликабельными ссылками
            if (dependents.length > 0) {
                skillInfoDependent.innerHTML = ''; // Очищаем содержимое
                dependents.forEach((id, index) => {
                    const depNode = nodes.get(id);
                    if (depNode) {
                        const depLink = document.createElement('a');
                        depLink.href = 'javascript:void(0)';
                        depLink.className = 'text-blue-600 hover:underline';
                        depLink.textContent = depNode.label;
                        depLink.onclick = function() {
                            highlightDependencies(id);
                        };
                        
                        skillInfoDependent.appendChild(depLink);
                        
                        if (index < dependents.length - 1) {
                            skillInfoDependent.appendChild(document.createTextNode(', '));
                        }
                    }
                });
            } else {
                skillInfoDependent.textContent = 'Нет зависимых навыков';
            }
            
            skillInfoPanel.style.display = 'block';
        } else {
            skillInfoPanel.style.display = 'none';
        }
    }
    
    // Обработчики событий взаимодействия пользователя с графом
    network.on('dragStart', function() {
        isUserInteracting = true;
    });
    
    network.on('zoom', function() {
        isUserInteracting = true;
    });
    
    // Обработчик щелчка по узлу
    network.on('click', function(params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const node = nodes.get(nodeId);
            
            // Разрешаем автофокусировку для клика по узлу
            isUserInteracting = false;
            autoFocusEnabled = true;
            
            if (node) {
                // Получаем ID навыка из ID узла
                const skillId = node.skillId || nodeId.replace('skill_', '');
                
                // Проверяем, был ли повторный клик по тому же узлу
                const currentSelected = document.getElementById('selected-skill-id').textContent;
                const isReclick = currentSelected === skillId.toString();
                
                // Выделяем зависимости выбранного узла
                highlightDependencies(nodeId);
                
                // Если это не повторный клик, обновляем URL
                if (!isReclick) {
                    document.getElementById('selected-skill-id').textContent = skillId;
                    updateUrlWithSkill(skillId);
                }
            }
            
            // Через небольшую задержку возвращаем контроль пользователю
            setTimeout(() => {
                isUserInteracting = true;
            }, 650); 
        } else {
            network.unselectAll();
            document.getElementById('skill-info-panel').style.display = 'none';
        }
    });
    
    // Обработчики курсора при наведении
    network.on('hoverNode', function() {
        document.body.style.cursor = 'pointer';
    });
    
    network.on('blurNode', function() {
        document.body.style.cursor = 'default';
    });
    
    // Обновленная функция для перехода к выбранному навыку
    function updateUrlWithSkill(skillId) {
        // Создаем URL для прямого перехода
        const url = new URL(window.location.href);
        
        // Устанавливаем параметр skill
        url.searchParams.set('skill', skillId);
        
        // Сохраняем параметр course, если он есть
        const courseSelect = document.getElementById('course');
        if (courseSelect && courseSelect.value) {
            url.searchParams.set('course', courseSelect.value);
        } else {
            url.searchParams.delete('course');
        }
        
        // Перенаправляем на новый URL
        window.location.href = url.toString();
    }
    
    // УДАЛИТЬ БЛОК, КОТОРЫЙ ДОБАВЛЯЕТ ОПЦИЮ "НЕ ВЫБРАНО" В СЕЛЕКТОР
    
    // Получаем текущий выбранный курс и проверяем выбранный навык
    const currentCourse = document.getElementById('course').value;
    
    if (selectedSkillId && nodesArray.length > 0) {
        const nodeId = 'skill_' + selectedSkillId;
        // Проверяем наличие узла
        const nodeExists = nodesArray.some(node => node.id === nodeId);
        
        // Если выбран "все курсы" и выбран навык, но узел не найден — отображаем полный граф
        if (!nodeExists && (!currentCourse || currentCourse === '' || currentCourse === 'None')) {
            // Принудительно сбрасываем фильтр по навыку (отображаем полный граф)
            window.location.href = window.location.pathname;
            return;
        }
        
        // Если узел не существует и есть фильтр по курсу, предлагаем сбросить фильтр
        if (!nodeExists && window.location.search.includes('course=') && window.location.search.includes('skill=')) {
            // Создаем сообщение для пользователя
            const messageContainer = document.createElement('div');
            messageContainer.className = 'fixed inset-0 flex items-center justify-center z-50';
            messageContainer.innerHTML = `
                <div class="bg-white rounded-lg shadow-lg p-6 max-w-md mx-4">
                    <h3 class="font-bold text-lg mb-3">Навык не найден в выбранном курсе</h3>
                    <p class="mb-4">Выбранный навык не относится к текущему курсу. Хотите сбросить фильтр по курсу?</p>
                    <div class="flex justify-end gap-3">
                        <button id="cancel-course-reset" class="px-3 py-1 bg-gray-200 hover:bg-gray-300 rounded">Отмена</button>
                        <button id="confirm-course-reset" class="px-3 py-1 bg-blue-600 text-white hover:bg-blue-700 rounded">Сбросить фильтр</button>
                    </div>
                </div>
                <div class="fixed inset-0 bg-black bg-opacity-50 -z-10"></div>
            `;
            
            document.body.appendChild(messageContainer);
            
            // Обработчики для кнопок
            document.getElementById('cancel-course-reset').addEventListener('click', function() {
                document.body.removeChild(messageContainer);
            });
            
            document.getElementById('confirm-course-reset').addEventListener('click', function() {                
                const url = new URL(window.location.href);
                url.searchParams.delete('course');
                
                window.location.href = url.toString();
            });
            
            return;
        }
        
        // Даем время на инициализацию сети и затем выделяем навык
        setTimeout(function() {
            const node = nodes.get(nodeId);
            if (node) {
                // Временно отключаем блокировку автофокусировки
                isUserInteracting = false;
                autoFocusEnabled = true;
                
                // Выделяем зависимости
                highlightDependencies(nodeId);
                
                // Через задержку восстанавливаем контроль пользователя
                setTimeout(() => {
                    isUserInteracting = false;
                }, 700);
            }
        }, 800);
    }
    
    // Обработчик кнопки экспорта
    document.getElementById('export-png-btn').addEventListener('click', function() {
        // Временно включаем автофокус для этой операции
        const prevAutoFocus = autoFocusEnabled;
        const prevUserInteracting = isUserInteracting;
        
        autoFocusEnabled = true;
        isUserInteracting = false;
        
        // Используем оригинальный метод для подгонки графа перед экспортом
        originalFit.call(network, {animation: false});
        
        const canvas = container.querySelector('canvas');
        
        const courseName = document.getElementById('course').options[document.getElementById('course').selectedIndex].text;
        const fileName = courseName === "Все курсы (полный граф)" ? "skills-graph-full" : "skills-graph-" + courseName.toLowerCase().replace(/\s+/g, '-');
        
        try {
            const link = document.createElement('a');
            link.href = canvas.toDataURL('image/png');
            link.download = fileName + '.png';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } catch (error) {
            alert("Произошла ошибка при экспорте графа. Убедитесь, что ваш браузер поддерживает эту функцию.");
        }
        
        // Восстанавливаем предыдущие настройки
        setTimeout(() => {
            autoFocusEnabled = prevAutoFocus;
            isUserInteracting = prevUserInteracting;
        }, 100);
    });
    
    // Проверка пустого графа
    if (nodesArray.length === 0) {
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
        
        const container = document.getElementById('network-container');
        if (container) {
            const noDataMessage = document.createElement('div');
            noDataMessage.innerHTML = '<div class="text-center p-8 text-gray-500"><i class="fas fa-exclamation-circle text-3xl mb-2"></i><p>Нет данных для отображения графа.</p></div>';
            container.appendChild(noDataMessage);
        }
    }
    
    // Обработка состояния селектора курса при просмотре конкретного навыка
    if (window.location.search.match(/([?&])skill=\d+/)) {
        const courseSelect = document.getElementById('course');
        if (courseSelect) {
            // Получаем параметр из URL
            const url = new URL(window.location.href);
            const skillId = url.searchParams.get('skill');
            const nodeId = skillId ? 'skill_' + skillId : '';
            const node = nodeId ? nodes.get(nodeId) : null;
            
            if (node) {
                // Добавляем класс для стилизации селектора
                courseSelect.classList.add('active-skill-filter');
                
                // Удаляем все специальные опции перед добавлением новой
                Array.from(courseSelect.querySelectorAll('option[value="__no_selection__"], option[value="__skill_view__"]')).forEach(opt => {
                    courseSelect.removeChild(opt);
                });
                
                // Создаем опцию для просмотра навыка
                const viewOption = document.createElement('option');
                viewOption.value = '__skill_view__';
                viewOption.textContent = `Просмотр: ${node.label}`;
                viewOption.title = 'Выберите другую опцию, чтобы вернуться к полному графу';
                
                // Вставляем опцию в начало списка
                courseSelect.insertBefore(viewOption, courseSelect.firstChild);
                
                // Устанавливаем опцию просмотра навыка как выбранную
                viewOption.selected = true;
                
                // Снимаем выделение с других опций
                Array.from(courseSelect.options).forEach(opt => {
                    if (opt.value !== '__skill_view__') {
                        opt.selected = false;
                    }
                });
            }
        }
    }
    
    // Добавляем обработку ошибок для загрузки графа и кэширования
    window.addEventListener('error', function(event) {
        // Проверяем, связана ли ошибка с vis.js
        if (event.message && (event.message.includes('vis') || 
                             event.message.includes('network') || 
                             event.message.includes('canvas'))) {
            console.error('Ошибка в графе навыков:', event);
            
            // Скрываем индикатор загрузки
            const loadingIndicator = document.getElementById('loading-indicator');
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }
            
            // Показываем сообщение об ошибке
            const container = document.getElementById('network-container');
            if (container) {
                container.innerHTML = '<div class="p-4 text-center text-red-600"><i class="fas fa-exclamation-triangle text-3xl mb-2"></i><p>Произошла ошибка при отображении графа. Попробуйте обновить страницу.</p></div>';
            }
            
            // Предотвращаем всплытие ошибки
            event.preventDefault();
        }
    });
});
