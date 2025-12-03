document.addEventListener('DOMContentLoaded', function() {

    // --- Инициализация переключателей пароля ---
    initPasswordToggles();

    // --- Обработчики событий ---
    const loginForm = document.querySelector('#login-form');
    const registerForm = document.querySelector('#register-form');

    // --- Логика для формы входа ---
    if (loginForm) {
        loginForm.addEventListener('submit', async function(event) {
            event.preventDefault();

            const nickname = document.querySelector('#login-nickname').value.trim();
            const password = document.querySelector('#login-password').value;
            const submitButton = loginForm.querySelector('button[type="submit"]');

            // Блокируем кнопку
            submitButton.disabled = true;
            submitButton.textContent = 'Вход...';

            try {
                // Логин через API (username = nickname в FastAPI)
                const response = await API.login(nickname, password);

                // Сохраняем токен
                AuthService.setToken(response.access_token);

                // Получаем данные пользователя
                const user = await API.getCurrentUser();
                AuthService.setUser(user);

                // Успешный вход - сразу переходим
                window.location.href = 'chat.html';

            } catch (error) {
                await Modal.error(error.message || 'Ошибка входа. Проверьте данные.');
                console.error('Login error:', error);
            } finally {
                // Разблокируем кнопку
                submitButton.disabled = false;
                submitButton.textContent = 'Войти';
            }
        });
    }

    // --- Логика для формы регистрации ---
    if (registerForm) {
        registerForm.addEventListener('submit', async function(event) {
            event.preventDefault();

            const nickname = document.querySelector('#register-nickname').value.trim();
            const email = document.querySelector('#register-email').value.trim();
            const password = document.querySelector('#register-password').value;
            const passwordConfirm = document.querySelector('#register-password-confirm').value;
            const submitButton = registerForm.querySelector('button[type="submit"]');

            // Валидация никнейма
            if (nickname.length < 3 || nickname.length > 20) {
                Modal.warning('Никнейм должен содержать от 3 до 20 символов!');
                return;
            }

            if (!/^[a-zA-Z][a-zA-Z0-9_-]*$/.test(nickname)) {
                Modal.warning('Никнейм должен начинаться с буквы и содержать только латиницу, цифры, _ или -');
                return;
            }

            // Валидация email
            if (email && !/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(email)) {
                Modal.warning('Неверный формат email!');
                return;
            }

            // Валидация пароля
            if (password.length < 8) {
                Modal.warning('Пароль должен содержать минимум 8 символов!');
                return;
            }

            if (!/[a-zA-Z]/.test(password)) {
                Modal.warning('Пароль должен содержать хотя бы одну букву!');
                return;
            }

            if (!/\d/.test(password)) {
                Modal.warning('Пароль должен содержать хотя бы одну цифру!');
                return;
            }

            // Совпадение паролей
            if (password !== passwordConfirm) {
                Modal.warning('Пароли не совпадают!');
                return;
            }

            // Блокируем кнопку
            submitButton.disabled = true;
            submitButton.textContent = 'Регистрация...';

            try {
                // Регистрация через API
                await API.register(nickname, email, password);

                // Регистрация успешна - переходим на страницу входа
                window.location.href = 'login.html';

            } catch (error) {
                await Modal.error(error.message || 'Ошибка регистрации. Попробуйте другой никнейм или email.');
                console.error('Registration error:', error);
            } finally {
                // Разблокируем кнопку
                submitButton.disabled = false;
                submitButton.textContent = 'Зарегистрироваться';
            }
        });
    }
});

// Функция для инициализации переключателей пароля
function initPasswordToggles() {
    const toggleButtons = document.querySelectorAll('.password-toggle');

    toggleButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault(); // Предотвращаем submit формы
            e.stopPropagation();

            const targetId = this.getAttribute('data-target');
            const passwordInput = document.getElementById(targetId);

            if (!passwordInput) return;

            // Переключаем тип input
            const isPassword = passwordInput.type === 'password';
            passwordInput.type = isPassword ? 'text' : 'password';

            // Меняем иконку и title
            this.classList.toggle('visible', isPassword);
            this.title = isPassword ? 'Скрыть пароль' : 'Показать пароль';

            // Меняем иконку (перечеркнутый глаз)
            const svg = this.querySelector('.eye-icon');
            if (isPassword) {
                // Добавляем линию перечеркивания
                svg.innerHTML = `
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                    <circle cx="12" cy="12" r="3"></circle>
                    <line x1="2" y1="2" x2="22" y2="22" stroke-linecap="round"></line>
                `;
            } else {
                // Обычный глаз
                svg.innerHTML = `
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                    <circle cx="12" cy="12" r="3"></circle>
                `;
            }
        });
    });
}

