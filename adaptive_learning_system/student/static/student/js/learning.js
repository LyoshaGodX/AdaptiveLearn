/*
СОБЫТИЯ ЛОГИРОВАНИЯ ДЛЯ ОТСЛЕЖИВАНИЯ UX ПОТОКА:

🎯 ИНИЦИАЛИЗАЦИЯ - Загрузка страницы
🚀 [СОБЫТИЕ 1] - Нажатие кнопки "Отправить ответ"
📊 [СОБЫТИЕ 2] - Начало отрисовки правильного ответа
✅ [СОБЫТИЕ 2] - Завершение отрисовки правильного ответа
⏳ [СОБЫТИЕ 3] - Появление надписи "Подбираем новое задание..." (через 2.5 сек)
🔄 [СОБЫТИЕ 3] - Создание кнопки ожидания
🔍 ПРОВЕРКА - Запуск периодической проверки статуса
📡 ПРОВЕРКА - Ответы от сервера на проверки
🎉 ГОТОВО - Рекомендация готова
🎯 [СОБЫТИЕ 4] - Показ кнопки "Начать новое задание"
🕐 [СОБЫТИЕ 4] - Фолбэк по таймауту (30 сек)

Все события содержат timestamp для точного отслеживания времени выполнения.
*/

// JavaScript для страницы обучения

document.addEventListener('DOMContentLoaded', function() {
    console.log('🎯 Инициализация страницы обучения', {
        timestamp: new Date().toISOString(),
        url: window.location.href,
        userAgent: navigator.userAgent
    });
    
    initLearningPage();
});

function initLearningPage() {
    setupAnswerSelection();
    setupFormSubmission();
    setupTimer();
}

// Настройка выбора ответов
function setupAnswerSelection() {
    const answerOptions = document.querySelectorAll('.answer-option');
    const taskType = document.getElementById('task-type')?.value;
    
    answerOptions.forEach(option => {
        option.addEventListener('click', function() {
            const input = this.querySelector('input[type="radio"], input[type="checkbox"]');
            
            if (taskType === 'multiple') {
                // Для множественного выбора
                input.checked = !input.checked;
                this.classList.toggle('selected', input.checked);
            } else {
                // Для одиночного выбора
                answerOptions.forEach(opt => opt.classList.remove('selected'));
                input.checked = true;
                this.classList.add('selected');
            }
            
            updateSubmitButton();
        });
    });
}

// Обновление состояния кнопки отправки
function updateSubmitButton() {
    const submitBtn = document.getElementById('submit-answer-btn');
    const selectedAnswers = document.querySelectorAll('input[name="answer"]:checked');
    
    if (selectedAnswers.length > 0) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Отправить ответ';
    } else {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Выберите ответ';
    }
}

// Настройка отправки формы
function setupFormSubmission() {
    const form = document.getElementById('task-answer-form');
    if (!form) return;
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        submitAnswer();
    });
}

// Отправка ответа
function submitAnswer() {
    const form = document.getElementById('task-answer-form');
    const submitBtn = document.getElementById('submit-answer-btn');
    const selectedAnswers = document.querySelectorAll('input[name="answer"]:checked');
    
    if (selectedAnswers.length === 0) {
        showError('Выберите хотя бы один вариант ответа');
        return;
    }
    
    // СОБЫТИЕ 1: Нажатие на кнопку "Отправить ответ"
    console.log('🚀 [СОБЫТИЕ 1] Нажата кнопка "Отправить ответ"', {
        timestamp: new Date().toISOString(),
        selectedAnswersCount: selectedAnswers.length,
        selectedAnswerIds: Array.from(selectedAnswers).map(a => a.value)
    });
      // 1. СРАЗУ скрываем кнопку и показываем загрузку
    submitBtn.style.display = 'none';
    
    // Показываем индикатор загрузки сразу
    showLoadingState();
    
    // Подготавливаем данные формы
    const formData = new FormData(form);
    // Добавляем время начала задания
    const startTime = document.getElementById('task-started-at')?.value || new Date().toISOString();
    formData.append('start_time', startTime);
    
    // Отправляем запрос для сохранения в БД
    fetch(window.location.href, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())    .then(data => {        if (data.success) {
            // Скрываем состояние загрузки
            hideLoadingState();
            
            // 2. СРАЗУ показываем результат
            console.log('📊 [СОБЫТИЕ 2] Начинаем отрисовку правильного ответа', {
                timestamp: new Date().toISOString(),
                isCorrect: data.is_correct,
                timeSpent: data.time_spent,
                correctAnswerIds: data.correct_answer_ids
            });
            
            highlightAnswers(data);
            showResultMessage(data);
            
            console.log('✅ [СОБЫТИЕ 2] Правильный ответ отрисован', {
                timestamp: new Date().toISOString()
            });
              // 3. ПОСЛЕ показа результата (дать время изучить результат) показываем ожидание и запускаем проверку
            setTimeout(() => {
                console.log('⏳ [СОБЫТИЕ 3] Появляется надпись "Подбираем новое задание..."', {
                    timestamp: new Date().toISOString(),
                    delayFromResult: '1500ms'
                });
                
                showWaitingButton();
                checkRecommendationStatusPeriodically();
            }, 1500); // Даем пользователю время изучить результат (1.5 секунды)
              } else {
            // Если ошибка, скрываем загрузку и возвращаем кнопку
            hideLoadingState();
            submitBtn.style.display = 'block';
            showError(data.error || 'Произошла ошибка');
        }
    })    .catch(error => {
        // Если ошибка, скрываем загрузку и возвращаем кнопку
        hideLoadingState();
        submitBtn.style.display = 'block';
        console.error('Ошибка:', error);
        showError('Произошла ошибка при отправке ответа');
    });
}

