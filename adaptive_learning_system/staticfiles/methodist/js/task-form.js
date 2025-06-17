/**
 * JavaScript для формы создания/редактирования задания
 */

document.addEventListener('DOMContentLoaded', function() {
    const taskTypeSelect = document.getElementById('task_type');
    const answersSection = document.getElementById('answers-section');
    const correctAnswerSection = document.getElementById('correct-answer-section');
    const addAnswerBtn = document.getElementById('add-answer');
    const answersContainer = document.getElementById('answers-container');
    let answerCounter = 0;

    // Обработка изменения типа задания
    taskTypeSelect.addEventListener('change', function() {
        toggleAnswerSections();
    });

    // Кнопка добавления варианта ответа
    addAnswerBtn.addEventListener('click', function() {
        addAnswerOption();
    });    // Инициализация при загрузке страницы
    toggleAnswerSections();
    
    // Инициализируем функциональность связей
    initializeSkillsAndCoursesHandlers();
      // Инициализируем предпросмотр
    initializePreview();
    
    // Инициализируем Markdown редактор
    initializeMarkdownEditor();
    
    // Проверяем наличие данных о существующих ответах
    setTimeout(function() {
        const taskType = taskTypeSelect.value;
        
        // Загружаем существующие варианты ответов (если редактируем)
        if (window.existingAnswers && window.existingAnswers.length > 0) {
            loadExistingAnswers();
        } else {
            // Добавляем начальные варианты для новых заданий с выбором
            if (['single', 'multiple'].includes(taskType)) {
                // Для single и multiple уже добавлены в setupAnswerTypeSpecifics
            } else if (taskType === 'true_false') {
                // Для true_false варианты уже настроены в HTML
            }
        }
    }, 100); // Небольшая задержка для загрузки данных

    // Валидация формы перед отправкой
    document.querySelector('.task-form').addEventListener('submit', function(e) {
        if (!validateForm()) {
            e.preventDefault();
        }    });
});

function toggleAnswerSections() {
    const taskType = document.getElementById('task_type').value;
    const answersSection = document.getElementById('answers-section');
    const correctAnswerSection = document.getElementById('correct-answer-section');
    const answersContainer = document.getElementById('answers-container');
    const trueFalseContainer = document.getElementById('true-false-container');
    const addAnswerBtn = document.getElementById('add-answer');
    
    if (['single', 'multiple', 'true_false'].includes(taskType)) {
        // Показываем секцию с вариантами ответов
        answersSection.style.display = 'block';
        correctAnswerSection.style.display = 'none';
        
        // Убираем обязательность с поля правильного ответа
        document.getElementById('correct_answer').required = false;
        
        // Настраиваем специфичные для типа параметры
        setupAnswerTypeSpecifics(taskType);
    } else {
        // Показываем секцию с правильным ответом
        answersSection.style.display = 'none';
        correctAnswerSection.style.display = 'block';
        
        // Добавляем обязательность полю правильного ответа
        document.getElementById('correct_answer').required = true;
        
        // Скрываем контейнеры ответов
        answersContainer.style.display = 'block';
        trueFalseContainer.style.display = 'none';
    }
}

function setupAnswerTypeSpecifics(taskType) {
    const answersContainer = document.getElementById('answers-container');
    const trueFalseContainer = document.getElementById('true-false-container');
    const addAnswerBtn = document.getElementById('add-answer');
    
    if (taskType === 'true_false') {
        // Для типа "верно/неверно" - показываем фиксированные варианты
        answersContainer.style.display = 'none';
        trueFalseContainer.style.display = 'block';
        addAnswerBtn.style.display = 'none';
        
        // Очищаем обычные варианты ответов
        clearAnswers();
        
    } else {
        // Для других типов - показываем обычные варианты
        answersContainer.style.display = 'block';
        trueFalseContainer.style.display = 'none';
        addAnswerBtn.style.display = 'block';
        
        // Очищаем и добавляем начальные варианты
        clearAnswers();
        
        // Добавляем 2 пустых варианта
        addAnswerOption();
        addAnswerOption();
        
        // Настраиваем тип переключателей
        updateAnswerInputTypes(taskType);
    }
}

function updateAnswerInputTypes(taskType) {
    const correctInputs = document.querySelectorAll('.answer-correct');
    
    correctInputs.forEach((input, index) => {
        if (taskType === 'single') {
            // Для единственного выбора - radio buttons
            input.type = 'radio';
            input.name = 'correct_answer_single';
            input.value = index;
            
            // Добавляем обработчик для эксклюзивного выбора
            input.addEventListener('change', function() {
                if (this.checked) {
                    correctInputs.forEach(otherInput => {
                        if (otherInput !== this) {
                            otherInput.checked = false;
                        }
                    });
                }
            });
            
        } else if (taskType === 'multiple') {
            // Для множественного выбора - checkboxes
            input.type = 'checkbox';
            input.name = 'correct_answers_multiple';
            input.value = index;
        }
    });
}

