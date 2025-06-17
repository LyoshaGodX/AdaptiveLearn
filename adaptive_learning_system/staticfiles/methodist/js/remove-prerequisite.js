/**
 * Модуль для удаления предпосылок у навыков
 */

document.addEventListener('DOMContentLoaded', function() {
    let currentRemovalData = null; // Храним данные для удаления
    
    // Обрабатываем клики по кнопкам удаления предпосылок
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('remove-prerequisite-btn')) {
            e.preventDefault();
            
            const skillId = e.target.getAttribute('data-skill-id');
            const prereqId = e.target.getAttribute('data-prereq-id');
            const prereqBadge = e.target.closest('.prerequisite-badge');
            const prereqName = prereqBadge ? prereqBadge.querySelector('span').textContent : 'Неизвестный навык';
            
            if (!skillId || !prereqId) {
                alert('Ошибка: не удается определить навык или зависимость');
                return;
            }
            
            // Находим название навыка
            const selectedSkillElement = document.querySelector('.skill-list-item.active .skill-name');
            const skillName = selectedSkillElement ? selectedSkillElement.textContent : 'Выбранный навык';
            
            // Сохраняем данные для удаления
            currentRemovalData = {
                skillId: skillId,
                prereqId: prereqId,
                button: e.target
            };
            
            // Заполняем модальное окно
            document.getElementById('remove-prereq-name').textContent = prereqName;
            document.getElementById('remove-prereq-skill-name').textContent = skillName;
            
            // Показываем модальное окно
            const modal = document.getElementById('remove-prereq-modal');
            if (modal) {
                modal.classList.add('show');
                document.body.style.overflow = 'hidden';
            }
        }
    });
    
    // Обработчик кнопки подтверждения удаления
    const confirmBtn = document.getElementById('remove-prereq-confirm');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', function() {
            if (currentRemovalData) {
                removePrerequisite(currentRemovalData.skillId, currentRemovalData.prereqId, currentRemovalData.button);
                
                // Закрываем модальное окно
                const modal = document.getElementById('remove-prereq-modal');
                if (modal) {
                    modal.classList.remove('show');
                    document.body.style.overflow = '';
                }
                
                currentRemovalData = null;
            }
        });
    }    
    function removePrerequisite(skillId, prereqId, button) {
        // Блокируем кнопку во время запроса
        const originalHTML = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
          // Получаем CSRF токен
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        fetch('/methodist/api/remove_prerequisite/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: `skill_id=${encodeURIComponent(skillId)}&prereq_id=${encodeURIComponent(prereqId)}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Перезагружаем страницу для обновления UI
                window.location.reload();
            } else {
                console.error('Ошибка при удалении зависимости:', data.error);
                // Восстанавливаем кнопку
                button.disabled = false;
                button.innerHTML = originalHTML;
                
                // Показываем ошибку в модальном окне или alert как fallback
                alert('Ошибка при удалении зависимости: ' + (data.error || 'Неизвестная ошибка'));
            }
        })
        .catch(error => {
            console.error('Ошибка запроса:', error);
            // Восстанавливаем кнопку
            button.disabled = false;
            button.innerHTML = originalHTML;
            
            alert('Ошибка при удалении зависимости: ' + error.message);
        });
    }
});
