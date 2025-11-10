# Архитектура Frontend части проекта "The Space"

## Содержание
1. [Обзор архитектуры](#обзор-архитектуры)
2. [Структура проекта](#структура-проекта)
3. [HTML страницы](#html-страницы)
4. [JavaScript модули](#javascript-модули)
5. [CSS стили](#css-стили)
6. [Ресурсы и иконки](#ресурсы-и-иконки)
7. [Технологии и паттерны](#технологии-и-паттерны)
8. [Поток данных](#поток-данных)
9. [WebSocket коммуникация](#websocket-коммуникация)
10. [Взаимодействие с Backend](#взаимодействие-с-backend)

---

## Обзор архитектуры

**The Space** - это фронтенд часть веб-приложения для группового чата, написанная на **чистом JavaScript** (Vanilla JS) без использования фреймворков типа React, Vue или Angular.

### Ключевые технологии:
- **Vanilla JavaScript** (ES6+) - никаких фреймворков
- **HTML5** - семантическая разметка
- **CSS3** - современные стили, градиенты, анимации
- **Socket.IO** - реальное время через WebSocket
- **Fetch API** - HTTP запросы к backend
- **LocalStorage** - хранение токена и данных пользователя
- **FastAPI Backend** - Python сервер на http://localhost:8000

### Архитектурный подход:
- **Модульная архитектура** - каждый JS файл отвечает за свою область
- **Service Layer паттерн** - AuthService, API, WebSocketClient
- **State Management** - глобальное состояние в объекте `state` (chat.js)
- **Event-driven** - обработка событий DOM и WebSocket
- **Promise-based** - асинхронные операции через async/await

---

## Структура проекта

```
MIN/
├── assets/
│   └── icons/           # SVG иконки
│       ├── avatar.svg       # Аватар пользователя
│       ├── avatarchat.svg   # Иконка чата
│       ├── cat.svg          # Кот для пустого состояния
│       ├── newchat.svg      # Кнопка создания чата
│       ├── sendbutt.svg     # Иконка отправки
│       └── settings.svg     # Иконка настроек
│
├── css/
│   ├── style.css        # Стили для login/register страниц
│   ├── stylechat.css    # Стили для чата
│   └── modal.css        # Стили для модальных окон
│
├── js/
│   ├── config.js        # Конфигурация приложения
│   ├── auth.js          # Модуль аутентификации
│   ├── api.js           # API клиент для HTTP запросов
│   ├── websocket.js     # WebSocket клиент (Socket.IO)
│   ├── modal.js         # Система модальных окон
│   ├── login.js         # Логика login/register форм
│   └── chat.js          # Основная логика чата
│
├── login.html           # Страница входа
├── register.html        # Страница регистрации
└── chat.html            # Основное приложение чата
```

---

## HTML страницы

### 1. login.html

**Назначение**: Страница входа в систему.

**Структура**:
```html
<!DOCTYPE html>
<html lang="ru">
<head>
    <!-- Meta теги -->
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <!-- Отключение favicon -->
    <link rel="icon" href="data:,">

    <!-- CSS -->
    <link rel="stylesheet" href="css/style.css?v=3">
    <link rel="stylesheet" href="css/modal.css">
</head>
<body>
    <main class="form-container">
        <h2>Вход в аккаунт</h2>
        <form id="login-form">
            <!-- Поля формы -->
        </form>
    </main>

    <!-- Скрипты загружаются в строгом порядке -->
    <script src="js/config.js"></script>
    <script src="js/auth.js"></script>
    <script src="js/api.js"></script>
    <script src="js/modal.js"></script>
    <script src="js/login.js"></script>
</body>
</html>
```

**Важные детали**:
- `?v=3` в CSS - cache busting для обновления стилей
- `<link rel="icon" href="data:,">` - отключает запрос favicon для чистоты консоли
- Скрипты загружаются последовательно, так как есть зависимости между модулями
- Форма имеет ID `login-form`, который используется в login.js

**Поля формы**:
1. `login-nickname` - Никнейм пользователя (используется как username в FastAPI)
2. `login-password` - Пароль

**Ссылки**:
- "Ещё нет аккаунта? Зарегистрироваться" → register.html
- "Я не помню пароль" - пока не функциональна

---

### 2. register.html

**Назначение**: Страница регистрации нового пользователя.

**Структура**: Аналогична login.html, но с формой `register-form`.

**Поля формы**:
1. `register-nickname` - Никнейм (уникальный)
2. `register-email` - Email (уникальный)
3. `register-password` - Пароль (минимум 6 символов)
4. `register-password-confirm` - Подтверждение пароля

**Валидация**:
- Проверка совпадения паролей (на фронтенде)
- Проверка минимальной длины пароля (6 символов)
- Backend дополнительно проверяет уникальность nickname и email

**Ссылки**:
- "Уже есть аккаунт? Войти" → login.html

---

### 3. chat.html

**Назначение**: Главная страница приложения - интерфейс чата.

**Структура**:
```html
<body>
    <div class="chat-container">
        <!-- 1. Левая темная панель с иконками -->
        <div class="sidebar-dark-bar">
            <svg class="sidebar-icon settings-icon">...</svg>
            <svg class="sidebar-icon logout-icon">...</svg>
        </div>

        <!-- 2. Сайдбар со списком чатов -->
        <aside class="sidebar">
            <div class="user-profile">...</div>
            <div class="chat-list">...</div>
            <div class="new-chat-button">...</div>
        </aside>

        <!-- 3. Основная область чата -->
        <main class="chat-main">
            <!-- Динамический контент -->
        </main>

        <!-- 4. Правый сайдбар (резерв) -->
        <aside class="sidebar-right"></aside>
    </div>

    <!-- Socket.IO CDN -->
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>

    <!-- Модули приложения -->
    <script src="js/config.js"></script>
    <script src="js/auth.js"></script>
    <script src="js/api.js"></script>
    <script src="js/modal.js"></script>
    <script src="js/websocket.js"></script>
    <script src="js/chat.js"></script>
</body>
```

**Компоненты интерфейса**:

1. **Темная панель слева** (`.sidebar-dark-bar`):
   - Ширина: 70px
   - Фон: темно-красный (#800000)
   - Иконки настроек и выхода внизу

2. **Сайдбар чатов** (`.sidebar`):
   - Ширина: 320px
   - Фон: светло-серый (#d8d0c8)
   - Профиль пользователя вверху
   - Список пространств (spaces)
   - Кнопка создания нового чата

3. **Основная область** (`.chat-main`):
   - Динамически заполняется через JavaScript
   - Может отображать:
     - Пустое состояние с котом
     - Выбранный чат с сообщениями
     - Форму отправки сообщения

4. **Правый сайдбар** (`.sidebar-right`):
   - Ширина: 70px
   - Резерв для будущего функционала

**SVG иконки inline**:
- Настройки (settings-icon) - шестеренка
- Выход (logout-icon) - стрелка выхода

Inline SVG используется для возможности стилизации через CSS (stroke, fill).

---

## JavaScript модули

### 1. config.js

**Назначение**: Централизованная конфигурация приложения.

**Код**:
```javascript
const CONFIG = {
    API_BASE_URL: 'http://localhost:8000',
    FRONTEND_URL: 'http://localhost:3000',
    TOKEN_KEY: 'auth_token',
    USER_KEY: 'current_user'
};

window.CONFIG = CONFIG;
```

**Параметры**:
- `API_BASE_URL` - адрес FastAPI backend
- `FRONTEND_URL` - адрес фронтенда (не используется активно)
- `TOKEN_KEY` - ключ для хранения JWT токена в localStorage
- `USER_KEY` - ключ для хранения данных пользователя в localStorage

**Экспорт**: Объект CONFIG добавляется в глобальный объект `window` для доступа из других модулей.

**Использование**:
```javascript
const url = `${CONFIG.API_BASE_URL}/auth/me`;
localStorage.setItem(CONFIG.TOKEN_KEY, token);
```

---

### 2. auth.js

**Назначение**: Модуль управления аутентификацией и работы с токенами.

**Код**:
```javascript
const AuthService = {
    setToken(token) {
        localStorage.setItem(CONFIG.TOKEN_KEY, token);
    },

    getToken() {
        return localStorage.getItem(CONFIG.TOKEN_KEY);
    },

    removeToken() {
        localStorage.removeItem(CONFIG.TOKEN_KEY);
        localStorage.removeItem(CONFIG.USER_KEY);
    },

    isAuthenticated() {
        return !!this.getToken();
    },

    setUser(user) {
        localStorage.setItem(CONFIG.USER_KEY, JSON.stringify(user));
    },

    getUser() {
        const user = localStorage.getItem(CONFIG.USER_KEY);
        return user ? JSON.parse(user) : null;
    },

    logout() {
        this.removeToken();
        window.location.href = 'login.html';
    }
};

window.AuthService = AuthService;
```

**Методы**:

1. **setToken(token)** - Сохранить JWT токен в localStorage
2. **getToken()** - Получить токен из localStorage
3. **removeToken()** - Удалить токен и данные пользователя
4. **isAuthenticated()** - Проверка наличия токена (!! конвертирует в boolean)
5. **setUser(user)** - Сохранить объект пользователя (сериализация в JSON)
6. **getUser()** - Получить объект пользователя (десериализация из JSON)
7. **logout()** - Выход: удаление токена + редирект на login.html

**Паттерн**: Service Object - объект с методами, экспортированный в window

**Использование**:
```javascript
// После успешного логина
AuthService.setToken(response.access_token);
AuthService.setUser(userData);

// Проверка авторизации
if (!AuthService.isAuthenticated()) {
    window.location.href = 'login.html';
}

// Выход
AuthService.logout();
```

---

### 3. api.js

**Назначение**: HTTP клиент для взаимодействия с FastAPI backend.

**Архитектура**:
- Базовый метод `request()` - обертка над fetch
- Методы для HTTP глаголов: `get()`, `post()`, `patch()`, `delete()`
- Эндпоинты API сгруппированы по доменам (auth, spaces, messages)

**Код базового метода**:
```javascript
async request(endpoint, options = {}) {
    const url = `${CONFIG.API_BASE_URL}${endpoint}`;
    const token = AuthService.getToken();

    const config = {
        headers: {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` })
        },
        ...options
    };

    try {
        const response = await fetch(url, config);
        const data = await response.json();

        if (!response.ok) {
            if (response.status === 401) {
                AuthService.logout();
                throw new Error('Сессия истекла. Войдите снова.');
            }
            throw new Error(data.detail || 'Ошибка сервера');
        }

        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}
```

**Ключевые моменты**:
- Автоматическое добавление Bearer токена из AuthService
- Обработка 401 ошибки (автоматический logout)
- Парсинг JSON ответа
- Проброс ошибок с detail из FastAPI

**HTTP методы**:
```javascript
get(endpoint) {
    return this.request(endpoint, { method: 'GET' });
}

post(endpoint, data) {
    return this.request(endpoint, {
        method: 'POST',
        body: JSON.stringify(data)
    });
}

patch(endpoint, data) {
    return this.request(endpoint, {
        method: 'PATCH',
        body: JSON.stringify(data)
    });
}

delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
}
```

**AUTH Endpoints**:

1. **register(nickname, email, password)**
   - POST `/auth/register`
   - Создает нового пользователя
   - Возвращает данные созданного пользователя

2. **login(username, password)**
   - POST `/auth/token`
   - Использует `application/x-www-form-urlencoded` (требование OAuth2)
   - Возвращает `{ access_token: "...", token_type: "bearer" }`
   - **Важно**: username = nickname в нашем случае

```javascript
async login(username, password) {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const response = await fetch(`${CONFIG.API_BASE_URL}/auth/token`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: formData
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || 'Ошибка входа');
    }

    return data;
}
```

3. **getCurrentUser()**
   - GET `/auth/me`
   - Требует токен в Authorization header
   - Возвращает данные текущего пользователя

**SPACES Endpoints**:

1. **getSpaces()**
   - GET `/spaces/`
   - Получить список всех пространств
   - Возвращает массив объектов Space с chat_id

2. **createSpace(name, description, background_url)**
   - POST `/spaces/`
   - Создать новое пространство
   - Автоматически создает связанный Chat

3. **joinSpace(spaceId)**
   - POST `/spaces/{spaceId}/join`
   - Присоединиться к пространству
   - Создает ChatParticipant запись

4. **getSpaceParticipants(spaceId)**
   - GET `/spaces/{spaceId}/participants`
   - Получить список участников

**MESSAGES Endpoints**:

1. **getMessages(chatId, limit=50, offset=0)**
   - GET `/messages/{chatId}?limit=50&offset=0`
   - Получить сообщения чата (пагинация)

2. **sendMessage(chatId, content, type='text')**
   - POST `/messages/{chatId}`
   - Отправить текстовое сообщение

3. **searchMessages(chatId, query, limit=50, offset=0)**
   - GET `/messages/{chatId}/search?q=текст`
   - Поиск по содержимому сообщений

**Экспорт**: `window.API = API;`

---

### 4. websocket.js

**Назначение**: WebSocket клиент на основе Socket.IO для реал-тайм коммуникации.

**Класс WebSocketClient**:
```javascript
class WebSocketClient {
    constructor() {
        this.socket = null;
        this.connected = false;
        this.currentRoomId = null;
        this.onMessageCallback = null;
        this.onUserJoinedCallback = null;
        this.onUserLeftCallback = null;
    }
}
```

**Свойства**:
- `socket` - экземпляр Socket.IO клиента
- `connected` - флаг подключения
- `currentRoomId` - ID текущей комнаты
- `onMessageCallback` - callback для новых сообщений
- `onUserJoinedCallback` - callback при входе пользователя
- `onUserLeftCallback` - callback при выходе пользователя

**Методы**:

1. **connect(userId, nickname)**
   - Подключение к серверу Socket.IO
   - Передает user_id и nickname в query параметрах
   - Настраивает обработчики событий

```javascript
connect(userId, nickname) {
    this.socket = io(CONFIG.API_BASE_URL, {
        transports: ['websocket', 'polling'],
        query: {
            user_id: userId,
            nickname: nickname
        }
    });

    this.socket.on('connect', () => {
        console.log('Socket.IO connected');
        this.connected = true;
    });

    this.socket.on('new_message', (data) => {
        if (this.onMessageCallback) {
            this.onMessageCallback(data);
        }
    });

    // ... другие обработчики
}
```

2. **joinRoom(roomId, userId, nickname)**
   - Присоединение к комнате чата
   - Отправляет событие `join_room` на сервер

```javascript
joinRoom(roomId, userId, nickname) {
    this.currentRoomId = roomId;
    this.socket.emit('join_room', {
        room_id: roomId,
        user_id: userId,
        nickname: nickname
    });
}
```

3. **leaveRoom(roomId, userId)**
   - Покинуть комнату
   - Отправляет событие `leave_room`

4. **sendMessage(roomId, userId, nickname, message)**
   - Отправить сообщение через WebSocket (опционально)
   - В текущей реализации используется HTTP API для отправки

5. **onMessage(callback)**, **onUserJoined(callback)**, **onUserLeft(callback)**
   - Установка обработчиков событий

**События Socket.IO**:

**От клиента к серверу** (emit):
- `join_room` - присоединиться к комнате
- `leave_room` - покинуть комнату
- `send_message` - отправить сообщение

**От сервера к клиенту** (on):
- `connect` - успешное подключение
- `disconnect` - отключение
- `connected` - подтверждение сервера
- `new_message` - новое сообщение в комнате
- `user_joined_room` - пользователь зашел
- `user_left_room` - пользователь вышел
- `error` - ошибка

**Экспорт**: `window.WebSocketClient = WebSocketClient;`

**Использование**:
```javascript
const wsClient = new WebSocketClient();
wsClient.connect(user.id, user.nickname);

wsClient.onMessage((data) => {
    console.log('New message:', data);
    // Добавить сообщение в UI
});

wsClient.joinRoom(chatId, userId, nickname);
```

---

### 5. modal.js

**Назначение**: Система модальных окон, замена браузерных alert/confirm/prompt.

**Класс Modal**:
Singleton объект с методами для показа разных типов модальных окон.

**Публичные методы**:

1. **alert(message, title, type)**
   - Информационное сообщение
   - Возвращает Promise<boolean>
   - Типы: info, error, success, warning

```javascript
alert(message, title = 'Внимание', type = 'info') {
    return new Promise((resolve) => {
        this._show({
            title,
            message,
            type,
            buttons: [
                {
                    text: 'OK',
                    class: 'modal-button-primary',
                    onClick: () => resolve(true)
                }
            ]
        });
    });
}
```

2. **confirm(message, title, options)**
   - Диалог подтверждения
   - Возвращает Promise<boolean>
   - Опции: confirmText, cancelText, danger

```javascript
const confirmed = await Modal.confirm(
    'Удалить сообщение?',
    'Подтверждение',
    { confirmText: 'Удалить', danger: true }
);
if (confirmed) {
    // Удалить
}
```

3. **error(message, title)** - Ошибка (красный)
4. **success(message, title)** - Успех (зеленый)
5. **warning(message, title)** - Предупреждение (желтый)

6. **createRoom()**
   - Форма создания комнаты
   - Возвращает Promise<object|null>
   - Null если отменено, иначе объект с данными формы

```javascript
const formData = await Modal.createRoom();
if (!formData) return; // Отменено

const { 'room-name': name, 'room-description': description } = formData;
```

**Внутренние методы**:

1. **_show(config)**
   - Показать простое модальное окно
   - Создает overlay + modal-window
   - Добавляет обработчики кнопок

2. **_showForm(config)**
   - Показать модальное окно с формой
   - Поддерживает текстовые поля и textarea
   - Собирает данные при нажатии primary кнопки

```javascript
_showForm(config) {
    const { title, fields, buttons } = config;

    // Генерация HTML полей
    const fieldsHTML = fields.map(field => {
        if (field.type === 'textarea') {
            return `<textarea id="${field.id}" ...></textarea>`;
        } else {
            return `<input type="${field.type}" id="${field.id}" ...>`;
        }
    }).join('');

    // Создание модального окна
    // ...

    // Обработчик primary кнопки
    const formData = {};
    fields.forEach(field => {
        const input = document.getElementById(field.id);
        formData[field.id] = input.value.trim();
    });
    buttons[index].onClick(formData);
}
```

**Особенность обработки событий**:
После исправления бага, кнопки обрабатываются через click event, а не form submit:

```javascript
buttonElements.forEach((btnEl, index) => {
    btnEl.addEventListener('click', (e) => {
        e.preventDefault();

        if (!buttons[index].class.includes('primary')) {
            // Вторичная кнопка
            buttons[index].onClick();
            this._close(overlay);
        } else {
            // Primary кнопка
            const formData = { /* собрать данные */ };
            buttons[index].onClick(formData);
            this._close(overlay);
        }
    });
});
```

3. **_close(overlay)**
   - Закрытие с анимацией
   - Добавляет класс `closing`
   - Удаляет элемент через 300ms

4. **_escapeHtml(text)**
   - Защита от XSS атак
   - Экранирует HTML символы

**Фичи**:
- Закрытие по ESC
- Закрытие по клику вне окна
- Анимации появления/исчезновения (CSS)
- Promise-based API для удобного использования

**Экспорт**: `window.Modal = Modal;`

---

### 6. login.js

**Назначение**: Логика форм входа и регистрации.

**Структура**:
```javascript
document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.querySelector('#login-form');
    const registerForm = document.querySelector('#register-form');

    if (loginForm) {
        // Логика входа
    }

    if (registerForm) {
        // Логика регистрации
    }
});
```

**Логика формы входа**:

```javascript
loginForm.addEventListener('submit', async function(event) {
    event.preventDefault();

    const nickname = document.querySelector('#login-nickname').value.trim();
    const password = document.querySelector('#login-password').value;
    const submitButton = loginForm.querySelector('button[type="submit"]');

    // Блокировка кнопки
    submitButton.disabled = true;
    submitButton.textContent = 'Вход...';

    try {
        // 1. Логин через API
        const response = await API.login(nickname, password);

        // 2. Сохраняем токен
        AuthService.setToken(response.access_token);

        // 3. Получаем данные пользователя
        const user = await API.getCurrentUser();
        AuthService.setUser(user);

        // 4. Редирект на чат
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
```

**Логика формы регистрации**:

```javascript
registerForm.addEventListener('submit', async function(event) {
    event.preventDefault();

    const nickname = document.querySelector('#register-nickname').value.trim();
    const email = document.querySelector('#register-email').value.trim();
    const password = document.querySelector('#register-password').value;
    const passwordConfirm = document.querySelector('#register-password-confirm').value;

    // Валидация паролей
    if (password !== passwordConfirm) {
        Modal.warning('Пароли не совпадают!');
        return;
    }

    if (password.length < 6) {
        Modal.warning('Пароль должен быть минимум 6 символов!');
        return;
    }

    // Блокировка кнопки
    submitButton.disabled = true;
    submitButton.textContent = 'Регистрация...';

    try {
        await API.register(nickname, email, password);

        // Успешная регистрация - редирект на login
        window.location.href = 'login.html';

    } catch (error) {
        await Modal.error(error.message || 'Ошибка регистрации.');
        console.error('Registration error:', error);
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = 'Зарегистрироваться';
    }
});
```

**Фичи**:
- Валидация на клиенте (длина пароля, совпадение)
- Блокировка кнопки во время запроса
- Визуальный feedback (текст кнопки меняется)
- Обработка ошибок через модальные окна
- После успешной регистрации - редирект на login

---

### 7. chat.js

**Назначение**: Основная логика приложения чата.

Это самый большой и важный модуль. Разберем по частям.

#### Структура state (глобальное состояние)

```javascript
const state = {
    currentUser: null,          // Объект User из API
    spaces: [],                 // Массив Space объектов
    currentSpace: null,         // Выбранный Space
    currentChatId: null,        // ID текущего чата
    messages: [],               // Массив Message объектов
    wsClient: null              // Экземпляр WebSocketClient
};
```

#### Инициализация (init)

```javascript
async function init() {
    try {
        // 1. Получаем текущего пользователя
        state.currentUser = await API.getCurrentUser();
        updateUserProfile();

        // 2. Инициализируем WebSocket
        if (typeof WebSocketClient !== 'undefined') {
            initWebSocket();
        }

        // 3. Загружаем список пространств
        await loadSpaces();

    } catch (error) {
        console.error('Init error:', error);
        await Modal.error('Ошибка загрузки данных. Попробуйте перезайти.');
        AuthService.logout();
    }
}
```

**Проверка авторизации**:
```javascript
if (!AuthService.isAuthenticated()) {
    window.location.href = 'login.html';
    return;
}
```

#### WebSocket инициализация

```javascript
function initWebSocket() {
    state.wsClient = new WebSocketClient();
    state.wsClient.connect(state.currentUser.id, state.currentUser.nickname);

    // Обработчик новых сообщений
    state.wsClient.onMessage((data) => {
        // Проверяем что мы в нужной комнате
        if (data.room_id == state.currentChatId || data.chat_id == state.currentChatId) {

            // Если сообщение от другого пользователя - добавляем
            if (parseInt(data.user_id) !== parseInt(state.currentUser.id)) {
                const message = {
                    id: Date.now(),
                    user_id: parseInt(data.user_id),
                    content: data.message || data.content,
                    created_at: data.timestamp || new Date().toISOString(),
                    type: 'text'
                };

                state.messages.push(message);
                updateMessagesInChat();
            }
        }
    });
}
```

**Важно**: Собственные сообщения не добавляются повторно, так как они уже добавлены через HTTP API.

#### Загрузка и отображение пространств

```javascript
async function loadSpaces() {
    try {
        state.spaces = await API.getSpaces();
        renderSpaces();
    } catch (error) {
        console.error('Error loading spaces:', error);
        Modal.error('Ошибка загрузки пространств');
    }
}
```

**Генерация градиентов для иконок**:
```javascript
function generateGradientFromId(id) {
    const seed = id || 1;

    // Золотое сечение для распределения цветов
    const hue1 = (seed * 137.5) % 360;
    const hue2 = (hue1 + 60) % 360;

    const saturation = 65 + (seed % 20); // 65-85%
    const lightness = 45 + (seed % 15);  // 45-60%

    const color1 = `hsl(${hue1}, ${saturation}%, ${lightness}%)`;
    const color2 = `hsl(${hue2}, ${saturation}%, ${lightness - 5}%)`;

    return `linear-gradient(135deg, ${color1} 0%, ${color2} 100%)`;
}
```

Этот алгоритм генерирует уникальный, но стабильный градиент для каждого ID. Используется:
- Для иконок чатов (первая буква на градиентном фоне)
- Для аватаров пользователей в сообщениях

**Рендер списка пространств**:
```javascript
function renderSpaces() {
    chatListElement.innerHTML = '';

    if (state.spaces.length === 0) {
        chatListElement.innerHTML = '<li class="no-spaces">Нет доступных пространств</li>';
        return;
    }

    state.spaces.forEach(space => {
        const li = document.createElement('li');
        li.className = 'chat-item';
        li.dataset.spaceId = space.id;
        li.dataset.chatId = space.chat_id;

        const firstLetter = space.name.charAt(0).toUpperCase();
        const gradient = generateGradientFromId(space.chat_id || space.id);

        li.innerHTML = `
            <div class="chat-icon" style="background: ${gradient}">${firstLetter}</div>
            ${space.name}
        `;

        li.addEventListener('click', () => selectSpace(space));
        chatListElement.appendChild(li);
    });
}
```

#### Выбор пространства

```javascript
async function selectSpace(space) {
    if (!space.chat_id) {
        Modal.warning('У этого пространства нет чата');
        return;
    }

    // 1. Покидаем предыдущую комнату в WebSocket
    if (state.wsClient && state.currentChatId) {
        state.wsClient.leaveRoom(state.currentChatId, state.currentUser.id);
    }

    // 2. Обновляем активный элемент в списке
    document.querySelectorAll('.chat-item').forEach(item => {
        item.classList.remove('active');
    });
    const selectedItem = chatListElement.querySelector(`[data-space-id="${space.id}"]`);
    if (selectedItem) {
        selectedItem.classList.add('active');
    }

    // 3. Обновляем state
    state.currentSpace = space;
    state.currentChatId = space.chat_id;

    // 4. Присоединяемся к пространству через API
    try {
        await API.joinSpace(space.id);
    } catch (error) {
        console.error('Error joining space:', error);
        // Игнорируем если уже в пространстве
    }

    // 5. Присоединяемся к комнате через WebSocket
    if (state.wsClient) {
        state.wsClient.joinRoom(space.chat_id, state.currentUser.id, state.currentUser.nickname);
    }

    // 6. Загружаем сообщения
    await loadMessages();
}
```

#### Рендер чата

**Пустое состояние**:
```javascript
if (!state.currentSpace) {
    chatMainElement.innerHTML = `
        <div class="empty-chat-message">
            <img src="assets/icons/cat.svg" alt="Кот" class="empty-chat-cat">
            <p>Выберите чат для общения</p>
        </div>
    `;
    return;
}
```

**Активный чат**:
```javascript
chatMainElement.innerHTML = `
    <div class="chat-header">
        <h3>${state.currentSpace.name}</h3>
        <p class="chat-description">${state.currentSpace.description || ''}</p>
    </div>
    <div class="messages-container" id="messages-container">
        ${renderMessages()}
    </div>
    <div class="message-input-container">
        <form id="message-form">
            <input type="text" id="message-input" placeholder="Напишите сообщение..." required autocomplete="off">
            <img src="assets/icons/sendbutt.svg" alt="Отправить" class="send-button-icon">
        </form>
    </div>
`;

// Подключаем обработчики
const messageForm = document.getElementById('message-form');
const sendIcon = document.querySelector('.send-button-icon');

messageForm.addEventListener('submit', handleSendMessage);

if (sendIcon) {
    sendIcon.addEventListener('click', (e) => {
        e.preventDefault();
        handleSendMessage(e);
    });
}

scrollToBottom();
```

**Рендер сообщений**:
```javascript
function renderMessages() {
    if (state.messages.length === 0) {
        return '<div class="no-messages">Сообщений пока нет. Начните общение!</div>';
    }

    return state.messages.map(msg => {
        const isOwn = msg.user_id === state.currentUser.id;
        const time = new Date(msg.created_at).toLocaleTimeString('ru-RU', {
            hour: '2-digit',
            minute: '2-digit'
        });

        const authorName = isOwn ? 'Вы' : (msg.user_nickname || 'User#' + msg.user_id);

        // Аватарка с первой буквой
        const avatarLetter = isOwn
            ? (state.currentUser?.nickname ? state.currentUser.nickname.charAt(0).toUpperCase() : 'Я')
            : (msg.user_nickname ? msg.user_nickname.charAt(0).toUpperCase() : 'U');
        const avatarGradient = generateGradientFromId(msg.user_id);

        return `
            <div class="message ${isOwn ? 'own-message' : 'other-message'}">
                <div class="message-avatar" style="background: ${avatarGradient}">${avatarLetter}</div>
                <div class="message-body">
                    <div class="message-author">${authorName}</div>
                    <div class="message-content">${escapeHtml(msg.content)}</div>
                    <div class="message-time">${time}</div>
                </div>
            </div>
        `;
    }).join('');
}
```

**Классы сообщений**:
- `own-message` - собственное сообщение (справа, фиолетовый градиент)
- `other-message` - чужое сообщение (слева, серый)

#### Отправка сообщения

```javascript
async function handleSendMessage(event) {
    event.preventDefault();

    const input = document.getElementById('message-input');
    const content = input.value.trim();

    if (!content) return;

    try {
        // Отправляем через HTTP API
        const newMessage = await API.sendMessage(state.currentChatId, content);

        // Добавляем сообщение в state
        state.messages.push(newMessage);

        // Перерисовываем чат
        renderChat();

        // Очищаем поле
        input.value = '';

    } catch (error) {
        console.error('Error sending message:', error);
        Modal.error('Ошибка отправки сообщения: ' + error.message);
    }
}
```

**Почему HTTP, а не WebSocket?**
- HTTP гарантирует доставку и сохранение в БД
- WebSocket используется только для получения сообщений от других

#### Обновление сообщений через WebSocket

```javascript
function updateMessagesInChat() {
    const container = document.getElementById('messages-container');
    if (!container) return;

    // Берем последнее сообщение из state
    const lastMessage = state.messages[state.messages.length - 1];
    if (!lastMessage) return;

    // Генерируем HTML для одного сообщения
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isOwn ? 'own-message' : 'other-message'}`;
    messageDiv.innerHTML = `...`;

    // Удаляем заглушку если есть
    const noMessages = container.querySelector('.no-messages');
    if (noMessages) {
        noMessages.remove();
    }

    // Добавляем в конец
    container.appendChild(messageDiv);
    scrollToBottom();
}
```

Этот метод добавляет только новое сообщение без полной перерисовки, что более эффективно.

#### Создание новой комнаты

```javascript
newChatButton.addEventListener('click', async () => {
    const formData = await Modal.createRoom();

    if (!formData) return; // Отменено

    const { 'room-name': name, 'room-description': description } = formData;

    if (!name) {
        Modal.warning('Введите название комнаты');
        return;
    }

    try {
        const newSpace = await API.createSpace(name, description);

        // Перезагружаем список
        await loadSpaces();

        Modal.success('Комната успешно создана!');
    } catch (error) {
        console.error('Error creating space:', error);
        Modal.error('Ошибка при создании комнаты: ' + error.message);
    }
});
```

#### Настройки и выход

```javascript
// Настройки (заглушка)
settingsIcon.addEventListener('click', () => {
    Modal.alert('Настройки будут доступны позже', 'Настройки', 'info');
});

// Выход с подтверждением
logoutIcon.addEventListener('click', async () => {
    const confirmed = await Modal.confirm(
        'Вы уверены, что хотите выйти из аккаунта?',
        'Выход',
        { confirmText: 'Выйти', cancelText: 'Отмена', danger: true }
    );
    if (confirmed) {
        AuthService.logout();
    }
});
```

#### Утилиты

```javascript
// Защита от XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Скролл в конец чата
function scrollToBottom() {
    const container = document.getElementById('messages-container');
    if (container) {
        setTimeout(() => {
            container.scrollTop = container.scrollHeight;
        }, 100);
    }
}

// Обновление профиля
function updateUserProfile() {
    if (state.currentUser) {
        userNameElement.textContent = state.currentUser.nickname;
    }
}
```

---

## CSS стили

### 1. style.css

**Назначение**: Стили для страниц login.html и register.html.

**Основные элементы**:

1. **body**
   - Фон: градиент серых оттенков
   - Flexbox центрирование по вертикали и горизонтали
   - `min-height: 100vh` - минимум на весь экран

2. **form-container**
   - Белый фон
   - Скругленные углы (16px)
   - Тень для объема
   - Анимация появления (slideUp)

```css
.form-container {
    background-color: #fff;
    padding: 40px;
    border-radius: 16px;
    width: 100%;
    max-width: 420px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
    animation: slideUp 0.4s ease;
}

@keyframes slideUp {
    from {
        opacity: 0;
        transform: translateY(30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
```

3. **Поля ввода**
   - Светло-серый фон (#f8f9fa)
   - Скругленные углы
   - Переход на белый при фокусе
   - Кастомная тень при фокусе

```css
.form-group input:focus {
    outline: none;
    border-color: #555;
    background-color: #fff;
    box-shadow: 0 0 0 3px rgba(85, 85, 85, 0.1);
}
```

4. **Кнопка**
   - Темный градиент (#555 → #333)
   - Поднимается при hover (`translateY(-2px)`)
   - Увеличенная тень при hover

```css
button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
    background: linear-gradient(135deg, #666 0%, #444 100%);
}
```

5. **Ссылки**
   - Синий цвет (#3498db)
   - Подчеркивание при hover

---

### 2. modal.css

**Назначение**: Стили для модальных окон.

**Структура**:

1. **modal-overlay**
   - Полноэкранный затемненный фон
   - `position: fixed` - поверх всего контента
   - `z-index: 9999` - самый верхний слой
   - Анимация fadeIn/fadeOut

```css
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
    opacity: 0;
    animation: fadeIn 0.3s ease forwards;
}
```

2. **modal-window**
   - Светлый градиентный фон
   - Скругленные углы
   - Анимация scaleIn (увеличение от 0.8 до 1.0)

3. **modal-header**
   - Заголовок
   - Нижняя граница

4. **modal-body**
   - Контент модального окна
   - Может содержать иконку и текст или форму

```css
.modal-body.with-icon {
    display: flex;
    gap: 16px;
    align-items: flex-start;
}

.modal-icon {
    font-size: 48px;
    flex-shrink: 0;
}
```

5. **modal-footer**
   - Кнопки справа
   - Flexbox с gap между кнопками

6. **Кнопки**
   - `modal-button-primary` - основная (синяя/темная)
   - `modal-button-secondary` - вторичная (серая)
   - `modal-button-danger` - опасная (красная)

```css
.modal-button-primary {
    background: linear-gradient(135deg, #555 0%, #333 100%);
    color: white;
}

.modal-button-danger {
    background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
    color: white;
}
```

7. **Форма**
   - `modal-form-group` - группа поля
   - Стили похожи на основные формы

---

### 3. stylechat.css

**Назначение**: Стили для интерфейса чата.

Самый большой CSS файл. Разберем по компонентам.

#### Layout

```css
body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', ...;
    background-color: #fff;
    display: block;
    overflow: hidden; /* Фиксированная высота */
}

.chat-container {
    display: flex;
    height: 100vh;
    box-sizing: border-box;
}
```

4 колонки слева направо:
1. `.sidebar-dark-bar` - 70px темно-красная
2. `.sidebar` - 320px светло-серая
3. `.chat-main` - flex-grow (оставшееся пространство)
4. `.sidebar-right` - 70px коричневая

#### Темная панель слева

```css
.sidebar-dark-bar {
    width: 70px;
    background: #800000; /* Темно-красный */
    height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: flex-end; /* Иконки внизу */
    padding: 20px 0;
    align-items: center;
    box-shadow: 2px 0 5px rgba(0, 0, 0, 0.15);
    gap: 15px;
}
```

**Иконки**:
```css
.sidebar-icon {
    width: 32px;
    height: 32px;
    cursor: pointer;
    filter: brightness(0) invert(1); /* Белый цвет */
    opacity: 0.8;
    transition: all 0.3s ease;
    padding: 8px;
    border-radius: 8px;
}

.sidebar-icon:hover {
    opacity: 1;
    background-color: rgba(255, 255, 255, 0.1);
    transform: scale(1.1);
}
```

#### Сайдбар с чатами

```css
.sidebar {
    width: 320px;
    background-color: #d8d0c8; /* Светло-серый/бежевый */
    display: flex;
    flex-direction: column;
    border-right: 1px solid #bbb;
    position: relative;
}
```

**Профиль пользователя**:
```css
.user-profile {
    display: flex;
    align-items: center;
    padding: 20px 15px;
    border-bottom: 1px solid #bbb;
    background-color: #c8d0d8;
}

.user-avatar {
    width: 50px;
    height: 50px;
    border-radius: 50%;
    margin-right: 12px;
    border: 2px solid #666;
}
```

**Элемент чата**:
```css
.chat-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 15px;
    cursor: pointer;
    border-bottom: 1px solid #bbb;
    transition: all 0.2s ease;
    color: #2c3e50;
}

.chat-item:hover {
    background-color: #c8beb0;
}

.chat-item.active {
    background-color: #b8a898;
    border-left: 3px solid #555; /* Индикатор слева */
    font-weight: 600;
    color: #000;
}
```

**Иконка чата**:
```css
.chat-icon {
    width: 45px;
    height: 45px;
    border-radius: 50%;
    background: #555; /* Перезаписывается градиентом из JS */
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: bold;
    font-size: 18px;
    flex-shrink: 0;
}
```

**Кнопка создания чата**:
```css
.new-chat-button {
    position: absolute;
    bottom: 20px;
    right: 20px;
    width: 56px;
    height: 56px;
    cursor: pointer;
    transition: transform 0.3s ease;
}

.new-chat-button:hover {
    transform: scale(1.15);
}
```

#### Основная область чата

**Заголовок чата**:
```css
.chat-header {
    padding: 20px 24px;
    border-bottom: 2px solid #e0e0e0;
    background: linear-gradient(180deg, #f8f9fa 0%, #ffffff 100%);
}

.chat-header h3 {
    margin: 0 0 8px 0;
    font-size: 24px;
    font-weight: 600;
    color: #2c3e50;
}

.chat-description {
    margin: 0;
    color: #7f8c8d;
    font-size: 14px;
}
```

**Контейнер сообщений**:
```css
.messages-container {
    flex: 1;
    overflow-y: auto; /* Скролл */
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    background-color: #f5f5f5;
}
```

**Сообщение**:
```css
.message {
    display: flex;
    gap: 12px;
    max-width: 70%;
    animation: messageSlideIn 0.3s ease;
}

@keyframes messageSlideIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* Собственное сообщение справа */
.own-message {
    align-self: flex-end;
    flex-direction: row-reverse; /* Аватар справа */
}

/* Чужое сообщение слева */
.other-message {
    align-self: flex-start;
}
```

**Аватар в сообщении**:
```css
.message-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: #555; /* Перезаписывается градиентом */
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: bold;
    font-size: 16px;
    flex-shrink: 0;
    border: 2px solid #fff;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
```

**Тело сообщения**:
```css
.message-body {
    background: white;
    border-radius: 12px;
    padding: 10px 14px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

/* Собственное сообщение - фиолетовый градиент */
.own-message .message-body {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}

.message-author {
    font-weight: 600;
    font-size: 13px;
    margin-bottom: 4px;
}

.message-content {
    font-size: 15px;
    line-height: 1.4;
    word-wrap: break-word;
}

.message-time {
    font-size: 11px;
    margin-top: 4px;
    opacity: 0.7;
}
```

#### Форма отправки

```css
.message-input-container {
    padding: 16px 24px;
    background-color: #fff;
    border-top: 2px solid #e0e0e0;
}

#message-form {
    display: flex;
    gap: 12px;
    align-items: center;
}

#message-input {
    flex: 1;
    padding: 12px 16px;
    border: 2px solid #e5e5e5;
    border-radius: 24px; /* Скругленное поле */
    font-size: 15px;
    font-family: inherit;
    background-color: #f8f9fa;
    transition: all 0.2s ease;
}

#message-input:focus {
    outline: none;
    border-color: #555;
    background-color: #fff;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}
```

**Иконка отправки**:
```css
.send-button-icon {
    width: 72px; /* Увеличено с 48px */
    height: 72px;
    cursor: pointer;
    transition: all 0.2s ease;
    flex-shrink: 0;
}

.send-button-icon:hover {
    transform: scale(1.1);
}

.send-button-icon:active {
    transform: scale(1.05);
}
```

#### Пустое состояние

```css
.empty-chat-message {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 100%;
    text-align: center;
    gap: 20px;
}

.empty-chat-cat {
    width: 300px; /* Увеличено с 200px */
    height: 300px;
    animation: catFloat 3s ease-in-out infinite;
    filter: drop-shadow(0 4px 12px rgba(0, 0, 0, 0.1));
}

@keyframes catFloat {
    0%, 100% {
        transform: translateY(0) rotate(0deg);
    }
    25% {
        transform: translateY(-10px) rotate(2deg);
    }
    50% {
        transform: translateY(0) rotate(0deg);
    }
    75% {
        transform: translateY(-5px) rotate(-2deg);
    }
}
```

Анимация создает эффект плавающего кота с небольшими поворотами.

---

## Ресурсы и иконки

### SVG иконки в assets/icons/

1. **avatar.svg** - Аватар пользователя (в профиле)
2. **avatarchat.svg** - Иконка чата (не используется после рефакторинга)
3. **cat.svg** - Кот для пустого состояния (300x300px)
4. **newchat.svg** - Иконка создания чата (кнопка в сайдбаре)
5. **sendbutt.svg** - Иконка отправки сообщения (72x72px, красная)
6. **settings.svg** - Иконка настроек (встроена в HTML)

**Почему SVG?**
- Векторная графика - четкость при любом масштабе
- Малый размер файлов
- Возможность стилизации через CSS
- Поддержка градиентов и анимаций

---

## Технологии и паттерны

### 1. Vanilla JavaScript (ES6+)

**Используемые возможности ES6+**:
- `const` / `let` - блочная область видимости
- Arrow functions - `() => {}`
- Template literals - `` `Hello ${name}` ``
- Destructuring - `const { name, description } = formData`
- Async/await - асинхронный код
- Spread operator - `{ ...options }`
- Modules pattern - через window объект

### 2. Архитектурные паттерны

**Service Layer**:
```
AuthService - управление токенами
API - HTTP клиент
WebSocketClient - WebSocket клиент
Modal - система модальных окон
```

Каждый сервис инкапсулирует логику своей области.

**Module Pattern**:
Каждый JS файл - отдельный модуль с экспортом в window:
```javascript
window.AuthService = AuthService;
window.API = API;
window.CONFIG = CONFIG;
```

**State Management**:
Глобальный объект state в chat.js хранит состояние приложения:
```javascript
const state = {
    currentUser: null,
    spaces: [],
    currentSpace: null,
    currentChatId: null,
    messages: [],
    wsClient: null
};
```

**Event-Driven**:
- DOM события (click, submit)
- WebSocket события (new_message, user_joined)
- Кастомные callbacks (onMessage, onUserJoined)

### 3. Promise-based асинхронность

Все API методы возвращают Promise:
```javascript
async function login() {
    const response = await API.login(username, password);
    const user = await API.getCurrentUser();
    // ...
}
```

Модальные окна тоже Promise-based:
```javascript
const confirmed = await Modal.confirm('Удалить?');
if (confirmed) {
    await API.deleteMessage(messageId);
}
```

### 4. XSS защита

Экранирование HTML для предотвращения инъекций:
```javascript
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text; // textContent экранирует
    return div.innerHTML;
}
```

Используется при рендере сообщений:
```javascript
<div class="message-content">${escapeHtml(msg.content)}</div>
```

### 5. Responsive Design элементы

- `max-width` для форм
- Flexbox для layout
- `overflow-y: auto` для скроллинга
- `@media` запросы (если есть)

---

## Поток данных

### Регистрация и вход

```
1. Пользователь вводит данные
   ↓
2. login.js отправляет через API.login()
   ↓
3. API делает POST /auth/token
   ↓
4. Backend возвращает JWT токен
   ↓
5. AuthService.setToken() сохраняет в localStorage
   ↓
6. API.getCurrentUser() получает данные пользователя
   ↓
7. AuthService.setUser() сохраняет в localStorage
   ↓
8. Редирект на chat.html
```

### Загрузка чата

```
1. chat.js проверяет авторизацию
   ↓
2. Получает currentUser из localStorage
   ↓
3. Инициализирует WebSocket
   ↓
4. Загружает список spaces через API.getSpaces()
   ↓
5. Рендерит список в сайдбаре
   ↓
6. Пользователь кликает на space
   ↓
7. selectSpace() вызывается
   ↓
8. API.joinSpace() - присоединение через HTTP
   ↓
9. wsClient.joinRoom() - присоединение через WebSocket
   ↓
10. API.getMessages() - загрузка истории
   ↓
11. renderChat() - отображение сообщений
```

### Отправка сообщения

```
1. Пользователь вводит текст и нажимает Enter/иконку
   ↓
2. handleSendMessage() вызывается
   ↓
3. API.sendMessage() отправляет POST /messages/{chatId}
   ↓
4. Backend сохраняет в БД и рассылает через WebSocket
   ↓
5. API возвращает созданное сообщение
   ↓
6. state.messages.push(newMessage)
   ↓
7. renderChat() перерисовывает
   ↓
8. WebSocket получает то же сообщение, но игнорирует (свое)
```

### Получение чужого сообщения

```
1. Другой пользователь отправил сообщение
   ↓
2. Backend рассылает через WebSocket событие 'new_message'
   ↓
3. wsClient.onMessage() получает данные
   ↓
4. Проверка: правильная ли комната и не свое ли сообщение
   ↓
5. state.messages.push(message)
   ↓
6. updateMessagesInChat() добавляет только новое сообщение
   ↓
7. scrollToBottom() скроллит вниз
```

---

## WebSocket коммуникация

### Протокол Socket.IO

**Подключение**:
```javascript
const socket = io('http://localhost:8000', {
    transports: ['websocket', 'polling'],
    query: {
        user_id: 123,
        nickname: 'UserName'
    }
});
```

**Transports**:
- `websocket` - основной протокол (бинарный, низкая задержка)
- `polling` - fallback (HTTP long polling)

### События клиент → сервер

1. **join_room**
```javascript
socket.emit('join_room', {
    room_id: 456,
    user_id: 123,
    nickname: 'UserName'
});
```

2. **leave_room**
```javascript
socket.emit('leave_room', {
    room_id: 456,
    user_id: 123
});
```

3. **send_message** (опционально)
```javascript
socket.emit('send_message', {
    room_id: 456,
    user_id: 123,
    nickname: 'UserName',
    message: 'Hello!'
});
```

### События сервер → клиент

1. **connect** - успешное подключение
2. **disconnect** - отключение
3. **connected** - подтверждение от сервера с данными
4. **new_message** - новое сообщение в комнате
```javascript
{
    room_id: 456,
    chat_id: 456,
    user_id: 789,
    message: "Hello from another user",
    timestamp: "2025-10-28T12:34:56.789Z"
}
```

5. **user_joined_room** - пользователь зашел
6. **user_left_room** - пользователь вышел
7. **error** - ошибка

### Обработка в приложении

```javascript
wsClient.onMessage((data) => {
    // Фильтрация по комнате
    if (data.room_id == state.currentChatId) {
        // Фильтрация собственных сообщений
        if (data.user_id !== state.currentUser.id) {
            // Добавить в UI
            state.messages.push(message);
            updateMessagesInChat();
        }
    }
});
```

---

## Взаимодействие с Backend

### API эндпоинты

**Authentication**:
- POST `/auth/register` - регистрация
- POST `/auth/token` - получение токена
- GET `/auth/me` - текущий пользователь

**Spaces**:
- GET `/spaces/` - список пространств
- POST `/spaces/` - создать пространство
- POST `/spaces/{id}/join` - присоединиться
- GET `/spaces/{id}/participants` - участники

**Messages**:
- GET `/messages/{chatId}` - получить сообщения
- POST `/messages/{chatId}` - отправить сообщение
- GET `/messages/{chatId}/search` - поиск

### Формат данных

**User**:
```json
{
    "id": 123,
    "nickname": "UserName",
    "email": "user@example.com",
    "created_at": "2025-10-28T12:00:00Z"
}
```

**Space**:
```json
{
    "id": 456,
    "name": "My Space",
    "description": "Description here",
    "admin_id": 123,
    "chat_id": 789,
    "created_at": "2025-10-28T12:00:00Z"
}
```

**Message**:
```json
{
    "id": 999,
    "chat_id": 789,
    "user_id": 123,
    "user_nickname": "UserName",
    "content": "Hello world!",
    "type": "text",
    "created_at": "2025-10-28T12:34:56Z",
    "is_deleted": false
}
```

**Token response**:
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
}
```

### Авторизация

JWT токен передается в заголовке:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

При 401 ошибке автоматический logout:
```javascript
if (response.status === 401) {
    AuthService.logout();
    throw new Error('Сессия истекла. Войдите снова.');
}
```

### CORS

Backend настроен на `allow_origins=["*"]` для разработки.

В продакшене должен быть:
```python
allow_origins=["http://localhost:3000", "https://yourapp.com"]
```

---

## Заключение

Этот фронтенд представляет собой полноценное SPA (Single Page Application) на чистом JavaScript без фреймворков.

**Преимущества подхода**:
- Нет зависимостей от фреймворков
- Полный контроль над кодом
- Быстрая загрузка (малый размер)
- Простота отладки

**Ограничения**:
- Ручное управление DOM
- Нет реактивности из коробки
- Больше boilerplate кода
- Масштабирование требует дисциплины

**Возможные улучшения**:
- Добавить виртуальный скроллинг для больших списков
- Реализовать оптимистичные UI обновления
- Добавить offline support через Service Workers
- Использовать IndexedDB для кеширования
- Добавить поддержку файлов/изображений
- Реализовать редактирование/удаление сообщений
- Добавить индикаторы набора текста (typing indicators)
- Реализовать приватные сообщения
