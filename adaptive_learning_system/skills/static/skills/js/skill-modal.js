/**
 * Модуль для работы с модальным окном создания/редактирования навыка
 */

/**
 * Инициализирует обработчики для модальных окон создания/редактирования навыка
 */
function initializeModalHandlers() {
    const skillModal = document.getElementById('skill-modal');
    // Используем querySelectorAll для поддержки нескольких кнопок
    const createBtns = document.querySelectorAll('#create-skill-btn');
    const renameBtns = document.querySelectorAll('#rename-skill-btn');
    const cancelBtn = document.getElementById('modal-cancel');
    const closeBtn = document.getElementById('modal-close');
    const modalTitle = document.getElementById('modal-title');
    const form = document.getElementById('skill-form');
    
    // Обработчик для кнопки создания навыка
    createBtns.forEach(createBtn => {
        createBtn.addEventListener('click', function() {
            // Настройка формы для создания
            modalTitle.textContent = 'Создание нового навыка';
            document.getElementById('edit-mode').value = 'create';
            form.reset();
            document.getElementById('form-skill-id').value = ''; // Пустой ID для нового навыка
            
            // Скрываем поле update_courses
            document.getElementById('update-courses').value = '';
            
            // Сбрасываем чекбоксы курсов
            resetCourseCheckboxes();
            
            // Показываем модальное окно
            skillModal.classList.remove('hidden');
        });
    });
    
    // Обработчик для кнопки переименования/редактирования навыка
    renameBtns.forEach(renameBtn => {
        renameBtn.addEventListener('click', function() {
            // Настройка формы для редактирования
            const skillId = renameBtn.dataset.skillId;
            const skillName = renameBtn.dataset.skillName;
            const isBase = renameBtn.dataset.isBase === 'true';
            
            modalTitle.textContent = 'Редактирование навыка';
            document.getElementById('edit-mode').value = 'edit';
            document.getElementById('form-skill-id').value = skillId;
            document.getElementById('form-name').value = skillName;
            document.getElementById('form-is-base').value = isBase ? 'true' : 'false';
            
            // Устанавливаем значение update_courses для отправки информации о курсах
            document.getElementById('update-courses').value = 'true';
            
            // Сначала сбрасываем все чекбоксы
            resetCourseCheckboxes();
            
            // Загружаем данные о навыке, включая курсы
            loadSkillCourses(skillId);
            
            // Показываем модальное окно
            skillModal.classList.remove('hidden');
        });
    });
    
    // Обработчик для кнопки отмены
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function() {
            skillModal.classList.add('hidden');
        });
    }
    
    // Обработчик для кнопки закрытия (X)
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            skillModal.classList.add('hidden');
        });
    }
    
    // Клик вне модального окна закрывает его
    skillModal.addEventListener('click', function(event) {
        if (event.target === skillModal) {
            skillModal.classList.add('hidden');
        }
    });
}

/**
 * Сбрасывает состояние чекбоксов курсов
 */
function resetCourseCheckboxes() {
    const courseCheckboxes = document.querySelectorAll('#skill-form input[name="courses"]');
    courseCheckboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
}

/**
 * Загрузка информации о курсах для модального окна редактирования навыка
 */
function loadSkillCourses(skillId) {
    // Добавим визуальную обратную связь, что идёт загрузка данных
    const courseSection = document.querySelector('#skill-form .bg-gray-50');
    if (courseSection) {
        courseSection.style.opacity = "0.5"; // Используем прямое присваивание стиля вместо класса
        courseSection.insertAdjacentHTML('beforeend', '<div id="courses-loader" class="absolute inset-0 flex items-center justify-center"><i class="fas fa-circle-notch fa-spin text-blue-600"></i></div>');
    }
    
    fetch(`/api/skills/${skillId}/courses/`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Ошибка запроса: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Удаляем индикатор загрузки
            if (courseSection) {
                courseSection.style.opacity = "1";
                const loader = document.getElementById('courses-loader');
                if (loader) loader.remove();
            }
            
            // Устанавливаем чекбоксы курсов
            if (data.courses && Array.isArray(data.courses)) {
                data.courses.forEach(courseId => {
                    const checkbox = document.querySelector(`#skill-form input[value="${courseId}"]`);
                    if (checkbox) {
                        checkbox.checked = true;
                    }
                });
            }
        })
        .catch(error => {
            // Удаляем индикатор загрузки в случае ошибки
            if (courseSection) {
                courseSection.style.opacity = "1";
                const loader = document.getElementById('courses-loader');
                if (loader) loader.remove();
                
                // Добавляем сообщение об ошибке в раздел с курсами
                courseSection.insertAdjacentHTML('beforeend', 
                    '<div class="error-message p-2 mt-2 bg-red-100 text-red-700 rounded text-sm">' +
                    'Не удалось загрузить курсы. Пожалуйста, попробуйте позже.</div>');
                
                setTimeout(() => {
                    const errorMsg = courseSection.querySelector('.error-message');
                    if (errorMsg) errorMsg.remove();
                }, 5000); // Удаляем сообщение через 5 секунд
            }
        });
}

// Экспортируем функции в глобальную область видимости
window.initializeModalHandlers = initializeModalHandlers;
window.loadSkillCourses = loadSkillCourses;
window.resetCourseCheckboxes = resetCourseCheckboxes;