function addAnswerOption(text = '', isCorrect = false) {
    const template = document.getElementById('answer-template');
    const clone = template.content.cloneNode(true);
    const taskType = document.getElementById('task_type').value;
    
    // Настраиваем элементы
    const input = clone.querySelector('input[name="answer_text"]');
    const correctInput = clone.querySelector('.answer-correct');
    const removeBtn = clone.querySelector('.remove-answer');
    
    input.value = text;
    correctInput.value = answerCounter;
    correctInput.checked = isCorrect;
    
    // Настраиваем тип переключателя в зависимости от типа задания
    if (taskType === 'single') {
        correctInput.type = 'radio';
        correctInput.name = 'correct_answer_single';
        
        // Добавляем обработчик для эксклюзивного выбора
        correctInput.addEventListener('change', function() {
            if (this.checked) {
                document.querySelectorAll('.answer-correct').forEach(otherInput => {
                    if (otherInput !== this) {
                        otherInput.checked = false;
                    }
                });
            }
        });
        
    } else if (taskType === 'multiple') {
        correctInput.type = 'checkbox';
        correctInput.name = 'correct_answers_multiple';
    }
    
    // Обработчик удаления
    removeBtn.addEventListener('click', function() {
        removeAnswerOption(this);
    });
      // Добавляем в контейнер
    document.getElementById('answers-container').appendChild(clone);
    answerCounter++;
    
    // Инициализируем Markdown редактор для нового элемента
    const newAnswerItem = document.getElementById('answers-container').lastElementChild;
    initializeAnswerMarkdownEditor(newAnswerItem);
    
    // Обновляем индексы для radio buttons если нужно
    if (taskType === 'single') {
        updateRadioButtonsGroup();
    }
}

function updateRadioButtonsGroup() {
    const radioButtons = document.querySelectorAll('.answer-correct[type="radio"]');
    radioButtons.forEach((radio, index) => {
        radio.value = index;
    });
}

function removeAnswerOption(button) {
    const answerItem = button.closest('.answer-item');
    const container = document.getElementById('answers-container');
    const taskType = document.getElementById('task_type').value;
    
    // Не даем удалить, если остался только один вариант
    if (container.children.length <= 1) {
        alert('Должен остаться хотя бы один вариант ответа');
        return;
    }
    
    // Для единственного выбора - минимум 2 варианта
    if (taskType === 'single' && container.children.length <= 2) {
        alert('Для типа "Один вариант ответа" должно быть минимум 2 варианта');
        return;
    }
    
    // Анимация удаления
    answerItem.style.opacity = '0';
    answerItem.style.transform = 'translateX(-100%)';
    
    setTimeout(() => {
        answerItem.remove();
        
        // Обновляем индексы для radio buttons
        if (taskType === 'single') {
            updateRadioButtonsGroup();
        }
    }, 300);
}

function clearAnswers() {
    const container = document.getElementById('answers-container');
    container.innerHTML = '';
    answerCounter = 0;
}

function loadExistingAnswers() {
    const taskType = document.getElementById('task_type').value;
    
    if (taskType === 'true_false') {
        // Для типа "Верно/Неверно" устанавливаем правильное значение в radio buttons
        if (window.existingAnswers && window.existingAnswers.length > 0) {
            // Ищем правильный ответ среди вариантов
            const correctAnswer = window.existingAnswers.find(answer => answer.is_correct);
            if (correctAnswer) {
                const radioValue = correctAnswer.text === 'Верно' ? 'true' : 'false';
                const radioButton = document.querySelector(`input[name="true_false_answer"][value="${radioValue}"]`);
                if (radioButton) {
                    radioButton.checked = true;
                }
            }
        }
    } else {
        // Для обычных типов заданий загружаем варианты ответов как раньше
        clearAnswers();
        
        if (window.existingAnswers) {
            window.existingAnswers.forEach(answer => {
                addAnswerOption(answer.text, answer.is_correct);
            });
        }
    }
}

function validateForm() {
    const taskType = document.getElementById('task_type').value;
    let isValid = true;
    
    // Очищаем предыдущие ошибки
    clearValidationErrors();
      // Проверяем обязательные поля
    const requiredFields = ['title', 'question_text'];
    requiredFields.forEach(fieldName => {
        const field = document.getElementsByName(fieldName)[0];
        if (!field.value.trim()) {
            showFieldError(field, 'Это поле обязательно для заполнения');
            isValid = false;
        }
    });
      // Проверяем выбор навыков
    const selectedSkills = document.querySelectorAll('input[name="skills"]:checked');
    if (selectedSkills.length === 0) {
        showFieldError(document.getElementById('skills-list'), 'Выберите хотя бы один навык');
        isValid = false;
    }
    
    // Проверяем выбор курса
    const selectedCourse = document.querySelector('input[name="course"]:checked');
    if (!selectedCourse) {
        showFieldError(document.querySelector('.courses-container'), 'Выберите курс для задания');
        isValid = false;
    }// Специфичная валидация для заданий с выбором
    if (['single', 'multiple', 'true_false'].includes(taskType)) {
        if (taskType === 'true_false') {
            // Для верно/неверно проверяем радио-кнопки
            const trueFalseAnswer = document.querySelector('input[name="true_false_answer"]:checked');
            if (!trueFalseAnswer) {
                showFieldError(document.getElementById('true-false-container'), 'Выберите правильный ответ');
                isValid = false;
            }
        } else {
            // Для single и multiple проверяем обычные варианты
            const answerTexts = document.querySelectorAll('input[name="answer_text"]');
            let correctAnswers;
            
            if (taskType === 'single') {
                correctAnswers = document.querySelectorAll('input[name="correct_answer_single"]:checked');
            } else {
                correctAnswers = document.querySelectorAll('input[name="correct_answers_multiple"]:checked');
            }
            
            // Проверяем, что есть варианты ответов
            let hasValidAnswers = false;
            answerTexts.forEach(input => {
                if (input.value.trim()) {
                    hasValidAnswers = true;
                }
            });
            
            if (!hasValidAnswers) {
                showFieldError(document.getElementById('answers-container'), 'Добавьте хотя бы один вариант ответа');
                isValid = false;
            }
            
            // Проверяем, что выбран правильный ответ
            if (correctAnswers.length === 0) {
                showFieldError(document.getElementById('answers-container'), 'Отметьте правильный ответ');
                isValid = false;
            }
            
            // Для single - проверяем что выбран только один правильный ответ
            if (taskType === 'single' && correctAnswers.length > 1) {
                showFieldError(document.getElementById('answers-container'), 'Для типа "Один вариант ответа" может быть выбран только один правильный ответ');
                isValid = false;            }
        }
    }
    
    return isValid;
}

