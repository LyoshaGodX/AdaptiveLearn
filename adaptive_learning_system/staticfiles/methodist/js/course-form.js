// JavaScript для формы создания/редактирования курса

// Глобальные переменные
let allSkills = [];
let allTasks = [];
let selectedSkills = new Set();
let selectedTasks = new Set();
let isEditing = false;
let currentCourseId = null;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    initializeCourseForm();
});

// === ОСНОВНАЯ ИНИЦИАЛИЗАЦИЯ ===
function initializeCourseForm() {
    console.log('=== ИНИЦИАЛИЗАЦИЯ ФОРМЫ КУРСА ===');
    
    // Определяем режим (создание или редактирование)
    const courseIdInput = document.getElementById('course_id');
    isEditing = courseIdInput && courseIdInput.readOnly;
    currentCourseId = isEditing ? courseIdInput.value : null;
    
    console.log('Режим редактирования:', isEditing);
    console.log('ID курса:', currentCourseId);
    
    // Проверяем наличие контейнеров
    const skillsContainer = document.getElementById('available-skills-container');
    const tasksContainer = document.getElementById('available-tasks-container');
    
    console.log('Контейнер навыков найден:', !!skillsContainer);
    console.log('Контейнер заданий найден:', !!tasksContainer);
    
    // Инициализируем валидацию ID курса
    initializeCourseIdValidation();
    
    // Загружаем данные навыков и заданий
    loadSkillsAndTasks();
      // Инициализируем интерфейсы
    initializeSkillsInterface();
    initializeTasksInterface();
    
    // Инициализируем валидацию формы
    initializeFormValidation();
    
    console.log('=== ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА ===');
}

// === ВАЛИДАЦИЯ ID КУРСА ===
function initializeCourseIdValidation() {
    const courseIdInput = document.getElementById('course_id');
    
    if (courseIdInput && !courseIdInput.readOnly) {
        courseIdInput.addEventListener('input', function() {
            validateCourseId(this);
        });
        
        courseIdInput.addEventListener('blur', function() {
            validateCourseId(this);
        });
    }
}

function validateCourseId(input) {
    const value = input.value.trim().toUpperCase();
    const pattern = /^C\d+$/;
    
    // Автоматически приводим к верхнему регистру
    if (input.value !== value) {
        input.value = value;
    }
    
    if (value === '') {
        setValidationState(input, 'neutral', 'ID курса обязателен');
        return false;
    }
    
    if (!pattern.test(value)) {
        setValidationState(input, 'invalid', 'Формат: C + число (например, C4, C5)');
        return false;
    }
    
    // Проверяем на существующие ID (можно расширить AJAX проверкой)
    const existingIds = ['C1', 'C2', 'C3']; // Можно получать через AJAX
    if (existingIds.includes(value)) {
        setValidationState(input, 'invalid', 'Этот ID уже занят');
        return false;
    }
    
    setValidationState(input, 'valid', 'ID доступен');
    return true;
}

function setValidationState(input, state, message) {
    const formText = input.parentElement.querySelector('.form-text');
    
    // Удаляем предыдущие классы
    input.classList.remove('is-valid', 'is-invalid');
    
    switch (state) {
        case 'valid':
            input.classList.add('is-valid');
            if (formText) {
                formText.textContent = message;
                formText.style.color = '#28a745';
            }
            break;
        case 'invalid':
            input.classList.add('is-invalid');
            if (formText) {
                formText.textContent = message;
                formText.style.color = '#dc3545';
            }
            break;
        default:
            if (formText) {
                formText.textContent = message;
                formText.style.color = '#6c757d';
            }
    }
}

