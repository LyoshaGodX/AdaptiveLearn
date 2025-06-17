/**
 * Модуль для добавления предпосылок к навыкам
 */

document.addEventListener('DOMContentLoaded', function() {
    const addPrereqBtn = document.getElementById('add-prerequisite-btn');
    const prereqSearch = document.getElementById('prereq-search');
    const prereqList = document.getElementById('prereq-list');
    const prereqEmptyMessage = document.getElementById('prereq-empty-message');
    const modal = document.getElementById('add-prereq-modal');
    
    if (addPrereqBtn) {
        addPrereqBtn.addEventListener('click', function() {
            // Проверяем, что данные загружены
            if (!window.allSkills || !window.selectedSkillId) {
                alert('Данные навыков не загружены');
                return;
            }
            
            // Очищаем поиск при открытии
            if (prereqSearch) {
                prereqSearch.value = '';
                updatePrereqList('');
            }
            
            // Открываем модальное окно
            if (modal) {
                modal.classList.add('show');
                document.body.style.overflow = 'hidden';
            }
        });
    }

    // Закрытие модального окна
    const closeBtn = document.getElementById('add-prereq-close');
    const cancelBtn = document.getElementById('add-prereq-cancel');
    
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            closeModal();
        });
    }
    
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function() {
            closeModal();
        });
    }
    
    // Закрытие по клику вне модального окна
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeModal();
            }
        });
    }

    function closeModal() {
        if (modal) {
            modal.classList.remove('show');
            document.body.style.overflow = '';
        }
    }

    // Обработчик поиска
    if (prereqSearch) {
        prereqSearch.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            updatePrereqList(searchTerm);
        });
    }

    function updatePrereqList(searchTerm) {
        if (!window.allSkills || !window.selectedSkillId) {
            return;
        }
        
        const selectedSkillId = parseInt(window.selectedSkillId);
        const selectedSkill = window.allSkills.find(s => s.id === selectedSkillId);
        
        if (!selectedSkill) {
            return;
        }        // Собираем запрещенные ID для предотвращения циклических зависимостей
        const forbiddenIds = new Set();
        const forbiddenReasons = {};
        
        // 1. Сам выбранный навык (навык не может быть предпосылкой для себя)
        forbiddenIds.add(selectedSkillId);
        forbiddenReasons[selectedSkillId] = 'Сам выбранный навык';
        
        // 2. Уже добавленные предпосылки (избегаем дублирования)
        if (selectedSkill.prerequisites) {
            selectedSkill.prerequisites.forEach(prereqId => {
                const id = parseInt(prereqId);
                forbiddenIds.add(id);
                forbiddenReasons[id] = 'Уже является предпосылкой';
            });
        }
        
        // Функция для сбора всех предпосылок навыка (вверх по графу)
        function collectAllPrerequisites(skillId, visited = new Set()) {
            if (visited.has(skillId)) return;
            visited.add(skillId);
            
            const skill = window.allSkills.find(s => s.id === skillId);
            if (skill && skill.prerequisites) {
                skill.prerequisites.forEach(prereqId => {
                    const id = parseInt(prereqId);
                    collectAllPrerequisites(id, visited);
                });
            }
        }
        
        // Функция для сбора всех зависимых навыков (вниз по графу)
        function collectAllDependents(skillId, visited = new Set()) {
            if (visited.has(skillId)) return;
            visited.add(skillId);
            
            window.allSkills.forEach(skill => {
                if (skill.prerequisites && skill.prerequisites.includes(skillId)) {
                    collectAllDependents(skill.id, visited);
                }
            });
        }
        
        // Собираем все предпосылки выбранного навыка (вверх по графу)
        // Эти навыки нельзя добавлять как предпосылки, т.к. это создаст цикл
        const allPrereqs = new Set();
        collectAllPrerequisites(selectedSkillId, allPrereqs);
        allPrereqs.forEach(id => {
            if (id !== selectedSkillId) { // исключаем сам навык, он уже добавлен
                forbiddenIds.add(id);
                forbiddenReasons[id] = 'Входит в цепочку предпосылок (создаст цикл)';
            }
        });
          // Собираем все зависимые навыки (вниз по графу)
        // Эти навыки нельзя добавлять как предпосылки, т.к. это создаст цикл
        const allDependents = new Set();
        collectAllDependents(selectedSkillId, allDependents);
        allDependents.forEach(id => {
            if (id !== selectedSkillId) { // исключаем сам навык, он уже добавлен
                forbiddenIds.add(id);
                forbiddenReasons[id] = 'Входит в цепочку зависимых (создаст цикл)';
            }
        });
          // Логирование исключенных навыков для отладки
        console.group('=== DEBUG: Анализ зависимостей ===');
        console.log('Выбранный навык:', selectedSkill);
        console.log('Все предпосылки выбранного навыка (вверх по графу):', Array.from(allPrereqs));
        console.log('Все зависимые навыки (вниз по графу):', Array.from(allDependents));
        console.log('=== Исключенные навыки для добавления в предпосылки ===');
        window.allSkills.forEach(skill => {
            if (forbiddenIds.has(skill.id)) {
                console.log(`ID: ${skill.id}, Название: ${skill.name}, Причина: ${forbiddenReasons[skill.id]}`);
            }
        });
        console.groupEnd();
        
        // Фильтруем навыки
        const filteredSkills = window.allSkills.filter(skill => {
            // Исключаем запрещенные навыки
            if (forbiddenIds.has(skill.id)) return false;
            
            // Фильтруем по поисковому запросу
            if (searchTerm && !skill.name.toLowerCase().includes(searchTerm)) return false;
            
            return true;
        });
        
        // Сортируем по названию
        filteredSkills.sort((a, b) => a.name.localeCompare(b.name));
          // Обновляем UI
        if (filteredSkills.length === 0) {
            if (prereqList) prereqList.innerHTML = '';
            if (prereqEmptyMessage) {
                if (searchTerm) {
                    prereqEmptyMessage.innerHTML = `
                        <div class="text-center py-3">
                            <i class="fas fa-search fa-2x text-muted mb-2"></i>
                            <p class="text-muted">По запросу "<strong>${searchTerm}</strong>" навыки не найдены</p>
                            <small class="text-muted">Попробуйте изменить поисковый запрос</small>
                        </div>
                    `;
                } else {
                    const totalSkills = window.allSkills.length;
                    const forbiddenCount = forbiddenIds.size;
                    const availableCount = totalSkills - forbiddenCount;
                    
                    prereqEmptyMessage.innerHTML = `
                        <div class="text-center py-3">
                            <i class="fas fa-info-circle fa-2x text-muted mb-2"></i>
                            <p class="text-muted mb-2">Введите название навыка для поиска</p>
                            <small class="text-muted">
                                Доступно для добавления: <strong>${availableCount}</strong> из ${totalSkills} навыков<br>
                                Исключены: навыки, которые могут создать циклические зависимости
                            </small>
                        </div>
                    `;
                }
                prereqEmptyMessage.style.display = 'block';
            }
        } else {
            if (prereqEmptyMessage) prereqEmptyMessage.style.display = 'none';
            if (prereqList) {
                prereqList.innerHTML = filteredSkills.map(skill => `
                    <a href="#" class="list-group-item list-group-item-action" data-skill-id="${skill.id}">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <div class="fw-semibold">${skill.name}</div>
                                ${skill.is_base ? '<small class="text-muted">Базовый навык</small>' : ''}
                            </div>
                            <i class="fas fa-plus text-primary"></i>
                        </div>
                    </a>
                `).join('');
                
                // Добавляем обработчики клика
                prereqList.querySelectorAll('.list-group-item').forEach(item => {
                    item.addEventListener('click', function(e) {
                        e.preventDefault();
                        const skillId = this.getAttribute('data-skill-id');
                        addPrerequisite(selectedSkillId, parseInt(skillId));
                    });
                });
            }
        }
    }    function addPrerequisite(skillId, prereqId) {
        // Проверяем наличие CSRF токена
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        if (!csrfToken) {
            alert('CSRF токен не найден на странице');
            return;
        }
        
        console.log('Отправляем запрос:', { skillId, prereqId });
        
        fetch('/methodist/api/add_prerequisite/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken.value
            },
            body: `skill_id=${encodeURIComponent(skillId)}&prereq_id=${encodeURIComponent(prereqId)}`
        }).then(response => {
            console.log('Ответ получен:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();        }).then(data => {
            console.log('Данные ответа:', data);
            if (data.success) {
                // Закрываем модальное окно
                closeModal();
                // Перезагружаем страницу для обновления UI
                window.location.reload();
            } else {
                // Показываем подробное сообщение об ошибке
                const errorMessage = data.error || 'Неизвестная ошибка';
                alert('Ошибка при добавлении зависимости:\n\n' + errorMessage);
            }
        })
        .catch(error => {
            console.error('Ошибка запроса:', error);
            alert('Ошибка при добавлении зависимости: ' + error.message);
        });
    }
});