function showFieldError(field, message) {
    field.classList.add('is-invalid');
    
    // Создаем или обновляем сообщение об ошибке
    let errorDiv = field.parentNode.querySelector('.invalid-feedback');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        field.parentNode.appendChild(errorDiv);
    }
    errorDiv.textContent = message;
}

function clearValidationErrors() {
    document.querySelectorAll('.is-invalid').forEach(element => {
        element.classList.remove('is-invalid');
    });
    
    document.querySelectorAll('.invalid-feedback').forEach(element => {
        element.remove();
    });
}

// Инициализация обработчиков для навыков и курсов
function initializeSkillsAndCoursesHandlers() {
    // Поиск навыков
    const skillSearch = document.getElementById('skill-search');
    const skillCourseFilter = document.getElementById('skill-course-filter');
    const clearFiltersBtn = document.getElementById('clear-skill-filters');
    const courseToggles = document.querySelectorAll('.course-toggle');
    
    // Обработчики фильтрации навыков
    if (skillSearch) {
        skillSearch.addEventListener('input', filterSkills);
    }
    
    if (skillCourseFilter) {
        skillCourseFilter.addEventListener('change', filterSkills);
    }
    
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', clearSkillFilters);
    }
    
    // Обработчики для тогглетов курсов
    courseToggles.forEach(toggle => {
        toggle.addEventListener('change', handleCourseToggle);
    });
}

function filterSkills() {
    const searchTerm = document.getElementById('skill-search').value.toLowerCase();
    const courseFilter = document.getElementById('skill-course-filter').value.toLowerCase();
    const skillCards = document.querySelectorAll('.skill-card');
    const courseHeaders = document.querySelectorAll('.skills-container h6');
    const noResultsDiv = document.getElementById('no-skills-found');
    
    let visibleCount = 0;
    
    // Сначала скрываем все заголовки курсов
    courseHeaders.forEach(header => {
        header.style.display = 'none';
        // Скрываем разделители после заголовков
        const nextElement = header.parentElement.nextElementSibling;
        if (nextElement && nextElement.classList.contains('col-12') && nextElement.innerHTML.trim() === '') {
            nextElement.style.display = 'none';
        }
    });
    
    skillCards.forEach(card => {
        const skillName = card.dataset.name;
        const skillCourse = card.dataset.course;
        
        const matchesSearch = !searchTerm || skillName.includes(searchTerm);
        const matchesCourse = !courseFilter || skillCourse === courseFilter;
        
        const cardContainer = card.closest('.col-md-6, .col-lg-4');
        
        if (matchesSearch && matchesCourse) {
            cardContainer.style.display = 'block';
            visibleCount++;
            
            // Показываем заголовок курса для этого навыка
            const courseHeader = findCourseHeaderForSkill(card);
            if (courseHeader) {
                courseHeader.style.display = 'block';
                // Показываем разделитель после заголовка
                const nextElement = courseHeader.parentElement.nextElementSibling;
                if (nextElement && nextElement.classList.contains('col-12') && nextElement.innerHTML.trim() === '') {
                    nextElement.style.display = 'block';
                }
            }
        } else {
            cardContainer.style.display = 'none';
        }
    });
    
    // Показываем/скрываем сообщение "не найдено"
    if (visibleCount === 0) {
        noResultsDiv.style.display = 'block';
    } else {
        noResultsDiv.style.display = 'none';
    }
}

function findCourseHeaderForSkill(skillCard) {
    let currentElement = skillCard.closest('.col-md-6, .col-lg-4');
    
    // Идем назад до заголовка курса
    while (currentElement && currentElement.previousElementSibling) {
        currentElement = currentElement.previousElementSibling;
        if (currentElement.classList.contains('col-12')) {
            const header = currentElement.querySelector('h6');
            if (header) {
                return header;
            }
        }
    }
    
    return null;
}

function clearSkillFilters() {
    document.getElementById('skill-search').value = '';
    document.getElementById('skill-course-filter').value = '';
    filterSkills();
}

function handleCourseToggle(event) {
    const clickedToggle = event.target;
    const allCourseItems = document.querySelectorAll('.course-item');
    
    // Снимаем выделение со всех курсов
    allCourseItems.forEach(item => {
        item.classList.remove('border-primary', 'bg-light');
        item.classList.add('border');
    });
    
    // Выделяем выбранный курс
    if (clickedToggle.checked) {
        const courseItem = clickedToggle.closest('.course-item');
        courseItem.classList.add('border-primary', 'bg-light');
        courseItem.classList.remove('border');
    }
}

// ========== ФУНКЦИИ ПРЕДПРОСМОТРА ==========