// === ЗАГРУЗКА ДАННЫХ ===
async function loadSkillsAndTasks() {
    try {
        console.log('Загрузка навыков и заданий...');
        
        // Загружаем навыки
        const skillsResponse = await fetch('/methodist/test/api/skills/');
        if (skillsResponse.ok) {
            allSkills = await skillsResponse.json();
            console.log('Загружено навыков:', allSkills.length);
        } else {
            console.error('Ошибка загрузки навыков:', skillsResponse.status);
        }
        
        // Загружаем задания
        const tasksResponse = await fetch('/methodist/test/api/tasks/');
        if (tasksResponse.ok) {
            allTasks = await tasksResponse.json();
            console.log('Загружено заданий:', allTasks.length);
        } else {
            console.error('Ошибка загрузки заданий:', tasksResponse.status);
        }
        
        // Если редактируем курс, загружаем его данные
        if (isEditing && currentCourseId) {
            console.log('Загрузка данных курса:', currentCourseId);
            const courseResponse = await fetch(`/methodist/api/course/${currentCourseId}/`);
            if (courseResponse.ok) {
                const courseData = await courseResponse.json();
                
                // Заполняем выбранные навыки
                courseData.skills.forEach(skill => {
                    selectedSkills.add(skill.id);
                });
                
                // Заполняем выбранные задания
                courseData.tasks.forEach(task => {
                    selectedTasks.add(task.id);
                });
                
                console.log('Выбранные навыки:', selectedSkills.size);
                console.log('Выбранные задания:', selectedTasks.size);
            }
        }
        
        // Отрисовываем интерфейсы
        console.log('Отрисовка интерфейсов...');
        renderSkills();
        renderTasks();
        
    } catch (error) {
        console.error('Ошибка загрузки данных:', error);
        showError('Ошибка загрузки данных. Обновите страницу.');
    }
}

// === УПРАВЛЕНИЕ НАВЫКАМИ ===
function initializeSkillsInterface() {
    const availableSearch = document.getElementById('available-skills-search');
    const selectedSearch = document.getElementById('selected-skills-search');
    
    // Поиск в доступных навыках
    if (availableSearch) {
        availableSearch.addEventListener('input', () => filterAvailableSkills());
    }
    
    // Поиск в выбранных навыках
    if (selectedSearch) {
        selectedSearch.addEventListener('input', () => filterSelectedSkills());
    }
}

function renderSkills() {
    renderAvailableSkills();
    renderSelectedSkills();
    updateSkillsCounts();
    updateHiddenSkillsFields();
}

