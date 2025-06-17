/**
 * Модуль для добавления предпосылок (зависимых навыков)
 */

document.addEventListener('DOMContentLoaded', function() {
    const addDependentBtn = document.getElementById('add-dependent-btn');
    const dependentSearch = document.getElementById('dependent-search');
    const dependentList = document.getElementById('dependent-list');
    const dependentEmptyMessage = document.getElementById('dependent-empty-message');
    const modal = document.getElementById('add-dependent-modal');
    
    if (addDependentBtn) {
        addDependentBtn.addEventListener('click', function() {
            // Проверяем, что данные загружены
            if (!window.allSkills || !window.selectedSkillId) {
                alert('Данные навыков не загружены');
                return;
            }
            
            // Очищаем поиск при открытии
            if (dependentSearch) {
                dependentSearch.value = '';
                updateDependentList('');
            }
            
            // Открываем модальное окно
            if (modal) {
                modal.classList.add('show');
                document.body.style.overflow = 'hidden';
            }
        });
    }

    // Закрытие модального окна
    const closeBtn = document.getElementById('add-dependent-close');
    const cancelBtn = document.getElementById('add-dependent-cancel');
    
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
    if (dependentSearch) {
        dependentSearch.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            updateDependentList(searchTerm);
        });
    }

    function updateDependentList(searchTerm) {
        if (!window.allSkills || !window.selectedSkillId) {
            return;
        }
        
        const selectedSkillId = parseInt(window.selectedSkillId);
        const selectedSkill = window.allSkills.find(s => s.id === selectedSkillId);
        
        if (!selectedSkill) {
            return;
        }
        
        // Собираем запрещенные ID для предотвращения циклических зависимостей
        const forbiddenIds = new Set();
        const forbiddenReasons = {};
        
        // 1. Сам выбранный навык (навык не может зависеть от самого себя)
        forbiddenIds.add(selectedSkillId);
        forbiddenReasons[selectedSkillId] = 'Сам выбранный навык';
        
        // 2. Навыки, которые уже зависят от выбранного навыка
        window.allSkills.forEach(skill => {
            if (skill.prerequisites && skill.prerequisites.includes(selectedSkillId)) {
                forbiddenIds.add(skill.id);
                forbiddenReasons[skill.id] = 'Уже зависит от этого навыка';
            }
        });
        
        // Функция для сбора всех потомков навыка (навыков, которые от него зависят)
        function collectAllDescendants(skillId, visited = new Set()) {
            if (visited.has(skillId)) return;
            visited.add(skillId);
            
            window.allSkills.forEach(skill => {
                if (skill.prerequisites && skill.prerequisites.includes(skillId)) {
                    collectAllDescendants(skill.id, visited);
                }
            });
        }
        
        // Собираем всех потомков выбранного навыка (которые уже от него зависят)
        // Эти навыки нельзя добавлять, т.к. они уже в зависимости
        const allDescendants = new Set();
        collectAllDescendants(selectedSkillId, allDescendants);
        allDescendants.forEach(id => {
            if (id !== selectedSkillId) { // исключаем сам навык, он уже добавлен
                forbiddenIds.add(id);
                forbiddenReasons[id] = 'Входит в цепочку зависимых навыков';
            }
        });
        
        // Логирование исключенных навыков для отладки
        console.group('Исключенные навыки для добавления как зависимые:');
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
            if (dependentList) dependentList.innerHTML = '';
            if (dependentEmptyMessage) {
                if (searchTerm) {
                    dependentEmptyMessage.innerHTML = `
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
                    
                    dependentEmptyMessage.innerHTML = `
                        <div class="text-center py-3">
                            <i class="fas fa-info-circle fa-2x text-muted mb-2"></i>
                            <p class="text-muted mb-2">Введите название навыка для поиска</p>
                            <small class="text-muted">
                                Доступно для добавления: <strong>${availableCount}</strong> из ${totalSkills} навыков<br>
                                Исключены: навыки, которые уже зависят от этого или могут создать циклические зависимости
                            </small>
                        </div>
                    `;
                }
                dependentEmptyMessage.style.display = 'block';
            }
        } else {
            if (dependentEmptyMessage) dependentEmptyMessage.style.display = 'none';
            if (dependentList) {
                dependentList.innerHTML = filteredSkills.map(skill => `
                    <a href="#" class="list-group-item list-group-item-action" data-skill-id="${skill.id}">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <div class="fw-semibold">${skill.name}</div>
                                ${skill.is_base ? '<small class="text-muted">Базовый навык</small>' : ''}
                            </div>
                            <i class="fas fa-plus text-success"></i>
                        </div>
                    </a>
                `).join('');
                
                // Добавляем обработчики клика
                dependentList.querySelectorAll('.list-group-item').forEach(item => {
                    item.addEventListener('click', function(e) {
                        e.preventDefault();
                        const skillId = this.getAttribute('data-skill-id');
                        addDependent(selectedSkillId, parseInt(skillId));
                    });
                });
            }
        }
    }    function addDependent(selectedSkillId, dependentSkillId) {
        // Проверяем наличие CSRF токена
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        if (!csrfToken) {
            alert('CSRF токен не найден на странице');
            return;
        }
        
        console.log('Отправляем запрос на добавление зависимости:', { 
            dependentSkill: dependentSkillId, 
            prerequisite: selectedSkillId 
        });
        
        fetch('/methodist/api/add_prerequisite/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken.value
            },
            body: `skill_id=${encodeURIComponent(dependentSkillId)}&prereq_id=${encodeURIComponent(selectedSkillId)}`
        })
        .then(response => {
            console.log('Ответ получен:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Данные ответа:', data);
            if (data.success) {
                // Закрываем модальное окно
                closeModal();
                // Перезагружаем страницу для обновления UI
                window.location.reload();
            } else {
                // Показываем подробное сообщение об ошибке
                const errorMessage = data.error || 'Неизвестная ошибка';
                alert('Ошибка при добавлении предпосылки:\n\n' + errorMessage);
            }
        })
        .catch(error => {
            console.error('Ошибка запроса:', error);
            alert('Ошибка при добавлении предпосылки: ' + error.message);
        });
    }
});