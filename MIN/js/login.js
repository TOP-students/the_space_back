document.addEventListener('DOMContentLoaded', function() {

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

            // Валидация
            if (password !== passwordConfirm) {
                Modal.warning('Пароли не совпадают!');
                return;
            }

            if (password.length < 6) {
                Modal.warning('Пароль должен быть минимум 6 символов!');
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