// Показ сообщения о результате
function showResultMessage(data) {
    const submitSection = document.querySelector('.submit-section');
    const resultDiv = document.createElement('div');
    resultDiv.className = `result-message ${data.is_correct ? 'correct' : 'incorrect'}`;
    resultDiv.innerHTML = `
        <div class="result-content">
            <i class="fas fa-${data.is_correct ? 'check-circle' : 'times-circle'}"></i>
            <span>${data.is_correct ? 'Правильно!' : 'Неправильно'}</span>
            <small>Время решения: ${data.time_spent} сек.</small>
        </div>
    `;
    
    submitSection.insertBefore(resultDiv, submitSection.firstChild);
    
    // Плавное появление с задержкой
    setTimeout(() => {
        resultDiv.style.opacity = '1';
        resultDiv.style.transform = 'translateY(0) scale(1)';
    }, 150);
    
    // Эффект привлечения внимания
    setTimeout(() => {
        resultDiv.style.animation = 'pulse 0.6s ease-in-out';
    }, 600);
}

// Подсветка ответов
function highlightAnswers(data) {
    const answerOptions = document.querySelectorAll('.answer-option');
    const correctIds = data.correct_answer_ids || [];
    
    answerOptions.forEach(option => {
        const answerId = parseInt(option.dataset.answerId);
        const input = option.querySelector('input[type="radio"], input[type="checkbox"]');
        
        option.style.pointerEvents = 'none';
        input.disabled = true;
        option.classList.remove('selected');
        
        if (correctIds.includes(answerId)) {
            option.classList.add('correct');
        } else if (input.checked) {
            option.classList.add('incorrect');
        }
    });
}

// Показ кнопки ожидания
function showWaitingButton() {
    console.log('🔄 [СОБЫТИЕ 3] Создаем кнопку "Подбираем новое задание..."', {
        timestamp: new Date().toISOString()
    });
    
    const submitSection = document.querySelector('.submit-section');
    
    // Создаем новую кнопку ожидания
    const waitingBtn = document.createElement('button');
    waitingBtn.type = 'button';
    waitingBtn.id = 'waiting-btn';
    waitingBtn.className = 'waiting-recommendation-btn';
    waitingBtn.disabled = true;
    waitingBtn.innerHTML = '<span class="spinner"></span> Подбираем новое задание...';
    
    submitSection.appendChild(waitingBtn);
    
    console.log('✅ [СОБЫТИЕ 3] Надпись "Подбираем новое задание..." отображена', {
        timestamp: new Date().toISOString()
    });
}

// Замена кнопки на состояние ожидания
function replaceSubmitButtonWithWaiting() {
    const submitBtn = document.getElementById('submit-answer-btn');
    
    submitBtn.innerHTML = '<span class="spinner"></span> Подбираем новое задание...';
    submitBtn.disabled = true;
    submitBtn.className = 'waiting-recommendation-btn';
}

