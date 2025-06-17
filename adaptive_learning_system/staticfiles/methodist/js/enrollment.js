// enrollment.js — интерактив для управления зачислением студентов

document.addEventListener('DOMContentLoaded', function () {
    // Выбор студента
    document.querySelectorAll('.student-item').forEach(function (el) {
        el.addEventListener('click', function () {
            const studentId = el.getAttribute('data-student-id');
            const alreadySelected = el.classList.contains('selected');
            document.querySelectorAll('.student-item').forEach(e => e.classList.remove('selected'));
            if (alreadySelected) {
                // Сброс выбора и фильтра
                document.getElementById('selected-student-id').value = '';
                document.getElementById('selected-student').innerHTML = "<p class='text-muted'>Выберите студента из списка выше</p>";
                resetCourseFilter();
                checkFormReady();
                return;
            }
            el.classList.add('selected');
            const studentName = el.querySelector('.student-info h6').textContent;
            document.getElementById('selected-student-id').value = studentId;
            document.getElementById('selected-student').innerHTML = `<span class='fw-bold'>${studentName}</span>`;
            checkFormReady();
            resetCourseFilter();
            filterCoursesByStudent(studentId);
        });
    });

    // Выбор курса
    document.querySelectorAll('.course-item').forEach(function (el) {
        el.addEventListener('click', function () {
            const courseId = el.getAttribute('data-course-id');
            const alreadySelected = el.classList.contains('selected');
            document.querySelectorAll('.course-item').forEach(e => e.classList.remove('selected'));
            if (alreadySelected) {
                // Сброс выбора и фильтра
                document.getElementById('selected-course-id').value = '';
                document.getElementById('selected-course').innerHTML = "<p class='text-muted'>Выберите курс из списка выше</p>";
                resetStudentFilter();
                checkFormReady();
                return;
            }
            el.classList.add('selected');
            const courseName = el.querySelector('.course-info h6').textContent;
            document.getElementById('selected-course-id').value = courseId;
            document.getElementById('selected-course').innerHTML = `<span class='fw-bold'>${courseName}</span>`;
            checkFormReady();
            filterStudentsByCourse(courseId);
        });
    });

    // Проверка готовности формы
    function checkFormReady() {
        const studentId = document.getElementById('selected-student-id').value;
        const courseId = document.getElementById('selected-course-id').value;
        document.getElementById('enroll-btn').disabled = !(studentId && courseId);
    }

    // AJAX-запись студента на курс
    document.getElementById('enrollment-form').addEventListener('submit', function (e) {
        e.preventDefault();
        const btn = document.getElementById('enroll-btn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Запись...';
        const data = new FormData(this);
        fetch('/methodist/enrollment/enroll/', {
            method: 'POST',
            headers: { 'X-CSRFToken': data.get('csrfmiddlewaretoken') },
            body: data
        })
        .then(r => r.json())
        .then(resp => {
            btn.innerHTML = '<i class="fas fa-plus"></i> Записать';
            checkFormReady();
            if (resp.success) {
                setTimeout(() => window.location.reload(), 300);
            } else {
                // Можно добавить вывод ошибки в форму, если нужно
            }
        })
        .catch(() => {
            btn.innerHTML = '<i class="fas fa-plus"></i> Записать';
            checkFormReady();
        });
    });

    // Кнопка "Отчислить"
    document.querySelectorAll('.unenroll-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            if (!confirm('Вы уверены, что хотите отчислить студента?')) return;
            const enrollmentId = btn.getAttribute('data-enrollment-id');
            fetch('/methodist/enrollment/unenroll/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': getCSRFToken()
                },
                body: `enrollment_id=${enrollmentId}`
            })
            .then(r => r.json())
            .then(resp => {
                if (resp.success) {
                    btn.closest('tr').remove();
                } else {
                    // Можно добавить вывод ошибки в форму, если нужно
                }
            })
            .catch(() => {});
        });
    });

    // Получаем все связи студент-курс из DOM (генерируем data-enrollments на элементах)
    function getStudentEnrollmentsMap() {
        const map = {};
        document.querySelectorAll('.student-item').forEach(el => {
            const id = el.getAttribute('data-student-id');
            const enrolled = (el.getAttribute('data-enrolled-courses')||'').split(',').filter(Boolean);
            map[id] = new Set(enrolled);
        });
        return map;
    }
    function getCourseEnrollmentsMap() {
        const map = {};
        document.querySelectorAll('.course-item').forEach(el => {
            const id = el.getAttribute('data-course-id');
            const enrolled = (el.getAttribute('data-enrolled-students')||'').split(',').filter(Boolean);
            map[id] = new Set(enrolled);
        });
        return map;
    }
    const studentEnrollments = getStudentEnrollmentsMap();
    const courseEnrollments = getCourseEnrollmentsMap();

    // Фильтрация курсов по выбранному студенту
    function filterCoursesByStudent(studentId) {
        const enrolledSet = studentEnrollments[studentId] || new Set();
        document.querySelectorAll('.course-item').forEach(el => {
            const courseId = el.getAttribute('data-course-id');
            // Сравниваем как строки
            if (enrolledSet.has(String(courseId))) {
                el.style.display = 'none';
            } else {
                el.style.display = '';
            }
        });
        // Для отладки
        // console.log('Фильтрация курсов для студента', studentId, 'уже записан на:', Array.from(enrolledSet));
    }
    // Фильтрация студентов по выбранному курсу
    function filterStudentsByCourse(courseId) {
        document.querySelectorAll('.student-item').forEach(el => {
            const studentId = el.getAttribute('data-student-id');
            if (courseEnrollments[courseId] && courseEnrollments[courseId].has(studentId)) {
                el.style.display = 'none';
            } else {
                el.style.display = '';
            }
        });
    }
    // Сброс фильтра
    function resetCourseFilter() {
        document.querySelectorAll('.course-item').forEach(el => el.style.display = '');
    }
    function resetStudentFilter() {
        document.querySelectorAll('.student-item').forEach(el => el.style.display = '');
    }

    // При сбросе выбора (новый студент/курс) показываем всё
    document.getElementById('selected-student-id').addEventListener('change', function(){
        if (!this.value) resetCourseFilter();
    });
    document.getElementById('selected-course-id').addEventListener('change', function(){
        if (!this.value) resetStudentFilter();
    });

    // Вспомогательные функции
    function getCSRFToken() {
        return document.querySelector('input[name="csrfmiddlewaretoken"]').value;
    }
});
