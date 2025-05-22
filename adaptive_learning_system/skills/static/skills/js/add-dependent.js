// --- Логика для добавления зависимого навыка ---
function openAddDependentModal(selectedSkillId, allSkills, courses) {
    const modal = document.getElementById('add-dependent-modal');
    const closeBtn = modal.querySelector('.close-btn');
    const cancelBtn = modal.querySelector('.cancel-btn');
    const saveBtn = modal.querySelector('.save-btn');
    const skillsList = modal.querySelector('.skills-list');
    const courseFilter = modal.querySelector('.course-filter');
    const nameFilter = modal.querySelector('.name-filter');
    const selectedSkillName = modal.querySelector('.selected-skill-name');

    var selectedSkill = allSkills.find(s => Number(s.id) === Number(selectedSkillId));
    selectedSkillName.textContent = selectedSkill ? selectedSkill.name : '';
    let chosenSkillId = null;

    // Собрать все id потомков (всех зависимых навыков, включая транзитивно)
    function collectAllDescendants(skillId, visited = new Set()) {
        allSkills.forEach(s => {
            if (s.prerequisites.map(Number).includes(Number(skillId))) {
                if (!visited.has(Number(s.id))) {
                    visited.add(Number(s.id));
                    collectAllDescendants(s.id, visited);
                }
            }
        });
    }

    // --- Формируем forbiddenIds и причины ---
    const forbiddenIds = new Set();
    const forbiddenReasons = {};
    forbiddenIds.add(Number(selectedSkillId));
    forbiddenReasons[Number(selectedSkillId)] = 'Сам выбранный навык';
    // Все потомки (все зависимые навыки, включая транзитивно)
    const allDescendants = new Set();
    collectAllDescendants(selectedSkillId, allDescendants);
    allDescendants.forEach(id => {
        forbiddenIds.add(Number(id));
        forbiddenReasons[Number(id)] = 'Является потомком (зависимым)';
    });

    // Фильтрация навыков для выбора зависимого
    function filterSkills() {
        const courseId = courseFilter.value;
        const name = nameFilter.value.trim().toLowerCase();
        let filtered = allSkills.filter(skill => {
            if (forbiddenIds.has(Number(skill.id))) return false;
            if (courseId && !skill.courses.map(String).includes(courseId)) return false;
            if (name && !skill.name.toLowerCase().includes(name)) return false;
            return true;
        });
        filtered = filtered.sort((a, b) => a.name.localeCompare(b.name));
        return filtered;
    }

    function logExcludedSkills() {
        if (typeof console !== 'undefined' && console.groupCollapsed) {
            console.groupCollapsed('Исключённые навыки для добавления в зависимые:');
        } else {
            console.log('Исключённые навыки для добавления в зависимые:');
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

    function renderSkillsList() {
        logExcludedSkills();
        const filtered = filterSkills();
        skillsList.innerHTML = '';
        if (filtered.length === 0) {
            skillsList.innerHTML = '<div class="text-gray-500 italic py-2">Нет доступных навыков</div>';
            return;
        }
        filtered.forEach(skill => {
            const el = document.createElement('div');
            el.className = 'flex items-center px-2 py-1 rounded hover:bg-green-50 cursor-pointer' +
                (chosenSkillId === skill.id ? ' bg-green-100' : '');
            el.innerHTML = `
                <input type="radio" name="dependent-skill" value="${skill.id}" class="mr-2" ${chosenSkillId === skill.id ? 'checked' : ''}>
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

    courseFilter.onchange = renderSkillsList;
    nameFilter.oninput = renderSkillsList;
    closeBtn.onclick = cancelBtn.onclick = function() {
        modal.classList.add('hidden');
    };
    saveBtn.onclick = function() {
        if (!chosenSkillId) {
            alert('Выберите навык для добавления в зависимые');
            return;
        }
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
            // Здесь наоборот: выбранный навык становится предпосылкой для выбранного зависимого
            body: `skill_id=${encodeURIComponent(chosenSkillId)}&prereq_id=${encodeURIComponent(selectedSkillId)}`
        })
        .then(response => response.json())
        .then(data => {
            saveBtn.disabled = false;
            saveBtn.textContent = 'Добавить';
            if (data.success) {
                modal.classList.add('hidden');
                window.location.reload();
            } else {
                alert(data.error || 'Ошибка при добавлении зависимого навыка');
            }
        })
        .catch(() => {
            saveBtn.disabled = false;
            saveBtn.textContent = 'Добавить';
            alert('Ошибка сети при добавлении зависимого навыка');
        });
    };
    courseFilter.innerHTML = '<option value="">Все курсы</option>' +
        courses.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
    nameFilter.value = '';
    chosenSkillId = null;
    renderSkillsList();
    modal.classList.remove('hidden');
}
// --- Глобальный обработчик для кнопки "Добавить зависимый навык" ---
document.addEventListener('DOMContentLoaded', function() {
    const addBtn = document.getElementById('add-dependent-btn');
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
                openAddDependentModal(window.selectedSkillId, window.allSkills, window.courses);
            } else {
                alert('Данные навыков не загружены');
            }
        });
    }
});
// Экспортируем функцию
window.openAddDependentModal = openAddDependentModal;