function initializePreview() {
    const previewBtn = document.getElementById('preview-task-btn');
    const saveFromPreviewBtn = document.getElementById('save-from-preview');
    
    console.log('Инициализация предпросмотра...');
    console.log('Кнопка предпросмотра:', previewBtn);
    console.log('Кнопка сохранения из предпросмотра:', saveFromPreviewBtn);
    
    if (previewBtn) {
        previewBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('Клик по кнопке предпросмотра');
            showTaskPreview();
        });
    } else {
        console.error('Кнопка предпросмотра не найдена!');
    }
    
    if (saveFromPreviewBtn) {
        saveFromPreviewBtn.addEventListener('click', function() {
            console.log('Сохранение из предпросмотра');
            // Закрываем модальное окно и отправляем форму
            const modal = bootstrap.Modal.getInstance(document.getElementById('preview-modal'));
            if (modal) {
                modal.hide();
            }
            document.querySelector('.task-form').submit();
        });
    }
}

function showTaskPreview() {
    console.log('Показ предпросмотра задания');
    
    try {
        // Собираем данные из формы
        const formData = collectFormData();
        console.log('Данные формы:', formData);
        
        // Валидируем основные поля
        if (!validatePreviewData(formData)) {
            console.log('Валидация не прошла');
            return;
        }
        
        // Генерируем HTML предпросмотра
        const previewHTML = generatePreviewHTML(formData);
        console.log('HTML предпросмотра сгенерирован');
        
        // Показываем предпросмотр в модальном окне
        const previewContent = document.getElementById('preview-content');
        if (previewContent) {
            previewContent.innerHTML = previewHTML;
            console.log('Контент добавлен в модальное окно');
        } else {
            console.error('Контейнер предпросмотра не найден!');
            return;
        }
        
        // Открываем модальное окно
        const modalElement = document.getElementById('preview-modal');
        if (modalElement && typeof bootstrap !== 'undefined') {
            const modal = new bootstrap.Modal(modalElement);
            modal.show();
            console.log('Модальное окно открыто');
        } else {
            console.error('Модальное окно не найдено или Bootstrap не загружен!');
            console.log('modalElement:', modalElement);
            console.log('bootstrap:', typeof bootstrap);
        }
    } catch (error) {
        console.error('Ошибка при показе предпросмотра:', error);
        alert('Произошла ошибка при создании предпросмотра. Проверьте консоль браузера.');
    }
}

function collectFormData() {
    const taskType = document.getElementById('task_type').value;
    const title = document.getElementById('title').value.trim();
    const difficulty = document.getElementById('difficulty').value;
    const questionText = document.getElementById('question_text').value.trim();
    const correctAnswer = document.getElementById('correct_answer').value.trim();
    const explanation = document.getElementById('explanation').value.trim();
    
    // Получаем выбранные навыки
    const selectedSkills = Array.from(document.querySelectorAll('input[name="skills"]:checked')).map(input => ({
        id: input.value,
        name: input.closest('.skill-card').querySelector('.skill-title').textContent.trim()
    }));
    
    // Получаем выбранный курс
    const selectedCourseInput = document.querySelector('input[name="course"]:checked');
    const selectedCourse = selectedCourseInput ? {
        id: selectedCourseInput.value,
        name: selectedCourseInput.closest('.course-item').querySelector('strong').textContent.trim()
    } : null;
    
    // Собираем варианты ответов
    let answers = [];
    if (['single', 'multiple', 'true_false'].includes(taskType)) {
        if (taskType === 'true_false') {
            const trueFalseAnswer = document.querySelector('input[name="true_false_answer"]:checked');
            answers = [
                { text: 'Верно', isCorrect: trueFalseAnswer && trueFalseAnswer.value === 'true' },
                { text: 'Неверно', isCorrect: trueFalseAnswer && trueFalseAnswer.value === 'false' }
            ];
        } else {
            const answerInputs = document.querySelectorAll('#answers-container .answer-item');
            answers = Array.from(answerInputs).map((item, index) => {
                const text = item.querySelector('input[name="answer_text"]').value.trim();
                let isCorrect = false;
                
                if (taskType === 'single') {
                    const correctInput = document.querySelector(`input[name="correct_answer_single"][value="${index}"]`);
                    isCorrect = correctInput && correctInput.checked;
                } else if (taskType === 'multiple') {
                    const correctInput = item.querySelector('input[name="correct_answers_multiple"]');
                    isCorrect = correctInput && correctInput.checked;
                }
                
                return { text, isCorrect };
            }).filter(answer => answer.text !== '');
        }
    }
      return {
        title,
        taskType,
        difficulty,
        questionText,
        correctAnswer,
        explanation,
        selectedSkills,
        selectedCourse,
        answers
    };
}

function validatePreviewData(data) {
    if (!data.title) {
        alert('Введите название задания');
        return false;
    }
    
    if (!data.questionText) {
        alert('Введите формулировку задачи');
        return false;
    }
    
    if (data.selectedSkills.length === 0) {
        alert('Выберите хотя бы один навык');
        return false;
    }
    
    if (!data.selectedCourse) {
        alert('Выберите курс для задания');
        return false;
    }
    
    // Проверяем варианты ответов для заданий с выбором
    if (['single', 'multiple', 'true_false'].includes(data.taskType)) {
        if (data.answers.length === 0) {
            alert('Добавьте варианты ответов');
            return false;
        }
        
        const hasCorrectAnswer = data.answers.some(answer => answer.isCorrect);
        if (!hasCorrectAnswer) {
            alert('Укажите правильный ответ');
            return false;
        }
    }
    
    return true;
}

