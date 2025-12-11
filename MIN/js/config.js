// Конфигурация приложения
const CONFIG = {
    API_BASE_URL: window.location.hostname === 'localhost'
        ? 'http://localhost:8080'
        : 'https://the-space-back.onrender.com',
    FRONTEND_URL: window.location.origin,
    TOKEN_KEY: 'auth_token',
    USER_KEY: 'current_user'
};

// Экспорт для использования в других модулях
window.CONFIG = CONFIG;
