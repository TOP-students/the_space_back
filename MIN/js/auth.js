// Модуль управления аутентификацией
const AuthService = {
    // Сохранить токен
    setToken(token) {
        localStorage.setItem(CONFIG.TOKEN_KEY, token);
    },

    // Получить токен
    getToken() {
        return localStorage.getItem(CONFIG.TOKEN_KEY);
    },

    // Удалить токен
    removeToken() {
        localStorage.removeItem(CONFIG.TOKEN_KEY);
        localStorage.removeItem(CONFIG.USER_KEY);
    },

    // Проверка авторизации
    isAuthenticated() {
        return !!this.getToken();
    },

    // Сохранить данные пользователя
    setUser(user) {
        localStorage.setItem(CONFIG.USER_KEY, JSON.stringify(user));
    },

    // Получить данные пользователя
    getUser() {
        const user = localStorage.getItem(CONFIG.USER_KEY);
        return user ? JSON.parse(user) : null;
    },

    // Выход
    logout() {
        this.removeToken();
        window.location.href = 'login.html';
    }
};

window.AuthService = AuthService;
