// конфигурация приложения
window.CONFIG = {
  API_BASE_URL:
    window.location.hostname === 'localhost'
      ? 'http://localhost:8080'
      : 'https://the-space-backend.onrender.com',

  FRONTEND_URL: window.location.origin,
  TOKEN_KEY: 'auth_token',
  USER_KEY: 'current_user'
};

const API_URL = window.location.hostname === 'localhost'
  ? 'http://localhost:8080'
  : 'https://the-space-backend.onrender.com';

// использование
async function login(username, password) {
    const response = await fetch(`${API_URL}/auth/token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: new URLSearchParams({
      username: username,
      password: password
    })
  });
  
  const data = await response.json();
  if (data.access_token) {
    localStorage.setItem('token', data.access_token);
  }
  return data;
}

// экспорт для использования в других модулях
window.CONFIG = CONFIG;