function generatePreviewHTML(data) {
    const taskTypeLabels = {
        'single': 'Один вариант ответа',
        'multiple': 'Множественный выбор',
        'true_false': 'Верно/Неверно',
        'open': 'Открытый вопрос'
    };
    
    const difficultyLabels = {
        'beginner': 'Начальный',
        'intermediate': 'Средний',
        'advanced': 'Продвинутый'
    };
    
    let html = `
        <div class="task-preview">
            <div class="task-preview-header">
                <h4 class="task-preview-title">${escapeHtml(data.title)}</h4>
                <div class="task-preview-meta">
                    <span class="task-preview-badge type">
                        <i class="fas fa-question-circle me-1"></i>
                        ${taskTypeLabels[data.taskType] || data.taskType}
                    </span>
                    <span class="task-preview-badge difficulty">
                        <i class="fas fa-signal me-1"></i>
                        ${difficultyLabels[data.difficulty] || data.difficulty}
                    </span>
                </div>
            </div>            <div class="task-preview-question">
                <h6><i class="fas fa-question me-2"></i>Вопрос</h6>
                <div class="task-preview-question-text">${renderMarkdown(data.questionText)}</div>
            </div>
    `;
    
    // Добавляем варианты ответов
    if (['single', 'multiple', 'true_false'].includes(data.taskType)) {
        html += `
            <div class="task-preview-answers">
                <h6><i class="fas fa-list me-2"></i>Варианты ответов</h6>
        `;
        
        data.answers.forEach((answer, index) => {
            const inputType = data.taskType === 'single' || data.taskType === 'true_false' ? 'radio' : 'checkbox';
            const correctClass = answer.isCorrect ? ' correct' : '';
            const correctIndicator = answer.isCorrect ? '<span class="task-preview-correct-indicator">✓ Правильный</span>' : '';
            
            // Рендерим Markdown для текста ответа
            const renderedAnswerText = renderMarkdown(answer.text);
            
            html += `
                <div class="task-preview-answer${correctClass}">
                    <input type="${inputType}" class="task-preview-answer-input" disabled>
                    <div class="task-preview-answer-text">${renderedAnswerText}</div>
                    ${correctIndicator}
                </div>
            `;
        });
        
        html += '</div>';
    } else if (data.correctAnswer) {        // Для открытых вопросов показываем правильный ответ
        html += `
            <div class="task-preview-explanation">
                <h6><i class="fas fa-check-circle me-2"></i>Правильный ответ</h6>
                <div class="task-preview-explanation-text">${renderMarkdown(data.correctAnswer)}</div>
            </div>
        `;
    }
    
    // Добавляем объяснение если есть
    if (data.explanation) {
        html += `
            <div class="task-preview-explanation">
                <h6><i class="fas fa-lightbulb me-2"></i>Объяснение</h6>
                <div class="task-preview-explanation-text">${renderMarkdown(data.explanation)}</div>
            </div>
        `;
    }
    
    // Добавляем информацию о навыках и курсе
    html += `
        <div class="task-preview-skills">
            <h6><i class="fas fa-cogs me-2"></i>Связанные навыки</h6>
            <div class="task-preview-skill-tags">
    `;
    
    data.selectedSkills.forEach(skill => {
        html += `<span class="task-preview-skill-tag">${escapeHtml(skill.name)}</span>`;
    });
    
    html += `
            </div>
            <div class="task-preview-course">
                <span class="task-preview-course-tag">
                    <i class="fas fa-book me-2"></i>
                    ${escapeHtml(data.selectedCourse.name)}
                </span>
            </div>
        </div>
    `;
    
    html += '</div>';
    
    return html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========== ФУНКЦИИ MARKDOWN РЕДАКТОРА ==========

function initializeMarkdownEditor() {
    console.log('Инициализация Markdown редактора...');
    
    // Инициализируем главный редактор для текста вопроса
    initializeMainMarkdownEditor();
    
    // Инициализируем редакторы для существующих вариантов ответов
    initializeAnswerMarkdownEditors();
}

function initializeMainMarkdownEditor() {
    const textarea = document.getElementById('question_text');
    const preview = document.getElementById('question_text_preview');
    const toggleBtn = document.getElementById('toggle-markdown-view');
    const toolbar = textarea.closest('.mb-3').querySelector('.markdown-toolbar');
    
    if (!textarea || !preview || !toggleBtn || !toolbar) {
        console.error('Элементы главного Markdown редактора не найдены');
        return;
    }
    
    let isPreviewMode = false;
    
    // Обработчик переключения режима просмотра
    toggleBtn.addEventListener('click', function() {
        isPreviewMode = !isPreviewMode;
        
        if (isPreviewMode) {
            // Переключаемся в режим предпросмотра
            textarea.style.display = 'none';
            preview.style.display = 'block';
            preview.innerHTML = renderMarkdown(textarea.value);
            
            // Деактивируем кнопки форматирования
            toolbar.querySelectorAll('.markdown-btn').forEach(btn => {
                btn.disabled = true;
                btn.classList.add('disabled');
            });
            
            toggleBtn.innerHTML = '<i class="fas fa-edit"></i> Редактировать';
            toggleBtn.classList.remove('btn-outline-primary');
            toggleBtn.classList.add('btn-outline-success');
        } else {
            // Переключаемся в режим редактирования
            textarea.style.display = 'block';
            preview.style.display = 'none';
            
            // Активируем кнопки форматирования
            toolbar.querySelectorAll('.markdown-btn').forEach(btn => {
                btn.disabled = false;
                btn.classList.remove('disabled');
            });
            
            toggleBtn.innerHTML = '<i class="fas fa-eye"></i> Предпросмотр';
            toggleBtn.classList.remove('btn-outline-success');
            toggleBtn.classList.add('btn-outline-primary');
        }
    });
    
    // Обработчики кнопок форматирования
    toolbar.querySelectorAll('.markdown-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            if (!isPreviewMode) {
                const action = this.getAttribute('data-action');
                applyMarkdownFormatting(textarea, action);
            }
        });
    });
    
    // Обновление предпросмотра при изменении текста (с задержкой)
    let updateTimeout;
    textarea.addEventListener('input', function() {
        if (isPreviewMode) {
            clearTimeout(updateTimeout);
            updateTimeout = setTimeout(() => {
                preview.innerHTML = renderMarkdown(textarea.value);
            }, 300);
        }
    });
}

