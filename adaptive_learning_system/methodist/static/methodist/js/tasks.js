/**
 * JavaScript для страницы списка заданий
 */

document.addEventListener('DOMContentLoaded', function() {
    // Автоматическая отправка формы при изменении фильтров
    const filterSelects = document.querySelectorAll('#course, #difficulty, #skill');
    filterSelects.forEach(select => {
        select.addEventListener('change', function() {
            this.form.submit();
        });
    });

    // Подтверждение удаления задания
    const deleteButtons = document.querySelectorAll('form[action*="delete"] button[type="submit"]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const taskTitle = this.closest('.card').querySelector('.card-header h6').textContent.trim();
            if (!confirm(`Вы уверены, что хотите удалить задание "${taskTitle}"?\n\nЭто действие нельзя отменить.`)) {
                e.preventDefault();
            }
        });
    });

    // Улучшение UX для карточек заданий
    const taskCards = document.querySelectorAll('.task-card');
    taskCards.forEach(card => {
        // Добавляем эффект hover
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });

        // Клик по карточке для редактирования (исключая dropdown)
        card.addEventListener('click', function(e) {
            // Игнорируем клики по dropdown и его элементам
            if (e.target.closest('.dropdown') || e.target.closest('form')) {
                return;
            }
            
            const editLink = this.querySelector('a[href*="edit"]');
            if (editLink) {
                window.location.href = editLink.href;
            }
        });
    });

    // Подсветка активных фильтров
    highlightActiveFilters();

    // Показать/скрыть кнопку "Очистить фильтры"
    toggleClearFiltersButton();
});

function highlightActiveFilters() {
    const urlParams = new URLSearchParams(window.location.search);
    
    // Подсвечиваем активные фильтры
    ['course', 'difficulty', 'skill', 'search'].forEach(param => {
        const value = urlParams.get(param);
        if (value) {
            const element = document.getElementById(param);
            if (element) {
                element.style.borderColor = '#007bff';
                element.style.boxShadow = '0 0 0 0.2rem rgba(0, 123, 255, 0.25)';
            }
        }
    });
}

function toggleClearFiltersButton() {
    const urlParams = new URLSearchParams(window.location.search);
    const hasFilters = Array.from(urlParams.keys()).some(key => 
        ['course', 'difficulty', 'skill', 'search'].includes(key) && urlParams.get(key)
    );
    
    const clearButton = document.querySelector('a[href*="methodist_tasks"]:not([href*="create"])');
    if (clearButton && hasFilters) {
        clearButton.innerHTML = '<i class="fas fa-times"></i> Очистить';
        clearButton.classList.add('btn-warning');
        clearButton.classList.remove('btn-outline-secondary');
    }
}

// Функция для показа уведомлений (если Django messages не используются)
function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 1050; max-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Автоматически скрываем через 5 секунд
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}
