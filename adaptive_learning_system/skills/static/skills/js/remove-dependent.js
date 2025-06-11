/**
 * Обработчик для удаления зависимых навыков
 */

document.addEventListener('DOMContentLoaded', function() {
    // Обрабатываем клики по кнопкам удаления зависимых навыков
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('remove-dependent-btn') || e.target.closest('.remove-dependent-btn')) {
            e.preventDefault();
            
            const button = e.target.classList.contains('remove-dependent-btn') ? e.target : e.target.closest('.remove-dependent-btn');
            const skillId = button.getAttribute('data-skill-id');
            const dependentId = button.getAttribute('data-dependent-id');
            
            if (!skillId || !dependentId) {
                alert('Ошибка: не удается определить навык или зависимость');
                return;
            }
            
            // Получаем название зависимого навыка из элемента списка
            const listItem = button.closest('li');
            const dependentName = listItem ? listItem.querySelector('.font-medium').textContent : 'Неизвестный навык';
            
            if (confirm(`Вы уверены, что хотите убрать зависимость навыка "${dependentName}" от текущего навыка?`)) {
                removeDependent(skillId, dependentId, button);
            }
        }
    });
    
    function removeDependent(skillId, dependentId, button) {
        // Блокируем кнопку во время запроса
        const originalHTML = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        
        // Получаем CSRF токен
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        fetch('/skills/api/remove_dependent/', {
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
