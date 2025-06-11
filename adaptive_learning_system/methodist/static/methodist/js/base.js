/**
 * Общий JavaScript для панели методиста
 */

document.addEventListener('DOMContentLoaded', function() {
    // Подсветка активной ссылки в навигации
    highlightActiveNavLink();
    
    // Общие обработчики для модальных окон Bootstrap
    initializeBootstrapModals();
    
    // Автоматическое скрытие уведомлений Django messages
    autoDismissMessages();
});

function highlightActiveNavLink() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    navLinks.forEach(link => {
        link.classList.remove('active');
        
        const linkPath = new URL(link.href).pathname;
        
        // Точное соответствие или соответствие начала пути
        if (currentPath === linkPath || (linkPath !== '/methodist/' && currentPath.startsWith(linkPath))) {
            link.classList.add('active');
            link.style.backgroundColor = 'rgba(255, 255, 255, 0.2)';
            link.style.borderRadius = '4px';
        }
    });
}

function initializeBootstrapModals() {
    // Автоматически фокусируемся на первом input в модальных окнах
    document.addEventListener('shown.bs.modal', function(event) {
        const modal = event.target;
        const firstInput = modal.querySelector('input:not([type="hidden"]), textarea, select');
        if (firstInput) {
            firstInput.focus();
        }
    });
    
    // Сброс форм при закрытии модальных окон
    document.addEventListener('hidden.bs.modal', function(event) {
        const modal = event.target;
        const forms = modal.querySelectorAll('form');
        forms.forEach(form => {
            if (form.hasAttribute('data-reset-on-close')) {
                form.reset();
                // Очистка ошибок валидации
                form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
                form.querySelectorAll('.invalid-feedback').forEach(el => el.remove());
            }
        });
    });
}

function autoDismissMessages() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    
    alerts.forEach(alert => {
        // Автоматически скрываем success и info сообщения через 5 секунд
        if (alert.classList.contains('alert-success') || alert.classList.contains('alert-info')) {
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.style.opacity = '0';
                    alert.style.transform = 'translateY(-20px)';
                    setTimeout(() => {
                        alert.remove();
                    }, 300);
                }
            }, 5000);
        }
        
        // Warning и error сообщения остаются до ручного закрытия
    });
}

// Глобальные утилиты
window.MethodistUtils = {
    // Показать уведомление
    showNotification: function(message, type = 'success', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 1055; max-width: 350px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);';
        notification.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-${getIconForType(type)} me-2"></i>
                <span>${message}</span>
                <button type="button" class="btn-close ms-auto" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.classList.remove('show');
                    setTimeout(() => notification.remove(), 150);
                }
            }, duration);
        }
        
        function getIconForType(type) {
            const icons = {
                'success': 'check-circle',
                'danger': 'exclamation-circle',
                'warning': 'exclamation-triangle',
                'info': 'info-circle'
            };
            return icons[type] || 'info-circle';
        }
    },
    
    // Подтверждение действия
    confirmAction: function(message, callback) {
        if (confirm(message)) {
            callback();
        }
    },
    
    // Блокировка формы во время отправки
    lockForm: function(form) {
        const submitButtons = form.querySelectorAll('button[type="submit"], input[type="submit"]');
        const inputs = form.querySelectorAll('input, textarea, select, button');
        
        submitButtons.forEach(btn => {
            btn.disabled = true;
            const originalText = btn.textContent;
            btn.dataset.originalText = originalText;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Сохранение...';
        });
        
        inputs.forEach(input => {
            if (!input.matches('button[type="submit"], input[type="submit"]')) {
                input.disabled = true;
            }
        });
        
        return function unlock() {
            submitButtons.forEach(btn => {
                btn.disabled = false;
                btn.textContent = btn.dataset.originalText || 'Сохранить';
            });
            
            inputs.forEach(input => {
                input.disabled = false;
            });
        };
    }
};