// Показ готовности нового задания
function showNewTaskReady() {
    console.log('🎯 [СОБЫТИЕ 4] Начинаем показ кнопки "Начать новое задание"', {
        timestamp: new Date().toISOString()
    });
    
    const waitingBtn = document.getElementById('waiting-btn') || 
                      document.querySelector('.waiting-recommendation-btn');
    
    if (waitingBtn) {
        waitingBtn.textContent = 'Начать новое задание';
        waitingBtn.className = 'new-task-btn';
        waitingBtn.disabled = false;
        waitingBtn.id = 'new-task-btn';
        
        // Добавляем анимацию "готово"
        waitingBtn.style.animation = 'pulse 0.5s ease-in-out';
        
        waitingBtn.addEventListener('click', function(e) {
            e.preventDefault();
            loadNewTask();
        });
        
        console.log('✅ [СОБЫТИЕ 4] Кнопка "Начать новое задание" отображена и активна', {
            timestamp: new Date().toISOString()
        });
    } else {
        console.warn('⚠️ [СОБЫТИЕ 4] Кнопка ожидания не найдена для замены', {
            timestamp: new Date().toISOString()
        });
    }
}

// Фолбэк для показа нового задания (если таймаут)
function showNewTaskReadyFallback() {
    console.log('🕐 [СОБЫТИЕ 4] Таймаут ожидания - показываем кнопку "Начать новое задание" (фолбэк)', {
        timestamp: new Date().toISOString(),
        reason: 'timeout_60_seconds'
    });
    
    const waitingBtn = document.getElementById('waiting-btn') || 
                      document.querySelector('.waiting-recommendation-btn');
    
    if (waitingBtn) {
        waitingBtn.textContent = 'Начать новое задание';
        waitingBtn.className = 'new-task-btn';
        waitingBtn.disabled = false;
        waitingBtn.id = 'new-task-btn';
        
        waitingBtn.addEventListener('click', function(e) {
            e.preventDefault();
            loadNewTask();
        });
        
        console.log('✅ [СОБЫТИЕ 4] Кнопка "Начать новое задание" отображена (фолбэк)', {
            timestamp: new Date().toISOString()
        });
    } else {
        console.warn('⚠️ [СОБЫТИЕ 4] Кнопка ожидания не найдена для замены (фолбэк)', {
            timestamp: new Date().toISOString()
        });
    }
}

// Замена кнопки на "Новое задание" (для случаев без ожидания рекомендации)
function replaceSubmitButtonWithNewTask() {
    const submitBtn = document.getElementById('submit-answer-btn');
    
    submitBtn.textContent = 'Новое задание';
    submitBtn.className = 'new-task-btn';
    submitBtn.disabled = false;
    
    const newBtn = submitBtn.cloneNode(true);
    submitBtn.parentNode.replaceChild(newBtn, submitBtn);
    
    newBtn.addEventListener('click', function(e) {
        e.preventDefault();
        loadNewTask();
    });
}

// Загрузка нового задания
function loadNewTask() {
    const btn = document.querySelector('.new-task-btn');
    
    btn.innerHTML = '<span class="spinner"></span> Загружаем новое задание...';
    btn.disabled = true;
    
    // Запрашиваем новое задание через API
    fetch('/student/api/new-task/', {
        method: 'GET',
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.redirect_url) {
            // Переходим к новому заданию
            window.location.href = data.redirect_url;
        } else {
            showError(data.error || 'Не удалось получить новое задание');
            btn.disabled = false;
            btn.textContent = 'Новое задание';
        }
    })
    .catch(error => {
        console.error('Ошибка при загрузке нового задания:', error);
        showError('Произошла ошибка при загрузке нового задания');
        btn.disabled = false;
        btn.textContent = 'Новое задание';
    });
}

// Таймер
function setupTimer() {
    const timerElement = document.getElementById('task-timer');
    if (!timerElement) return;
    
    let startTime = Date.now();
    
    function updateTimer() {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        
        timerElement.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    
    updateTimer();
    setInterval(updateTimer, 1000);
}

// Показ ошибки
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.style.cssText = `
        position: fixed; top: 20px; right: 20px; z-index: 10000;
        max-width: 400px; padding: 1rem; border-radius: 8px;
        background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;
    `;
    errorDiv.innerHTML = `
        <button type="button" style="float: right; background: none; border: none; font-size: 1.2rem; cursor: pointer;" onclick="this.parentElement.remove()">&times;</button>
        ${message}
    `;
    
    document.body.appendChild(errorDiv);
    
    setTimeout(() => {
        if (errorDiv.parentElement) {
            errorDiv.remove();
        }
    }, 5000);
}

// Получение CSRF токена
function getCsrfToken() {
    const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
    return csrfInput ? csrfInput.value : '';
}

