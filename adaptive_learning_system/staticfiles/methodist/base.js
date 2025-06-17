// Базовый JavaScript для приложения методиста
document.addEventListener('DOMContentLoaded', function() {
    initializeDropdownFixes();
    initializeCardHoverEffects();
    initializeMessageAutoHide();
});

// Исправления для dropdown меню
function initializeDropdownFixes() {
    // Добавляем обработчики для всех dropdown в карточках
    const dropdowns = document.querySelectorAll('.card .dropdown');
    
    dropdowns.forEach(dropdown => {
        const toggle = dropdown.querySelector('.dropdown-toggle');
        const menu = dropdown.querySelector('.dropdown-menu');
        
        if (toggle && menu) {
            // При открытии dropdown
            toggle.addEventListener('shown.bs.dropdown', function() {
                const card = this.closest('.card');
                if (card) {
                    card.style.zIndex = '1051';
                }
            });
            
            // При закрытии dropdown
            toggle.addEventListener('hidden.bs.dropdown', function() {
                const card = this.closest('.card');
                if (card) {
                    card.style.zIndex = '';
                }
            });
            
            // Предотвращаем закрытие при клике на элементы формы
            menu.addEventListener('click', function(e) {
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON') {
                    e.stopPropagation();
                }
            });
        }
    });
}

// Улучшение эффектов при наведении на карточки
function initializeCardHoverEffects() {
    const cards = document.querySelectorAll('.card');
    
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            // Если dropdown не открыт, поднимаем карточку
            const dropdown = this.querySelector('.dropdown');
            if (!dropdown || !dropdown.classList.contains('show')) {
                this.style.zIndex = '1';
            }
        });
        
        card.addEventListener('mouseleave', function() {
            // Если dropdown не открыт, возвращаем z-index
            const dropdown = this.querySelector('.dropdown');
            if (!dropdown || !dropdown.classList.contains('show')) {
                this.style.zIndex = '';
            }
        });
    });
}

// Автоматическое скрытие сообщений
function initializeMessageAutoHide() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    
    alerts.forEach(alert => {
        // Автоматически скрываем через 5 секунд
        setTimeout(() => {
            if (alert && alert.parentNode) {
                const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                bsAlert.close();
            }
        }, 5000);
        
        // Добавляем прогресс-бар для показа времени до закрытия
        addProgressBar(alert);
    });
}

// Добавление прогресс-бара к сообщениям
function addProgressBar(alert) {
    const progressBar = document.createElement('div');
    progressBar.className = 'alert-progress';
    progressBar.style.cssText = `
        position: absolute;
        bottom: 0;
        left: 0;
        height: 3px;
        background-color: rgba(255,255,255,0.3);
        width: 100%;
        animation: alertProgress 5s linear forwards;
    `;
    
    // Добавляем CSS анимацию, если её нет
    if (!document.querySelector('#alert-progress-style')) {
        const style = document.createElement('style');
        style.id = 'alert-progress-style';
        style.textContent = `
            @keyframes alertProgress {
                from { width: 100%; }
                to { width: 0%; }
            }
            .alert {
                position: relative;
                overflow: hidden;
            }
        `;
        document.head.appendChild(style);
    }
    
    alert.style.position = 'relative';
    alert.style.overflow = 'hidden';
    alert.appendChild(progressBar);
}

// Утилиты для работы с CSRF токенами
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

// Универсальная функция для AJAX запросов
function makeAjaxRequest(url, data, method = 'POST') {
    const formData = new FormData();
    
    // Добавляем CSRF токен
    formData.append('csrfmiddlewaretoken', getCSRFToken());
    
    // Добавляем данные
    for (const [key, value] of Object.entries(data)) {
        if (Array.isArray(value)) {
            value.forEach(item => formData.append(key, item));
        } else {
            formData.append(key, value);
        }
    }
    
    return fetch(url, {
        method: method,
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
        }
    });
}

// Показ уведомлений
function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-${getIconForType(type)} me-2"></i>
            <span>${message}</span>
            <button type="button" class="btn-close ms-auto" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Найдем контейнер для сообщений или создадим его
    let messagesContainer = document.querySelector('.messages-container');
    if (!messagesContainer) {
        messagesContainer = document.createElement('div');
        messagesContainer.className = 'messages-container';
        document.querySelector('main').insertBefore(messagesContainer, document.querySelector('main').firstChild);
    }
    
    messagesContainer.appendChild(alertDiv);
    
    // Автоматически скрываем через 5 секунд
    setTimeout(() => {
        if (alertDiv && alertDiv.parentNode) {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alertDiv);
            bsAlert.close();
        }
    }, 5000);
}

function getIconForType(type) {
    switch (type) {
        case 'success': return 'check-circle';
        case 'error':
        case 'danger': return 'exclamation-circle';
        case 'warning': return 'exclamation-triangle';
        default: return 'info-circle';
    }
}

// Экспорт функций для использования в других скриптах
window.AdaptiveLearning = {
    makeAjaxRequest,
    showNotification,
    getCSRFToken
};