function initializeAnswerMarkdownEditors() {
    // Инициализируем редакторы для существующих вариантов ответов
    document.querySelectorAll('.answer-item').forEach(answerItem => {
        initializeAnswerMarkdownEditor(answerItem);
    });
}

function initializeAnswerMarkdownEditor(answerItem) {
    const textarea = answerItem.querySelector('.markdown-textarea');
    const preview = answerItem.querySelector('.markdown-preview');
    const toggleBtn = answerItem.querySelector('.toggle-answer-markdown');
    const toolbar = answerItem.querySelector('.markdown-toolbar');
    
    if (!textarea || !preview || !toggleBtn || !toolbar) {
        console.log('Элементы редактора ответа не найдены, возможно это старый элемент');
        return;
    }
    
    let isPreviewMode = false;
    
    // Обработчик переключения режима просмотра
    toggleBtn.addEventListener('click', function() {
        isPreviewMode = !isPreviewMode;
        
        if (isPreviewMode) {
            // Переключаемся в режим предпросмотра
            textarea.style.display = 'none';
            preview.style.display = 'block';
            preview.innerHTML = renderMarkdown(textarea.value);
            
            // Деактивируем кнопки форматирования
            toolbar.querySelectorAll('.markdown-btn').forEach(btn => {
                btn.disabled = true;
                btn.classList.add('disabled');
            });
            
            toggleBtn.innerHTML = '<i class="fas fa-edit"></i>';
            toggleBtn.classList.remove('btn-outline-primary');
            toggleBtn.classList.add('btn-outline-success');
        } else {
            // Переключаемся в режим редактирования
            textarea.style.display = 'block';
            preview.style.display = 'none';
            
            // Активируем кнопки форматирования
            toolbar.querySelectorAll('.markdown-btn').forEach(btn => {
                btn.disabled = false;
                btn.classList.remove('disabled');
            });
            
            toggleBtn.innerHTML = '<i class="fas fa-eye"></i>';
            toggleBtn.classList.remove('btn-outline-success');
            toggleBtn.classList.add('btn-outline-primary');
        }
    });
    
    // Обработчики кнопок форматирования
    toolbar.querySelectorAll('.markdown-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            if (!isPreviewMode) {
                const action = this.getAttribute('data-action');
                applyMarkdownFormatting(textarea, action);
            }
        });
    });
    
    // Обновление предпросмотра при изменении текста
    let updateTimeout;
    textarea.addEventListener('input', function() {
        if (isPreviewMode) {
            clearTimeout(updateTimeout);
            updateTimeout = setTimeout(() => {
                preview.innerHTML = renderMarkdown(textarea.value);
            }, 300);
        }
    });
}

