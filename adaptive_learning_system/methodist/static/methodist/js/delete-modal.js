/**
 * Модуль для работы с модальным окном удаления навыка
 */

/**
 * Функция для инициализации обработчиков удаления навыка
 */
function initializeDeleteHandlers() {
    const deleteSkillBtn = document.getElementById('delete-skill-btn');
    const confirmDeleteModal = document.getElementById('confirm-delete-modal');
    const cancelDeleteBtn = document.getElementById('cancel-delete');
    
    if (deleteSkillBtn) {
        deleteSkillBtn.addEventListener('click', function() {
            const skillId = deleteSkillBtn.dataset.skillId;
            const skillName = deleteSkillBtn.dataset.skillName;
            
            // Проверяем, что ID навыка получен корректно
            if (!skillId) {
                console.error('Не удалось получить ID навыка для удаления');
                return;
            }
            
            // Устанавливаем данные в модальное окно
            document.getElementById('delete-skill-id').value = skillId;
            document.getElementById('delete-skill-name').textContent = skillName || 'выбранный навык';
            
            // Показываем модальное окно подтверждения
            confirmDeleteModal.classList.remove('hidden');
        });
    } else {
        console.warn('Кнопка удаления навыка не найдена в DOM');
    }
    
    if (cancelDeleteBtn) {
        cancelDeleteBtn.addEventListener('click', function() {
            confirmDeleteModal.classList.add('hidden');
        });
    }
    
    // Клик вне модального окна закрывает его
    if (confirmDeleteModal) {
        confirmDeleteModal.addEventListener('click', function(event) {
            if (event.target === confirmDeleteModal) {
                confirmDeleteModal.classList.add('hidden');
            }
        });
    }
    
    // Добавляем обработчик для кнопки X в модальном окне
    const closeDeleteBtn = document.querySelector('#confirm-delete-modal .close-btn');
    if (closeDeleteBtn) {
        closeDeleteBtn.addEventListener('click', function() {
            confirmDeleteModal.classList.add('hidden');
        });
    }
}

/**
 * Общий метод для закрытия модальных окон
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('hidden');
    }
}

// Экспортируем функции в глобальную область видимости
window.initializeDeleteHandlers = initializeDeleteHandlers;
window.closeModal = closeModal;