function renderAvailableSkills() {
    const container = document.getElementById('available-skills-container');
    if (!container) {
        console.error('Контейнер available-skills-container не найден');
        return;
    }
    
    const searchElement = document.getElementById('available-skills-search');
    const searchTerm = searchElement ? searchElement.value.toLowerCase() : '';
    
    console.log('Отрисовка доступных навыков. Всего навыков:', allSkills.length);
    console.log('Выбранные навыки:', Array.from(selectedSkills));
    
    const availableSkills = allSkills.filter(skill => !selectedSkills.has(skill.id));
    const filteredSkills = availableSkills.filter(skill => 
        skill.name.toLowerCase().includes(searchTerm)
    );
    
    console.log('Доступных навыков после фильтрации:', filteredSkills.length);
    
    if (filteredSkills.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-brain"></i>
                <p>Нет доступных навыков</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = filteredSkills.map(skill => `
        <div class="skill-item" data-skill-id="${skill.id}">
            <div class="skill-info">
                <div class="skill-name">${skill.name}</div>
                <div class="skill-meta mt-1">
                    <span class="badge ${skill.is_base ? 'bg-primary' : 'bg-secondary'}">
                        ${skill.is_base ? 'Базовый' : 'Дополнительный'}
                    </span>
                </div>
            </div>
            <button type="button" class="add-btn" onclick="addSkill(${skill.id})">
                <i class="fas fa-plus"></i>
            </button>
        </div>
    `).join('');
    
    console.log('Отрисовка доступных навыков завершена');
}

function renderSelectedSkills() {
    console.log('=== ОТРИСОВКА ВЫБРАННЫХ НАВЫКОВ ===');
    
    const container = document.getElementById('selected-skills-container');
    if (!container) {
        console.error('Контейнер selected-skills-container не найден');
        return;
    }
    
    const searchElement = document.getElementById('selected-skills-search');
    const searchTerm = searchElement ? searchElement.value.toLowerCase() : '';
    
    console.log('Всего выбранных навыков:', selectedSkills.size);
    console.log('Выбранные ID навыков:', Array.from(selectedSkills));
    
    const skills = allSkills.filter(skill => selectedSkills.has(skill.id));
    console.log('Найденные навыки по ID:', skills.length);
    
    const filteredSkills = skills.filter(skill => 
        skill.name.toLowerCase().includes(searchTerm)
    );
    
    console.log('Навыки после фильтрации:', filteredSkills.length);
    
    if (filteredSkills.length === 0) {
        console.log('Показываем пустое состояние');
        container.innerHTML = `
            <div class="empty-state" id="skills-empty-state">
                <i class="fas fa-brain"></i>
                <p>Навыки не выбраны</p>
            </div>
        `;
        return;
    }
    
    console.log('Отрисовываем навыки:', filteredSkills.map(s => s.name));
    
    container.innerHTML = filteredSkills.map(skill => `
        <div class="selected-skill-item" data-skill-id="${skill.id}">
            <div class="skill-info">
                <div class="skill-name">${skill.name}</div>
                <div class="skill-meta mt-1">
                    <span class="badge ${skill.is_base ? 'bg-primary' : 'bg-secondary'}">
                        ${skill.is_base ? 'Базовый' : 'Дополнительный'}
                    </span>
                </div>
            </div>
            <button type="button" class="remove-btn" onclick="removeSkill(${skill.id})">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `).join('');
    
    console.log('Отрисовка выбранных навыков завершена');
}

function addSkill(skillId) {
    console.log('Добавляем навык:', skillId);
    console.log('До добавления:', Array.from(selectedSkills));
    
    selectedSkills.add(skillId);
    
    console.log('После добавления:', Array.from(selectedSkills));
    
    renderSkills();
}

function removeSkill(skillId) {
    console.log('Удаляем навык:', skillId);
    console.log('До удаления:', Array.from(selectedSkills));
    
    selectedSkills.delete(skillId);
    
    console.log('После удаления:', Array.from(selectedSkills));
    
    renderSkills();
}

function filterAvailableSkills() {
    renderAvailableSkills();
    updateSkillsCounts();
}

function filterSelectedSkills() {
    renderSelectedSkills();
}

function updateSkillsCounts() {
    const availableCount = allSkills.filter(skill => !selectedSkills.has(skill.id)).length;
    const selectedCount = selectedSkills.size;
    
    const availableCountEl = document.getElementById('available-skills-count');
    const selectedCountEl = document.getElementById('selected-skills-count');
    
    if (availableCountEl) availableCountEl.textContent = availableCount;
    if (selectedCountEl) selectedCountEl.textContent = selectedCount;
}

function updateHiddenSkillsFields() {
    const container = document.getElementById('selected-skills-hidden');
    if (!container) return;
    
    container.innerHTML = '';
    
    selectedSkills.forEach(skillId => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'skills';
        input.value = skillId;
        container.appendChild(input);
    });
}

// === УПРАВЛЕНИЕ ЗАДАНИЯМИ ===
function initializeTasksInterface() {
    const availableSearch = document.getElementById('available-tasks-search');
    const selectedSearch = document.getElementById('selected-tasks-search');
    const difficultyFilter = document.getElementById('tasks-difficulty-filter');
    const selectedDifficultyFilter = document.getElementById('selected-tasks-difficulty-filter');
    
    // Поиск в доступных заданиях
    if (availableSearch) {
        availableSearch.addEventListener('input', () => filterAvailableTasks());
    }
    
    // Поиск в выбранных заданиях
    if (selectedSearch) {
        selectedSearch.addEventListener('input', () => filterSelectedTasks());
    }
    
    // Фильтр по сложности для доступных заданий
    if (difficultyFilter) {
        difficultyFilter.addEventListener('change', () => filterAvailableTasks());
    }
    
    // Фильтр по сложности для выбранных заданий
    if (selectedDifficultyFilter) {
        selectedDifficultyFilter.addEventListener('change', () => filterSelectedTasks());
    }
}

