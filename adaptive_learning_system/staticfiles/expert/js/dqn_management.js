// AdaptiveLearn Expert Module - DQN Management JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initDQNManagement();
});

// Основная инициализация DQN управления
function initDQNManagement() {
    console.log('🧠 DQN Management: Initializing...');
    
    initStudentSelection();
    initFeedbackControls();
    initDatasetModal();
    initScrollAnimations();
}

// Инициализация выбора студентов
function initStudentSelection() {
    const studentCards = document.querySelectorAll('.student-card');
    
    studentCards.forEach(card => {
        card.addEventListener('click', function() {
            const studentId = this.dataset.studentId;
            if (studentId) {
                // Добавляем эффект выбора
                studentCards.forEach(c => c.classList.remove('selected'));
                this.classList.add('selected');
                
                // Показываем индикатор загрузки
                showLoadingIndicator('Загружаем данные студента...');
                
                // Переходим к детальной странице студента
                window.location.href = `/expert/dqn/student/${studentId}/`;
            }
        });
        
        // Эффекты наведения
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-6px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            if (!this.classList.contains('selected')) {
                this.style.transform = 'translateY(0) scale(1)';
            }
        });
    });
}

// Инициализация контролов обратной связи
function initFeedbackControls() {
    const feedbackPairs = document.querySelectorAll('.recommendation-pair');
    
    feedbackPairs.forEach((pair, index) => {
        const pairId = pair.dataset.recommendationId;
        if (!pairId || pair.classList.contains('has-feedback')) return;
        
        const feedbackControls = pair.querySelector('.feedback-controls');
        if (!feedbackControls) return;
        
        // Создаем контролы для этой пары
        createFeedbackControls(feedbackControls, pairId, index);
    });
}

// Создание контролов обратной связи для конкретной пары
function createFeedbackControls(container, recommendationId, index) {
    let selectedType = null;
    let selectedStrength = null;
    
    // Кнопки типа обратной связи
    const typeButtons = container.querySelectorAll('.feedback-type-btn');
    typeButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const type = this.dataset.type;
            
            // Убираем активность у всех кнопок типа
            typeButtons.forEach(b => b.classList.remove('active'));
            
            // Активируем текущую кнопку
            this.classList.add('active');
            selectedType = type;
            
            // Показываем селектор силы
            const strengthSelector = container.querySelector('.strength-selector');
            if (strengthSelector) {
                strengthSelector.style.display = 'block';
                strengthSelector.classList.add('fade-in-up');
            }
            
            updateSaveButtonState();
        });
    });
    
    // Кнопки силы
    const strengthButtons = container.querySelectorAll('.strength-btn');
    strengthButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const strength = this.dataset.strength;
            
            // Убираем активность у всех кнопок силы
            strengthButtons.forEach(b => b.classList.remove('active'));
            
            // Активируем текущую кнопку
            this.classList.add('active');
            selectedStrength = strength;
            
            updateSaveButtonState();
        });
    });
    
    // Кнопка сохранения
    const saveBtn = container.querySelector('.save-feedback-btn');
    if (saveBtn) {
        saveBtn.addEventListener('click', function() {
            if (!selectedType || !selectedStrength) {
                showNotification('Выберите тип и силу обратной связи', 'warning');
                return;
            }
            
            const comment = container.querySelector('.comment-input')?.value || '';
            
            saveFeedback(recommendationId, selectedType, selectedStrength, comment, container);
        });
    }
    
    // Функция обновления состояния кнопки сохранения
    function updateSaveButtonState() {
        if (saveBtn) {
            const isReady = selectedType && selectedStrength;
            saveBtn.disabled = !isReady;
            
            if (isReady) {
                saveBtn.style.opacity = '1';
                saveBtn.style.cursor = 'pointer';
            } else {
                saveBtn.style.opacity = '0.6';
                saveBtn.style.cursor = 'not-allowed';
            }
        }
    }
    
    // Инициализируем состояние кнопки
    updateSaveButtonState();
}

// Сохранение обратной связи
async function saveFeedback(recommendationId, feedbackType, strength, comment, container) {
    try {
        // Показываем индикатор загрузки
        const saveBtn = container.querySelector('.save-feedback-btn');
        const originalText = saveBtn.textContent;
        saveBtn.textContent = 'Сохраняем...';
        saveBtn.disabled = true;
        
        const response = await fetch('/expert/dqn/feedback/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                recommendation_id: recommendationId,
                feedback_type: feedbackType,
                strength: strength,
                comment: comment
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Успешно сохранено
            showNotification('Разметка сохранена успешно!', 'success');
            
            // Обновляем UI
            const pair = container.closest('.recommendation-pair');
            pair.classList.add('has-feedback');
            
            // Заменяем контролы на информацию о сохраненной разметке
            showExistingFeedback(container, feedbackType, strength, comment, result.reward_value);
            
            // Анимация успеха
            pair.style.background = 'rgba(16, 185, 129, 0.05)';
            setTimeout(() => {
                pair.style.background = '';
            }, 2000);
            
        } else {
            throw new Error(result.message || 'Ошибка сохранения');
        }
        
    } catch (error) {
        console.error('Error saving feedback:', error);
        showNotification(`Ошибка сохранения: ${error.message}`, 'error');
        
        // Восстанавливаем кнопку
        const saveBtn = container.querySelector('.save-feedback-btn');
        saveBtn.textContent = originalText;
        saveBtn.disabled = false;
    }
}

