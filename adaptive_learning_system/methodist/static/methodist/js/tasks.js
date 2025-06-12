/**
 * JavaScript для страницы списка заданий
 */

document.addEventListener('DOMContentLoaded', function() {
    // Исправление z-index для dropdown меню в карточках заданий
    initializeTaskCardDropdowns();
    
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

// Функция для исправления z-index dropdown меню в карточках заданий
function initializeTaskCardDropdowns() {
    const taskCards = document.querySelectorAll('.task-card');
    
    taskCards.forEach(card => {
        const dropdown = card.querySelector('.dropdown');
        const dropdownToggle = card.querySelector('.dropdown-toggle');
        const dropdownMenu = card.querySelector('.dropdown-menu');
        
        if (dropdown && dropdownToggle && dropdownMenu) {
            // События Bootstrap dropdown
            dropdownToggle.addEventListener('show.bs.dropdown', function(e) {
                console.log('Dropdown показывается для карточки задания');
                
                // Поднимаем z-index карточки
                card.style.setProperty('z-index', '1060', 'important');
                card.classList.add('dropdown-open');
                
                // Убеждаемся, что меню имеет правильный z-index
                dropdownMenu.style.setProperty('z-index', '1061', 'important');
                dropdownMenu.style.setProperty('position', 'absolute', 'important');
            });
            
            dropdownToggle.addEventListener('hide.bs.dropdown', function(e) {
                console.log('Dropdown скрывается для карточки задания');
                
                // Возвращаем z-index
                card.style.removeProperty('z-index');
                card.classList.remove('dropdown-open');
                dropdownMenu.style.removeProperty('z-index');
            });
            
            // Предотвращение закрытия dropdown при клике на элементы формы
            dropdownMenu.addEventListener('click', function(e) {
                // Если кликнули на кнопку удаления - позволяем продолжить
                if (e.target.type === 'submit' || e.target.closest('button[type="submit"]')) {
                    return true;
                }
                
                // Иначе предотвращаем закрытие
                e.stopPropagation();
            });
        }
        
        // При наведении на карточку поднимаем её z-index
        card.addEventListener('mouseenter', function() {
            if (!this.classList.contains('dropdown-open')) {
                this.style.setProperty('z-index', '5', 'important');
            }
        });
        
        card.addEventListener('mouseleave', function() {
            if (!this.classList.contains('dropdown-open')) {
                this.style.removeProperty('z-index');
            }
        });
    });
}
