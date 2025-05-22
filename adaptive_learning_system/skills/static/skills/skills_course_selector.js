/**
 * Дополнительный скрипт для улучшения обработки селектора курсов при просмотре навыков
 */
document.addEventListener('DOMContentLoaded', function() {
    // Получаем элементы формы
    const courseSelect = document.getElementById('course');
    const skillInput = document.getElementById('selected-skill-input');
    const filterForm = document.getElementById('course-filter-form');
    const clearSkillBtn = document.getElementById('clear-skill-filter');
    
    // Если элементы не найдены, выходим
    if (!courseSelect || !filterForm) return;
    
    // Кастомная функция отправки формы, которая игнорирует пустые значения
    function submitFormWithoutEmptyParams() {
        // Создаем новую форму, чтобы не изменять оригинальную
        const tempForm = document.createElement('form');
        tempForm.method = 'get';
        tempForm.action = window.location.pathname;
        
        // Добавляем только параметр course, если он не пустой
        const courseValue = courseSelect.value;
        if (courseValue) {
            const courseInput = document.createElement('input');
            courseInput.type = 'hidden';
            courseInput.name = 'course';
            courseInput.value = courseValue;
            tempForm.appendChild(courseInput);
        }
        
        // Не добавляем параметр skill (сбрасываем его)
        
        // Отправляем форму
        document.body.appendChild(tempForm);
        tempForm.submit();
    }
    
    // Переопределяем стандартный обработчик отправки формы
    filterForm.addEventListener('submit', function(e) {
        e.preventDefault();
        submitFormWithoutEmptyParams();
    });
    
    // Обработчик изменения селектора курса
    courseSelect.addEventListener('change', function(e) {
        // Предотвращаем стандартную отправку формы через onchange
        e.preventDefault();
        
        // Отправляем форму без параметра skill
        submitFormWithoutEmptyParams();
    });
    
    // Обработчик кнопки сброса фильтра по навыку
    if (clearSkillBtn) {
        clearSkillBtn.addEventListener('click', function(e) {
            e.preventDefault();
            submitFormWithoutEmptyParams();
        });
    }
});
