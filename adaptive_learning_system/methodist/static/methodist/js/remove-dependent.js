/**
 * Модуль для удаления зависимых навыков
 */

document.addEventListener('DOMContentLoaded', function() {
    let currentRemovalData = null; // Храним данные для удаления
    
    // Обрабатываем клики по кнопкам удаления зависимых навыков
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('remove-dependent-btn')) {
            e.preventDefault();
            
            const skillId = e.target.getAttribute('data-skill-id');
            const dependentId = e.target.getAttribute('data-dependent-id');
            const dependentBadge = e.target.closest('.dependent-badge');
            const dependentName = dependentBadge ? dependentBadge.querySelector('span').textContent : 'Неизвестный навык';
            
            if (!skillId || !dependentId) {
                alert('Ошибка: не удается определить навык или зависимость');
                return;
            }
            
            // Находим название навыка
            const selectedSkillElement = document.querySelector('.skill-list-item.active .skill-name');
            const skillName = selectedSkillElement ? selectedSkillElement.textContent : 'Выбранный навык';
            
            // Сохраняем данные для удаления
            currentRemovalData = {
                skillId: skillId,
                dependentId: dependentId,
                button: e.target
            };
            
            // Заполняем модальное окно
            document.getElementById('remove-dependent-name').textContent = dependentName;
            document.getElementById('remove-dependent-skill-name').textContent = skillName;
            
            // Показываем модальное окно
            const modal = document.getElementById('remove-dependent-modal');
            if (modal) {
                modal.classList.add('show');
                document.body.style.overflow = 'hidden';
            }
        }
    });
    
    // Обработчик кнопки подтверждения удаления
    const confirmBtn = document.getElementById('remove-dependent-confirm');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', function() {
            if (currentRemovalData) {
                removeDependent(currentRemovalData.skillId, currentRemovalData.dependentId, currentRemovalData.button);
                
                // Закрываем модальное окно
                const modal = document.getElementById('remove-dependent-modal');
                if (modal) {
                    modal.classList.remove('show');
                    document.body.style.overflow = '';
                }
                
                currentRemovalData = null;
            }
        });    }
    
    // Обработчик кнопки закрытия (X)
    const closeBtn = document.getElementById('remove-dependent-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            const modal = document.getElementById('remove-dependent-modal');
            if (modal) {
                modal.classList.remove('show');
                document.body.style.overflow = '';
            }
            currentRemovalData = null;
        });
    }
    
    // Обработчик кнопки отмены
    const cancelBtn = document.getElementById('remove-dependent-cancel');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function() {
            const modal = document.getElementById('remove-dependent-modal');
            if (modal) {
                modal.classList.remove('show');
                document.body.style.overflow = '';
            }
            currentRemovalData = null;
        });
    }
    
    // Обработчик закрытия модального окна по клику на overlay
    const modal = document.getElementById('remove-dependent-modal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                modal.classList.remove('show');
                document.body.style.overflow = '';
                currentRemovalData = null;
            }
        });
    }
    
    function removeDependent(skillId, dependentId, button) {
        // Блокируем кнопку во время запроса
        const originalHTML = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        
        // Получаем CSRF токен
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        fetch('/methodist/api/remove_dependent/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: `skill_id=${encodeURIComponent(skillId)}&dependent_id=${encodeURIComponent(dependentId)}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Перезагружаем страницу для обновления UI
                window.location.reload();
            } else {
                console.error('Ошибка при удалении зависимого навыка:', data.error);
                // Восстанавливаем кнопку
                button.disabled = false;
                button.innerHTML = originalHTML;
                
                // Показываем ошибку в модальном окне или alert как fallback
                alert('Ошибка при удалении зависимого навыка: ' + (data.error || 'Неизвестная ошибка'));
            }
        })
        .catch(error => {
            console.error('Ошибка запроса:', error);
            // Восстанавливаем кнопку
            button.disabled = false;
            button.innerHTML = originalHTML;
            
            alert('Ошибка при удалении зависимого навыка: ' + error.message);
        });
    }
});