function applyMarkdownFormatting(textarea, action) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = textarea.value.substring(start, end);
    const beforeText = textarea.value.substring(0, start);
    const afterText = textarea.value.substring(end);
    
    let newText = '';
    let newCursorPos = start;
    
    switch (action) {
        case 'bold':
            newText = `**${selectedText || 'жирный текст'}**`;
            newCursorPos = selectedText ? start + 2 : start + 2;
            break;
            
        case 'italic':
            newText = `*${selectedText || 'курсив'}*`;
            newCursorPos = selectedText ? start + 1 : start + 1;
            break;
            
        case 'underline':
            newText = `<u>${selectedText || 'подчеркнутый текст'}</u>`;
            newCursorPos = selectedText ? start + 3 : start + 3;
            break;
            
        case 'strikethrough':
            newText = `~~${selectedText || 'зачеркнутый текст'}~~`;
            newCursorPos = selectedText ? start + 2 : start + 2;
            break;
            
        case 'code':
            if (selectedText.includes('\n')) {
                newText = `\`\`\`\n${selectedText || 'код'}\n\`\`\``;
                newCursorPos = selectedText ? start + 4 : start + 4;
            } else {
                newText = `\`${selectedText || 'код'}\``;
                newCursorPos = selectedText ? start + 1 : start + 1;
            }
            break;
            
        case 'h1':
            newText = `# ${selectedText || 'Заголовок 1'}`;
            newCursorPos = selectedText ? start + 2 : start + 2;
            break;
            
        case 'h2':
            newText = `## ${selectedText || 'Заголовок 2'}`;
            newCursorPos = selectedText ? start + 3 : start + 3;
            break;
            
        case 'h3':
            newText = `### ${selectedText || 'Заголовок 3'}`;
            newCursorPos = selectedText ? start + 4 : start + 4;
            break;
            
        case 'ul':
            if (selectedText) {
                newText = selectedText.split('\n').map(line => `- ${line}`).join('\n');
                newCursorPos = start;
            } else {
                newText = '- Элемент списка';
                newCursorPos = start + 2;
            }
            break;
            
        case 'ol':
            if (selectedText) {
                newText = selectedText.split('\n').map((line, index) => `${index + 1}. ${line}`).join('\n');
                newCursorPos = start;
            } else {
                newText = '1. Элемент списка';
                newCursorPos = start + 3;
            }
            break;
            
        case 'blockquote':
            if (selectedText) {
                newText = selectedText.split('\n').map(line => `> ${line}`).join('\n');
                newCursorPos = start;
            } else {
                newText = '> Цитата';
                newCursorPos = start + 2;
            }
            break;
              case 'link':
            // Открываем модальное окно для ссылки
            showLinkModal(textarea, selectedText);
            return; // Не выполняем дальнейшую обработку
            
        case 'image':
            // Открываем модальное окно для изображения
            showImageModal(textarea, selectedText);
            return; // Не выполняем дальнейшую обработку
            
        case 'video':
            // Открываем модальное окно для видео
            showVideoModal(textarea, selectedText);
            return; // Не выполняем дальнейшую обработку
            
        case 'table':
            newText = `| Заголовок 1 | Заголовок 2 | Заголовок 3 |
|-------------|-------------|-------------|
| Ячейка 1    | Ячейка 2    | Ячейка 3    |
| Ячейка 4    | Ячейка 5    | Ячейка 6    |`;
            newCursorPos = start + 2;
            break;
            
        default:
            return;
    }
    
    // Обновляем значение textarea
    textarea.value = beforeText + newText + afterText;
    
    // Устанавливаем курсор
    textarea.focus();
    const endPos = selectedText ? end + (newText.length - selectedText.length) : newCursorPos + (newText.length - (selectedText || 'placeholder').length);
    textarea.setSelectionRange(newCursorPos, endPos);
    
    // Запускаем событие input для обновления предпросмотра
    textarea.dispatchEvent(new Event('input'));
}

function renderMarkdown(text) {
    if (typeof marked === 'undefined') {
        console.error('Библиотека marked.js не загружена');
        return text;
    }
    
    try {
        // Настраиваем marked для безопасного рендеринга
        marked.setOptions({
            breaks: true,
            gfm: true,
            sanitize: false, // Позволяем HTML теги
            smartLists: true,
            smartypants: true
        });
        
        return marked.parse(text);
    } catch (error) {
        console.error('Ошибка при рендеринге Markdown:', error);
        return text;
    }
}

// ========== ФУНКЦИИ МОДАЛЬНЫХ ОКОН MARKDOWN РЕДАКТОРА ==========

let currentMarkdownTextarea = null;
let currentSelectedText = '';

function showLinkModal(textarea, selectedText) {
    currentMarkdownTextarea = textarea;
    currentSelectedText = selectedText;
    
    // Очищаем форму
    document.getElementById('link-url').value = '';
    document.getElementById('link-text').value = selectedText || '';
    document.getElementById('link-new-window').checked = true;
    
    // Показываем модальное окно
    const modal = new bootstrap.Modal(document.getElementById('link-modal'));
    modal.show();
}

function showImageModal(textarea, selectedText) {
    currentMarkdownTextarea = textarea;
    currentSelectedText = selectedText;
    
    // Очищаем форму
    document.getElementById('image-url').value = '';
    document.getElementById('image-alt').value = selectedText || '';
    document.getElementById('image-title').value = '';
    document.getElementById('image-width').value = '';
    document.getElementById('image-height').value = '';
    
    // Показываем модальное окно
    const modal = new bootstrap.Modal(document.getElementById('image-modal'));
    modal.show();
}

function showVideoModal(textarea, selectedText) {
    currentMarkdownTextarea = textarea;
    currentSelectedText = selectedText;
    
    // Очищаем форму
    document.getElementById('video-url').value = '';
    document.getElementById('video-title').value = selectedText || '';
    document.getElementById('video-width').value = '560';
    document.getElementById('video-height').value = '315';
    
    // Показываем модальное окно
    const modal = new bootstrap.Modal(document.getElementById('video-modal'));
    modal.show();
}

function insertLink() {
    const url = document.getElementById('link-url').value.trim();
    const text = document.getElementById('link-text').value.trim();
    const newWindow = document.getElementById('link-new-window').checked;
    
    if (!url) {
        alert('Введите URL ссылки');
        return;
    }
    
    // Валидация URL
    try {
        new URL(url);
    } catch {
        alert('Введите корректный URL (начинающийся с http:// или https://)');
        return;
    }
    
    const linkText = text || currentSelectedText || url;
    let markdown;
    
    if (newWindow) {
        // Для открытия в новом окне используем HTML
        markdown = `<a href="${url}" target="_blank" rel="noopener noreferrer">${linkText}</a>`;
    } else {
        // Обычная Markdown ссылка
        markdown = `[${linkText}](${url})`;
    }
    
    insertMarkdownAtCursor(currentMarkdownTextarea, markdown);
    
    // Закрываем модальное окно
    const modal = bootstrap.Modal.getInstance(document.getElementById('link-modal'));
    modal.hide();
}

