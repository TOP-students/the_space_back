# The Space - Real-time Social Platform

**The Space** — это современная социальная платформа для общения в реальном времени, построенная на FastAPI и Socket.IO. Проект поддерживает создание пространств (spaces), приватные и групповые чаты, систему ролей и прав доступа.

## 🌟 Основные возможности

- **Real-time коммуникация** через WebSocket (Socket.IO)
- **Приватные чаты** между пользователями
- **Пространства (Spaces)** с групповыми чатами
- **Система ролей** с гибкими правами доступа (RBAC)
- **JWT аутентификация** с OAuth2 flow
- **Rate limiting** для защиты от злоупотреблений
- **Асинхронная архитектура** для высокой производительности
- **Статусы пользователей** (online/offline) в реальном времени

## 📁 Структура проекта

```
the_space/
├── main.py                    # Точка входа, инициализация приложения
├── requirements.txt           # Зависимости проекта
├── test_client.html          # Тестовый HTML клиент для проверки API
│
├── models/                    # SQLAlchemy модели базы данных
│   ├── __init__.py           # Экспорт всех моделей
│   ├── base.py               # Базовый класс для моделей
│   ├── user.py               # Модель пользователя
│   ├── chat.py               # Модели чата и участников (Chat, ChatParticipant)
│   ├── message.py            # Модели сообщения и вложений (Message, Attachment)
│   ├── space.py              # Модель пространства
│   ├── role.py               # Модели ролей (Role, UserRole)
│   └── ban.py                # Модель банов
│
├── schemas/                   # Pydantic схемы для валидации
│   ├── __init__.py           # Экспорт всех схем
│   ├── auth.py               # Схемы аутентификации (Token)
│   ├── user.py               # UserCreate, UserOut
│   ├── chat.py               # PrivateChatCreate, ChatResponse
│   ├── message.py            # MessageCreate, MessageOut
│   ├── space.py              # SpaceCreate, SpaceOut
│   ├── role.py               # RoleCreate, RoleOut
│   └── ban.py                # BanCreate
│
├── routers/                   # API endpoints (FastAPI роутеры)
│   ├── __init__.py           # Экспорт роутеров
│   ├── auth.py               # Регистрация, логин, выход
│   ├── chats.py              # Управление чатами и сообщениями
│   ├── spaces.py             # Управление пространствами, участниками, банами
│   └── roles.py              # Управление ролями и правами
│
├── utils/                     # Вспомогательные модули
│   ├── __init__.py           # Экспорт утилит
│   ├── database.py           # Подключение к БД, создание сессий
│   ├── security.py           # JWT токены, хеширование паролей
│   ├── dependencies.py       # FastAPI dependencies (get_current_user)
│   └── permissions.py        # Проверка прав доступа
│
└── websockets/                # Socket.IO обработчики
    ├── __init__.py           # Экспорт handlers
    └── handlers.py           # Обработчики событий (connect, join_room, send_message)
```

## 🛠 Технологический стек

- **Backend:** FastAPI (Python 3.13+)
- **Database:** PostgreSQL + asyncpg
- **Real-time:** Socket.IO (python-socketio)
- **ORM:** SQLAlchemy 2.0 (async)
- **Authentication:** JWT (python-jose)
- **Password Hashing:** bcrypt (passlib)
- **Validation:** Pydantic v2
- **Rate Limiting:** slowapi
- **ASGI Server:** Uvicorn

## 🚀 Быстрый старт

### Требования

- Python 3.13+
- PostgreSQL 13+
- pip

### Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-username/the_space.git
cd the_space
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Настройте переменные окружения (создайте `.env`):
```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql+asyncpg://user:password@localhost/chat_db
```

5. Создайте базу данных PostgreSQL:
```bash
createdb chat_db
```

6. Запустите приложение:
```bash
python main.py
```

Сервер будет доступен по адресу: http://localhost:8000

**API документация:** http://localhost:8000/docs

**Тестовый клиент:** откройте `test_client.html` в браузере

## 📚 Подробная инструкция

Полная инструкция по установке и настройке доступна в [SETUP.md](SETUP.md)

## 🏗 Архитектура

### REST API + WebSocket

Приложение использует гибридную архитектуру:
- **REST API** (FastAPI) для CRUD операций
- **WebSocket** (Socket.IO) для real-time обновлений

### Асинхронность

Все операции с БД полностью асинхронные:
- `AsyncSession` для работы с PostgreSQL
- `asyncpg` драйвер для максимальной производительности
- `async/await` во всех handlers

### Безопасность

- JWT токены с истечением срока действия
- Bcrypt хеширование паролей
- Rate limiting на критичных endpoints
- RBAC система прав доступа
- Проверка банов при входе в пространства

## 📝 API Endpoints

### Authentication
- `POST /register` - Регистрация нового пользователя
- `POST /token` - Вход (получение JWT токена)
- `POST /logout` - Выход из системы

### Chats
- `POST /chats` - Создать приватный чат
- `GET /chats/{chat_id}/messages` - Получить сообщения
- `POST /chats/{chat_id}/messages` - Отправить сообщение

### Spaces
- `POST /spaces` - Создать пространство
- `POST /spaces/{space_id}/join` - Присоединиться к пространству
- `GET /spaces/{space_id}/participants` - Список участников
- `POST /spaces/{space_id}/kick/{user_id}` - Исключить участника
- `POST /spaces/{space_id}/ban/{user_id}` - Забанить пользователя

### Roles
- `POST /spaces/{space_id}/roles` - Создать роль
- `POST /spaces/{space_id}/assign-role/{user_id}/{role_id}` - Назначить роль

### Socket.IO Events

**Client → Server:**
- `connect` - Подключение (с JWT токеном)
- `join_room` - Присоединиться к чату
- `leave_room` - Покинуть чат
- `send_message` - Отправить сообщение

**Server → Client:**
- `user_status_changed` - Статус пользователя изменился
- `user_joined` - Пользователь присоединился к чату
- `user_left` - Пользователь покинул чат
- `new_message` - Новое сообщение в чате

## 🧪 Тестирование

Откройте `test_client.html` в браузере после запуска сервера.

Тестовый клиент позволяет:
- Зарегистрировать пользователя
- Войти в систему
- Создать приватный чат
- Отправлять и получать сообщения в реальном времени

## 👥 Автор

Создано в рамках учебного проекта TopAcademy