// Настройка таймера
function setupTimer() {
    const timerElement = document.getElementById('task-timer');
    if (!timerElement) return;
    
    let startTime = Date.now();
    
    function updateTimer() {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;
        
        timerElement.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
    
    updateTimer();
    setInterval(updateTimer, 1000);
}

// Показ экрана загрузки
function showLoading(message = 'Загрузка...') {
    let overlay = document.getElementById('loading-overlay');
    
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-content">
                <div class="loading-spinner"></div>
                <div class="loading-text">${message}</div>
            </div>
        `;
        document.body.appendChild(overlay);
    } else {
        overlay.querySelector('.loading-text').textContent = message;
    }
    
    overlay.classList.add('active');
}

// Скрытие экрана загрузки
function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
}

// Показ состояния загрузки после отправки ответа
function showLoadingState() {
    console.log('⏳ Показываем состояние загрузки ответа', {
        timestamp: new Date().toISOString()
    });
    
    const submitSection = document.querySelector('.submit-section');
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'answer-loading';
    loadingDiv.className = 'answer-loading';
    loadingDiv.innerHTML = `
        <div class="loading-content">
            <div class="loading-spinner"></div>
            <div class="loading-text">Проверяем ваш ответ...</div>
        </div>
    `;
    
    submitSection.appendChild(loadingDiv);
    
    // Плавное появление
    setTimeout(() => {
        loadingDiv.style.opacity = '1';
        loadingDiv.style.transform = 'translateY(0)';
    }, 100);
}

// Скрытие состояния загрузки
function hideLoadingState() {
    const loadingDiv = document.getElementById('answer-loading');
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

// Markdown рендерер (простой)
function renderMarkdown(text) {
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/__(.*?)__/g, '<u>$1</u>')
        .replace(/~~(.*?)~~/g, '<del>$1</del>')
        .replace(/^# (.*$)/gm, '<h1>$1</h1>')
        .replace(/^## (.*$)/gm, '<h2>$1</h2>')
        .replace(/^### (.*$)/gm, '<h3>$1</h3>')
        .replace(/!\[([^\]]*)\]\(([^\)]+)\)/g, '<img src="$2" alt="$1" />')
        .replace(/\[([^\]]+)\]\(([^\)]+)\)/g, '<a href="$2">$1</a>')
        .replace(/\n/g, '<br>');
}

// Инициализация Markdown в вопросе
document.addEventListener('DOMContentLoaded', function() {
    const questionText = document.querySelector('.question-text');
    if (questionText && questionText.dataset.markdown) {
        questionText.innerHTML = renderMarkdown(questionText.textContent);
    }
});

// Периодическая проверка статуса рекомендации
function checkRecommendationStatusPeriodically() {    console.log('🔍 Запускаем периодическую проверку статуса рекомендации', {
        timestamp: new Date().toISOString(),
        checkInterval: '2 seconds',
        timeout: '60 seconds'
    });
    
    let checkCount = 0;
    
    const checkInterval = setInterval(() => {
        checkCount++;
        console.log(`🔄 Проверка статуса рекомендации #${checkCount}`, {
            timestamp: new Date().toISOString()
        });
        
        const url = '/student/api/recommendation/status/';
        
        fetch(url, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        })        .then(response => response.json())        .then(data => {
            console.log(`📡 Ответ от сервера на проверку #${checkCount}:`, {
                timestamp: new Date().toISOString(),
                success: data.success,
                recommendationReady: data.recommendation_ready,
                generating: data.generating,
                data: data
            });
            
            if (data.success && data.recommendation_ready && !data.generating) {
                console.log('🎉 Рекомендация готова! Показываем кнопку нового задания', {
                    timestamp: new Date().toISOString(),
                    checksPerformed: checkCount
                });
                
                clearInterval(checkInterval);
                showNewTaskReady();
            } else if (data.success && data.generating) {
                console.log('⏳ Генерация рекомендации в процессе...', {
                    timestamp: new Date().toISOString(),
                    checkNumber: checkCount
                });
            }
        })
        .catch(error => {
            console.error(`❌ Ошибка при проверке статуса рекомендации #${checkCount}:`, {
                timestamp: new Date().toISOString(),
                error: error
            });
        });
    }, 2000); // Проверяем каждые 2 секунды (было 3)
      // Останавливаем проверку через 60 секунд (таймаут) - увеличили с 30 до 60 сек
    setTimeout(() => {
        console.log('⏰ Таймаут периодической проверки (60 сек)', {
            timestamp: new Date().toISOString(),
            totalChecks: checkCount
        });
        
        clearInterval(checkInterval);
        showNewTaskReadyFallback();
    }, 60000);
}