function insertImage() {
    const url = document.getElementById('image-url').value.trim();
    const alt = document.getElementById('image-alt').value.trim();
    const title = document.getElementById('image-title').value.trim();
    const width = document.getElementById('image-width').value.trim();
    const height = document.getElementById('image-height').value.trim();
    
    if (!url) {
        alert('Введите URL изображения');
        return;
    }
    
    // Валидация URL
    try {
        new URL(url);
    } catch {
        alert('Введите корректный URL изображения');
        return;
    }
    
    const altText = alt || currentSelectedText || 'Изображение';
    let markdown;
    
    if (width || height || title) {
        // Используем HTML для дополнительных атрибутов
        let htmlAttributes = `src="${url}" alt="${altText}"`;
        
        if (title) {
            htmlAttributes += ` title="${title}"`;
        }
        
        if (width) {
            htmlAttributes += ` width="${width}"`;
        }
        
        if (height) {
            htmlAttributes += ` height="${height}"`;
        }
        
        markdown = `<img ${htmlAttributes}>`;
    } else {
        // Обычная Markdown разметка
        if (title) {
            markdown = `![${altText}](${url} "${title}")`;
        } else {
            markdown = `![${altText}](${url})`;
        }
    }
    
    insertMarkdownAtCursor(currentMarkdownTextarea, markdown);
    
    // Закрываем модальное окно
    const modal = bootstrap.Modal.getInstance(document.getElementById('image-modal'));
    modal.hide();
}

function insertVideo() {
    const url = document.getElementById('video-url').value.trim();
    const title = document.getElementById('video-title').value.trim();
    const width = document.getElementById('video-width').value.trim() || '560';
    const height = document.getElementById('video-height').value.trim() || '315';
    
    if (!url) {
        alert('Введите URL видео');
        return;
    }
    
    // Валидация URL
    try {
        new URL(url);
    } catch {
        alert('Введите корректный URL видео');
        return;
    }
    
    let markdown = '';
    
    // Определяем тип видео и генерируем соответствующий код
    if (url.includes('youtube.com') || url.includes('youtu.be')) {
        // YouTube видео
        const videoId = extractYouTubeId(url);
        if (videoId) {
            markdown = `<iframe width="${width}" height="${height}" src="https://www.youtube.com/embed/${videoId}" frameborder="0" allowfullscreen${title ? ` title="${title}"` : ''}></iframe>`;
        } else {
            alert('Не удалось извлечь ID видео из ссылки YouTube');
            return;
        }
    } else if (url.includes('vimeo.com')) {
        // Vimeo видео
        const videoId = extractVimeoId(url);
        if (videoId) {
            markdown = `<iframe width="${width}" height="${height}" src="https://player.vimeo.com/video/${videoId}" frameborder="0" allowfullscreen${title ? ` title="${title}"` : ''}></iframe>`;
        } else {
            alert('Не удалось извлечь ID видео из ссылки Vimeo');
            return;
        }
    } else if (url.match(/\.(mp4|webm|ogg)$/i)) {
        // Прямая ссылка на видеофайл
        markdown = `<video width="${width}" height="${height}" controls${title ? ` title="${title}"` : ''}>
    <source src="${url}" type="video/${url.split('.').pop().toLowerCase()}">
    Ваш браузер не поддерживает видео тег.
</video>`;
    } else {
        // Общая ссылка на видео
        const linkText = title || currentSelectedText || 'Видео';
        markdown = `[🎥 ${linkText}](${url})`;
    }
    
    insertMarkdownAtCursor(currentMarkdownTextarea, markdown);
    
    // Закрываем модальное окно
    const modal = bootstrap.Modal.getInstance(document.getElementById('video-modal'));
    modal.hide();
}

function extractYouTubeId(url) {
    const regex = /(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/;
    const match = url.match(regex);
    return match ? match[1] : null;
}

function extractVimeoId(url) {
    const regex = /vimeo\.com\/(?:.*\/)?(\d+)/;
    const match = url.match(regex);
    return match ? match[1] : null;
}

function insertMarkdownAtCursor(textarea, markdown) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const beforeText = textarea.value.substring(0, start);
    const afterText = textarea.value.substring(end);
    
    // Обновляем значение textarea
    textarea.value = beforeText + markdown + afterText;
    
    // Устанавливаем курсор в конец вставленного текста
    const newPosition = start + markdown.length;
    textarea.focus();
    textarea.setSelectionRange(newPosition, newPosition);
    
    // Запускаем событие input для обновления предпросмотра
    textarea.dispatchEvent(new Event('input'));
}

// Инициализация обработчиков модальных окон
document.addEventListener('DOMContentLoaded', function() {
    // Обработчики кнопок вставки
    const insertLinkBtn = document.getElementById('insert-link-btn');
    const insertImageBtn = document.getElementById('insert-image-btn');
    const insertVideoBtn = document.getElementById('insert-video-btn');
    
    if (insertLinkBtn) {
        insertLinkBtn.addEventListener('click', insertLink);
    }
    
    if (insertImageBtn) {
        insertImageBtn.addEventListener('click', insertImage);
    }
    
    if (insertVideoBtn) {
        insertVideoBtn.addEventListener('click', insertVideo);
    }
    
    // Обработчики Enter в модальных окнах
    document.getElementById('link-form').addEventListener('submit', function(e) {
        e.preventDefault();
        insertLink();
    });
    
    document.getElementById('image-form').addEventListener('submit', function(e) {
        e.preventDefault();
        insertImage();
    });
    
    document.getElementById('video-form').addEventListener('submit', function(e) {
        e.preventDefault();
        insertVideo();
    });
});
