// Основная логика чата
document.addEventListener('DOMContentLoaded', async function() {

    // Проверка авторизации
    if (!AuthService.isAuthenticated()) {
        window.location.href = 'login.html';
        return;
    }

    // Состояние приложения
    const state = {
        currentUser: null,
        spaces: [],
        currentSpace: null,
        currentChatId: null,
        messages: [],
        wsClient: null,
        emojiPicker: null
    };

    // DOM элементы
    const userNameElement = document.querySelector('.user-name');
    const chatListElement = document.querySelector('.chat-list ul');
    const chatMainElement = document.querySelector('.chat-main');
    const sidebarRight = document.querySelector('.sidebar-right');
    const sidebarRightContent = document.querySelector('.sidebar-right-content');
    const sidebarRightToggle = document.getElementById('sidebar-right-toggle');
    const settingsIcon = document.querySelector('.settings-icon');
    const logoutIcon = document.querySelector('.logout-icon');
    const newChatButton = document.querySelector('.new-chat-button');
    const userProfile = document.querySelector('.user-profile');
    const profileModal = document.getElementById('profile-modal');
    const profileModalContent = profileModal?.querySelector('.profile-modal-content');

    // Элементы для загрузки файлов
    const avatarUploadBtn = document.getElementById('avatar-upload-btn');
    const bannerUploadBtn = document.getElementById('banner-upload-btn');
    const avatarFileInput = document.getElementById('avatar-file-input');
    const bannerFileInput = document.getElementById('banner-file-input');

    // Инициализация
    async function init() {
        try {
            // Получаем данные пользователя
            state.currentUser = await API.getCurrentUser();
            updateUserProfile();

            // Инициализируем WebSocket (если доступен)
            if (typeof WebSocketClient !== 'undefined') {
                initWebSocket();
            }

            // Загружаем список пространств
            await loadSpaces();

        } catch (error) {
            console.error('Init error:', error);
            await Modal.error('Ошибка загрузки данных. Попробуйте перезайти.');
            AuthService.logout();
        }
    }

    // Инициализация WebSocket
    function initWebSocket() {
        state.wsClient = new WebSocketClient();
        state.wsClient.connect(state.currentUser.id, state.currentUser.nickname);

        // Обработчик новых сообщений
        state.wsClient.onMessage((data) => {
            console.log('WS: New message received', data);

            // Проверяем что мы в нужной комнате
            if (data.room_id == state.currentChatId || data.chat_id == state.currentChatId) {

                // Добавляем сообщение для всех (включая отправителя)
                const message = {
                    id: data.id || Date.now(),
                    user_id: parseInt(data.user_id),
                    content: data.message || data.content,
                    created_at: data.created_at || data.timestamp || new Date().toISOString(),
                    user_nickname: data.user_nickname || data.nickname,
                    user_avatar_url: data.user_avatar_url,
                    type: data.type || 'text'
                };

                state.messages.push(message);
                updateMessagesInChat();
            }
        });

        // Обработчик редактирования сообщений
        state.wsClient.socket.on('message_edited', (data) => {
            console.log('WS: Message edited', data);

            // Игнорируем свои собственные изменения (они уже применены локально)
            if (data.user_id == state.currentUser.id) {
                console.log('Ignoring own edit event');
                return;
            }

            console.log('Current chat ID:', state.currentChatId);
            console.log('Message ID to find:', data.message_id);

            if (data.room_id == state.currentChatId) {
                // Обновляем сообщение в локальном стейте
                const message = state.messages.find(m => m.id == data.message_id);
                if (message) {
                    message.content = data.content;
                    console.log('Updated message in state:', message);
                } else {
                    console.warn('Message not found in state');
                }

                // Обновляем UI
                const messageElement = document.querySelector(`.message[data-message-id="${data.message_id}"]`);
                console.log('Found message element:', messageElement);

                if (messageElement) {
                    const contentElement = messageElement.querySelector('.message-content');
                    console.log('Found content element:', contentElement);

                    if (contentElement) {
                        contentElement.textContent = data.content;
                        contentElement.dataset.originalContent = data.content;
                        console.log('UI updated successfully');
                    } else {
                        console.error('Content element not found');
                    }
                } else {
                    console.error('Message element not found, trying all messages:', document.querySelectorAll('.message'));
                }
            } else {
                console.log('Room mismatch, ignoring edit');
            }
        });

        // Обработчик удаления сообщений
        state.wsClient.socket.on('message_deleted', (data) => {
            console.log('WS: Message deleted', data);

            // Игнорируем свои собственные удаления (они уже применены локально)
            if (data.user_id == state.currentUser.id) {
                console.log('Ignoring own delete event');
                return;
            }

            console.log('Current chat ID:', state.currentChatId);
            console.log('Message ID to delete:', data.message_id);

            if (data.room_id == state.currentChatId) {
                // Удаляем из локального стейта
                const beforeCount = state.messages.length;
                state.messages = state.messages.filter(m => m.id != data.message_id);
                console.log(`Messages count: ${beforeCount} -> ${state.messages.length}`);

                // Удаляем из UI
                const messageElement = document.querySelector(`.message[data-message-id="${data.message_id}"]`);
                console.log('Found message element to delete:', messageElement);

                if (messageElement) {
                    messageElement.remove();
                    console.log('Message deleted from UI successfully');
                } else {
                    console.error('Message element not found, trying all messages:', document.querySelectorAll('.message'));
                }
            } else {
                console.log('Room mismatch, ignoring delete');
            }
        });
    }

    // Обновить профиль пользователя
    function updateUserProfile() {
        if (state.currentUser) {
            userNameElement.textContent = state.currentUser.nickname;

            // Обновляем аватар в сайдбаре
            const sidebarAvatar = document.querySelector('.user-avatar');
            if (sidebarAvatar && state.currentUser.avatar_url) {
                sidebarAvatar.src = state.currentUser.avatar_url;
                sidebarAvatar.style.objectFit = 'cover';
            }
        }
    }

    // Загрузить список пространств
    async function loadSpaces() {
        try {
            state.spaces = await API.getSpaces();
            renderSpaces();
        } catch (error) {
            console.error('Error loading spaces:', error);
            Modal.error('Ошибка загрузки пространств');
        }
    }

    // Генерация градиента на основе ID
    function generateGradientFromId(id) {
        // Используем ID для генерации стабильного цвета
        const seed = id || 1;

        // Генерируем два разных цвета для градиента
        const hue1 = (seed * 137.5) % 360; // Золотое сечение для распределения цветов
        const hue2 = (hue1 + 60) % 360; // Второй цвет смещен на 60 градусов

        // Насыщенность и яркость для красивых цветов
        const saturation = 65 + (seed % 20); // 65-85%
        const lightness = 45 + (seed % 15); // 45-60%

        const color1 = `hsl(${hue1}, ${saturation}%, ${lightness}%)`;
        const color2 = `hsl(${hue2}, ${saturation}%, ${lightness - 5}%)`;

        return `linear-gradient(135deg, ${color1} 0%, ${color2} 100%)`;
    }

    // Отрисовать список пространств
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

            // Первая буква названия для иконки
            const firstLetter = space.name.charAt(0).toUpperCase();

            // Генерируем градиент на основе ID чата
            const gradient = generateGradientFromId(space.chat_id || space.id);

            // Проверяем, является ли пользователь администратором
            const isAdmin = space.admin_id === state.currentUser.id;

            li.innerHTML = `
                <div class="chat-icon" style="background: ${gradient}">${firstLetter}</div>
                <span class="space-name">${space.name}</span>
                <button class="space-settings-btn" title="Настройки пространства">⚙️</button>
            `;

            // Клик по названию пространства
            li.querySelector('.space-name').addEventListener('click', () => selectSpace(space));

            // Клик по иконке настроек (доступна всем участникам)
            li.querySelector('.space-settings-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                openSpaceSettings(space);
            });

            chatListElement.appendChild(li);
        });
    }

    // Выбрать пространство
    async function selectSpace(space) {
        if (!space.chat_id) {
            Modal.warning('У этого пространства нет чата');
            return;
        }

        // Сохраняем градиент для использования в правой панели
        space.gradient = generateGradientFromId(space.chat_id || space.id);

        // Покидаем предыдущую комнату в WebSocket
        if (state.wsClient && state.currentChatId) {
            state.wsClient.leaveRoom(state.currentChatId, state.currentUser.id);
        }

        // Обновляем активный элемент
        document.querySelectorAll('.chat-item').forEach(item => {
            item.classList.remove('active');
        });
        const selectedItem = chatListElement.querySelector(`[data-space-id="${space.id}"]`);
        if (selectedItem) {
            selectedItem.classList.add('active');
        }

        state.currentSpace = space;
        state.currentChatId = space.chat_id;

        // Пробуем присоединиться к пространству через API
        try {
            await API.joinSpace(space.id);
        } catch (error) {
            console.error('Error joining space:', error);

            // Обрабатываем конкретные ошибки
            if (error.message.includes('забанены') || error.message.includes('banned')) {
                await Modal.error('Вы забанены в этом пространстве');
                return; // Прерываем выполнение
            } else if (error.message.includes('404')) {
                await Modal.error('Пространство не найдено');
                return;
            }
            // Игнорируем остальные ошибки (например, если уже в пространстве)
        }

        // Присоединяемся к комнате через WebSocket
        if (state.wsClient) {
            state.wsClient.joinRoom(space.chat_id, state.currentUser.id, state.currentUser.nickname);
        }

        // Загружаем сообщения
        await loadMessages();

        // Обновляем правую панель с информацией о чате
        await updateChatInfo();
    }

    // Загрузить сообщения
    async function loadMessages() {
        if (!state.currentChatId) return;

        try {
            state.messages = await API.getMessages(state.currentChatId);
            renderChat();
        } catch (error) {
            console.error('Error loading messages:', error);
            renderChat(); // Рендерим пустой чат с формой
        }
    }

    // Отрисовать чат
    function renderChat() {
        if (!state.currentSpace) {
            chatMainElement.innerHTML = `
                <div class="empty-chat-message">
                    <img src="assets/icons/cat.svg" alt="Кот" class="empty-chat-cat">
                    <p>Выберите чат для общения</p>
                </div>
            `;
            return;
        }

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
                    <textarea id="message-input" placeholder="Напишите сообщение..." required autocomplete="off" rows="1"></textarea>
                    <button type="button" id="emoji-picker-btn" title="Эмодзи">
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
                            <path d="M8 14C8 14 9.5 16 12 16C14.5 16 16 14 16 14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                            <circle cx="9" cy="9" r="1" fill="currentColor"/>
                            <circle cx="15" cy="9" r="1" fill="currentColor"/>
                        </svg>
                    </button>
                    <img src="assets/icons/sendbutt.svg" alt="Отправить" class="send-button-icon">
                </form>
            </div>
        `;

        // Подключаем обработчик отправки сообщения
        const messageForm = document.getElementById('message-form');
        const messageInput = document.getElementById('message-input');
        const sendIcon = document.querySelector('.send-button-icon');

        messageForm.addEventListener('submit', handleSendMessage);

        // Обработчик клика на иконку отправки
        if (sendIcon) {
            sendIcon.addEventListener('click', (e) => {
                e.preventDefault();
                handleSendMessage(e);
            });
        }

        // Обработчик Enter/Shift+Enter для textarea
        if (messageInput) {
            messageInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage(e);
                }
            });

            // Автоматическое изменение высоты textarea
            messageInput.addEventListener('input', () => {
                messageInput.style.height = 'auto';
                messageInput.style.height = messageInput.scrollHeight + 'px';
            });
        }

        // Инициализация emoji picker
        initEmojiPicker();

        // Добавляем обработчики для кнопок редактирования/удаления
        const container = document.getElementById('messages-container');
        attachMessageActionHandlers(container);

        // Скроллим вниз
        scrollToBottom();
    }

    // Обновить информацию о чате в правой панели
    async function updateChatInfo() {
        if (!state.currentSpace || !state.currentSpace.id) {
            // Показываем пустое состояние
            sidebarRightContent.innerHTML = `
                <div class="sidebar-right-empty">
                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M17 21V19C17 17.9391 16.5786 16.9217 15.8284 16.1716C15.0783 15.4214 14.0609 15 13 15H5C3.93913 15 2.92172 15.4214 2.17157 16.1716C1.42143 16.9217 1 17.9391 1 19V21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M9 11C11.2091 11 13 9.20914 13 7C13 4.79086 11.2091 3 9 3C6.79086 3 5 4.79086 5 7C5 9.20914 6.79086 11 9 11Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M23 21V19C22.9993 18.1137 22.7044 17.2528 22.1614 16.5523C21.6184 15.8519 20.8581 15.3516 20 15.13" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M16 3.13C16.8604 3.35031 17.623 3.85071 18.1676 4.55232C18.7122 5.25392 19.0078 6.11683 19.0078 7.005C19.0078 7.89318 18.7122 8.75608 18.1676 9.45769C17.623 10.1593 16.8604 10.6597 16 10.88" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    <p>Выберите чат, чтобы увидеть информацию</p>
                </div>
            `;
            return;
        }

        try {
            // Загружаем участников
            const data = await API.getSpaceParticipants(state.currentSpace.id);
            const participants = data.participants || [];

            // Сортируем: админ первый, остальные по алфавиту
            const sorted = participants.sort((a, b) => {
                if (a.id === state.currentSpace.admin_id) return -1;
                if (b.id === state.currentSpace.admin_id) return 1;
                return a.nickname.localeCompare(b.nickname);
            });

            // Получаем градиент чата
            const gradient = state.currentSpace.gradient || generateGradientFromId(state.currentSpace.chat_id || state.currentSpace.id);

            // Отрисовываем
            sidebarRightContent.innerHTML = `
                <div class="chat-info-header" style="background: ${gradient}">
                    <h3 class="chat-info-title">${state.currentSpace.name}</h3>
                </div>
                <div class="chat-info-section">
                    <div class="chat-info-section-title">Участники (${participants.length})</div>
                    <div class="chat-members-list">
                        ${sorted.length > 0 ? sorted.map(member => {
                            const isAdmin = member.id === state.currentSpace.admin_id;
                            const firstLetter = member.nickname.charAt(0).toUpperCase();
                            const gradient = generateGradientFromId(member.id);
                            const avatarContent = member.avatar_url
                                ? `<img src="${member.avatar_url}" alt="${member.nickname}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">`
                                : firstLetter;
                            const avatarStyle = member.avatar_url ? '' : `background: ${gradient};`;
                            return `
                                <div class="chat-member-item" data-user-id="${member.id}" style="cursor: pointer;">
                                    <div class="chat-member-avatar" style="${avatarStyle}">${avatarContent}</div>
                                    <div class="chat-member-info">
                                        <div class="chat-member-name">${member.nickname}</div>
                                        <span class="chat-member-role ${isAdmin ? 'admin' : 'member'}">
                                            ${isAdmin ? 'Администратор' : 'Участник'}
                                        </span>
                                    </div>
                                </div>
                            `;
                        }).join('') : '<div class="no-members">Нет участников</div>'}
                    </div>
                </div>
            `;

            // Добавляем обработчики кликов по участникам
            setTimeout(() => {
                const memberItems = sidebarRightContent.querySelectorAll('.chat-member-item[data-user-id]');
                memberItems.forEach(item => {
                    item.addEventListener('click', () => {
                        const userId = parseInt(item.dataset.userId);
                        openProfileModal({ id: userId, nickname: item.querySelector('.chat-member-name').textContent });
                    });
                });
            }, 0);
        } catch (error) {
            console.error('Error loading chat info:', error);
            sidebarRightContent.innerHTML = `
                <div class="sidebar-right-empty">
                    <p>Ошибка загрузки информации</p>
                </div>
            `;
        }
    }

    // Отрисовать сообщения
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

            // Используем user_nickname если есть, иначе fallback на User#id
            const authorName = isOwn ? 'Вы' : (msg.user_nickname || 'User#' + msg.user_id);

            // Генерируем аватарку с первой буквой и градиентом
            const avatarLetter = isOwn
                ? (state.currentUser?.nickname ? state.currentUser.nickname.charAt(0).toUpperCase() : 'Я')
                : (msg.user_nickname ? msg.user_nickname.charAt(0).toUpperCase() : 'U');
            const avatarGradient = generateGradientFromId(msg.user_id);

            // Проверяем, есть ли реальный аватар
            const avatarUrl = isOwn ? state.currentUser?.avatar_url : (msg.user_avatar_url || msg.user?.avatar_url);
            const avatarContent = avatarUrl
                ? `<img src="${avatarUrl}" alt="${authorName}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">`
                : avatarLetter;
            const avatarStyle = avatarUrl ? '' : `background: ${avatarGradient};`;

            // Кнопки редактирования и удаления для своих сообщений
            const messageActions = isOwn ? `
                <div class="message-actions">
                    <button class="message-action-btn edit-btn" data-message-id="${msg.id}" title="Редактировать">
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M11 4H4C3.46957 4 2.96086 4.21071 2.58579 4.58579C2.21071 4.96086 2 5.46957 2 6V20C2 20.5304 2.21071 21.0391 2.58579 21.4142C2.96086 21.7893 3.46957 22 4 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V13" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            <path d="M18.5 2.50023C18.8978 2.1024 19.4374 1.87891 20 1.87891C20.5626 1.87891 21.1022 2.1024 21.5 2.50023C21.8978 2.89805 22.1213 3.43762 22.1213 4.00023C22.1213 4.56284 21.8978 5.1024 21.5 5.50023L12 15.0002L8 16.0002L9 12.0002L18.5 2.50023Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </button>
                    <button class="message-action-btn delete-btn" data-message-id="${msg.id}" title="Удалить">
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M3 6H5H21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            <path d="M8 6V4C8 3.46957 8.21071 2.96086 8.58579 2.58579C8.96086 2.21071 9.46957 2 10 2H14C14.5304 2 15.0391 2.21071 15.4142 2.58579C15.7893 2.96086 16 3.46957 16 4V6M19 6V20C19 20.5304 18.7893 21.0391 18.4142 21.4142C18.0391 21.7893 17.5304 22 17 22H7C6.46957 22 5.96086 21.7893 5.58579 21.4142C5.21071 21.0391 5 20.5304 5 20V6H19Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </button>
                </div>
            ` : '';

            return `
                <div class="message ${isOwn ? 'own-message' : 'other-message'}" data-message-id="${msg.id}">
                    <div class="message-avatar" data-user-id="${msg.user_id}" style="${avatarStyle} cursor: pointer;" title="Открыть профиль">${avatarContent}</div>
                    <div class="message-body">
                        <div class="message-author">${authorName}</div>
                        <div class="message-content" data-original-content="${escapeHtml(msg.content)}">${escapeHtml(msg.content)}</div>
                        <div class="message-time">${time}</div>
                        ${messageActions}
                    </div>
                </div>
            `;
        }).join('');
    }

    // Отправить сообщение
    async function handleSendMessage(event) {
        event.preventDefault();

        const input = document.getElementById('message-input');
        const content = input.value.trim();

        if (!content) return;

        console.log('Sending message:', {
            content,
            wsConnected: state.wsClient?.connected,
            chatId: state.currentChatId
        });

        // Отправляем через Socket.IO для realtime
        if (state.wsClient && state.wsClient.connected) {
            console.log('Sending via WebSocket');
            state.wsClient.sendMessage(
                state.currentChatId,
                state.currentUser.id,
                state.currentUser.nickname,
                content
            );

            // Очищаем поле ввода и сбрасываем высоту
            input.value = '';
            input.style.height = 'auto';

        } else {
            console.warn('WebSocket not connected, using HTTP API fallback');
            // Fallback на HTTP API если WebSocket недоступен
            try {
                const newMessage = await API.sendMessage(state.currentChatId, content);

                // Добавляем сообщение в список
                state.messages.push(newMessage);

                // Перерисовываем чат
                renderChat();

                // Очищаем поле ввода и сбрасываем высоту
                input.value = '';
                input.style.height = 'auto';

            } catch (error) {
                console.error('Error sending message:', error);
                Modal.error('Ошибка отправки сообщения: ' + error.message);
            }
        }
    }

    // Скролл вниз
    function scrollToBottom() {
        const container = document.getElementById('messages-container');
        if (container) {
            setTimeout(() => {
                container.scrollTop = container.scrollHeight;
            }, 100);
        }
    }

    // Обновить сообщения в текущем чате (без полной перерисовки)
    function updateMessagesInChat() {
        const container = document.getElementById('messages-container');
        if (!container) return;

        // Добавляем только новое сообщение
        const lastMessage = state.messages[state.messages.length - 1];
        if (!lastMessage) return;

        const isOwn = lastMessage.user_id === state.currentUser.id;
        const time = new Date(lastMessage.created_at).toLocaleTimeString('ru-RU', {
            hour: '2-digit',
            minute: '2-digit'
        });

        // Используем user_nickname если есть, иначе fallback на User#id
        const authorName = isOwn ? 'Вы' : (lastMessage.user_nickname || 'User#' + lastMessage.user_id);

        // Генерируем аватарку с первой буквой и градиентом
        const avatarLetter = isOwn
            ? (state.currentUser?.nickname ? state.currentUser.nickname.charAt(0).toUpperCase() : 'Я')
            : (lastMessage.user_nickname ? lastMessage.user_nickname.charAt(0).toUpperCase() : 'U');
        const avatarGradient = generateGradientFromId(lastMessage.user_id);

        // Проверяем, есть ли реальный аватар
        const avatarUrl = isOwn ? state.currentUser?.avatar_url : lastMessage.user_avatar_url;
        const avatarContent = avatarUrl
            ? `<img src="${avatarUrl}" alt="${authorName}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">`
            : avatarLetter;
        const avatarStyle = avatarUrl ? '' : `background: ${avatarGradient};`;

        // Кнопки редактирования и удаления для своих сообщений
        const messageActions = isOwn ? `
            <div class="message-actions">
                <button class="message-action-btn edit-btn" data-message-id="${lastMessage.id}" title="Редактировать">
                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M11 4H4C3.46957 4 2.96086 4.21071 2.58579 4.58579C2.21071 4.96086 2 5.46957 2 6V20C2 20.5304 2.21071 21.0391 2.58579 21.4142C2.96086 21.7893 3.46957 22 4 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V13" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M18.5 2.50023C18.8978 2.1024 19.4374 1.87891 20 1.87891C20.5626 1.87891 21.1022 2.1024 21.5 2.50023C21.8978 2.89805 22.1213 3.43762 22.1213 4.00023C22.1213 4.56284 21.8978 5.1024 21.5 5.50023L12 15.0002L8 16.0002L9 12.0002L18.5 2.50023Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </button>
                <button class="message-action-btn delete-btn" data-message-id="${lastMessage.id}" title="Удалить">
                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M3 6H5H21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M8 6V4C8 3.46957 8.21071 2.96086 8.58579 2.58579C8.96086 2.21071 9.46957 2 10 2H14C14.5304 2 15.0391 2.21071 15.4142 2.58579C15.7893 2.96086 16 3.46957 16 4V6M19 6V20C19 20.5304 18.7893 21.0391 18.4142 21.4142C18.0391 21.7893 17.5304 22 17 22H7C6.46957 22 5.96086 21.7893 5.58579 21.4142C5.21071 21.0391 5 20.5304 5 20V6H19Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </button>
            </div>
        ` : '';

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isOwn ? 'own-message' : 'other-message'}`;
        messageDiv.dataset.messageId = lastMessage.id;
        messageDiv.innerHTML = `
            <div class="message-avatar" data-user-id="${lastMessage.user_id}" style="${avatarStyle} cursor: pointer;" title="Открыть профиль">${avatarContent}</div>
            <div class="message-body">
                <div class="message-author">${authorName}</div>
                <div class="message-content" data-original-content="${escapeHtml(lastMessage.content)}">${escapeHtml(lastMessage.content)}</div>
                <div class="message-time">${time}</div>
                ${messageActions}
            </div>
        `;

        // Удаляем заглушку "нет сообщений" если она есть
        const noMessages = container.querySelector('.no-messages');
        if (noMessages) {
            noMessages.remove();
        }

        container.appendChild(messageDiv);

        // Добавляем обработчики для кнопок
        attachMessageActionHandlers(messageDiv);

        scrollToBottom();
    }

    // Прикрепить обработчики к кнопкам сообщений
    function attachMessageActionHandlers(container) {
        if (!container) return;

        // Обработчики кликов по аватарам
        const avatars = container.querySelectorAll('.message-avatar[data-user-id]');
        avatars.forEach(avatar => {
            avatar.addEventListener('click', (e) => {
                e.stopPropagation();
                const userId = parseInt(avatar.dataset.userId);
                openProfileModal(userId);
            });
        });

        // Обработчики кнопок редактирования
        const editButtons = container.querySelectorAll('.edit-btn');
        editButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const messageId = btn.dataset.messageId;
                handleEditMessage(messageId);
            });
        });

        // Обработчики кнопок удаления
        const deleteButtons = container.querySelectorAll('.delete-btn');
        deleteButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const messageId = btn.dataset.messageId;
                handleDeleteMessage(messageId);
            });
        });
    }

    // Редактировать сообщение
    async function handleEditMessage(messageId) {
        const messageElement = document.querySelector(`.message[data-message-id="${messageId}"]`);
        if (!messageElement) return;

        const contentElement = messageElement.querySelector('.message-content');
        const actionsElement = messageElement.querySelector('.message-actions');
        const originalContent = contentElement.dataset.originalContent;

        // Создаем форму редактирования
        const editForm = document.createElement('div');
        editForm.className = 'message-edit-form';
        editForm.innerHTML = `
            <input type="text" class="message-edit-input" value="${originalContent}" autocomplete="off">
            <div class="message-edit-actions">
                <button class="message-edit-save" title="Сохранить">✓</button>
                <button class="message-edit-cancel" title="Отмена">✕</button>
            </div>
        `;

        // Скрываем контент и кнопки
        contentElement.style.display = 'none';
        if (actionsElement) actionsElement.style.display = 'none';

        // Вставляем форму
        contentElement.parentNode.insertBefore(editForm, contentElement);

        const input = editForm.querySelector('.message-edit-input');
        const saveBtn = editForm.querySelector('.message-edit-save');
        const cancelBtn = editForm.querySelector('.message-edit-cancel');

        input.focus();
        input.select();

        // Сохранить изменения
        const saveEdit = async () => {
            const newContent = input.value.trim();

            if (!newContent) {
                Modal.warning('Сообщение не может быть пустым');
                return;
            }

            if (newContent === originalContent) {
                cancelEdit();
                return;
            }

            try {
                await API.updateMessage(state.currentChatId, messageId, newContent);

                // Обновляем в локальном стейте
                const message = state.messages.find(m => m.id == messageId);
                if (message) {
                    message.content = newContent;
                }

                // Обновляем UI
                contentElement.textContent = newContent;
                contentElement.dataset.originalContent = newContent;
                cancelEdit();

                // Отправляем через WebSocket для realtime обновления у других пользователей
                if (state.wsClient && state.wsClient.connected) {
                    console.log('Sending edit_message event:', {
                        room_id: state.currentChatId,
                        message_id: messageId,
                        content: newContent,
                        user_id: state.currentUser.id
                    });
                    state.wsClient.socket.emit('edit_message', {
                        room_id: state.currentChatId,
                        message_id: messageId,
                        content: newContent,
                        user_id: state.currentUser.id
                    });
                } else {
                    console.error('WebSocket not connected!');
                }

                console.log('Message edited successfully');

            } catch (error) {
                console.error('Error editing message:', error);
                Modal.error('Ошибка редактирования сообщения: ' + error.message);
            }
        };

        // Отменить редактирование
        const cancelEdit = () => {
            editForm.remove();
            contentElement.style.display = '';
            if (actionsElement) actionsElement.style.display = '';
        };

        saveBtn.addEventListener('click', saveEdit);
        cancelBtn.addEventListener('click', cancelEdit);

        // Enter для сохранения, Escape для отмены
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                saveEdit();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                cancelEdit();
            }
        });
    }

    // Удалить сообщение
    async function handleDeleteMessage(messageId) {
        const confirmed = await Modal.confirm(
            'Вы уверены, что хотите удалить это сообщение?',
            'Удаление сообщения',
            { confirmText: 'Удалить', cancelText: 'Отмена', danger: true }
        );

        if (!confirmed) return;

        try {
            await API.deleteMessage(state.currentChatId, messageId);

            // Удаляем из локального стейта
            state.messages = state.messages.filter(m => m.id != messageId);

            // Удаляем из UI
            const messageElement = document.querySelector(`.message[data-message-id="${messageId}"]`);
            if (messageElement) {
                messageElement.remove();
            }

            // Отправляем через WebSocket для realtime обновления у других пользователей
            if (state.wsClient && state.wsClient.connected) {
                console.log('Sending delete_message event:', {
                    room_id: state.currentChatId,
                    message_id: messageId,
                    user_id: state.currentUser.id
                });
                state.wsClient.socket.emit('delete_message', {
                    room_id: state.currentChatId,
                    message_id: messageId,
                    user_id: state.currentUser.id
                });
            } else {
                console.error('WebSocket not connected!');
            }

            console.log('Message deleted successfully');

        } catch (error) {
            console.error('Error deleting message:', error);
            Modal.error('Ошибка удаления сообщения: ' + error.message);
        }
    }

    // Экранирование HTML
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Настройки (пока не функциональная)
    if (settingsIcon) {
        settingsIcon.addEventListener('click', () => {
            Modal.alert('Настройки будут доступны позже', 'Настройки', 'info');
        });
    }

    // Выход
    if (logoutIcon) {
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
    }

    // Переключение правой боковой панели
    // Клик по всей панели в свернутом состоянии - разворачиваем
    if (sidebarRight) {
        sidebarRight.addEventListener('click', (e) => {
            // Разворачиваем только если панель свернута и клик не по кнопке
            if (!sidebarRight.classList.contains('expanded') && e.target !== sidebarRightToggle && !sidebarRightToggle.contains(e.target)) {
                sidebarRight.classList.add('expanded');
            }
        });
    }

    // Клик по кнопке-стрелке - сворачиваем
    if (sidebarRightToggle) {
        sidebarRightToggle.addEventListener('click', (e) => {
            e.stopPropagation(); // Предотвращаем всплытие к родителю
            sidebarRight.classList.remove('expanded');
        });
    }

    // Модальное окно профиля
    async function openProfileModal(user = null) {
        // Если пользователь не передан, открываем профиль текущего пользователя
        const targetUser = user || state.currentUser;

        if (!targetUser) {
            console.error('No user to display');
            return;
        }

        if (!profileModal) {
            console.error('profileModal element not found');
            return;
        }

        // Если передан только ID или неполные данные, загружаем данные пользователя
        let userData = targetUser;
        const needsFullData = typeof targetUser === 'number' ||
                              (targetUser.id &&
                               !targetUser.hasOwnProperty('avatar_url') &&
                               !targetUser.hasOwnProperty('profile_background_url'));

        if (needsFullData) {
            try {
                const userId = typeof targetUser === 'number' ? targetUser : targetUser.id;
                userData = await API.getUserProfile(userId);
            } catch (error) {
                console.error('Failed to load user data:', error);
                Modal.error('Не удалось загрузить данные пользователя');
                return;
            }
        }

        // Заполняем данные профиля
        const profileName = profileModal.querySelector('.profile-name');
        const profileEmail = profileModal.querySelector('.profile-email');
        const profileUserId = profileModal.querySelector('#profile-user-id');
        const profileNickname = profileModal.querySelector('#profile-nickname');
        const profileBanner = profileModal.querySelector('.profile-banner');
        const profileAvatar = profileModal.querySelector('#profile-avatar-img');

        if (profileName) profileName.textContent = userData.nickname;

        // Показываем/скрываем кнопки загрузки только для своего профиля
        const isOwnProfile = userData.id === state.currentUser?.id;
        const avatarContainer = document.getElementById('avatar-container');

        if (avatarUploadBtn) avatarUploadBtn.style.display = isOwnProfile ? 'flex' : 'none';
        if (bannerUploadBtn) bannerUploadBtn.style.display = isOwnProfile ? 'flex' : 'none';

        // Включаем/выключаем hover эффект на аватаре
        if (avatarContainer) {
            if (isOwnProfile) {
                avatarContainer.style.cursor = 'pointer';
            } else {
                avatarContainer.style.cursor = 'default';
            }
        }

        // Email показываем только для текущего пользователя
        if (profileEmail) {
            if (isOwnProfile) {
                profileEmail.textContent = state.currentUser.email;
                profileEmail.style.display = 'block';
            } else {
                profileEmail.style.display = 'none';
            }
        }
        if (profileUserId) profileUserId.textContent = `#${userData.id}`;
        if (profileNickname) profileNickname.textContent = userData.nickname;

        // Устанавливаем аватар (реальный или градиент)
        if (profileAvatar) {
            if (userData.avatar_url) {
                profileAvatar.src = userData.avatar_url;
                profileAvatar.style.background = 'none';
            } else {
                profileAvatar.src = 'assets/icons/avatar.svg';
                const gradient = generateGradientFromId(userData.id);
                profileAvatar.style.background = gradient;
            }
        }

        // Устанавливаем баннер (реальный или градиент)
        if (profileBanner) {
            if (userData.profile_background_url) {
                profileBanner.style.backgroundImage = `url('${userData.profile_background_url}')`;
                profileBanner.style.backgroundSize = 'cover';
                profileBanner.style.backgroundPosition = 'center';
            } else {
                // Генерируем красивый горизонтальный градиент для баннера
                const gradient = generateGradientFromId(userData.id);
                profileBanner.style.background = `linear-gradient(135deg, ${gradient.split('linear-gradient(135deg, ')[1]}`;
                profileBanner.style.backgroundImage = profileBanner.style.background;
            }
        }

        // Показываем модальное окно
        profileModal.classList.add('show');
    }

    function closeProfileModal() {
        if (profileModal) {
            profileModal.classList.remove('show');
        }
    }

    // Открытие профиля при клике на user-profile (свой профиль)
    if (userProfile) {
        userProfile.addEventListener('click', () => {
            openProfileModal();
        });
    }

    // Закрытие профиля при клике вне модального окна
    if (profileModal) {
        profileModal.addEventListener('click', (e) => {
            if (e.target === profileModal) {
                closeProfileModal();
            }
        });
    }

    // Закрытие профиля при нажатии ESC
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && profileModal && profileModal.classList.contains('show')) {
            closeProfileModal();
        }
    });

    // Создание новой комнаты
    if (newChatButton) {
        newChatButton.addEventListener('click', async () => {
            const formData = await Modal.createRoom();

            if (!formData) return; // Отмена

            const { name, description, participants } = formData;

            if (!name) {
                Modal.warning('Введите название комнаты');
                return;
            }

            try {
                const newSpace = await API.createSpace(name, description);

                // Если указаны участники, добавляем их
                if (participants && participants.length > 0) {
                    for (const participant of participants) {
                        try {
                            await API.addUserToSpace(newSpace.id, participant.id);
                        } catch (err) {
                            console.warn(`Failed to add user ${participant.nickname}:`, err);
                        }
                    }
                }

                // Перезагружаем список комнат
                await loadSpaces();

                Modal.success('Комната успешно создана!');
            } catch (error) {
                console.error('Error creating space:', error);
                Modal.error('Ошибка при создании комнаты: ' + error.message);
            }
        });
    }

    // Инициализация emoji picker
    function initEmojiPicker() {
        // Удаляем старый picker если есть
        const oldPicker = document.getElementById('emoji-picker');
        if (oldPicker) {
            oldPicker.remove();
        }

        // Создаем новый picker
        if (typeof EmojiPicker !== 'undefined') {
            state.emojiPicker = new EmojiPicker();
            state.emojiPicker.init(chatMainElement, (emoji) => {
                // Вставляем эмодзи в поле ввода
                const input = document.getElementById('message-input');
                if (input) {
                    const cursorPos = input.selectionStart;
                    const textBefore = input.value.substring(0, cursorPos);
                    const textAfter = input.value.substring(cursorPos);
                    input.value = textBefore + emoji + textAfter;

                    // Устанавливаем курсор после эмодзи
                    const newCursorPos = cursorPos + emoji.length;
                    input.setSelectionRange(newCursorPos, newCursorPos);
                    input.focus();
                }
            });

            // Обработчик кнопки открытия picker
            const emojiBtn = document.getElementById('emoji-picker-btn');
            if (emojiBtn) {
                emojiBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    state.emojiPicker.toggle();
                });
            }
        }
    }

    // === УПРАВЛЕНИЕ ПРОСТРАНСТВОМ ===

    async function openSpaceSettings(space) {
        const isAdmin = space.admin_id === state.currentUser.id;

        // Кнопки для всех пользователей
        const commonButtons = `
            <button class="space-action-btn" onclick="window.chatApp.showParticipants(${space.id})">
                <span class="action-icon">👥</span>
                <div class="action-text">
                    <div class="action-title">Список участников</div>
                    <div class="action-desc">Просмотр и управление</div>
                </div>
            </button>
        `;

        // Кнопки только для админа
        const adminButtons = `
            <button class="space-action-btn" onclick="window.chatApp.renameSpace(${space.id})">
                <span class="action-icon">✏️</span>
                <div class="action-text">
                    <div class="action-title">Изменить название</div>
                    <div class="action-desc">Переименовать пространство</div>
                </div>
            </button>
            <button class="space-action-btn" onclick="window.chatApp.addUserToSpace(${space.id})">
                <span class="action-icon">👤</span>
                <div class="action-text">
                    <div class="action-title">Добавить пользователя</div>
                    <div class="action-desc">Пригласить по нику или ID</div>
                </div>
            </button>
            <button class="space-action-btn space-action-danger" onclick="window.chatApp.deleteSpace(${space.id})">
                <span class="action-icon">🗑️</span>
                <div class="action-text">
                    <div class="action-title">Удалить пространство</div>
                    <div class="action-desc">Удалить навсегда со всеми сообщениями</div>
                </div>
            </button>
        `;

        // Кнопка для обычных участников
        const userButtons = `
            <button class="space-action-btn space-action-warning" onclick="window.chatApp.leaveSpace(${space.id})">
                <span class="action-icon">🚪</span>
                <div class="action-text">
                    <div class="action-title">Покинуть пространство</div>
                    <div class="action-desc">Выйти из этой комнаты</div>
                </div>
            </button>
        `;

        const content = `
            <div class="space-settings-menu">
                <div class="space-settings-header">
                    <div class="space-icon-large">${space.name.charAt(0).toUpperCase()}</div>
                    <h3>${space.name}</h3>
                </div>
                <div class="space-settings-actions">
                    ${commonButtons}
                    ${isAdmin ? adminButtons : userButtons}
                </div>
            </div>
        `;

        await Modal.custom(content);
    }

    async function renameSpace(spaceId) {
        const currentSpace = state.spaces.find(s => s.id === spaceId);
        if (!currentSpace) return;

        const newName = await Modal.prompt('Введите новое название пространства', currentSpace.name);
        if (!newName || newName === currentSpace.name) return;

        try {
            await API.updateSpaceName(spaceId, newName);
            await Modal.success('Название обновлено!');
            await loadSpaces();
        } catch (error) {
            await Modal.error('Ошибка: ' + error.message);
        }
    }

    async function addUserToSpace(spaceId) {
        const userIdentifier = await Modal.prompt('Введите никнейм или ID пользователя');
        if (!userIdentifier) return;

        try {
            const result = await API.addUserToSpace(spaceId, userIdentifier);
            await Modal.success(`Пользователь ${result.user.nickname} добавлен!`);
        } catch (error) {
            await Modal.error('Ошибка: ' + error.message);
        }
    }

    async function showParticipants(spaceId) {
        try {
            const data = await API.getSpaceParticipants(spaceId);
            const participants = data.participants;

            if (participants.length === 0) {
                await Modal.info('В этом пространстве пока нет участников');
                return;
            }

            const space = state.spaces.find(s => s.id === spaceId);
            const isAdmin = space && space.admin_id === state.currentUser.id;

            const content = `
                <div class="participants-container">
                    <div class="participants-header">
                        <span class="participants-count">${participants.length} участник${participants.length % 10 === 1 && participants.length !== 11 ? '' : participants.length % 10 >= 2 && participants.length % 10 <= 4 && (participants.length < 10 || participants.length > 20) ? 'а' : 'ов'}</span>
                    </div>
                    <div class="participants-list">
                        ${participants.map(p => {
                            const isSpaceAdmin = p.id === space.admin_id;
                            const firstLetter = p.nickname.charAt(0).toUpperCase();
                            return `
                                <div class="participant-card">
                                    <div class="participant-avatar">${firstLetter}</div>
                                    <div class="participant-info">
                                        <div class="participant-name">${p.nickname}</div>
                                        ${isSpaceAdmin ? '<div class="participant-badge admin-badge">Администратор</div>' : '<div class="participant-badge member-badge">Участник</div>'}
                                    </div>
                                    ${isAdmin && p.id !== state.currentUser.id ? `
                                        <button class="participant-kick-btn" onclick="window.chatApp.kickUserFromSpace(${spaceId}, ${p.id})" title="Удалить">
                                            ❌
                                        </button>
                                    ` : ''}
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;

            await Modal.custom(content);
        } catch (error) {
            await Modal.error('Ошибка: ' + error.message);
        }
    }

    async function kickUserFromSpace(spaceId, userId) {
        const confirm = await Modal.confirm('Вы уверены, что хотите удалить этого пользователя?');
        if (!confirm) return;

        try {
            await API.kickUser(spaceId, userId);

            // Обновляем список участников без закрытия окна
            await refreshParticipantsList(spaceId);

            // Показываем уведомление об успехе
            await Modal.success('Пользователь удален из пространства');
        } catch (error) {
            await Modal.error('Ошибка: ' + error.message);
        }
    }

    async function refreshParticipantsList(spaceId) {
        try {
            const data = await API.getSpaceParticipants(spaceId);
            const participants = data.participants;

            const space = state.spaces.find(s => s.id === spaceId);
            const isAdmin = space && space.admin_id === state.currentUser.id;

            // Находим контейнер участников в текущем модальном окне
            const participantsContainer = document.querySelector('.participants-container');
            if (!participantsContainer) return;

            // Обновляем только контент внутри контейнера
            const newContent = `
                <div class="participants-header">
                    <span class="participants-count">${participants.length} участник${participants.length % 10 === 1 && participants.length !== 11 ? '' : participants.length % 10 >= 2 && participants.length % 10 <= 4 && (participants.length < 10 || participants.length > 20) ? 'а' : 'ов'}</span>
                </div>
                <div class="participants-list">
                    ${participants.map(p => {
                        const isSpaceAdmin = p.id === space.admin_id;
                        const firstLetter = p.nickname.charAt(0).toUpperCase();
                        return `
                            <div class="participant-card">
                                <div class="participant-avatar">${firstLetter}</div>
                                <div class="participant-info">
                                    <div class="participant-name">${p.nickname}</div>
                                    ${isSpaceAdmin ? '<div class="participant-badge admin-badge">Администратор</div>' : '<div class="participant-badge member-badge">Участник</div>'}
                                </div>
                                ${isAdmin && p.id !== state.currentUser.id ? `
                                    <button class="participant-kick-btn" onclick="window.chatApp.kickUserFromSpace(${spaceId}, ${p.id})" title="Удалить">
                                        ❌
                                    </button>
                                ` : ''}
                            </div>
                        `;
                    }).join('')}
                </div>
            `;

            participantsContainer.innerHTML = newContent;
        } catch (error) {
            console.error('Error refreshing participants:', error);
        }
    }

    async function leaveSpace(spaceId) {
        const space = state.spaces.find(s => s.id === spaceId);
        if (!space) return;

        const confirm = await Modal.confirm(
            `Вы уверены, что хотите покинуть пространство "${space.name}"?`,
            'Покинуть пространство',
            { danger: true, confirmText: 'Покинуть' }
        );

        if (!confirm) return;

        try {
            await API.leaveSpace(spaceId);

            // Закрываем все модальные окна
            Modal.closeAll();

            // Обновляем список пространств
            await loadSpaces();

            // Если покинутое пространство было выбрано, очищаем чат
            if (state.currentChatId === space.chat_id) {
                state.currentChatId = null;
                state.messages = [];
                renderChat();
            }

            await Modal.success('Вы покинули пространство');
        } catch (error) {
            await Modal.error('Ошибка при выходе: ' + error.message);
        }
    }

    async function deleteSpace(spaceId) {
        const space = state.spaces.find(s => s.id === spaceId);
        if (!space) return;

        const confirm = await Modal.confirm(
            `Вы уверены, что хотите удалить пространство "${space.name}"? Все сообщения будут удалены безвозвратно!`,
            'Удалить пространство',
            { danger: true, confirmText: 'Удалить' }
        );

        if (!confirm) return;

        try {
            await API.deleteSpace(spaceId);

            // Закрываем все модальные окна
            Modal.closeAll();

            // Обновляем список пространств
            await loadSpaces();

            // Если удалённое пространство было выбрано, очищаем чат
            if (state.currentChatId === space.chat_id) {
                state.currentChatId = null;
                state.messages = [];
                renderChat();
            }

            await Modal.success('Пространство успешно удалено');
        } catch (error) {
            await Modal.error('Ошибка при удалении: ' + error.message);
        }
    }

    // === ЗАГРУЗКА АВАТАРА И БАННЕРА ===

    // Обработчики для загрузки аватара
    if (avatarUploadBtn && avatarFileInput) {
        avatarUploadBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            avatarFileInput.click();
        });

        avatarFileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            // Проверка типа файла
            if (!file.type.startsWith('image/')) {
                Modal.error('Пожалуйста, выберите изображение');
                return;
            }

            // Проверка размера (макс 5MB)
            if (file.size > 5 * 1024 * 1024) {
                Modal.error('Файл слишком большой. Максимум 5MB');
                return;
            }

            try {
                // Загружаем файл
                const updatedUser = await API.uploadAvatar(file);

                // Обновляем state
                state.currentUser = updatedUser;

                // Обновляем UI
                const profileAvatar = document.querySelector('#profile-avatar-img');
                if (profileAvatar && updatedUser.avatar_url) {
                    profileAvatar.src = updatedUser.avatar_url;
                    profileAvatar.style.background = 'none';
                }

                // Обновляем аватар в сайдбаре
                const sidebarAvatar = document.querySelector('.user-avatar');
                if (sidebarAvatar && updatedUser.avatar_url) {
                    sidebarAvatar.src = updatedUser.avatar_url;
                }

                Modal.success('Аватар успешно обновлен!');
            } catch (error) {
                console.error('Error uploading avatar:', error);
                Modal.error('Ошибка загрузки: ' + error.message);
            } finally {
                // Сбрасываем input для возможности повторной загрузки того же файла
                avatarFileInput.value = '';
            }
        });
    }

    // Обработчики для загрузки баннера
    if (bannerUploadBtn && bannerFileInput) {
        bannerUploadBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            bannerFileInput.click();
        });

        bannerFileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            // Проверка типа файла
            if (!file.type.startsWith('image/')) {
                Modal.error('Пожалуйста, выберите изображение');
                return;
            }

            // Проверка размера (макс 10MB)
            if (file.size > 10 * 1024 * 1024) {
                Modal.error('Файл слишком большой. Максимум 10MB');
                return;
            }

            try {
                // Загружаем файл
                const updatedUser = await API.uploadBanner(file);

                // Обновляем state
                state.currentUser = updatedUser;

                // Обновляем UI
                const profileBanner = document.querySelector('.profile-banner');
                if (profileBanner && updatedUser.profile_background_url) {
                    profileBanner.style.backgroundImage = `url('${updatedUser.profile_background_url}')`;
                    profileBanner.style.backgroundSize = 'cover';
                    profileBanner.style.backgroundPosition = 'center';
                }

                Modal.success('Баннер успешно обновлен!');
            } catch (error) {
                console.error('Error uploading banner:', error);
                Modal.error('Ошибка загрузки: ' + error.message);
            } finally {
                // Сбрасываем input для возможности повторной загрузки того же файла
                bannerFileInput.value = '';
            }
        });
    }

    // Экспортируем функции в window для доступа из HTML
    window.chatApp = {
        renameSpace,
        addUserToSpace,
        showParticipants,
        kickUserFromSpace,
        leaveSpace,
        deleteSpace
    };

    // Запускаем приложение
    init();
});
