# 🚀 Полная инструкция по установке и запуску The Space

Этот документ содержит пошаговую инструкцию по установке, настройке и запуску проекта **The Space**.

---

## 📋 Содержание

1. [Системные требования](#системные-требования)
2. [Установка Python](#установка-python)
3. [Установка PostgreSQL](#установка-postgresql)
4. [Клонирование проекта](#клонирование-проекта)
5. [Настройка виртуального окружения](#настройка-виртуального-окружения)
6. [Установка зависимостей](#установка-зависимостей)
7. [Настройка базы данных](#настройка-базы-данных)
8. [Конфигурация переменных окружения](#конфигурация-переменных-окружения)
9. [Запуск приложения](#запуск-приложения)
10. [Тестирование](#тестирование)
11. [Возможные проблемы и решения](#возможные-проблемы-и-решения)

---

## 1. Системные требования

### Минимальные требования:
- **ОС:** Windows 10/11, Linux, macOS
- **Процессор:** 2+ ядра
- **RAM:** 4 GB+
- **Свободное место:** 500 MB+

### Необходимое ПО:
- **Python:** 3.13 или выше
- **PostgreSQL:** 13 или выше
- **Git:** последняя версия
- **pip:** менеджер пакетов Python (устанавливается с Python)

---

## 2. Установка Python

### Windows:

1. Скачайте Python с официального сайта: https://www.python.org/downloads/
2. Запустите установщик
3. **ВАЖНО:** Отметьте галочку "Add Python to PATH"
4. Нажмите "Install Now"
5. Проверьте установку:
```bash
python --version
```

Вы должны увидеть версию Python 3.13 или выше.

### Linux (Ubuntu/Debian):

```bash
sudo apt update
sudo apt install python3.13 python3.13-venv python3-pip
```

### macOS:

```bash
brew install python@3.13
```

---

## 3. Установка PostgreSQL

### Windows:

1. Скачайте PostgreSQL: https://www.postgresql.org/download/windows/
2. Запустите установщик
3. Следуйте инструкциям установщика
4. **Запомните пароль для пользователя `postgres`!**
5. Убедитесь, что PostgreSQL запущен:
   - Откройте "Службы" (services.msc)
   - Найдите "PostgreSQL" и проверьте, что служба запущена

### Linux (Ubuntu/Debian):

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### macOS:

```bash
brew install postgresql@13
brew services start postgresql@13
```

### Проверка установки:

```bash
psql --version
```

---

## 4. Клонирование проекта

### Если у вас еще нет Git:

**Windows:** Скачайте с https://git-scm.com/download/win

**Linux:**
```bash
sudo apt install git
```

**macOS:**
```bash
brew install git
```

### Клонирование репозитория:

```bash
git clone https://github.com/your-username/the_space.git
cd the_space
```

Или скачайте ZIP архив и распакуйте его.

---

## 5. Настройка виртуального окружения

Виртуальное окружение изолирует зависимости проекта от системного Python.

### Создание виртуального окружения:

**Windows:**
```bash
python -m venv venv
```

**Linux/macOS:**
```bash
python3 -m venv venv
```

### Активация виртуального окружения:

**Windows (CMD):**
```bash
venv\Scripts\activate
```

**Windows (PowerShell):**
```bash
venv\Scripts\Activate.ps1
```

Если PowerShell выдает ошибку политики выполнения:
```bash
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Linux/macOS:**
```bash
source venv/bin/activate
```

После активации вы увидите `(venv)` в начале строки терминала.

---

## 6. Установка зависимостей

С активированным виртуальным окружением:

```bash
pip install -r requirements.txt
```

Это установит все необходимые библиотеки:
- FastAPI
- Uvicorn
- SQLAlchemy + asyncpg
- python-socketio
- pydantic
- python-jose (для JWT)
- passlib (для хеширования паролей)
- slowapi (для rate limiting)

### Проверка установки:

```bash
pip list
```

---

## 7. Настройка базы данных

### Создание базы данных PostgreSQL:

#### Windows:

1. Откройте командную строку (cmd)
2. Подключитесь к PostgreSQL:
```bash
psql -U postgres
```
(Введите пароль, который вы указали при установке PostgreSQL)

3. Создайте базу данных:
```sql
CREATE DATABASE chat_db;
```

4. Создайте пользователя (опционально):
```sql
CREATE USER chat_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE chat_db TO chat_user;
```

5. Выйдите из psql:
```sql
\q
```

#### Linux/macOS:

```bash
# Переключитесь на пользователя postgres
sudo -u postgres psql

# В psql выполните:
CREATE DATABASE chat_db;
CREATE USER chat_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE chat_db TO chat_user;
\q
```

### Проверка подключения:

```bash
psql -U postgres -d chat_db -c "SELECT version();"
```

---

## 8. Конфигурация переменных окружения

### Создание файла `.env`:

В корне проекта создайте файл `.env` (без расширения!):

**Windows (через блокнот):**
```bash
notepad .env
```

**Linux/macOS:**
```bash
nano .env
```

### Содержимое `.env`:

```env
# Секретный ключ для JWT (ОБЯЗАТЕЛЬНО ИЗМЕНИТЕ!)
SECRET_KEY=your-super-secret-key-change-this-in-production-12345

# URL подключения к базе данных
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost/chat_db
```

### Генерация секретного ключа:

**Python:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Скопируйте сгенерированный ключ и вставьте его в `.env` вместо `your-super-secret-key-change-this-in-production-12345`.

### Формат DATABASE_URL:

```
postgresql+asyncpg://username:password@host:port/database_name
```

**Примеры:**

Стандартный пользователь postgres:
```
DATABASE_URL=postgresql+asyncpg://postgres:mypassword@localhost/chat_db
```

Кастомный пользователь:
```
DATABASE_URL=postgresql+asyncpg://chat_user:chat_password@localhost/chat_db
```

Удаленный сервер:
```
DATABASE_URL=postgresql+asyncpg://user:pass@192.168.1.100:5432/chat_db
```

---

## 9. Запуск приложения

### Проверка конфигурации:

Убедитесь, что:
1. ✅ Виртуальное окружение активировано `(venv)`
2. ✅ PostgreSQL запущен
3. ✅ База данных `chat_db` создана
4. ✅ Файл `.env` настроен

### Запуск сервера:

**Способ 1 - Через main.py:**
```bash
python main.py
```

**Способ 2 - Через uvicorn:**
```bash
uvicorn main:socket_app --host 0.0.0.0 --port 8000 --reload
```

`--reload` включает автоперезагрузку при изменении кода (для разработки).

### Успешный запуск:

Вы должны увидеть:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Database tables created
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## 10. Тестирование

### Swagger UI (API документация):

Откройте в браузере:
```
http://localhost:8000/docs
```

Здесь вы можете:
- Посмотреть все endpoints
- Протестировать API прямо в браузере
- Увидеть схемы запросов/ответов

### Тестовый HTML клиент:

1. Убедитесь, что сервер запущен
2. Откройте файл `test_client.html` в браузере
3. Выполните тесты:
   - Зарегистрируйте пользователя
   - Войдите в систему
   - Создайте приватный чат
   - Отправьте сообщения в реальном времени

### Проверка Socket.IO подключения:

В консоли браузера (F12) вы должны увидеть:
```
Socket connected: xyz123
```

---

## 11. Возможные проблемы и решения

### Проблема 1: `ModuleNotFoundError: No module named 'asyncpg'`

**Решение:**
```bash
pip install asyncpg
```

---

### Проблема 2: PostgreSQL не запускается

**Windows:**
```bash
# Откройте services.msc
# Найдите PostgreSQL и нажмите "Запустить"
```

**Linux:**
```bash
sudo systemctl start postgresql
sudo systemctl status postgresql
```

---

### Проблема 3: Ошибка подключения к БД

**Проверьте:**
1. PostgreSQL запущен
2. Правильный пароль в `.env`
3. База данных существует:
```bash
psql -U postgres -l
```

**Решение:**
```bash
# Пересоздайте базу данных
psql -U postgres
DROP DATABASE IF EXISTS chat_db;
CREATE DATABASE chat_db;
\q
```

---

### Проблема 4: `[Errno 10048] error while attempting to bind on address`

**Причина:** Порт 8000 уже занят.

**Решение:**
```bash
# Используйте другой порт
python main.py --port 8001

# Или найдите и остановите процесс на порту 8000
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/macOS:
lsof -i :8000
kill -9 <PID>
```

---

### Проблема 5: `uvicorn.run()` не работает

**Решение:**
```bash
# Обновите uvicorn
pip install --upgrade uvicorn

# Или используйте последнюю версию
pip install uvicorn==0.37.0
```

---

### Проблема 6: Ошибки с websockets

**Решение:**
```bash
# Установите правильную версию websockets
pip install "websockets<15.0"
```

Или проверьте, что в `main.py` есть:
```python
uvicorn.run(socket_app, host="0.0.0.0", port=8000, ws="none")
```

---

### Проблема 7: `.env` файл не читается

**Проверьте:**
1. Файл называется `.env` (с точкой в начале)
2. Файл находится в корне проекта (рядом с `main.py`)
3. Нет пробелов вокруг `=`

**Пример правильного `.env`:**
```env
SECRET_KEY=abc123
DATABASE_URL=postgresql+asyncpg://postgres:pass@localhost/chat_db
```

---

## 🎉 Готово!

Теперь ваше приложение **The Space** запущено и готово к работе!

**Полезные ссылки:**
- API документация: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Тестовый клиент: откройте `test_client.html`

**Команды для работы:**
```bash
# Активировать виртуальное окружение
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/macOS

# Запустить сервер
python main.py

# Остановить сервер
Ctrl + C

# Деактивировать виртуальное окружение
deactivate
```

---

## 📞 Поддержка

Если у вас возникли проблемы:
1. Проверьте раздел "Возможные проблемы и решения"
2. Убедитесь, что выполнены все шаги инструкции
3. Проверьте логи в консоли
4. Создайте issue в GitHub репозитории

---

**Успешной работы с The Space! 🚀**
