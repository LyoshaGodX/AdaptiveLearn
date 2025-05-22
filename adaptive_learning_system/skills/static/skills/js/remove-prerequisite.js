// Логика для удаления предпосылки (связи зависит от)

document.addEventListener('DOMContentLoaded', function() {
    // --- Модальное подтверждение удаления связи ---
    const modal = document.getElementById('confirm-remove-prereq-modal');
    const skillNameSpan = document.getElementById('remove-prereq-skill-name');
    const cancelBtn = document.getElementById('cancel-remove-prereq');
    const confirmBtn = document.getElementById('confirm-remove-prereq');
    const closeBtn = document.getElementById('close-remove-prereq-modal');
    let pendingSkillId = null;
    let pendingPrereqId = null;
    let pendingBtn = null;
    let pendingSkillName = '';

    document.querySelectorAll('.remove-prerequisite-btn').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            pendingSkillId = btn.getAttribute('data-skill-id');
            pendingPrereqId = btn.getAttribute('data-prereq-id');
            pendingSkillName = btn.closest('li').querySelector('.font-medium')?.textContent || '';
            pendingBtn = btn;
            if (!pendingSkillId || !pendingPrereqId) return;
            skillNameSpan.textContent = pendingSkillName;
            modal.classList.remove('hidden');
        });
    });

    function closeModal() {
        modal.classList.add('hidden');
        pendingSkillId = null;
        pendingPrereqId = null;
        pendingBtn = null;
        pendingSkillName = '';
    }

    cancelBtn && cancelBtn.addEventListener('click', closeModal);
    closeBtn && closeBtn.addEventListener('click', closeModal);
    modal && modal.addEventListener('click', function(e) {
        if (e.target === modal) closeModal();
    });

    confirmBtn && confirmBtn.addEventListener('click', function() {
        if (!pendingSkillId || !pendingPrereqId) return;
        // Получить CSRF-токен
        function getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
        const csrftoken = getCookie('csrftoken');
        confirmBtn.disabled = true;
        confirmBtn.textContent = 'Удаление...';
        fetch('/api/remove_prerequisite/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrftoken
            },
            body: `skill_id=${encodeURIComponent(pendingSkillId)}&prereq_id=${encodeURIComponent(pendingPrereqId)}`
        })
        .then(response => response.json())
        .then(data => {
            confirmBtn.disabled = false;
            confirmBtn.textContent = 'Удалить';
            if (data.success) {
                window.location.reload();
            } else {
                alert(data.error || 'Ошибка при удалении связи');
                closeModal();
            }
        })
        .catch(() => {
            confirmBtn.disabled = false;
            confirmBtn.textContent = 'Удалить';
            alert('Ошибка сети при удалении связи');
            closeModal();
        });
    });
});
