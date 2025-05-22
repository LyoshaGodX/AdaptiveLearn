// --- Логика для добавления предпосылки навыку ---

/**
 * Открывает модальное окно выбора предпосылки для выбранного навыка.
 * @param {number} selectedSkillId - ID выбранного навыка
 * @param {Array} allSkills - массив всех навыков [{id, name, courses, prerequisites}]
 * @param {Array} courses - массив всех курсов [{id, name}]
 */
function openAddPrerequisiteModal(selectedSkillId, allSkills, courses) {
    // Получаем DOM-элементы модального окна
    const modal = document.getElementById('add-prerequisite-modal');
    const closeBtn = modal.querySelector('.close-btn');
    const cancelBtn = modal.querySelector('.cancel-btn');
    const saveBtn = modal.querySelector('.save-btn');
    const skillsList = modal.querySelector('.skills-list');
    const courseFilter = modal.querySelector('.course-filter');
    const nameFilter = modal.querySelector('.name-filter');
    const selectedSkillName = modal.querySelector('.selected-skill-name');

    // Находим выбранный навык (без повторного объявления переменной)
    var selectedSkill = allSkills.find(s => Number(s.id) === Number(selectedSkillId));
    selectedSkillName.textContent = selectedSkill ? selectedSkill.name : '';

    // Сохраняем выбранный навык для добавления в предпосылки
    let chosenSkillId = null;

    // --- Вспомогательные функции для рекурсивного обхода вверх и вниз ---
    // Собрать все id навыков, от которых skill зависит (вверх по графу)
    function collectAllPrerequisites(skillId, visited = new Set()) {
        if (visited.has(Number(skillId))) return;
        visited.add(Number(skillId));
        const skill = allSkills.find(s => Number(s.id) === Number(skillId));
        if (skill && skill.prerequisites) {
            skill.prerequisites.map(Number).forEach(prereqId => {
                collectAllPrerequisites(prereqId, visited);
            });
        }
    }
    // Собрать все id навыков, которые зависят от skill (вниз по графу)
    function collectAllDependents(skillId, visited = new Set()) {
        if (visited.has(Number(skillId))) return;
        visited.add(Number(skillId));
        allSkills.forEach(s => {
            if (s.prerequisites.map(Number).includes(Number(skillId))) {
                collectAllDependents(s.id, visited);
            }
        });
    }

    // --- Формируем forbiddenIds и причины ---
    const forbiddenIds = new Set();
    const forbiddenReasons = {};
    // Сам выбранный навык
    forbiddenIds.add(Number(selectedSkillId));
    forbiddenReasons[Number(selectedSkillId)] = 'Сам выбранный навык';

    // Все id, от которых выбранный навык зависит (вверх)
    const allPrereqs = new Set();
    collectAllPrerequisites(selectedSkillId, allPrereqs);
    allPrereqs.forEach(id => {
        forbiddenIds.add(Number(id));
        forbiddenReasons[Number(id)] = 'Входит в цепочку предпосылок (вверх)';
    });

    // Все id, которые зависят от выбранного навыка (вниз)
    const allDependents = new Set();
    collectAllDependents(selectedSkillId, allDependents);
    allDependents.forEach(id => {
        forbiddenIds.add(Number(id));
        forbiddenReasons[Number(id)] = 'Входит в цепочку зависимых (вниз)';
    });

    // Уже связанные предпосылки
    const alreadyPrereqIds = selectedSkill ? selectedSkill.prerequisites.map(Number) : [];
    alreadyPrereqIds.forEach(id => {
        forbiddenIds.add(Number(id));
        forbiddenReasons[Number(id)] = 'Уже является предпосылкой';
    });

    // Фильтрация навыков для выбора предпосылки
    function filterSkills() {
        const courseId = courseFilter.value;
        const name = nameFilter.value.trim().toLowerCase();
        // Фильтруем навыки по условиям
        let filtered = allSkills.filter(skill => {
            if (forbiddenIds.has(Number(skill.id))) return false; // Исключаем выбранный и всех его зависимых
            // Исправлено: courseId всегда строка, skill.courses - массив чисел
            if (courseId && !skill.courses.map(String).includes(courseId)) return false;
            if (name && !skill.name.toLowerCase().includes(name)) return false;
            return true;
        });
        // Сортировка по имени
        filtered = filtered.sort((a, b) => a.name.localeCompare(b.name));
        return filtered;
    }

    // Логирование исключённых навыков (перемещено внутрь renderSkillsList для гарантированного вызова при каждом открытии и фильтрации)
    function logExcludedSkills() {
        if (typeof console !== 'undefined' && console.groupCollapsed) {
            console.groupCollapsed('Исключённые навыки для добавления в предпосылки:');
        } else {
            console.log('Исключённые навыки для добавления в предпосылки:');
        }
        allSkills.forEach(skill => {
            if (forbiddenIds.has(Number(skill.id))) {
                console.log(`ID: ${skill.id}, Название: ${skill.name}, Причина: ${forbiddenReasons[Number(skill.id)]}`);
            }
        });
        if (typeof console !== 'undefined' && console.groupEnd) {
            console.groupEnd();
        }
    }

    // Рендер списка навыков
    function renderSkillsList() {
        logExcludedSkills(); // Логируем при каждом рендере
        const filtered = filterSkills();
        skillsList.innerHTML = '';
        if (filtered.length === 0) {
            skillsList.innerHTML = '<div class="text-gray-500 italic py-2">Нет доступных навыков</div>';
            return;
        }
        filtered.forEach(skill => {
            const el = document.createElement('div');
            el.className = 'flex items-center px-2 py-1 rounded hover:bg-blue-50 cursor-pointer' +
                (chosenSkillId === skill.id ? ' bg-blue-100' : '');
            el.innerHTML = `
                <input type="radio" name="prereq-skill" value="${skill.id}" class="mr-2" ${chosenSkillId === skill.id ? 'checked' : ''}>
                <span class="font-medium">${skill.name}</span>
                <span class="text-xs text-gray-400 ml-2">ID: ${skill.id}</span>
            `;
            el.addEventListener('click', () => {
                chosenSkillId = skill.id;
                renderSkillsList();
            });
            skillsList.appendChild(el);
        });
    }

    // Обработчики фильтров
    courseFilter.onchange = renderSkillsList;
    nameFilter.oninput = renderSkillsList;

    // Кнопки закрытия
    closeBtn.onclick = cancelBtn.onclick = function() {
        modal.classList.add('hidden');
    };

    // Кнопка сохранить (добавить предпосылку)
    saveBtn.onclick = function() {
        if (!chosenSkillId) {
            alert('Выберите навык для добавления в предпосылки');
            return;
        }
        // Получаем CSRF-токен
        function getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
        const csrftoken = getCookie('csrftoken');
        saveBtn.disabled = true;
        saveBtn.textContent = 'Добавление...';
        fetch('/api/add_prerequisite/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrftoken
            },
            body: `skill_id=${encodeURIComponent(selectedSkillId)}&prereq_id=${encodeURIComponent(chosenSkillId)}`
        })
        .then(response => response.json())
        .then(data => {
            saveBtn.disabled = false;
            saveBtn.textContent = 'Добавить';
            if (data.success) {
                modal.classList.add('hidden');
                // Обновляем страницу для отображения новой связи
                window.location.reload();
            } else {
                alert(data.error || 'Ошибка при добавлении предпосылки');
            }
        })
        .catch(err => {
            saveBtn.disabled = false;
            saveBtn.textContent = 'Добавить';
            alert('Ошибка сети при добавлении предпосылки');
        });
    };

    // Заполнить фильтр курсов
    courseFilter.innerHTML = '<option value="">Все курсы</option>' +
        courses.map(c => `<option value="${c.id}">${c.name}</option>`).join('');

    // Сбросить фильтры и выбранный навык
    nameFilter.value = '';
    chosenSkillId = null;

    // Рендерим список навыков
    renderSkillsList();

    // Показываем модальное окно
    modal.classList.remove('hidden');
}

// --- Глобальный обработчик для кнопки "Добавить предпосылку" ---
document.addEventListener('DOMContentLoaded', function() {
    // --- Исправленный обработчик для кнопки "Добавить предпосылку" ---
    const addBtn = document.getElementById('add-prerequisite-btn');
    if (addBtn) {
        addBtn.addEventListener('click', function() {
            if (
                typeof window.allSkills !== 'undefined' &&
                Array.isArray(window.allSkills) &&
                typeof window.courses !== 'undefined' &&
                Array.isArray(window.courses) &&
                typeof window.selectedSkillId !== 'undefined' &&
                window.selectedSkillId !== null &&
                window.selectedSkillId !== ''
            ) {
                openAddPrerequisiteModal(window.selectedSkillId, window.allSkills, window.courses);
            } else {
                alert('Данные навыков не загружены');
            }
        });
    }
});

// --- Экспортируем функцию для использования из других скриптов ---
window.openAddPrerequisiteModal = openAddPrerequisiteModal;
