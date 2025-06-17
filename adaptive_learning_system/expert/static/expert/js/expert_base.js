// AdaptiveLearn Expert Module - Base JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация базовых компонентов эксперта
    initExpertComponents();
    initAnalyticsDashboard();
    initModelStatusMonitoring();
    initExpertNotifications();
});

// Инициализация основных компонентов эксперта
function initExpertComponents() {
    console.log('🎯 Expert Module: Initializing components...');

    // Добавляем анимации для карточек статистики
    const statCards = document.querySelectorAll('.stat-card');
    statCards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
        card.classList.add('fade-in-up');
    });

    // Улучшенные tooltips для навигации
    const navLinks = document.querySelectorAll('.nav-link-compact');
    navLinks.forEach(link => {
        link.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px) scale(1.02)';
        });
        
        link.addEventListener('mouseleave', function() {
            if (!this.classList.contains('active')) {
                this.style.transform = 'translateY(0) scale(1)';
            }
        });
    });

    // Улучшенные эффекты для аватара пользователя
    const userAvatar = document.querySelector('.user-avatar');
    if (userAvatar) {
        userAvatar.addEventListener('click', function() {
            this.style.transform = 'scale(1.1) rotate(5deg)';
            setTimeout(() => {
                this.style.transform = 'scale(1) rotate(0deg)';
            }, 200);
        });
    }
}

// Инициализация дашборда аналитики
function initAnalyticsDashboard() {
    console.log('📊 Expert Module: Initializing analytics dashboard...');

    // Анимация для прогресс-баров
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(bar => {
        const targetWidth = bar.style.width || bar.getAttribute('aria-valuenow') + '%';
        bar.style.width = '0%';
        
        setTimeout(() => {
            bar.style.width = targetWidth;
        }, 300);
    });

    // Интерактивные карточки аналитики
    const analyticsCards = document.querySelectorAll('.analytics-card');
    analyticsCards.forEach(card => {
        card.addEventListener('click', function() {
            this.classList.add('clicked');
            setTimeout(() => {
                this.classList.remove('clicked');
            }, 200);
        });
    });
}

// Мониторинг статуса моделей
function initModelStatusMonitoring() {
    console.log('🧠 Expert Module: Initializing model status monitoring...');

    const modelStatuses = document.querySelectorAll('.model-status');
    modelStatuses.forEach(status => {
        const statusType = status.classList.contains('active') ? 'active' : 
                          status.classList.contains('training') ? 'training' : 'inactive';
        
        // Добавляем индикатор для активных моделей
        if (statusType === 'active') {
            const indicator = document.createElement('span');
            indicator.className = 'status-indicator';
            indicator.innerHTML = '●';
            status.prepend(indicator);
        }
        
        // Добавляем анимацию для тренирующихся моделей
        if (statusType === 'training') {
            status.classList.add('pulse-animation');
        }
    });
}

// Система уведомлений для эксперта
function initExpertNotifications() {
    console.log('🔔 Expert Module: Initializing notification system...');

    // Автоматическое скрытие сообщений через 5 секунд
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                alert.style.opacity = '0';
                alert.style.transform = 'translateY(-20px)';
                setTimeout(() => {
                    alert.remove();
                }, 300);
            }
        }, 5000);
    });
}

// Утилитарные функции для экспертов
const ExpertUtils = {
    // Форматирование чисел для статистики
    formatNumber: function(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    },

    // Расчет процента успешности
    calculateSuccessRate: function(correct, total) {
        return total > 0 ? Math.round((correct / total) * 100) : 0;
    },

    // Форматирование времени
    formatDuration: function(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;

        if (hours > 0) {
            return `${hours}ч ${minutes}м`;
        } else if (minutes > 0) {
            return `${minutes}м ${secs}с`;
        } else {
            return `${secs}с`;
        }
    },

    // Показ всплывающих уведомлений
    showNotification: function(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = `
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.15);
        `;
        
        notification.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-${type === 'success' ? 'check-circle' : 
                                  type === 'error' ? 'exclamation-circle' : 
                                  type === 'warning' ? 'exclamation-triangle' : 
                                  'info-circle'} me-2"></i>
                <span>${message}</span>
                <button type="button" class="btn-close ms-auto" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Автоматическое удаление через 4 секунды
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 4000);
    }
};

// Добавляем CSS анимации
const style = document.createElement('style');
style.textContent = `
    .fade-in-up {
        animation: fadeInUp 0.6s ease-out forwards;
    }

    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .pulse-animation {
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }

    .clicked {
        transform: scale(0.98) !important;
        transition: transform 0.1s ease;
    }

    .status-indicator {
        color: #10b981;
        font-size: 0.6rem;
        margin-right: 0.25rem;
        animation: blink 1.5s infinite;
    }

    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0.5; }
    }

    .nav-link-compact {
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .user-avatar {
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        cursor: pointer;
    }

    .stat-card {
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
`;
document.head.appendChild(style);

// Экспорт утилит для использования в других модулях
window.ExpertUtils = ExpertUtils;