function renderTasks() {
    renderAvailableTasks();
    renderSelectedTasks();
    updateTasksCounts();
    updateHiddenTasksFields();
}

function renderAvailableTasks() {
    console.log('=== ОТРИСОВКА ДОСТУПНЫХ ЗАДАНИЙ ===');
    
    const container = document.getElementById('available-tasks-container');
    if (!container) {
        console.error('Контейнер available-tasks-container не найден');
        return;
    }
    
    const searchElement = document.getElementById('available-tasks-search');
    const filterElement = document.getElementById('tasks-difficulty-filter');
    const searchTerm = searchElement ? searchElement.value.toLowerCase() : '';
    const difficultyFilter = filterElement ? filterElement.value : '';
    
    console.log('Всего заданий:', allTasks.length);
    console.log('Выбранные задания:', Array.from(selectedTasks));
    
    const availableTasks = allTasks.filter(task => !selectedTasks.has(task.id));
    console.log('Доступных заданий:', availableTasks.length);
    
    let filteredTasks = availableTasks.filter(task => 
        task.title.toLowerCase().includes(searchTerm)
    );
    
    if (difficultyFilter) {
        filteredTasks = filteredTasks.filter(task => task.difficulty === difficultyFilter);
    }
    
    console.log('Заданий после фильтрации:', filteredTasks.length);
    
    if (filteredTasks.length === 0) {
        console.log('Показываем пустое состояние для заданий');
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-tasks"></i>
                <p>Нет доступных заданий</p>
            </div>
        `;
        return;
    }
    
    console.log('Отрисовываем задания:', filteredTasks.map(t => t.title));
      container.innerHTML = filteredTasks.map(task => `
        <div class="task-item" data-task-id="${task.id}">
            <div class="task-info">
                <div class="task-title">${task.title}</div>
                <div class="task-meta mt-1">
                    <span class="badge ${getDifficultyBadgeClass(task.difficulty)}">
                        ${getDifficultyLabel(task.difficulty)}
                    </span>
                    ${task.task_type ? `<span class="badge bg-info">${getTaskTypeLabel(task.task_type)}</span>` : ''}
                </div>
            </div>
            <button type="button" class="add-btn" onclick="addTask(${task.id})">
                <i class="fas fa-plus"></i>
            </button>
        </div>
    `).join('');
    
    console.log('Отрисовка доступных заданий завершена');
}

function renderSelectedTasks() {
    const container = document.getElementById('selected-tasks-container');
    const searchElement = document.getElementById('selected-tasks-search');
    const filterElement = document.getElementById('selected-tasks-difficulty-filter');
    const searchTerm = searchElement ? searchElement.value.toLowerCase() : '';
    const difficultyFilter = filterElement ? filterElement.value : '';
    
    const tasks = allTasks.filter(task => selectedTasks.has(task.id));
    let filteredTasks = tasks.filter(task => 
        task.title.toLowerCase().includes(searchTerm)
    );
    
    // Применяем фильтр по сложности
    if (difficultyFilter) {
        filteredTasks = filteredTasks.filter(task => task.difficulty === difficultyFilter);
    }
    
    if (filteredTasks.length === 0) {
        container.innerHTML = `
            <div class="empty-state" id="tasks-empty-state">
                <i class="fas fa-tasks"></i>
                <p>Задания не найдены</p>
            </div>
        `;
        return;
    }
      container.innerHTML = filteredTasks.map(task => `
        <div class="selected-task-item" data-task-id="${task.id}">
            <div class="task-info">
                <div class="task-title">${task.title}</div>
                <div class="task-meta mt-1">
                    <span class="badge ${getDifficultyBadgeClass(task.difficulty)}">
                        ${getDifficultyLabel(task.difficulty)}
                    </span>
                    ${task.task_type ? `<span class="badge bg-info">${getTaskTypeLabel(task.task_type)}</span>` : ''}
                </div>
            </div>
            <button type="button" class="remove-btn" onclick="removeTask(${task.id})">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `).join('');
}

function addTask(taskId) {
    selectedTasks.add(taskId);
    renderTasks();
}

function removeTask(taskId) {
    selectedTasks.delete(taskId);
    renderTasks();
}

function filterAvailableTasks() {
    renderAvailableTasks();
    updateTasksCounts();
}

function filterSelectedTasks() {
    renderSelectedTasks();
}

function updateTasksCounts() {
    const availableCount = allTasks.filter(task => !selectedTasks.has(task.id)).length;
    const selectedCount = selectedTasks.size;
    
    const availableCountEl = document.getElementById('available-tasks-count');
    const selectedCountEl = document.getElementById('selected-tasks-count');
    
    if (availableCountEl) availableCountEl.textContent = availableCount;
    if (selectedCountEl) selectedCountEl.textContent = selectedCount;
}

function updateHiddenTasksFields() {
    const container = document.getElementById('selected-tasks-hidden');
    if (!container) return;
    
    container.innerHTML = '';
    
    selectedTasks.forEach(taskId => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'tasks';
        input.value = taskId;
        container.appendChild(input);
    });
}

// Вспомогательные функции для заданий
function getDifficultyBadgeClass(difficulty) {
    switch (difficulty) {
        case 'beginner': return 'bg-success';
        case 'intermediate': return 'bg-warning text-dark';
        case 'advanced': return 'bg-danger';
        default: return 'bg-secondary';
    }
}

function getDifficultyLabel(difficulty) {
    switch (difficulty) {
        case 'beginner': return 'Начальный';
        case 'intermediate': return 'Средний';
        case 'advanced': return 'Продвинутый';
        default: return 'Не указан';
    }
}

function getTaskTypeLabel(taskType) {
    switch (taskType) {
        case 'single': return 'Один ответ';
        case 'multiple': return 'Много ответов';
        case 'true_false': return 'Верно/Неверно';
        default: return taskType;
    }
}

// === ВАЛИДАЦИЯ ФОРМЫ ===
function initializeFormValidation() {
    const form = document.querySelector('form.course-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            if (!validateForm()) {
                e.preventDefault();
                return false;
            }
            return true;
        });
    }
}

function validateForm() {
    const courseName = document.getElementById('name').value.trim();
    const courseDescription = document.getElementById('description').value.trim();
    const courseIdInput = document.getElementById('course_id');
    
    // Проверяем название курса
    if (!courseName) {
        showValidationError('Пожалуйста, введите название курса', 'name');
        return false;
    }
    
    // Проверяем описание курса
    if (!courseDescription) {
        showValidationError('Пожалуйста, введите описание курса', 'description');
        return false;
    }
    
    // Проверяем ID курса для новых курсов
    if (courseIdInput && !courseIdInput.readOnly) {
        if (!validateCourseId(courseIdInput)) {
            showValidationError('Пожалуйста, введите корректный ID курса', 'course_id');
            return false;
        }
    }
    
    // Проверяем длительность
    const durationInput = document.getElementById('duration_hours');
    if (durationInput.value && (isNaN(durationInput.value) || parseInt(durationInput.value) < 1)) {
        showValidationError('Длительность должна быть положительным числом', 'duration_hours');
        return false;
    }
    
    // Предупреждение о пустых навыках
    if (selectedSkills.size === 0) {
        const confirmResult = window.confirm('Вы не выбрали ни одного навыка для курса. Продолжить?');
        if (!confirmResult) {
            return false;
        }
    }
    
    return true;
}

function showValidationError(message, fieldId) {
    // Показываем ошибку
    alert(message);
    
    // Фокусируемся на поле с ошибкой
    const field = document.getElementById(fieldId);
    if (field) {
        field.focus();
        field.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // Добавляем класс ошибки
        field.classList.add('is-invalid');
        
        // Убираем класс ошибки через 3 секунды
        setTimeout(() => {
            field.classList.remove('is-invalid');
        }, 3000);
    }
}

function showError(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-danger alert-dismissible fade show';
    alertDiv.style.position = 'fixed';
    alertDiv.style.top = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.zIndex = '9999';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Автоматически удаляем через 5 секунд
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.parentNode.removeChild(alertDiv);
        }
    }, 5000);
}