// Показ информации о существующей обратной связи
function showExistingFeedback(container, type, strength, comment, rewardValue) {
    const typeText = type === 'positive' ? 'Положительная' : 'Отрицательная';
    const strengthText = {
        'low': 'Низкая',
        'medium': 'Средняя',
        'high': 'Высокая'
    }[strength];
    
    const feedbackHtml = `
        <div class="existing-feedback">
            <div class="existing-feedback-header">
                <i class="fas fa-check-circle"></i>
                Разметка сохранена
            </div>
            <div class="existing-feedback-details">
                <strong>Тип:</strong> ${typeText}<br>
                <strong>Сила:</strong> ${strengthText}<br>
                <strong>Награда:</strong> ${rewardValue > 0 ? '+' : ''}${rewardValue}<br>
                ${comment ? `<strong>Комментарий:</strong> ${comment}` : ''}
            </div>
        </div>
    `;
    
    container.innerHTML = feedbackHtml;
    container.classList.add('has-feedback');
}

// Инициализация модального окна датасета
function initDatasetModal() {
    const viewDatasetBtn = document.getElementById('viewDatasetBtn');
    const datasetModal = document.getElementById('datasetModal');
    const startTrainingBtn = document.getElementById('startTrainingBtn');
    
    if (viewDatasetBtn) {
        viewDatasetBtn.addEventListener('click', function() {
            showDatasetModal();
        });
    }
    
    if (startTrainingBtn) {
        startTrainingBtn.addEventListener('click', function() {
            // Пока это заглушка
            showNotification('Функция дообучения DQN будет реализована позже', 'info');
        });
    }
}

// Показ модального окна датасета
async function showDatasetModal() {
    try {
        const response = await fetch('/expert/dqn/dataset/');
        const html = await response.text();
        
        // Создаем модальное окно
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'datasetModal';
        modal.innerHTML = `
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    ${html}
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Показываем модальное окно
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
        
        // Удаляем модальное окно после закрытия
        modal.addEventListener('hidden.bs.modal', function() {
            modal.remove();
        });
        
    } catch (error) {
        console.error('Error loading dataset:', error);
        showNotification('Ошибка загрузки датасета', 'error');
    }
}

// Инициализация анимаций при прокрутке
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in-up');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // Наблюдаем за парами рекомендаций
    document.querySelectorAll('.recommendation-pair').forEach(pair => {
        observer.observe(pair);
    });
    
    // Наблюдаем за карточками студентов
    document.querySelectorAll('.student-card').forEach(card => {
        observer.observe(card);
    });
}

// Утилитарные функции

// Получение CSRF токена
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
           document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
}

// Показ уведомлений
function showNotification(message, type = 'info') {
    if (typeof ExpertUtils !== 'undefined' && ExpertUtils.showNotification) {
        ExpertUtils.showNotification(message, type);
    } else {
        // Fallback для случая, если ExpertUtils недоступен
        alert(message);
    }
}

// Показ индикатора загрузки
function showLoadingIndicator(message = 'Загрузка...') {
    // Создаем overlay с индикатором загрузки
    const overlay = document.createElement('div');
    overlay.id = 'loadingOverlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(255, 255, 255, 0.9);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        z-index: 9999;
        font-family: inherit;
    `;
    
    overlay.innerHTML = `
        <div style="text-align: center;">
            <div style="width: 40px; height: 40px; border: 4px solid #e2e8f0; border-top: 4px solid #3b82f6; border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 1rem;"></div>
            <div style="font-size: 1.1rem; font-weight: 600; color: #1e293b;">${message}</div>
        </div>
    `;
    
    // Добавляем стили анимации
    const style = document.createElement('style');
    style.textContent = `
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(style);
    
    document.body.appendChild(overlay);
    
    // Автоматически убираем через 10 секунд
    setTimeout(() => {
        if (overlay.parentNode) {
            overlay.remove();
        }
    }, 10000);
}

// Убираем индикатор загрузки
function hideLoadingIndicator() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.remove();
    }
}

// Вспомогательные функции для работы с уровнями освоения навыков
const DQNUtils = {
    // Форматирование уровня освоения навыка
    formatMasteryLevel: function(level) {
        if (level >= 0.8) return { text: 'Высокий', class: 'mastery-high' };
        if (level >= 0.5) return { text: 'Средний', class: 'mastery-medium' };
        return { text: 'Низкий', class: 'mastery-low' };
    },
    
    // Форматирование Q-value
    formatQValue: function(qValue) {
        return qValue.toFixed(4);
    },
    
    // Получение иконки для типа задания
    getTaskTypeIcon: function(taskType) {
        const icons = {
            'single': 'fas fa-dot-circle',
            'multiple': 'fas fa-check-square',
            'true_false': 'fas fa-question-circle'
        };
        return icons[taskType] || 'fas fa-question';
    },
    
    // Получение цвета для уровня сложности
    getDifficultyColor: function(difficulty) {
        const colors = {
            'beginner': 'difficulty-beginner',
            'intermediate': 'difficulty-intermediate', 
            'advanced': 'difficulty-advanced'
        };
        return colors[difficulty] || 'difficulty-beginner';
    }
};

// Экспортируем утилиты
window.DQNUtils = DQNUtils;
