# Журнал разработки The Space

## 2025-10-28 - Инициализация проекта

- Настроена базовая структура проекта
- Создана документация по архитектуре
- Инициализирован журнал разработки

---

## Исправление UI проблем фронтенда

### Реализованные возможности

- Настройка CORS
- Система аутентификации
- Базовая функциональность чата
- Модальные окна
- Градиентные иконки для чатов
- Аватары в сообщениях
- Цветовая схема (темно-красный #8B0000 для левой панели)

---

### Исправление путей к SVG иконкам

**Проблема:** SVG иконки `cat.svg` и `newchat.svg` не загружались - отображались как сломанные изображения.

**Причина:**
- Файлы находились в `assets/icons/`
- В коде использовались неверные пути `assets/cat.svg` и `assets/newchat.svg`

**Решение:** Исправлены пути во всех файлах на `assets/icons/cat.svg` и `assets/icons/newchat.svg`

**Измененные файлы:**
- `MIN/chat.html` - путь к иконке кота в пустом состоянии
- `MIN/js/chat.js` - путь к иконке в функции рендеринга
- Кнопка создания чата - путь к иконке `newchat.svg`

---

### Исправление модального окна создания комнаты

**Проблема:** Кнопка "Создать" в модальном окне не работала - не создавалась комната, окно не закрывалось, ошибок не было.

**Диагностика:** Обработчик `submit` формы не срабатывал, несмотря на правильную установку обработчика событий.

**Решение:** Переработана архитектура обработки событий в `MIN/js/modal.js`

**Было:**
- Обработчик клика проверял `isPrimary` и ничего не делал для главной кнопки
- Ожидалось срабатывание события `submit` формы
- Событие `submit` никогда не срабатывало

**Стало:**
- Вся логика перенесена в обработчик клика кнопки
- Сбор данных формы происходит напрямую при клике
- Обработчик `submit` удален

**Результат:** Создание комнат работает корректно.

---

### Изменение цветовой схемы кнопки отправки

**Задача:** Изменить цвет кнопки отправки с фиолетового на темно-красный (в соответствии с цветом левой панели).

**Реализация:** В `MIN/css/stylechat.css` изменен градиент:
- Было: `linear-gradient(135deg, #667eea 0%, #764ba2 100%)` (фиолетовый)
- Стало: `linear-gradient(135deg, #a52a2a 0%, #8B0000 100%)` (темно-красный)

---

### Замена кнопки отправки на иконку

**Задача:** Заменить текстовую кнопку "Отправить" на SVG иконку `sendbutt.svg`.

**Реализация:**

1. **HTML структура** (`MIN/js/chat.js`):
   - Удален элемент `<button type="submit" class="send-button">Отправить</button>`
   - Добавлен `<img src="assets/icons/sendbutt.svg" alt="Отправить" class="send-button-icon">`

2. **Обработчики событий**:
   - Сохранен обработчик `submit` формы для Enter
   - Добавлен обработчик клика по иконке

3. **Стили** (`MIN/css/stylechat.css`):
   - Удалены сложные стили кнопки (градиенты, padding, shadows)
   - Добавлены простые стили для иконки: размер 48x48px, hover эффект (scale 1.1)

---

### Увеличение размера иконки отправки

**Задача:** Увеличить иконку отправки в 1.5 раза.

**Реализация:** Изменен размер в `MIN/css/stylechat.css`:
- Было: 48x48px
- Стало: 72x72px

---

### Увеличение размера иконки кота

**Задача:** Увеличить иконку кота в пустом состоянии чата в 1.5 раза.

**Реализация:** Изменен размер в `MIN/css/stylechat.css`:
- Было: 200x200px
- Стало: 300x300px

**Детали:** Сохранены все визуальные эффекты (анимация `catFloat`, drop shadow).

---

## 2025-11-06 - Редактирование и удаление сообщений

### Добавлены API методы

**Файл:** `MIN/js/api.js`

Добавлены методы для работы с сообщениями:
```javascript
async updateMessage(chatId, messageId, content) {
    return this.patch(`/messages/${chatId}/${messageId}`, { content });
}

async deleteMessage(chatId, messageId) {
    return this.delete(`/messages/${chatId}/${messageId}`);
}
```

---

### UI для редактирования и удаления

**Файл:** `MIN/js/chat.js`

#### Кнопки действий
- Добавлены кнопки редактирования и удаления для собственных сообщений
- Кнопки отображаются только при наведении курсора

#### Inline редактирование
При клике на кнопку редактирования:
1. Текст сообщения заменяется на поле ввода
2. Доступны кнопки "Сохранить" (✓) и "Отмена" (✕)
3. Поддержка клавиш Enter (сохранить) и Escape (отмена)
4. После сохранения: PATCH запрос → обновление UI → broadcast через Socket.IO

#### Удаление сообщений
При клике на кнопку удаления:
1. Модальное окно подтверждения
2. DELETE запрос → удаление из UI → broadcast через Socket.IO

---

### Socket.IO обработчики (клиент)

**Файл:** `MIN/js/chat.js`

#### Обработчик редактирования
```javascript
state.wsClient.socket.on('message_edited', (data) => {
    if (data.user_id == state.currentUser.id) return; // Игнорируем свои события

    // Обновляем в state
    const message = state.messages.find(m => m.id == data.message_id);
    if (message) message.content = data.content;

    // Обновляем в DOM
    const messageElement = document.querySelector(`.message[data-message-id="${data.message_id}"]`);
    if (messageElement) {
        messageElement.querySelector('.message-content').textContent = data.content;
    }
});
```

#### Обработчик удаления
```javascript
state.wsClient.socket.on('message_deleted', (data) => {
    if (data.user_id == state.currentUser.id) return; // Игнорируем свои события

    // Удаляем из state и DOM
    state.messages = state.messages.filter(m => m.id != data.message_id);
    document.querySelector(`.message[data-message-id="${data.message_id}"]`)?.remove();
});
```

**Важно:** Фильтрация собственных событий происходит на клиенте по `user_id` для избежания дублирования (локальное обновление UI уже выполнено).

---

### Socket.IO обработчики (сервер)

**Файл:** `utils/socketio_handlers.py`

Добавлены обработчики событий:

```python
@sio.event
async def edit_message(sid, data):
    room_id = str(data.get('room_id'))
    message_id = data.get('message_id')
    content = data.get('content')
    user_id = data.get('user_id')

    await sio.emit('message_edited', {
        'room_id': room_id,
        'message_id': message_id,
        'content': content,
        'user_id': user_id
    }, room=room_id)

@sio.event
async def delete_message(sid, data):
    room_id = str(data.get('room_id'))
    message_id = data.get('message_id')
    user_id = data.get('user_id')

    await sio.emit('message_deleted', {
        'room_id': room_id,
        'message_id': message_id,
        'user_id': user_id
    }, room=room_id)
```

События рассылаются всем участникам комнаты, клиент сам фильтрует свои события.

---

### Стилизация

**Файл:** `MIN/css/stylechat.css`

#### Кнопки действий
```css
.message-actions {
    display: flex;
    gap: 6px;
    margin-top: 6px;
    opacity: 0;
    transition: opacity 0.2s ease;
}

.message:hover .message-actions {
    opacity: 1;
}
```

#### Форма редактирования
```css
.message-edit-input {
    flex: 1;
    padding: 8px 12px;
    border: 2px solid #667eea;
    border-radius: 12px;
    font-size: 14px;
    background: white;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}
```

---

### Решение проблемы с realtime

**Проблема:** События `message_edited` и `message_deleted` не доходили до других пользователей.

**Причина:** Использование параметра `skip_sid` в `sio.emit()` приводило к некорректной работе broadcast.

**Решение:** Удален `skip_sid`, реализована клиентская фильтрация по `user_id`.

---

## Итоговые изменения

### Измененные файлы
1. `MIN/chat.html` - пути к SVG иконкам
2. `MIN/js/chat.js` - пути, иконка отправки, редактирование/удаление сообщений
3. `MIN/js/modal.js` - обработка событий модальных окон
4. `MIN/css/stylechat.css` - размеры иконок, стили редактирования/удаления
5. `MIN/js/api.js` - методы для работы с сообщениями
6. `utils/socketio_handlers.py` - обработчики Socket.IO событий

### Реализованный функционал
- ✅ Исправлены пути к SVG иконкам
- ✅ Модальные окна работают корректно
- ✅ Иконка отправки вместо текстовой кнопки
- ✅ Увеличены размеры интерактивных элементов
- ✅ Цветовая схема приведена к единому стилю
- ✅ Редактирование собственных сообщений
- ✅ Удаление собственных сообщений
- ✅ Realtime синхронизация изменений между пользователями
- ✅ Inline редактирование с поддержкой клавиатуры
- ✅ Модальные подтверждения для деструктивных действий

---
