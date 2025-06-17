// Профиль студента - JavaScript функциональность

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация графика активности
    initActivityChart();
    
    // Анимация прогресс-баров
    animateProgressBars();
    
    // Инициализация интерактивных элементов
    initInteractiveElements();
});

function initActivityChart() {
    const canvas = document.getElementById('activityChart');
    if (!canvas || typeof dailyStats === 'undefined') return;
    
    const ctx = canvas.getContext('2d');
    
    // Подготовка данных
    const labels = dailyStats.map(stat => {
        const date = new Date(stat.date);
        return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
    });
    
    const attempts = dailyStats.map(stat => stat.total_attempts);
    const accuracy = dailyStats.map(stat => stat.accuracy);
    
    // Размеры графика
    const width = canvas.width;
    const height = canvas.height;
    const padding = 40;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;
    
    // Очистка canvas
    ctx.clearRect(0, 0, width, height);
    
    // Настройка стиля
    ctx.font = '12px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    
    // Максимальные значения для масштабирования
    const maxAttempts = Math.max(...attempts, 1);
    const maxAccuracy = 100;
    
    // Рисуем сетку
    ctx.strokeStyle = '#e0e0e0';
    ctx.lineWidth = 1;
    
    for (let i = 0; i <= 5; i++) {
        const y = padding + (chartHeight / 5) * i;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(width - padding, y);
        ctx.stroke();
        
        // Подписи оси Y (количество попыток)
        ctx.fillStyle = '#666';
        ctx.textAlign = 'right';
        ctx.fillText(Math.round(maxAttempts - (maxAttempts / 5) * i), padding - 10, y);
    }
    
    // Рисуем столбцы (количество попыток)
    ctx.fillStyle = 'rgba(33, 150, 243, 0.6)';
    const barWidth = chartWidth / dailyStats.length * 0.6;
    
    attempts.forEach((value, index) => {
        const x = padding + (chartWidth / dailyStats.length) * index + (chartWidth / dailyStats.length - barWidth) / 2;
        const barHeight = (value / maxAttempts) * chartHeight;
        const y = padding + chartHeight - barHeight;
        
        ctx.fillRect(x, y, barWidth, barHeight);
    });
    
    // Рисуем линию точности
    ctx.strokeStyle = '#ff5722';
    ctx.lineWidth = 3;
    ctx.beginPath();
    
    accuracy.forEach((value, index) => {
        const x = padding + (chartWidth / dailyStats.length) * index + (chartWidth / dailyStats.length) / 2;
        const y = padding + chartHeight - (value / maxAccuracy) * chartHeight;
        
        if (index === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
        
        // Точки на линии
        ctx.fillStyle = '#ff5722';
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, 2 * Math.PI);
        ctx.fill();
    });
    
    ctx.stroke();
    
    // Подписи оси X (даты)
    ctx.fillStyle = '#666';
    ctx.textAlign = 'center';
    ctx.font = '10px Arial';
    
    labels.forEach((label, index) => {
        if (index % 3 === 0) { // Показываем каждую третью дату
            const x = padding + (chartWidth / dailyStats.length) * index + (chartWidth / dailyStats.length) / 2;
            ctx.fillText(label, x, height - 10);
        }
    });
    
    // Легенда
    ctx.font = '12px Arial';
    ctx.textAlign = 'left';
    
    // Столбцы
    ctx.fillStyle = 'rgba(33, 150, 243, 0.6)';
    ctx.fillRect(padding, 10, 15, 10);
    ctx.fillStyle = '#333';
    ctx.fillText('Количество попыток', padding + 20, 15);
    
    // Линия
    ctx.strokeStyle = '#ff5722';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(padding + 150, 15);
    ctx.lineTo(padding + 165, 15);
    ctx.stroke();
    ctx.fillText('Точность (%)', padding + 170, 15);
}

function animateProgressBars() {
    const progressBars = document.querySelectorAll('.progress-fill, .metric-fill');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const progressBar = entry.target;
                const width = progressBar.style.width;
                progressBar.style.width = '0%';
                progressBar.style.transition = 'width 1s ease-out';
                
                setTimeout(() => {
                    progressBar.style.width = width;
                }, 100);
                
                observer.unobserve(progressBar);
            }
        });
    }, { threshold: 0.5 });
    
    progressBars.forEach(bar => observer.observe(bar));
}

function initInteractiveElements() {
    // Добавляем интерактивность к карточкам навыков
    const skillCards = document.querySelectorAll('.skill-card');
    skillCards.forEach(card => {
        card.addEventListener('click', function() {
            // Можно добавить модальное окно с деталями навыка
            console.log('Клик по навыку:', this.querySelector('h3').textContent);
        });
    });
    
    // Добавляем интерактивность к попыткам решений
    const attemptItems = document.querySelectorAll('.attempt-item');
    attemptItems.forEach(item => {
        item.addEventListener('click', function() {
            // Можно добавить модальное окно с деталями попытки
            console.log('Клик по попытке:', this.querySelector('h4').textContent);
        });
    });
    
    // Анимация появления карточек при скролле
    const cards = document.querySelectorAll('.stat-card, .skill-card, .course-card, .attempt-item');
    
    const cardObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                setTimeout(() => {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }, index * 100);
                cardObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });
    
    cards.forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        cardObserver.observe(card);
    });
}

// Функция для обновления статистики (можно вызывать через AJAX)
function updateStats(newStats) {
    const statElements = {
        totalAttempts: document.querySelector('.stat-content h3'),
        accuracy: document.querySelectorAll('.stat-content h3')[1],
        learningStreak: document.querySelectorAll('.stat-content h3')[2],
        level: document.querySelectorAll('.stat-content h3')[3]
    };
    
    if (statElements.totalAttempts) {
        statElements.totalAttempts.textContent = newStats.totalAttempts;
    }
    if (statElements.accuracy) {
        statElements.accuracy.textContent = newStats.accuracy + '%';
    }
    if (statElements.learningStreak) {
        statElements.learningStreak.textContent = newStats.learningStreak;
    }
    if (statElements.level) {
        statElements.level.textContent = newStats.level;
    }
}

// Экспорт функций для использования в других файлах
window.ProfileJS = {
    updateStats: updateStats,
    initActivityChart: initActivityChart
};
