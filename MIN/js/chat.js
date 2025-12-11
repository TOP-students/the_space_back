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
        emojiPicker: null,
        currentUserPermissions: [],
        chats: [], // Список чатов для проверки space_id
        heartbeatInterval: null, // Интервал для heartbeat
        statusUpdateInterval: null // Интервал для обновления статусов
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

    // Элементы уведомлений
    const notificationsIcon = document.getElementById('notifications-icon');
    const notificationBadge = document.getElementById('notification-badge');

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

            // Устанавливаем статус "онлайн" при входе
            try {
                await API.setStatus('online');
                state.currentUser.status = 'online';
            } catch (error) {
                console.error('Failed to set online status:', error);
                // Не критично, продолжаем работу
            }

            updateUserProfile();

            // Инициализируем WebSocket (если доступен)
            if (typeof WebSocketClient !== 'undefined') {
                initWebSocket();
            }

            // Загружаем список пространств
            await loadSpaces();

            // Обновляем счётчик уведомлений
            await updateNotificationBadge();

            // Запускаем heartbeat для поддержания онлайн статуса
            startHeartbeat();

        } catch (error) {
            console.error('Init error:', error);
            await Modal.error('Ошибка загрузки данных. Попробуйте перезайти.');
            AuthService.logout();
        }
    }

    // Запуск heartbeat механизма
    function startHeartbeat() {
        // Отправляем heartbeat каждые 30 секунд для более быстрого обновления статусов
        state.heartbeatInterval = setInterval(async () => {
            try {
                await API.heartbeat();
                console.log('Heartbeat sent');

                // Обновляем счётчик уведомлений при каждом heartbeat
                await updateNotificationBadge();
            } catch (error) {
                console.error('Heartbeat error:', error);
            }
        }, 30 * 1000); // 30 секунд

        // Отправляем первый heartbeat сразу
        API.heartbeat().catch(err => console.error('Initial heartbeat error:', err));
    }

    // Остановка heartbeat при выходе
    function stopHeartbeat() {
        if (state.heartbeatInterval) {
            clearInterval(state.heartbeatInterval);
            state.heartbeatInterval = null;
        }
        if (state.statusUpdateInterval) {
            clearInterval(state.statusUpdateInterval);
            state.statusUpdateInterval = null;
        }
    }

    // Периодическое обновление статусов участников
    function startStatusUpdates(spaceId) {
        // Очистить предыдущий интервал если есть
        if (state.statusUpdateInterval) {
            clearInterval(state.statusUpdateInterval);
        }

        // Обновлять статусы каждые 30 секунд
        state.statusUpdateInterval = setInterval(async () => {
            // Обновляем только если открыта панель участников
            if (document.getElementById('participants-list')) {
                try {
                    await showParticipants(spaceId);
                } catch (error) {
                    console.error('Failed to update participant statuses:', error);
                }
            }
        }, 30 * 1000); // 30 секунд
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
                    type: data.type || 'text',
                    attachment: data.attachment || null,
                    reactions: data.reactions || [],
                    my_reaction: data.my_reaction || null
                };

                state.messages.push(message);
                updateMessagesInChat();

                // Проверяем, есть ли упоминание текущего пользователя
                const content = message.content.toLowerCase();
                const currentNickname = state.currentUser.nickname.toLowerCase();
                if (content.includes(`@${currentNickname}`) || content.includes('@all')) {
                    // Обновляем счётчик уведомлений, так как возможно новое уведомление
                    updateNotificationBadge();
                }
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

        // Обработчик обновления реакций
        state.wsClient.socket.on('reaction_updated', (data) => {
            console.log('WS: Reaction updated', data);

            if (data.room_id == state.currentChatId || data.chat_id == state.currentChatId) {
                // Обновляем реакции в локальном стейте
                const message = state.messages.find(m => m.id == data.message_id);
                if (message) {
                    message.reactions = data.reactions;

                    // Вычисляем my_reaction на основе reactions
                    message.my_reaction = null;
                    for (const reaction of data.reactions) {
                        const userReacted = reaction.users.find(u => u.id === state.currentUser.id);
                        if (userReacted) {
                            message.my_reaction = reaction.reaction;
                            break;
                        }
                    }

                    console.log('Updated reactions in state:', message.reactions, 'my_reaction:', message.my_reaction);
                }

                // Обновляем UI - перерисовываем весь чат
                renderChat();
                console.log('Reactions updated in UI');
            } else {
                console.log('Room mismatch, ignoring reaction update');
            }
        });

        // Обработчик кика пользователя
        state.wsClient.onUserKicked((data) => {
            console.log('WS: User kicked from space', data);

            // Если кикнули нас самих - возвращаемся к списку пространств
            if (data.user_id == state.currentUser.id) {
                Modal.warning('Вы были исключены из пространства');
                // Покидаем пространство
                state.currentSpace = null;
                state.currentChatId = null;
                // Перезагружаем список пространств
                loadSpaces();
                // Очищаем чат
                chatMainElement.innerHTML = `
                    <div class="empty-chat-message">
                        <img src="assets/icons/cat.svg" alt="Кот" class="empty-chat-cat">
                        <p>Выберите чат для общения</p>
                    </div>
                `;
                sidebarRightContent.innerHTML = `
                    <div class="sidebar-right-empty">
                        <p>Выберите чат, чтобы увидеть информацию</p>
                    </div>
                `;
            } else if (state.currentSpace && data.space_id == state.currentSpace.id) {
                // Если кикнули кого-то другого в текущем пространстве - обновляем список участников
                updateChatInfo();
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

            // Обновляем индикатор статуса в сайдбаре
            const sidebarStatusIndicator = document.getElementById('sidebar-status-indicator');
            if (sidebarStatusIndicator) {
                const statusConfig = {
                    'online': '#43b581',
                    'away': '#faa61a',
                    'dnd': '#f04747',
                    'offline': '#747f8d'
                };
                const statusColor = statusConfig[state.currentUser.status] || statusConfig['online'];
                sidebarStatusIndicator.style.backgroundColor = statusColor;
            }
        }
    }

    // Загрузить список пространств
    async function loadSpaces() {
        try {
            state.spaces = await API.getSpaces();
            // Сохраняем информацию о чатах для проверки space_id
            state.chats = state.spaces.map(s => ({ id: s.chat_id, space_id: s.id }));
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

            // Аватар или градиент
            let iconStyle = '';
            let iconContent = '';
            if (space.avatar_url) {
                iconStyle = `background-image: url('${space.avatar_url}'); background-size: cover; background-position: center;`;
                iconContent = '';
            } else {
                iconStyle = `background: ${gradient}`;
                iconContent = firstLetter;
            }

            li.innerHTML = `
                <div class="chat-icon" style="${iconStyle}">${iconContent}</div>
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

        // Сбрасываем список участников для автодополнения
        mentionAutocompleteParticipants = [];

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

        // Получаем права пользователя в этом пространстве
        try {
            const permissions = await API.getMyPermissions(space.id);
            state.currentUserPermissions = permissions.permissions || [];
            console.log('User permissions in space:', state.currentUserPermissions);
        } catch (error) {
            console.error('Error loading permissions:', error);
            state.currentUserPermissions = [];
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

        // Генерируем аватар или градиент для шапки
        const firstLetter = state.currentSpace.name.charAt(0).toUpperCase();
        const gradient = generateGradientFromId(state.currentSpace.chat_id || state.currentSpace.id);
        let headerIconStyle = '';
        let headerIconContent = '';
        if (state.currentSpace.avatar_url) {
            headerIconStyle = `background-image: url('${state.currentSpace.avatar_url}'); background-size: cover; background-position: center;`;
            headerIconContent = '';
        } else {
            headerIconStyle = `background: ${gradient}`;
            headerIconContent = firstLetter;
        }

        chatMainElement.innerHTML = `
            <div class="chat-header">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div class="chat-icon" style="${headerIconStyle}; width: 48px; height: 48px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: bold; color: white;">${headerIconContent}</div>
                    <div>
                        <h3 style="margin: 0;">${state.currentSpace.name}</h3>
                        <p class="chat-description" style="margin: 0;">${state.currentSpace.description || ''}</p>
                    </div>
                </div>
            </div>
            <div class="messages-container" id="messages-container">
                ${renderMessages()}
            </div>
            <div class="message-input-container">
                <form id="message-form">
                    <div id="mention-autocomplete" class="mention-autocomplete"></div>
                    <button type="button" id="attach-file-btn" class="attach-file-btn" title="Прикрепить файл">
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M21.44 11.05L12.25 20.24C11.1242 21.3658 9.59723 21.9983 8.005 21.9983C6.41277 21.9983 4.88579 21.3658 3.76 20.24C2.63421 19.1142 2.00166 17.5872 2.00166 15.995C2.00166 14.4028 2.63421 12.8758 3.76 11.75L12.33 3.18C13.0806 2.42944 14.0967 2.00562 15.155 2.00562C16.2133 2.00562 17.2294 2.42944 17.98 3.18C18.7306 3.93056 19.1544 4.94667 19.1544 6.005C19.1544 7.06333 18.7306 8.07944 17.98 8.83L9.41 17.4C9.03471 17.7753 8.52664 17.9872 7.995 17.9872C7.46336 17.9872 6.95529 17.7753 6.58 17.4C6.20471 17.0247 5.99279 16.5166 5.99279 15.985C5.99279 15.4534 6.20471 14.9453 6.58 14.57L15.07 6.07" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </button>
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

            // Инициализация автодополнения @-упоминаний
            initMentionAutocomplete(messageInput);
        }

        // Инициализация emoji picker
        initEmojiPicker();

        // Инициализация прикрепления файлов
        initFileAttachment();

        // Добавляем обработчики для кнопок редактирования/удаления
        const container = document.getElementById('messages-container');
        attachMessageActionHandlers(container);

        // Добавляем обработчики для реакций
        attachReactionHandlers(container);

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
            // Загружаем участников и роли параллельно
            const [participantsData, rolesData] = await Promise.all([
                API.getSpaceParticipants(state.currentSpace.id),
                API.getSpaceRoles(state.currentSpace.id).catch(() => [])
            ]);

            const participants = participantsData.participants || [];
            const roles = rolesData || [];

            // Загружаем статусы участников
            const statusPromises = participants.map(p =>
                API.getUserStatus(p.id).catch(err => ({ status: 'offline' }))
            );
            const statuses = await Promise.all(statusPromises);

            // Добавляем статусы к участникам
            participants.forEach((p, i) => {
                p.userStatus = statuses[i].status || 'offline';
            });

            // Группируем участников по ролям
            const roleGroups = {};

            // Сортируем роли по приоритету (выше = важнее)
            const sortedRoles = [...roles].sort((a, b) => b.priority - a.priority);

            // Инициализируем группы для каждой роли
            sortedRoles.forEach(role => {
                roleGroups[role.id] = {
                    role: role,
                    members: []
                };
            });

            // Добавляем группу для участников без роли
            const noRoleGroup = {
                role: {
                    id: 'no-role',
                    name: 'Участники',
                    color: '#808080',
                    priority: 0
                },
                members: []
            };

            // Группируем участников
            participants.forEach(member => {
                const roleId = member.role?.id;
                if (roleId && roleGroups[roleId]) {
                    roleGroups[roleId].members.push(member);
                } else {
                    // Участники без роли идут в отдельную группу
                    noRoleGroup.members.push(member);
                }
            });

            // Добавляем группу без роли в конец, если в ней есть участники
            if (noRoleGroup.members.length > 0) {
                roleGroups['no-role'] = noRoleGroup;
            }

            // Получаем градиент чата
            const gradient = state.currentSpace.gradient || generateGradientFromId(state.currentSpace.chat_id || state.currentSpace.id);

            // Аватар для правой панели
            const spaceLetter = state.currentSpace.name.charAt(0).toUpperCase();
            let spaceIconStyle = '';
            let spaceIconContent = '';
            if (state.currentSpace.avatar_url) {
                spaceIconStyle = `background-image: url('${state.currentSpace.avatar_url}'); background-size: cover; background-position: center;`;
                spaceIconContent = '';
            } else {
                spaceIconStyle = `background: ${gradient}`;
                spaceIconContent = spaceLetter;
            }

            // Функция для рендера участника
            const renderMember = (member) => {
                const firstLetter = member.nickname.charAt(0).toUpperCase();
                const avatarGradient = generateGradientFromId(member.id);
                const avatarContent = member.avatar_url
                    ? `<img src="${member.avatar_url}" alt="${member.nickname}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">`
                    : firstLetter;
                const avatarStyle = member.avatar_url ? '' : `background: ${avatarGradient};`;

                // Конфигурация статусов
                const statusConfig = {
                    'online': { color: '#43b581', title: 'В сети' },
                    'away': { color: '#faa61a', title: 'Отошёл' },
                    'dnd': { color: '#f04747', title: 'Не беспокоить' },
                    'offline': { color: '#747f8d', title: 'Не в сети' }
                };
                const statusInfo = statusConfig[member.userStatus] || statusConfig['offline'];

                return `
                    <div class="chat-member-item" data-user-id="${member.id}" style="cursor: pointer; display: flex; align-items: center; padding: 8px; border-radius: 6px; margin-bottom: 2px;">
                        <div style="position: relative; margin-right: 12px; width: 40px; height: 40px;">
                            <div class="chat-member-avatar" style="${avatarStyle} width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 16px;">${avatarContent}</div>
                            <div class="status-indicator" style="
                                position: absolute;
                                bottom: -2px;
                                right: -2px;
                                width: 12px;
                                height: 12px;
                                background-color: ${statusInfo.color};
                                border: 2px solid var(--bg-primary, #1a1a1a);
                                border-radius: 50%;
                            " title="${statusInfo.title}"></div>
                        </div>
                        <div class="chat-member-info">
                            <div class="chat-member-name">
                                ${member.nickname}
                                ${member.is_banned ? '<span class="ban-icon" title="Забанен">🚫</span>' : ''}
                            </div>
                        </div>
                    </div>
                `;
            };

            // Создаем массив всех ролей для отображения (включая группу без роли)
            const allRolesToDisplay = [...sortedRoles];
            if (noRoleGroup.members.length > 0) {
                allRolesToDisplay.push(noRoleGroup.role);
            }

            // Отрисовываем
            sidebarRightContent.innerHTML = `
                <div class="chat-info-header" style="background: ${gradient}">
                    <div style="display: flex; flex-direction: column; align-items: center; padding: 20px;">
                        <div class="chat-icon" style="${spaceIconStyle}; width: 80px; height: 80px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 32px; font-weight: bold; color: white; margin-bottom: 12px;">${spaceIconContent}</div>
                        <h3 class="chat-info-title" style="margin: 0;">${state.currentSpace.name}</h3>
                    </div>
                </div>
                <div class="chat-info-section">
                    <div class="chat-info-section-title">Участники — ${participants.length}</div>
                    <div class="chat-members-by-roles">
                        ${allRolesToDisplay.map(role => {
                            const group = roleGroups[role.id];
                            if (!group || group.members.length === 0) return '';

                            // Сортируем участников: онлайн первые, потом по алфавиту
                            const sortedMembers = group.members.sort((a, b) => {
                                if (a.userStatus === 'online' && b.userStatus !== 'online') return -1;
                                if (a.userStatus !== 'online' && b.userStatus === 'online') return 1;
                                return a.nickname.localeCompare(b.nickname);
                            });

                            return `
                                <div class="role-group" style="margin-bottom: 16px;">
                                    <div class="role-group-header" style="
                                        display: flex;
                                        align-items: center;
                                        margin-bottom: 8px;
                                        padding: 4px 8px;
                                    ">
                                        <div style="
                                            width: 12px;
                                            height: 12px;
                                            background-color: ${role.color};
                                            border-radius: 50%;
                                            margin-right: 8px;
                                        "></div>
                                        <span style="
                                            color: ${role.color};
                                            font-weight: 600;
                                            font-size: 12px;
                                            text-transform: uppercase;
                                            letter-spacing: 0.5px;
                                        ">${role.name} — ${sortedMembers.length}</span>
                                    </div>
                                    <div class="role-members">
                                        ${sortedMembers.map(renderMember).join('')}
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;

            // Добавляем обработчики кликов по участникам и контекстное меню
            setTimeout(() => {
                const memberItems = sidebarRightContent.querySelectorAll('.chat-member-item[data-user-id]');
                memberItems.forEach(item => {
                    // Левый клик - открыть профиль
                    item.addEventListener('click', (e) => {
                        // Не открываем профиль если это ПКМ (контекстное меню)
                        if (e.button !== 0) return;
                        const userId = parseInt(item.dataset.userId);
                        const nickname = item.querySelector('.chat-member-name').textContent.trim();
                        openProfileModal({ id: userId, nickname: nickname });
                    });

                    // Правый клик - контекстное меню
                    item.addEventListener('contextmenu', (e) => {
                        e.preventDefault();
                        const userId = parseInt(item.dataset.userId);
                        const nickname = item.querySelector('.chat-member-name').textContent.trim();
                        showMemberContextMenu(e, { id: userId, nickname: nickname }, state.currentSpace.id);
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

            // Проверка прав на удаление
            const currentChat = state.chats.find(c => c.id === state.currentChatId);
            const canDeleteAny = currentChat?.space_id && state.currentUserPermissions?.includes('delete_any_messages');
            const canDelete = isOwn || canDeleteAny;

            // Кнопки редактирования и удаления
            let messageActions = '';
            if (canDelete) {
                messageActions = `
                    <div class="message-actions">
                        ${isOwn ? `
                            <button class="message-action-btn edit-btn" data-message-id="${msg.id}" title="Редактировать">
                                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M11 4H4C3.46957 4 2.96086 4.21071 2.58579 4.58579C2.21071 4.96086 2 5.46957 2 6V20C2 20.5304 2.21071 21.0391 2.58579 21.4142C2.96086 21.7893 3.46957 22 4 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V13" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                    <path d="M18.5 2.50023C18.8978 2.1024 19.4374 1.87891 20 1.87891C20.5626 1.87891 21.1022 2.1024 21.5 2.50023C21.8978 2.89805 22.1213 3.43762 22.1213 4.00023C22.1213 4.56284 21.8978 5.1024 21.5 5.50023L12 15.0002L8 16.0002L9 12.0002L18.5 2.50023Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                </svg>
                            </button>
                        ` : ''}
                        <button class="message-action-btn delete-btn" data-message-id="${msg.id}" title="Удалить">
                            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M3 6H5H21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                                <path d="M8 6V4C8 3.46957 8.21071 2.96086 8.58579 2.58579C8.96086 2.21071 9.46957 2 10 2H14C14.5304 2 15.0391 2.21071 15.4142 2.58579C15.7893 2.96086 16 3.46957 16 4V6M19 6V20C19 20.5304 18.7893 21.0391 18.4142 21.4142C18.0391 21.7893 17.5304 22 17 22H7C6.46957 22 5.96086 21.7893 5.58579 21.4142C5.21071 21.0391 5 20.5304 5 20V6H19Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            </svg>
                        </button>
                    </div>
                `;
            }

            // Рендер вложения если есть
            const attachmentHTML = msg.attachment ? AttachmentUtils.renderAttachment(msg.attachment, msg.type) : '';

            // Рендер реакций если есть
            const reactionsHTML = AttachmentUtils.renderReactions(msg.reactions || [], msg.my_reaction, msg.id);

            return `
                <div class="message ${isOwn ? 'own-message' : 'other-message'}" data-message-id="${msg.id}">
                    <div class="message-avatar" data-user-id="${msg.user_id}" style="${avatarStyle} cursor: pointer;" title="Открыть профиль">${avatarContent}</div>
                    <div class="message-body">
                        <div class="message-author">${authorName}</div>
                        <div class="message-content" data-original-content="${escapeHtml(msg.content)}">${processMentions(msg.content)}</div>
                        ${attachmentHTML}
                        ${reactionsHTML}
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

        // Рендер вложения если есть
        const attachmentHTML = lastMessage.attachment ? AttachmentUtils.renderAttachment(lastMessage.attachment, lastMessage.type) : '';

        // Рендер реакций если есть
        const reactionsHTML = AttachmentUtils.renderReactions(lastMessage.reactions || [], lastMessage.my_reaction, lastMessage.id);

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isOwn ? 'own-message' : 'other-message'}`;
        messageDiv.dataset.messageId = lastMessage.id;
        messageDiv.innerHTML = `
            <div class="message-avatar" data-user-id="${lastMessage.user_id}" style="${avatarStyle} cursor: pointer;" title="Открыть профиль">${avatarContent}</div>
            <div class="message-body">
                <div class="message-author">${authorName}</div>
                <div class="message-content" data-original-content="${escapeHtml(lastMessage.content)}">${processMentions(lastMessage.content)}</div>
                ${attachmentHTML}
                ${reactionsHTML}
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

        // Добавляем обработчики для реакций и изображений
        attachReactionHandlers(messageDiv);

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

    // Обработка @-упоминаний в тексте сообщения
    function processMentions(text) {
        if (!text) return '';

        try {
            // Сначала экранируем HTML
            const escaped = escapeHtml(text);

            // Паттерн для поиска @-упоминаний: @ + любые символы кроме пробелов и @
            const mentionPattern = /@([^\s@]+)/g;

            // Заменяем упоминания на span с классами
            const processed = escaped.replace(mentionPattern, (match, nickname) => {
                try {
                    const lowerNickname = nickname.toLowerCase();

                    // Определяем класс упоминания
                    let mentionClass = 'mention';

                    if (lowerNickname === 'all') {
                        mentionClass += ' mention-all';
                    } else if (state.currentUser && lowerNickname === state.currentUser.nickname.toLowerCase()) {
                        mentionClass += ' mention-me';
                    }

                    // Дважды экранируем nickname для безопасности
                    const escapedNickname = escapeHtml(nickname);
                    return `<span class="${mentionClass}" data-mention="${escapedNickname}">@${escapedNickname}</span>`;
                } catch (err) {
                    console.error('Error processing mention:', err);
                    return match; // Возвращаем оригинальный текст если ошибка
                }
            });

            return processed;
        } catch (error) {
            console.error('Error in processMentions:', error);
            return escapeHtml(text); // Fallback на просто экранированный текст
        }
    }

    // Настройки (пока не функциональная)
    if (settingsIcon) {
        settingsIcon.addEventListener('click', () => {
            Modal.alert('Настройки будут доступны позже', 'Настройки', 'info');
        });
    }

    // Уведомления
    if (notificationsIcon) {
        notificationsIcon.addEventListener('click', async () => {
            await showNotifications();
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
                // Останавливаем heartbeat перед выходом
                stopHeartbeat();
                // Устанавливаем статус offline
                try {
                    await API.setStatus('offline');
                } catch (error) {
                    console.error('Error setting offline status:', error);
                }
                AuthService.logout();
            }
        });
    }

    // Обработка закрытия страницы/вкладки
    window.addEventListener('beforeunload', () => {
        stopHeartbeat();
        // Синхронный запрос для установки offline статуса при закрытии страницы
        navigator.sendBeacon(`${CONFIG.API_BASE_URL}/status/set-status?status=offline`);
    });

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

        // Определяем чей это профиль
        const isOwnProfile = userData.id === state.currentUser?.id;

        // Для своего профиля используем актуальный статус из state (не делаем запрос к серверу)
        if (isOwnProfile) {
            userData.status = state.currentUser.status || 'online';
        } else {
            // Для чужих профилей - получаем их статус
            try {
                const statusData = await API.getUserStatus(userData.id);
                userData.status = statusData.status || 'offline';
            } catch (error) {
                console.error('Failed to get user status:', error);
                userData.status = 'offline';
            }
        }

        // Заполняем данные профиля
        const profileName = profileModal.querySelector('#profile-name');
        const profileEmail = profileModal.querySelector('#profile-email');
        const profileUserId = profileModal.querySelector('#profile-user-id');
        const profileBio = profileModal.querySelector('#profile-bio');
        const profileBanner = profileModal.querySelector('.profile-banner');
        const profileAvatar = profileModal.querySelector('#profile-avatar-img');
        const bioEditBtn = profileModal.querySelector('#bio-edit-btn');

        if (profileName) profileName.textContent = userData.nickname;

        // Показываем/скрываем кнопки загрузки только для своего профиля
        const avatarContainer = document.getElementById('avatar-container');

        if (avatarUploadBtn) avatarUploadBtn.style.display = isOwnProfile ? 'flex' : 'none';
        if (bannerUploadBtn) bannerUploadBtn.style.display = isOwnProfile ? 'flex' : 'none';
        if (bioEditBtn) bioEditBtn.style.display = isOwnProfile ? 'flex' : 'none';

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

        // Отображение статуса
        const statusDisplay = document.getElementById('profile-status-display');
        const statusIndicator = document.getElementById('profile-status-indicator');
        const statusText = document.getElementById('profile-status-text');
        const statusSelector = document.getElementById('profile-status-selector');
        const statusSelect = document.getElementById('status-select');

        const statusConfig = {
            'online': { color: '#43b581', text: 'В сети' },
            'away': { color: '#faa61a', text: 'Отошёл' },
            'dnd': { color: '#f04747', text: 'Не беспокоить' },
            'offline': { color: '#747f8d', text: 'Не в сети' }
        };

        // Для своего профиля используем актуальный статус из state
        const userStatus = isOwnProfile ? (state.currentUser.status || 'online') : (userData.status || 'offline');
        const statusInfo = statusConfig[userStatus] || statusConfig['offline'];

        if (statusIndicator) {
            statusIndicator.style.backgroundColor = statusInfo.color;
        }
        if (statusText) {
            statusText.textContent = statusInfo.text;
        }

        // Показываем селектор статуса только для своего профиля
        if (isOwnProfile && statusSelector && statusSelect) {
            statusSelector.style.display = 'block';
            statusSelect.value = userStatus;

            // Удаляем старые обработчики
            const newSelect = statusSelect.cloneNode(true);
            statusSelect.parentNode.replaceChild(newSelect, statusSelect);

            // Добавляем обработчик изменения статуса
            newSelect.addEventListener('change', async (e) => {
                const newStatus = e.target.value;
                try {
                    await API.setStatus(newStatus);

                    // Обновляем отображение
                    const newStatusInfo = statusConfig[newStatus];
                    if (statusIndicator) {
                        statusIndicator.style.backgroundColor = newStatusInfo.color;
                    }
                    if (statusText) {
                        statusText.textContent = newStatusInfo.text;
                    }

                    // Обновляем state
                    state.currentUser.status = newStatus;

                    // Обновляем индикатор статуса в левой панели
                    updateUserProfile();

                    // Обновляем статус в правой панели (список участников по ролям)
                    const memberItem = document.querySelector(`.chat-member-item[data-user-id="${state.currentUser.id}"]`);
                    if (memberItem) {
                        const statusDot = memberItem.querySelector('.status-indicator');
                        if (statusDot) {
                            statusDot.style.backgroundColor = newStatusInfo.color;
                            statusDot.title = newStatusInfo.text;
                        }
                    }

                    // Если открыта панель участников в модальном окне - обновляем её
                    const participantsList = document.querySelector('.participants-list');
                    if (participantsList) {
                        const myCard = participantsList.querySelector(`.participant-card[data-user-id="${state.currentUser.id}"]`);
                        if (myCard) {
                            const statusDot = myCard.querySelector('.participant-status-indicator');
                            if (statusDot) {
                                statusDot.style.backgroundColor = newStatusInfo.color;
                            }
                        }
                    }

                    console.log('Status changed to:', newStatus);
                } catch (error) {
                    console.error('Failed to change status:', error);
                    Modal.error('Не удалось изменить статус');
                    // Возвращаем предыдущее значение
                    e.target.value = userStatus;
                }
            });
        } else if (statusSelector) {
            statusSelector.style.display = 'none';
        }

        // Bio
        if (profileBio) {
            if (userData.bio && userData.bio.trim()) {
                profileBio.textContent = userData.bio;
                profileBio.style.color = '#555';
                profileBio.style.fontStyle = 'normal';
            } else {
                profileBio.textContent = 'Информация о пользователе отсутствует';
                profileBio.style.color = '#95a5a6';
                profileBio.style.fontStyle = 'italic';
            }
        }

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

            const { name, description, participants, avatarFile } = formData;

            if (!name) {
                Modal.warning('Введите название комнаты');
                return;
            }

            try {
                const newSpace = await API.createSpace(name, description);

                // Если выбран аватар, загружаем его
                if (avatarFile) {
                    try {
                        console.log('Uploading space avatar...', avatarFile);
                        const uploadResult = await API.uploadSpaceAvatar(newSpace.id, avatarFile);
                        console.log('Avatar upload result:', uploadResult);
                    } catch (err) {
                        console.error('Failed to upload space avatar:', err);
                        Modal.warning('Не удалось загрузить аватар: ' + err.message);
                    }
                }

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

                            // Отображение роли
                            let roleBadge = '';
                            if (p.role) {
                                // Если есть роль из базы - показываем её
                                const roleColor = p.role.color || '#808080';
                                roleBadge = `<div class="participant-badge role-badge" style="background-color: ${roleColor}; border: 1px solid ${roleColor};">${p.role.name}</div>`;
                            } else {
                                // Фоллбек если роль не назначена
                                roleBadge = '<div class="participant-badge member-badge">Участник</div>';
                            }

                            // Цвет статуса
                            const statusColors = {
                                'online': '#43b581',
                                'away': '#faa61a',
                                'dnd': '#f04747',
                                'offline': '#747f8d'
                            };
                            const statusColor = statusColors[p.status] || statusColors['offline'];

                            return `
                                <div class="participant-card" data-user-id="${p.id}">
                                    <div style="position: relative; display: inline-block;">
                                        <div class="participant-avatar">${firstLetter}</div>
                                        <div class="participant-status-indicator" style="
                                            position: absolute;
                                            bottom: 0;
                                            right: 0;
                                            width: 10px;
                                            height: 10px;
                                            border-radius: 50%;
                                            background-color: ${statusColor};
                                            border: 2px solid white;
                                        "></div>
                                    </div>
                                    <div class="participant-info">
                                        <div class="participant-name">
                                            ${p.nickname}
                                            ${p.is_banned ? '<span class="ban-icon" title="Забанен">🚫</span>' : ''}
                                        </div>
                                        ${roleBadge}
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

            // Запускаем автообновление статусов
            startStatusUpdates(spaceId);

            await Modal.custom(content, '', () => {
                // Инициализация контекстного меню после отрисовки
                initParticipantContextMenu(spaceId, isAdmin);
            });

            // Останавливаем автообновление после закрытия модального окна
            if (state.statusUpdateInterval) {
                clearInterval(state.statusUpdateInterval);
                state.statusUpdateInterval = null;
            }
        } catch (error) {
            await Modal.error('Ошибка: ' + error.message);
        }
    }

    // Контекстное меню участников
    function initParticipantContextMenu(spaceId, hasAdminRights) {
        const participantCards = document.querySelectorAll('.participant-card');

        // Создаем меню если его нет
        let contextMenu = document.querySelector('.participant-context-menu');
        if (!contextMenu) {
            contextMenu = document.createElement('div');
            contextMenu.className = 'participant-context-menu';
            document.body.appendChild(contextMenu);
        }

        participantCards.forEach(card => {
            const userId = parseInt(card.dataset.userId);

            // Не показываем меню на себе
            if (userId === state.currentUser.id) return;

            card.addEventListener('contextmenu', async (e) => {
                e.preventDefault();

                // Получаем права текущего пользователя
                const permissions = await API.getMyPermissions(spaceId);
                const canKick = permissions.is_admin || permissions.permissions.includes('kick_members');
                const canBan = permissions.is_admin || permissions.permissions.includes('ban_members');
                const canManageRoles = permissions.is_admin || permissions.permissions.includes('manage_roles');

                if (!canKick && !canBan && !canManageRoles) return;

                // Получаем роль целевого пользователя
                const participantsData = await API.getSpaceParticipants(spaceId);
                const targetUser = participantsData.participants.find(p => p.id === userId);
                const targetUserRole = targetUser?.role?.name || 'Участник';

                // Определяем текущую роль (из permissions)
                const currentUserRole = permissions.role?.name || 'Участник';

                // Иерархия ролей
                const roleHierarchy = {
                    'Участник': 1,
                    'Модератор': 2,
                    'Владелец': 3
                };

                const currentLevel = roleHierarchy[currentUserRole] || 0;
                const targetLevel = roleHierarchy[targetUserRole] || 0;
                const canModerate = permissions.is_admin || currentLevel > targetLevel;

                // Получаем список ролей для назначения
                const allRoles = await API.getSpaceRoles(spaceId);
                // Фильтруем роли: исключаем "Владелец" и роли >= текущей роли модератора
                const roles = allRoles.filter(r => {
                    if (r.name === 'Владелец') return false;
                    if (permissions.is_admin) return true; // Владелец видит все роли кроме "Владелец"
                    const roleLevel = roleHierarchy[r.name] || 0;
                    return roleLevel < currentLevel; // Модератор видит только роли ниже своей
                });

                // Формируем меню
                let menuHTML = '';

                if (canManageRoles && canModerate && roles.length > 0) {
                    menuHTML += '<div class="context-menu-section">';
                    menuHTML += '<div style="padding: 8px 16px; font-size: 12px; color: #666; font-weight: 600;">Назначить роль</div>';
                    roles.forEach(role => {
                        menuHTML += `
                            <button class="context-menu-item" onclick="window.chatApp.assignRoleToUser(${spaceId}, ${userId}, ${role.id})">
                                <span style="width: 12px; height: 12px; border-radius: 50%; background: ${role.color || '#808080'};"></span>
                                ${role.name}
                            </button>
                        `;
                    });
                    menuHTML += '</div>';
                }

                if (canModerate) {
                    if (menuHTML) menuHTML += '<div class="context-menu-divider"></div>';

                    // Если пользователь забанен, показываем кнопку разбана
                    if (targetUser && targetUser.is_banned && canBan) {
                        menuHTML += `
                            <button class="context-menu-item" onclick="window.chatApp.unbanUserFromSpace(${spaceId}, ${userId})" style="color: #2e7d32;">
                                ✅ Разбанить
                            </button>
                        `;
                    }

                    if (canKick) {
                        menuHTML += `
                            <button class="context-menu-item" onclick="window.chatApp.kickUserFromSpace(${spaceId}, ${userId})">
                                👢 Исключить
                            </button>
                        `;
                    }

                    if (canBan && (!targetUser || !targetUser.is_banned)) {
                        menuHTML += `
                            <button class="context-menu-item danger" onclick="window.chatApp.banUserFromSpace(${spaceId}, ${userId})">
                                🚫 Забанить
                            </button>
                        `;
                    }
                }

                contextMenu.innerHTML = menuHTML;
                contextMenu.style.left = `${e.pageX}px`;
                contextMenu.style.top = `${e.pageY}px`;
                contextMenu.classList.add('active');
            });
        });

        // Закрытие меню по клику вне его
        document.addEventListener('click', () => {
            if (contextMenu) {
                contextMenu.classList.remove('active');
            }
        });
    }

    // Показать контекстное меню для участника
    async function showMemberContextMenu(event, user, spaceId) {
        console.log('showMemberContextMenu called:', { userId: user.id, currentUserId: state.currentUser.id, adminId: state.currentSpace.admin_id });

        // Не показываем меню на себе
        if (user.id === state.currentUser.id) {
            console.log('Skipping: user is current user');
            return;
        }

        // Не показываем меню на владельце пространства
        if (user.id === state.currentSpace.admin_id) {
            console.log('Skipping: user is admin');
            return;
        }

        // Создаем меню если его нет
        let contextMenu = document.querySelector('.participant-context-menu');
        if (!contextMenu) {
            contextMenu = document.createElement('div');
            contextMenu.className = 'participant-context-menu';
            document.body.appendChild(contextMenu);

            // Закрытие меню по клику вне его
            document.addEventListener('click', () => {
                contextMenu.classList.remove('active');
            });
        }

        try {
            // Проверяем права текущего пользователя
            const isAdmin = state.currentSpace.admin_id === state.currentUser.id;
            console.log('isAdmin:', isAdmin);

            // Получаем разрешения через API
            const permissions = await API.getMyPermissions(spaceId).catch((err) => {
                console.error('Error getting permissions:', err);
                return { permissions: [] };
            });
            const userPermissions = permissions.permissions || [];
            console.log('userPermissions:', userPermissions);

            const canManageRoles = isAdmin || userPermissions.includes('promote_members');
            const canKick = isAdmin || userPermissions.includes('kick_members');
            const canBan = isAdmin || userPermissions.includes('ban_members');
            const canRestrict = isAdmin || userPermissions.includes('restrict_members');
            console.log('Permissions:', { canManageRoles, canKick, canBan, canRestrict });

            // Если нет никаких прав, не показываем меню
            if (!canManageRoles && !canKick && !canBan && !canRestrict) {
                console.log('No permissions to show menu');
                return;
            }

            // Получаем информацию о целевом пользователе
            const participantsData = await API.getSpaceParticipants(spaceId);
            const targetUser = participantsData.participants.find(p => p.id === user.id);

            // Проверяем, является ли целевой пользователь "неприкасаемым"
            // Получаем разрешения целевого пользователя
            let targetUserPermissions = [];
            if (targetUser && targetUser.role) {
                // Нужно получить разрешения роли целевого пользователя
                // Пока проверим через API (можно оптимизировать)
                try {
                    const targetPerms = await API.getMyPermissions(spaceId);
                    // TODO: здесь нужен endpoint для получения разрешений другого пользователя
                    // Пока будем считать что у targetUser есть поле permissions
                } catch (e) {
                    console.error('Error getting target user permissions:', e);
                }
            }

            // Если пользователь неприкасаемый и текущий пользователь не владелец - не показываем меню
            const isTargetUntouchable = targetUser && targetUser.role && targetUser.role.permissions && targetUser.role.permissions.includes('untouchable');
            if (isTargetUntouchable && !isAdmin) {
                console.log('Target user is untouchable');
                return;
            }

            // Формируем меню
            let menuHTML = '';

            // 1. Назначить роль (только если есть разрешение)
            if (canManageRoles) {
                menuHTML += `
                    <button class="context-menu-item" onclick="window.chatApp.openAssignRoleModal(${spaceId}, ${user.id}, '${user.nickname}')">
                        👑 Назначить роль
                    </button>
                `;
            }

            // 2. Выгнать (только если есть разрешение)
            if (canKick) {
                menuHTML += `
                    <button class="context-menu-item" onclick="window.chatApp.kickUserFromSpace(${spaceId}, ${user.id})">
                        👢 Выгнать
                    </button>
                `;
            }

            // 3. Забанить или Разбанить (только если есть разрешение)
            if (canBan) {
                if (targetUser && targetUser.is_banned) {
                    menuHTML += `
                        <button class="context-menu-item" onclick="window.chatApp.unbanUserFromSpace(${spaceId}, ${user.id})" style="color: #2e7d32;">
                            ✅ Разбанить
                        </button>
                    `;
                } else {
                    menuHTML += `
                        <button class="context-menu-item danger" onclick="window.chatApp.banUserFromSpace(${spaceId}, ${user.id})">
                            🚫 Забанить
                        </button>
                    `;
                }
            }

            // 4. Ограничить (только если есть разрешение)
            if (canRestrict) {
                menuHTML += `
                    <button class="context-menu-item" onclick="window.chatApp.openRestrictModal(${spaceId}, ${user.id}, '${user.nickname}')">
                        🔒 Ограничить
                    </button>
                `;
            }

            if (!menuHTML) return;

            contextMenu.innerHTML = menuHTML;
            contextMenu.style.left = `${event.pageX}px`;
            contextMenu.style.top = `${event.pageY}px`;
            contextMenu.classList.add('active');

        } catch (error) {
            console.error('Error showing context menu:', error);
        }
    }

    // Контекстное меню для правой панели (аналогично модальному окну)
    function initRightPanelContextMenu(spaceId) {
        const memberItems = sidebarRightContent.querySelectorAll('.chat-member-item[data-user-id]');

        // Создаем меню если его нет
        let contextMenu = document.querySelector('.participant-context-menu');
        if (!contextMenu) {
            contextMenu = document.createElement('div');
            contextMenu.className = 'participant-context-menu';
            document.body.appendChild(contextMenu);
        }

        memberItems.forEach(item => {
            const userId = parseInt(item.dataset.userId);

            // Не показываем меню на себе
            if (userId === state.currentUser.id) return;

            item.addEventListener('contextmenu', async (e) => {
                e.preventDefault();
                e.stopPropagation();

                // Получаем права текущего пользователя
                const permissions = await API.getMyPermissions(spaceId);
                const canKick = permissions.is_admin || permissions.permissions.includes('kick_members');
                const canBan = permissions.is_admin || permissions.permissions.includes('ban_members');
                const canManageRoles = permissions.is_admin || permissions.permissions.includes('manage_roles');

                if (!canKick && !canBan && !canManageRoles) return;

                // Получаем роль целевого пользователя
                const participantsData = await API.getSpaceParticipants(spaceId);
                const targetUser = participantsData.participants.find(p => p.id === userId);
                const targetUserRole = targetUser?.role?.name || 'Участник';

                // Определяем текущую роль (из permissions)
                const currentUserRole = permissions.role?.name || 'Участник';

                // Иерархия ролей
                const roleHierarchy = {
                    'Участник': 1,
                    'Модератор': 2,
                    'Владелец': 3
                };

                const currentLevel = roleHierarchy[currentUserRole] || 0;
                const targetLevel = roleHierarchy[targetUserRole] || 0;
                const canModerate = permissions.is_admin || currentLevel > targetLevel;

                // Получаем список ролей для назначения
                const allRoles = await API.getSpaceRoles(spaceId);
                // Фильтруем роли: исключаем "Владелец" и роли >= текущей роли модератора
                const roles = allRoles.filter(r => {
                    if (r.name === 'Владелец') return false;
                    if (permissions.is_admin) return true; // Владелец видит все роли кроме "Владелец"
                    const roleLevel = roleHierarchy[r.name] || 0;
                    return roleLevel < currentLevel; // Модератор видит только роли ниже своей
                });

                // Формируем меню
                let menuHTML = '';

                if (canManageRoles && canModerate && roles.length > 0) {
                    menuHTML += '<div class="context-menu-section">';
                    menuHTML += '<div style="padding: 8px 16px; font-size: 12px; color: #666; font-weight: 600;">Назначить роль</div>';
                    roles.forEach(role => {
                        menuHTML += `
                            <button class="context-menu-item" onclick="window.chatApp.assignRoleToUser(${spaceId}, ${userId}, ${role.id})">
                                <span style="width: 12px; height: 12px; border-radius: 50%; background: ${role.color || '#808080'};"></span>
                                ${role.name}
                            </button>
                        `;
                    });
                    menuHTML += '</div>';
                }

                if (canModerate) {
                    if (menuHTML) menuHTML += '<div class="context-menu-divider"></div>';

                    // Если пользователь забанен, показываем кнопку разбана
                    if (targetUser && targetUser.is_banned && canBan) {
                        menuHTML += `
                            <button class="context-menu-item" onclick="window.chatApp.unbanUserFromSpace(${spaceId}, ${userId})" style="color: #2e7d32;">
                                ✅ Разбанить
                            </button>
                        `;
                    }

                    if (canKick) {
                        menuHTML += `
                            <button class="context-menu-item" onclick="window.chatApp.kickUserFromSpace(${spaceId}, ${userId})">
                                👢 Исключить
                            </button>
                        `;
                    }

                    if (canBan && (!targetUser || !targetUser.is_banned)) {
                        menuHTML += `
                            <button class="context-menu-item danger" onclick="window.chatApp.banUserFromSpace(${spaceId}, ${userId})">
                                🚫 Забанить
                            </button>
                        `;
                    }
                }

                contextMenu.innerHTML = menuHTML;
                contextMenu.style.left = `${e.pageX}px`;
                contextMenu.style.top = `${e.pageY}px`;
                contextMenu.classList.add('active');
            });
        });

        // Закрытие меню по клику вне его
        document.addEventListener('click', () => {
            if (contextMenu) {
                contextMenu.classList.remove('active');
            }
        });
    }

    async function assignRoleToUser(spaceId, userId, roleId) {
        // Закрываем контекстное меню
        const contextMenu = document.querySelector('.participant-context-menu');
        if (contextMenu) contextMenu.classList.remove('active');

        try {
            await API.assignRole(spaceId, userId, roleId);
            await Modal.success('Роль назначена!');
            await refreshParticipantsList(spaceId);
            // Обновляем правую панель тоже
            await updateChatInfo();
        } catch (error) {
            await Modal.error('Ошибка: ' + error.message);
        }
    }

    async function banUserFromSpace(spaceId, userId) {
        // Закрываем контекстное меню
        const contextMenu = document.querySelector('.participant-context-menu');
        if (contextMenu) contextMenu.classList.remove('active');

        // Простая форма бана (можно расширить)
        const reason = prompt('Причина бана (необязательно):');
        const durationDays = prompt('Длительность в днях (оставьте пустым для вечного бана):');

        let until = null;
        if (durationDays && !isNaN(durationDays)) {
            until = new Date();
            until.setDate(until.getDate() + parseInt(durationDays));
        }

        try {
            await API.banUser(spaceId, userId, {
                reason: reason || null,
                until: until ? until.toISOString() : null
            });
            await Modal.success('Пользователь забанен!');
            await refreshParticipantsList(spaceId);
            // Обновляем правую панель
            await updateChatInfo();
        } catch (error) {
            await Modal.error('Ошибка: ' + error.message);
        }
    }

    async function unbanUserFromSpace(spaceId, userId) {
        // Закрываем контекстное меню
        const contextMenu = document.querySelector('.participant-context-menu');
        if (contextMenu) contextMenu.classList.remove('active');

        const confirm = await Modal.confirm('Вы уверены, что хотите разбанить этого пользователя?');
        if (!confirm) return;

        try {
            await API.unbanUser(spaceId, userId);
            await Modal.success('Пользователь разбанен!');
            await refreshParticipantsList(spaceId);
            // Обновляем правую панель
            await updateChatInfo();
        } catch (error) {
            await Modal.error('Ошибка: ' + error.message);
        }
    }

    async function kickUserFromSpace(spaceId, userId) {
        // Закрываем контекстное меню
        const contextMenu = document.querySelector('.participant-context-menu');
        if (contextMenu) contextMenu.classList.remove('active');

        const confirm = await Modal.confirm('Вы уверены, что хотите удалить этого пользователя?');
        if (!confirm) return;

        try {
            await API.kickUser(spaceId, userId);

            // Обновляем список участников без закрытия окна
            await refreshParticipantsList(spaceId);
            // Обновляем правую панель
            await updateChatInfo();

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

                        // Отображение роли
                        let roleBadge = '';
                        if (p.role) {
                            const roleColor = p.role.color || '#808080';
                            roleBadge = `<div class="participant-badge role-badge" style="background-color: ${roleColor}; border: 1px solid ${roleColor};">${p.role.name}</div>`;
                        } else {
                            roleBadge = '<div class="participant-badge member-badge">Участник</div>';
                        }

                        return `
                            <div class="participant-card" data-user-id="${p.id}">
                                <div class="participant-avatar">${firstLetter}</div>
                                <div class="participant-info">
                                    <div class="participant-name">
                                        ${p.nickname}
                                        ${p.is_banned ? '<span class="ban-icon" title="Забанен">🚫</span>' : ''}
                                    </div>
                                    ${roleBadge}
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

            // Переинициализируем контекстное меню после обновления
            setTimeout(() => {
                initParticipantContextMenu(spaceId, isAdmin);
            }, 50);
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

    // Обработчики для редактирования bio
    const bioEditBtn = document.getElementById('bio-edit-btn');
    const bioSaveBtn = document.querySelector('.bio-save-btn');
    const bioCancelBtn = document.querySelector('.bio-cancel-btn');
    const profileBio = document.getElementById('profile-bio');
    const bioTextarea = document.getElementById('profile-bio-textarea');
    const bioControls = document.getElementById('bio-controls');

    if (bioEditBtn) {
        bioEditBtn.addEventListener('click', () => {
            // Показываем режим редактирования
            if (profileBio) profileBio.style.display = 'none';
            if (bioTextarea) {
                bioTextarea.style.display = 'block';
                bioTextarea.value = state.currentUser.bio || '';
            }
            if (bioControls) bioControls.style.display = 'flex';
        });
    }

    if (bioSaveBtn) {
        bioSaveBtn.addEventListener('click', async () => {
            const newBio = bioTextarea.value.trim();

            // Валидация длины (максимум 500 символов)
            if (newBio.length > 500) {
                Modal.warning('Описание не должно превышать 500 символов!');
                return;
            }

            try {
                // Обновляем профиль через API
                const updatedUser = await API.updateProfile({
                    bio: newBio || null
                });

                // Обновляем state
                state.currentUser = updatedUser;

                // Обновляем UI
                if (profileBio) {
                    if (newBio) {
                        profileBio.textContent = newBio;
                        profileBio.style.color = '#555';
                        profileBio.style.fontStyle = 'normal';
                    } else {
                        profileBio.textContent = 'Информация о пользователе отсутствует';
                        profileBio.style.color = '#95a5a6';
                        profileBio.style.fontStyle = 'italic';
                    }
                }

                // Скрываем режим редактирования
                if (bioTextarea) bioTextarea.style.display = 'none';
                if (profileBio) profileBio.style.display = 'block';
                if (bioControls) bioControls.style.display = 'none';

                Modal.success('Информация о себе обновлена!');
            } catch (error) {
                console.error('Error updating bio:', error);
                Modal.error('Ошибка обновления: ' + error.message);
            }
        });
    }

    if (bioCancelBtn) {
        bioCancelBtn.addEventListener('click', () => {
            // Отменяем изменения и скрываем режим редактирования
            if (bioTextarea) {
                bioTextarea.value = state.currentUser.bio || '';
                bioTextarea.style.display = 'none';
            }
            if (profileBio) profileBio.style.display = 'block';
            if (bioControls) bioControls.style.display = 'none';
        });
    }

    // === ПРИКРЕПЛЕНИЕ ФАЙЛОВ ===

    // Флаг для предотвращения множественной инициализации
    let fileAttachmentInitialized = false;

    function initFileAttachment() {
        const attachBtn = document.getElementById('attach-file-btn');
        const fileInput = document.getElementById('chat-file-input');

        if (!attachBtn || !fileInput) return;

        // Если уже инициализировано, удаляем старый input и создаем новый
        if (fileAttachmentInitialized) {
            // Клонируем input для удаления всех старых обработчиков
            const newFileInput = fileInput.cloneNode(true);
            fileInput.parentNode.replaceChild(newFileInput, fileInput);
            // Обновляем ссылку
            const updatedFileInput = document.getElementById('chat-file-input');

            // Добавляем обработчик на кнопку
            const newAttachBtn = document.getElementById('attach-file-btn');
            newAttachBtn.addEventListener('click', () => {
                updatedFileInput.click();
            });

            // Добавляем обработчик на input
            updatedFileInput.addEventListener('change', handleFileUpload);
            return;
        }

        fileAttachmentInitialized = true;

        attachBtn.addEventListener('click', () => {
            fileInput.click();
        });

        fileInput.addEventListener('change', handleFileUpload);
    }

    async function handleFileUpload(e) {
        const fileInput = e.target;
        const file = fileInput.files[0];
        if (!file) return;

        try {
            // Валидация файла
            AttachmentUtils.validateFile(file);

            // Определяем тип файла
            const fileType = AttachmentUtils.getFileType(file);
            if (!fileType) {
                throw new Error('Неподдерживаемый тип файла');
            }

            // Показываем индикатор загрузки
            const messageForm = document.getElementById('message-form');
            const progressDiv = document.createElement('div');
            progressDiv.className = 'upload-progress';
            progressDiv.innerHTML = `
                <div class="spinner"></div>
                <span>Загрузка ${file.name}...</span>
            `;
            messageForm.appendChild(progressDiv);

            // Загружаем файл
            let uploadedMessage;
            if (fileType === 'image') {
                uploadedMessage = await API.uploadImage(state.currentChatId, file);
            } else if (fileType === 'audio') {
                uploadedMessage = await API.uploadAudio(state.currentChatId, file);
            } else if (fileType === 'document') {
                uploadedMessage = await API.uploadDocument(state.currentChatId, file);
            }

            // Добавляем сообщение в список
            state.messages.push(uploadedMessage);
            updateMessagesInChat();

            // Убираем индикатор загрузки
            progressDiv.remove();

            // Очищаем input
            fileInput.value = '';

            await Modal.success('Файл успешно загружен');

        } catch (error) {
            console.error('File upload error:', error);
            await Modal.error('Ошибка загрузки файла: ' + error.message);
            fileInput.value = '';
        }
    }

    // === РЕАКЦИИ ===

    function attachReactionHandlers(container) {
        if (!container) return;

        // Обработчики кликов по существующим реакциям (toggle)
        const reactionItems = container.querySelectorAll('.reaction-item');
        reactionItems.forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const messageId = btn.dataset.messageId;
                const reaction = btn.dataset.reaction;
                await handleToggleReaction(messageId, reaction);
            });
        });

        // Обработчики кликов по сообщениям для открытия picker реакций
        const messages = container.querySelectorAll('.message');
        messages.forEach(messageEl => {
            // Кликаем на message-body, чтобы не конфликтовать с аватаром и кнопками
            const messageBody = messageEl.querySelector('.message-body');
            if (!messageBody) return;

            messageBody.addEventListener('click', (e) => {
                // Игнорируем клики по кнопкам редактирования/удаления и другим интерактивным элементам
                if (e.target.closest('.message-action-btn') ||
                    e.target.closest('.message-edit-form') ||
                    e.target.closest('.reaction-item') ||
                    e.target.closest('.attachment-image') ||
                    e.target.closest('audio') ||
                    e.target.closest('a') ||
                    e.target.closest('button')) {
                    return;
                }

                const messageId = messageEl.dataset.messageId;
                showReactionPicker(messageEl, messageId);
            });
        });

        // Обработчики кликов по изображениям для lightbox
        const images = container.querySelectorAll('.attachment-image');
        images.forEach(img => {
            img.addEventListener('click', (e) => {
                e.stopPropagation();
                const imageUrl = img.dataset.url;
                AttachmentUtils.openImageLightbox(imageUrl);
            });
        });
    }

    async function handleToggleReaction(messageId, reaction) {
        try {
            const result = await API.addReaction(state.currentChatId, messageId, reaction);

            // Обновляем реакции в локальном сообщении
            const message = state.messages.find(m => m.id == messageId);
            if (message) {
                message.reactions = result.reactions;
                message.my_reaction = result.my_reaction;
            }

            // Перерисовываем чат
            renderChat();

        } catch (error) {
            console.error('Reaction error:', error);
            await Modal.error('Ошибка добавления реакции');
        }
    }

    function showReactionPicker(element, messageId) {
        // Убираем старый picker если есть
        const oldPicker = document.querySelector('.reaction-picker-popup');
        if (oldPicker) oldPicker.remove();

        // Создаем popup с расширенным набором реакций
        const picker = document.createElement('div');
        picker.className = 'reaction-picker-popup';

        // Расширенный набор эмодзи (6 рядов по 7)
        const reactions = [
            // Часто используемые
            '👍', '❤️', '😂', '😮', '😢', '😡', '🔥',
            // Эмоции
            '😊', '😍', '🥰', '😘', '😎', '🤔', '🙄',
            // Жесты
            '👏', '🙌', '🤝', '👋', '✌️', '🤞', '💪',
            // Праздники
            '🎉', '🎊', '🎈', '🎁', '🎂', '🥳', '🎆',
            // Разное
            '⭐', '✨', '💯', '🏆', '✅', '❌', '💬',
            // Природа
            '🌟', '☀️', '🌈', '⚡', '🔴', '🟢', '🔵'
        ];

        reactions.forEach(emoji => {
            const btn = document.createElement('button');
            btn.textContent = emoji;
            btn.addEventListener('click', async () => {
                await handleToggleReaction(messageId, emoji);
                picker.remove();
            });
            picker.appendChild(btn);
        });

        document.body.appendChild(picker);

        // Позиционируем относительно элемента (используя фиксированное позиционирование)
        const rect = element.getBoundingClientRect();
        const pickerRect = picker.getBoundingClientRect();

        // Определяем где больше места - сверху или снизу
        const spaceBelow = window.innerHeight - rect.bottom;
        const spaceAbove = rect.top;

        if (spaceBelow >= pickerRect.height + 10) {
            // Размещаем снизу - небольшой отступ от сообщения
            picker.style.top = `${rect.bottom + 5}px`;
            picker.style.bottom = 'auto';
        } else if (spaceAbove >= pickerRect.height + 10) {
            // Размещаем сверху - прямо над сообщением
            picker.style.top = `${rect.top - pickerRect.height - 5}px`;
            picker.style.bottom = 'auto';
        } else {
            // Центрируем по вертикали
            picker.style.top = `${Math.max(10, (window.innerHeight - pickerRect.height) / 2)}px`;
            picker.style.bottom = 'auto';
        }

        // Горизонтальное позиционирование
        const leftPos = Math.min(
            rect.left,
            window.innerWidth - pickerRect.width - 10
        );
        picker.style.left = `${Math.max(10, leftPos)}px`;

        // Убираем по клику вне
        setTimeout(() => {
            const closePickerOnClick = (e) => {
                if (!picker.contains(e.target) && !element.contains(e.target)) {
                    picker.remove();
                    document.removeEventListener('click', closePickerOnClick);
                }
            };
            document.addEventListener('click', closePickerOnClick);
        }, 100);

        // Убираем по ESC
        const handleEsc = (e) => {
            if (e.key === 'Escape') {
                picker.remove();
                document.removeEventListener('keydown', handleEsc);
            }
        };
        document.addEventListener('keydown', handleEsc);
    }

    // Открыть модальное окно для назначения роли
    async function openAssignRoleModal(spaceId, userId, userNickname) {
        console.log('openAssignRoleModal called:', { spaceId, userId, userNickname });

        // Закрываем контекстное меню
        const contextMenu = document.querySelector('.participant-context-menu');
        if (contextMenu) contextMenu.classList.remove('active');

        // Создаем модальное окно
        const modal = document.createElement('div');
        modal.className = 'custom-modal active';
        modal.innerHTML = `
            <div class="custom-modal-content" style="max-width: 500px;">
                <div class="custom-modal-header">
                    <h3 id="modal-title">Назначить роль: ${userNickname}</h3>
                    <button class="custom-modal-close">&times;</button>
                </div>
                <div class="custom-modal-body" id="role-modal-body">
                    <div class="loading">Загрузка ролей...</div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        console.log('Modal appended to body:', modal);

        // Закрытие модального окна
        const closeModal = () => {
            modal.remove();
        };
        modal.querySelector('.custom-modal-close').addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });

        try {
            console.log('Loading roles and permissions...');
            // Загружаем роли и доступные разрешения
            const [roles, permissionsData] = await Promise.all([
                API.getSpaceRoles(spaceId),
                API.getAvailablePermissions(spaceId)
            ]);
            console.log('Roles loaded:', roles);
            console.log('Permissions loaded:', permissionsData);

            // Показываем режим выбора роли
            showRoleSelectionMode(modal, spaceId, userId, roles, permissionsData);

        } catch (error) {
            console.error('Error loading roles:', error);
            modal.querySelector('#role-modal-body').innerHTML = `
                <div class="error" style="color: #f04747; text-align: center; padding: 20px;">
                    Ошибка загрузки ролей: ${error.message}
                </div>
            `;
        }
    }

    // Показать режим выбора роли
    function showRoleSelectionMode(modal, spaceId, userId, roles, permissionsData) {
        const modalBody = modal.querySelector('#role-modal-body');
        modal.querySelector('#modal-title').textContent = 'Выберите роль';

        // Фильтруем роль "Владелец" - её нельзя назначать
        const assignableRoles = roles.filter(role => role.name !== 'Владелец');
        const sortedRoles = [...assignableRoles].sort((a, b) => b.priority - a.priority);

        modalBody.innerHTML = `
            <div class="roles-selection-list" style="max-height: 400px; overflow-y: auto;">
                ${sortedRoles.map(role => `
                    <div class="role-selection-item" data-role-id="${role.id}" style="
                        padding: 12px;
                        margin-bottom: 8px;
                        border-radius: 8px;
                        border: 2px solid transparent;
                        transition: all 0.2s;
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                    ">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div style="width: 16px; height: 16px; border-radius: 50%; background: ${role.color};"></div>
                            <div>
                                <div style="font-weight: 600; color: ${role.color};">${role.name}</div>
                                <div style="font-size: 11px; color: #888;">${role.member_count || 0} участников</div>
                            </div>
                        </div>
                        <div style="display: flex; gap: 8px; align-items: center;">
                            <button class="assign-role-btn" style="
                                padding: 6px 12px;
                                background: ${role.color};
                                color: white;
                                border: none;
                                border-radius: 6px;
                                cursor: pointer;
                                font-size: 12px;
                                font-weight: 600;
                            ">Назначить</button>
                            <button class="delete-role-btn" data-role-id="${role.id}" style="
                                padding: 6px 10px;
                                background: #e74c3c;
                                color: white;
                                border: none;
                                border-radius: 6px;
                                cursor: pointer;
                                font-size: 12px;
                                font-weight: 600;
                            " title="Удалить роль">🗑️</button>
                        </div>
                    </div>
                `).join('')}
            </div>
            <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #333;">
                <button id="create-new-role-btn" style="
                    width: 100%;
                    padding: 12px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    cursor: pointer;
                    font-weight: 600;
                    font-size: 14px;
                ">+ Создать новую роль</button>
            </div>
        `;

        // Обработчики назначения ролей
        modalBody.querySelectorAll('.assign-role-btn').forEach((btn, index) => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const roleId = sortedRoles[index].id;
                try {
                    await API.assignRoleToMember(spaceId, userId, roleId);
                    await Modal.success('Роль успешно назначена!');
                    modal.remove();
                    await updateChatInfo();
                } catch (error) {
                    await Modal.error('Ошибка: ' + error.message);
                }
            });
        });

        // Обработчики удаления ролей
        modalBody.querySelectorAll('.delete-role-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const roleId = parseInt(btn.getAttribute('data-role-id'));
                const role = sortedRoles.find(r => r.id === roleId);

                const confirmed = await Modal.confirm(
                    `Вы уверены, что хотите удалить роль "${role.name}"?`,
                    'Это действие нельзя отменить. Все пользователи с этой ролью потеряют её.'
                );

                if (confirmed) {
                    try {
                        await API.deleteRole(spaceId, roleId);
                        await Modal.success('Роль успешно удалена!');

                        // Перезагружаем список ролей
                        const updatedRoles = await API.getSpaceRoles(spaceId);
                        showRoleSelectionMode(modal, spaceId, userId, updatedRoles, permissionsData);
                        await updateChatInfo();
                    } catch (error) {
                        await Modal.error('Ошибка удаления роли: ' + error.message);
                    }
                }
            });
        });

        // Кнопка создания новой роли
        modalBody.querySelector('#create-new-role-btn').addEventListener('click', () => {
            showRoleCreationMode(modal, spaceId, userId, permissionsData);
        });
    }

    // Показать режим создания роли
    function showRoleCreationMode(modal, spaceId, userId, permissionsData) {
        const modalBody = modal.querySelector('#role-modal-body');
        modal.querySelector('#modal-title').textContent = 'Создать новую роль';

        // Формируем группы разрешений
        let permissionsHTML = '';
        for (const [groupKey, groupData] of Object.entries(permissionsData)) {
            permissionsHTML += `
                <div class="permission-group" style="margin-bottom: 20px;">
                    <div style="font-weight: 600; margin-bottom: 8px; color: #888; font-size: 12px; text-transform: uppercase;">
                        ${groupData.name}
                    </div>
                    ${groupData.permissions.map(perm => `
                        <label style="display: flex; align-items: center; padding: 8px; cursor: pointer; border-radius: 6px; transition: background 0.2s;">
                            <input type="checkbox" name="permission" value="${perm.key}" style="margin-right: 12px; width: 18px; height: 18px; cursor: pointer;">
                            <div>
                                <div style="font-weight: 500;">${perm.name}</div>
                                <div style="font-size: 11px; color: #666;">${perm.description}</div>
                            </div>
                        </label>
                    `).join('')}
                </div>
            `;
        }

        modalBody.innerHTML = `
            <div style="max-height: 500px; overflow-y: auto; padding-right: 8px;">
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 8px; font-weight: 600;">Название роли</label>
                    <input type="text" id="role-name-input" placeholder="Например: Модератор" style="
                        width: 100%;
                        padding: 10px;
                        border: 2px solid #ddd;
                        border-radius: 8px;
                        background: #fff;
                        color: #2c3e50;
                        font-size: 14px;
                    ">
                </div>

                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 8px; font-weight: 600;">Цвет роли</label>
                    <input type="color" id="role-color-input" value="#3498db" style="
                        width: 100%;
                        height: 40px;
                        border: 2px solid #333;
                        border-radius: 8px;
                        background: var(--bg-secondary);
                        cursor: pointer;
                    ">
                </div>

                <div>
                    <label style="display: block; margin-bottom: 12px; font-weight: 600;">Разрешения</label>
                    ${permissionsHTML}
                </div>
            </div>

            <div style="display: flex; gap: 12px; margin-top: 20px; padding-top: 16px; border-top: 1px solid #333;">
                <button id="back-btn" style="
                    flex: 1;
                    padding: 12px;
                    background: #555;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    cursor: pointer;
                    font-weight: 600;
                ">← Назад</button>
                <button id="create-role-btn" style="
                    flex: 2;
                    padding: 12px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    cursor: pointer;
                    font-weight: 600;
                ">Создать роль</button>
            </div>
        `;

        // Кнопка "Назад"
        modalBody.querySelector('#back-btn').addEventListener('click', async () => {
            const roles = await API.getSpaceRoles(spaceId);
            showRoleSelectionMode(modal, spaceId, userId, roles, permissionsData);
        });

        // Кнопка "Создать роль"
        modalBody.querySelector('#create-role-btn').addEventListener('click', async () => {
            const roleName = modalBody.querySelector('#role-name-input').value.trim();
            const roleColor = modalBody.querySelector('#role-color-input').value;
            const selectedPermissions = Array.from(modalBody.querySelectorAll('input[name="permission"]:checked'))
                .map(cb => cb.value);

            if (!roleName) {
                await Modal.error('Введите название роли');
                return;
            }

            if (selectedPermissions.length === 0) {
                const confirmed = await Modal.confirm('Вы не выбрали ни одного разрешения. Продолжить?');
                if (!confirmed) return;
            }

            try {
                // Создаем роль
                await API.createRole(spaceId, {
                    name: roleName,
                    color: roleColor,
                    permissions: selectedPermissions,
                    priority: 50
                });

                // Перезагружаем список ролей и сразу возвращаемся к выбору
                const roles = await API.getSpaceRoles(spaceId);
                showRoleSelectionMode(modal, spaceId, userId, roles, permissionsData);
                await updateChatInfo();

            } catch (error) {
                await Modal.error('Ошибка создания роли: ' + error.message);
            }
        });
    }

    // Открыть модальное окно для ограничения пользователя
    async function openRestrictModal(spaceId, userId, userNickname) {
        console.log('openRestrictModal called:', { spaceId, userId, userNickname });

        // Закрываем контекстное меню
        const contextMenu = document.querySelector('.participant-context-menu');
        if (contextMenu) contextMenu.classList.remove('active');

        // Создаем модальное окно
        const modal = document.createElement('div');
        modal.className = 'custom-modal active';
        modal.innerHTML = `
            <div class="custom-modal-content" style="max-width: 500px;">
                <div class="custom-modal-header">
                    <h3 id="modal-title">Ограничить: ${userNickname}</h3>
                    <button class="custom-modal-close">&times;</button>
                </div>
                <div class="custom-modal-body" id="restrict-modal-body">
                    <div class="loading">Загрузка текущих ограничений...</div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        console.log('Restrict modal appended to body');

        // Закрытие модального окна
        const closeModal = () => {
            modal.remove();
        };
        modal.querySelector('.custom-modal-close').addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });

        try {
            // TODO: Загрузить текущие ограничения пользователя через API
            // Пока используем пустой массив
            const currentRestrictions = [];

            const modalBody = modal.querySelector('#restrict-modal-body');

            // Список доступных ограничений
            const restrictions = [
                { key: 'change_chat_name', name: 'Изменение названия чата', icon: '✏️' },
                { key: 'add_users', name: 'Добавление пользователей', icon: '➕' },
                { key: 'create_invites', name: 'Создание приглашений', icon: '🔗' },
                { key: 'send_messages', name: 'Отправка сообщений', icon: '💬' },
                { key: 'send_images', name: 'Отправка изображений', icon: '🖼️' },
                { key: 'send_files', name: 'Отправка файлов', icon: '📎' },
                { key: 'send_music', name: 'Отправка музыки', icon: '🎵' },
                { key: 'delete_messages', name: 'Удаление сообщений', icon: '🗑️' },
                { key: 'add_reactions', name: 'Реакции на сообщения', icon: '😊' },
                { key: 'mention_all', name: 'Упоминание всех (@everyone)', icon: '📢' }
            ];

            modalBody.innerHTML = `
                <div style="margin-bottom: 20px;">
                    <p style="color: #666; font-size: 14px; margin-bottom: 16px;">
                        Отметьте действия, которые будут <strong>запрещены</strong> для этого пользователя:
                    </p>
                    <div class="restrictions-list">
                        ${restrictions.map(restriction => `
                            <label style="
                                display: flex;
                                align-items: center;
                                padding: 12px;
                                margin-bottom: 8px;
                                border: 2px solid #ddd;
                                border-radius: 8px;
                                cursor: pointer;
                                transition: all 0.2s;
                            " class="restriction-item">
                                <input
                                    type="checkbox"
                                    name="restriction"
                                    value="${restriction.key}"
                                    ${currentRestrictions.includes(restriction.key) ? 'checked' : ''}
                                    style="
                                        margin-right: 12px;
                                        width: 20px;
                                        height: 20px;
                                        cursor: pointer;
                                    "
                                >
                                <span style="font-size: 20px; margin-right: 12px;">${restriction.icon}</span>
                                <span style="font-weight: 500; color: #2c3e50;">${restriction.name}</span>
                            </label>
                        `).join('')}
                    </div>
                </div>
                <div style="display: flex; gap: 12px; justify-content: flex-end; margin-top: 20px;">
                    <button id="cancel-restrict-btn" style="
                        padding: 10px 20px;
                        background: #e0e0e0;
                        color: #555;
                        border: none;
                        border-radius: 6px;
                        cursor: pointer;
                        font-weight: 500;
                    ">Отмена</button>
                    <button id="save-restrict-btn" style="
                        padding: 10px 20px;
                        background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
                        color: white;
                        border: none;
                        border-radius: 6px;
                        cursor: pointer;
                        font-weight: 600;
                    ">Применить</button>
                </div>
            `;

            // Подсветка при наведении на чекбоксы
            modalBody.querySelectorAll('.restriction-item').forEach(item => {
                item.addEventListener('mouseenter', () => {
                    item.style.borderColor = '#f39c12';
                    item.style.backgroundColor = 'rgba(243, 156, 18, 0.05)';
                });
                item.addEventListener('mouseleave', () => {
                    item.style.borderColor = '#ddd';
                    item.style.backgroundColor = 'transparent';
                });
            });

            // Отмена
            modalBody.querySelector('#cancel-restrict-btn').addEventListener('click', closeModal);

            // Сохранение ограничений
            modalBody.querySelector('#save-restrict-btn').addEventListener('click', async () => {
                const checkboxes = modalBody.querySelectorAll('input[name="restriction"]:checked');
                const selectedRestrictions = Array.from(checkboxes).map(cb => cb.value);

                console.log('Selected restrictions:', selectedRestrictions);

                try {
                    // TODO: Отправить ограничения на сервер через API
                    // await API.restrictUser(spaceId, userId, selectedRestrictions);

                    await Modal.success('Ограничения применены!');
                    closeModal();
                    await updateChatInfo();
                } catch (error) {
                    await Modal.error('Ошибка применения ограничений: ' + error.message);
                }
            });

        } catch (error) {
            console.error('Error opening restrict modal:', error);
            modal.querySelector('#restrict-modal-body').innerHTML = `
                <div class="error" style="color: #f04747; text-align: center; padding: 20px;">
                    Ошибка загрузки: ${error.message}
                </div>
            `;
        }
    }

    // Загрузка ролей пространства
    async function loadSpaceRoles(spaceId) {
        const rolesContainer = document.getElementById('roles-list');
        if (!rolesContainer) return;

        try {
            const roles = await API.getSpaceRoles(spaceId);

            if (!roles || roles.length === 0) {
                rolesContainer.innerHTML = '<div class="no-roles">Роли не настроены</div>';
                return;
            }

            // Сортируем по приоритету (выше = важнее)
            const sortedRoles = roles.sort((a, b) => b.priority - a.priority);

            rolesContainer.innerHTML = sortedRoles.map(role => `
                <div class="role-item" data-role-id="${role.id}" style="cursor: pointer; display: flex; align-items: center; padding: 8px; border-radius: 6px; margin-bottom: 4px; transition: background 0.2s;">
                    <div class="role-color" style="background-color: ${role.color}; width: 12px; height: 12px; border-radius: 50%; margin-right: 8px;"></div>
                    <div class="role-info" style="flex: 1;">
                        <div class="role-name" style="color: ${role.color}; font-weight: 500; font-size: 13px;">
                            ${role.name}
                            ${role.is_system ? '<span style="font-size: 10px; color: #888;"> (системная)</span>' : ''}
                        </div>
                        <div class="role-member-count" style="font-size: 11px; color: #888;">
                            ${role.member_count || 0} ${role.member_count === 1 ? 'участник' : 'участников'}
                        </div>
                    </div>
                </div>
            `).join('');

            // Добавляем обработчики кликов и ховеров по ролям
            rolesContainer.querySelectorAll('.role-item').forEach(item => {
                item.addEventListener('click', () => {
                    const roleId = parseInt(item.dataset.roleId);
                    const role = roles.find(r => r.id === roleId);
                    showRoleDetails(role);
                });
                item.addEventListener('mouseenter', () => {
                    item.style.backgroundColor = 'rgba(255, 255, 255, 0.05)';
                });
                item.addEventListener('mouseleave', () => {
                    item.style.backgroundColor = '';
                });
            });

        } catch (error) {
            console.error('Error loading roles:', error);
            rolesContainer.innerHTML = '<div class="error-roles" style="padding: 8px; color: #f04747; font-size: 12px;">Ошибка загрузки ролей</div>';
        }
    }

    // Показать детали роли
    async function showRoleDetails(role) {
        const permissionsText = role.permissions && role.permissions.length > 0
            ? role.permissions.join(', ')
            : 'Нет специальных разрешений';

        await Modal.alert(
            `<div style="text-align: left;">
                <div style="margin-bottom: 10px;">
                    <strong style="color: ${role.color};">${role.name}</strong>
                    ${role.is_system ? '<span style="font-size: 12px; color: #888;"> (системная)</span>' : ''}
                </div>
                <div style="margin-bottom: 8px;">
                    <strong>Приоритет:</strong> ${role.priority}
                </div>
                <div style="margin-bottom: 8px;">
                    <strong>Участников:</strong> ${role.member_count || 0}
                </div>
                <div>
                    <strong>Разрешения:</strong><br/>
                    <span style="font-size: 12px; color: #888;">${permissionsText}</span>
                </div>
            </div>`,
            'Информация о роли',
            'info'
        );
    }

    // === УВЕДОМЛЕНИЯ ===

    // Обновить счётчик уведомлений
    async function updateNotificationBadge() {
        try {
            const result = await API.getUnreadNotificationsCount();
            const count = result.unread_count || 0;

            if (notificationBadge) {
                if (count > 0) {
                    notificationBadge.textContent = count > 99 ? '99+' : count;
                    notificationBadge.style.display = 'block';
                } else {
                    notificationBadge.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Failed to update notification badge:', error);
        }
    }

    // Показать панель уведомлений
    async function showNotifications() {
        try {
            const result = await API.getNotifications(false, 50);
            const notifications = Array.isArray(result) ? result : (result.notifications || []);

            // Формируем HTML для уведомлений
            const notificationsHTML = notifications.length > 0
                ? notifications.map(n => createNotificationHTML(n)).join('')
                : `
                    <div class="notifications-empty">
                        <div class="notifications-empty-icon">🔔</div>
                        <div class="notifications-empty-text">Нет уведомлений</div>
                    </div>
                `;

            const content = `
                <div class="notifications-view">
                    <div class="notifications-header">
                        <h2>Уведомления</h2>
                        <div class="notifications-actions">
                            ${notifications.length > 0 ? '<button class="mark-all-read-btn" id="mark-all-read-btn">Прочитать все</button>' : ''}
                        </div>
                    </div>
                    <div class="notifications-list">
                        ${notificationsHTML}
                    </div>
                </div>
            `;

            // Отображаем в центральной области (chatMainElement)
            chatMainElement.innerHTML = content;

            // Добавляем обработчики
            if (notifications.length > 0) {
                // Обработчик для кнопки "Прочитать все"
                const markAllReadBtn = document.getElementById('mark-all-read-btn');
                if (markAllReadBtn) {
                    markAllReadBtn.addEventListener('click', async () => {
                        try {
                            await API.markAllNotificationsAsRead();
                            await showNotifications(); // Обновляем список
                            await updateNotificationBadge();
                        } catch (error) {
                            console.error('Failed to mark all as read:', error);
                            Modal.error('Не удалось пометить уведомления как прочитанные');
                        }
                    });
                }

                // Обработчики для каждого уведомления
                notifications.forEach(notification => {
                    const notifEl = document.getElementById(`notification-${notification.id}`);
                    if (notifEl) {
                        notifEl.addEventListener('click', () => handleNotificationClick(notification));
                    }
                });
            }
        } catch (error) {
            console.error('Failed to load notifications:', error);
            Modal.error('Не удалось загрузить уведомления');
        }
    }

    // Создать HTML для одного уведомления
    function createNotificationHTML(notification) {
        const iconMap = {
            'mention': { icon: '@', class: 'mention' },
            'space_invite': { icon: '📨', class: 'space_invite' },
            'role_change': { icon: '👤', class: 'role_change' }
        };

        const iconInfo = iconMap[notification.type] || { icon: '🔔', class: 'info' };
        const unreadClass = notification.is_read ? '' : 'unread';
        const formattedTime = formatNotificationTime(notification.created_at);

        return `
            <div class="notification-item ${unreadClass}" id="notification-${notification.id}" data-notification-id="${notification.id}">
                <div class="notification-content">
                    <div class="notification-icon ${iconInfo.class}">
                        ${iconInfo.icon}
                    </div>
                    <div class="notification-text">
                        <div class="notification-title">${escapeHtml(notification.title)}</div>
                        <div class="notification-message">${escapeHtml(notification.content || '')}</div>
                        <div class="notification-time">${formattedTime}</div>
                    </div>
                </div>
            </div>
        `;
    }

    // Форматировать время уведомления
    function formatNotificationTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        // Форматируем дату и время без секунд
        const dateStr = date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
        const timeStr = date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });

        if (days > 0) {
            return `${dateStr} в ${timeStr}`;
        } else if (hours > 0) {
            return `Сегодня в ${timeStr}`;
        } else if (minutes > 0) {
            return `${minutes} мин назад`;
        } else {
            return 'Только что';
        }
    }

    // Обработать клик на уведомление
    async function handleNotificationClick(notification) {
        try {
            // Пометить как прочитанное
            if (!notification.is_read) {
                await API.markNotificationAsRead(notification.id);
                await updateNotificationBadge();
            }

            // Переход к связанному сообщению/спейсу
            if (notification.type === 'mention' && notification.related_message_id) {
                await navigateToMessage(notification.related_message_id);
            } else if (notification.type === 'space_invite' && notification.related_space_id) {
                // TODO: Показать приглашение в пространство
                Modal.info('Система приглашений будет реализована позже');
            }
        } catch (error) {
            console.error('Failed to handle notification click:', error);
            const errorMessage = error.response?.data?.detail || error.message || 'Не удалось перейти к сообщению';
            Modal.error(errorMessage);
        }
    }

    // Переход к конкретному сообщению
    async function navigateToMessage(messageId) {
        try {
            console.log('Navigating to message:', messageId);

            // Получаем информацию о сообщении
            const messageInfo = await API.getMessageInfo(messageId);
            console.log('Message info:', messageInfo);

            if (!messageInfo) {
                throw new Error('Сообщение не найдено');
            }

            const { chat_id, space_id } = messageInfo;
            console.log('Target chat_id:', chat_id, 'space_id:', space_id);

            // Находим чат/пространство
            let targetChat;

            if (space_id) {
                // Это сообщение в пространстве
                console.log('Looking for space:', space_id);
                const space = state.spaces.find(s => s.id === space_id);
                console.log('Found space:', space);

                if (space) {
                    // Открываем пространство
                    await selectSpace(space);
                } else {
                    throw new Error('Пространство не найдено');
                }
            } else {
                // Это личное сообщение
                console.log('Looking for private chat:', chat_id);
                targetChat = state.chats.find(c => c.id === chat_id);

                if (targetChat) {
                    await selectChat(targetChat);
                } else {
                    throw new Error('Чат не найден');
                }
            }

            // Ждём рендеринга сообщений
            await new Promise(resolve => setTimeout(resolve, 500));

            // Находим элемент сообщения и скроллим к нему
            console.log('Looking for message element:', messageId);
            const messageElement = document.querySelector(`.message[data-message-id="${messageId}"]`);
            console.log('Found message element:', messageElement);

            if (messageElement) {
                messageElement.scrollIntoView({ behavior: 'smooth', block: 'center' });

                // Подсвечиваем сообщение
                messageElement.classList.add('highlighted');
                setTimeout(() => {
                    messageElement.classList.remove('highlighted');
                }, 2000);
            } else {
                console.warn('Message element not found in DOM, available messages:',
                    Array.from(document.querySelectorAll('.message')).map(m => m.dataset.messageId));
            }
        } catch (error) {
            console.error('Failed to navigate to message:', error);
            throw error;
        }
    }

    // === АВТОДОПОЛНЕНИЕ @-УПОМИНАНИЙ ===
    let mentionAutocompleteParticipants = []; // Глобальная переменная для хранения участников

    function initMentionAutocomplete(input) {
        const autocomplete = document.getElementById('mention-autocomplete');
        if (!autocomplete) return;

        let currentMentionStart = -1;
        let currentMentionText = '';
        let selectedIndex = 0;

        // Обработчик ввода текста
        input.addEventListener('input', async (e) => {
            const text = input.value;
            const cursorPos = input.selectionStart;

            // Ищем @ перед курсором
            const textBeforeCursor = text.substring(0, cursorPos);
            const lastAtIndex = textBeforeCursor.lastIndexOf('@');

            if (lastAtIndex === -1) {
                hideMentionAutocomplete();
                return;
            }

            // Проверяем что @ начинает слово (начало строки или пробел перед)
            const charBeforeAt = lastAtIndex > 0 ? text[lastAtIndex - 1] : ' ';
            if (charBeforeAt !== ' ' && charBeforeAt !== '\n') {
                hideMentionAutocomplete();
                return;
            }

            // Получаем текст после @
            const textAfterAt = textBeforeCursor.substring(lastAtIndex + 1);

            // Проверяем что после @ нет пробелов
            if (textAfterAt.includes(' ') || textAfterAt.includes('\n')) {
                hideMentionAutocomplete();
                return;
            }

            currentMentionStart = lastAtIndex;
            currentMentionText = textAfterAt.toLowerCase();

            // Загружаем участников если ещё не загружены
            if (mentionAutocompleteParticipants.length === 0) {
                try {
                    if (state.currentSpace) {
                        // Для пространств - получаем участников пространства
                        const data = await API.getSpaceParticipants(state.currentSpace.id);
                        mentionAutocompleteParticipants = data.participants || [];
                        console.log('Loaded space participants:', mentionAutocompleteParticipants.length);
                    } else {
                        // Для личных чатов - используем участников из текущего чата
                        const currentChat = state.chats.find(c => c.id === state.currentChatId);
                        if (currentChat && currentChat.participants) {
                            mentionAutocompleteParticipants = currentChat.participants;
                            console.log('Loaded chat participants:', mentionAutocompleteParticipants.length);
                        }
                    }
                } catch (error) {
                    console.error('Failed to load participants:', error);
                    return;
                }
            }

            // Фильтруем участников
            const filtered = mentionAutocompleteParticipants.filter(p => {
                const nickname = (p.nickname || '').toLowerCase();
                return nickname.includes(currentMentionText);
            });

            console.log('Filtered participants:', filtered.length, 'for query:', currentMentionText);

            // Добавляем @all если текст подходит (только для пространств)
            if (state.currentSpace) {
                const allMatches = 'all'.includes(currentMentionText);
                if (allMatches) {
                    filtered.unshift({ nickname: 'all', display_name: 'Упомянуть всех', isSpecial: true });
                }
            }

            if (filtered.length === 0) {
                hideMentionAutocomplete();
                return;
            }

            // Показываем автодополнение
            showMentionAutocomplete(filtered);
        });

        // Обработчик клавиш для навигации
        input.addEventListener('keydown', (e) => {
            if (!autocomplete.classList.contains('visible')) return;

            const items = autocomplete.querySelectorAll('.mention-autocomplete-item');
            if (items.length === 0) return;

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
                updateSelection(items);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, 0);
                updateSelection(items);
            } else if (e.key === 'Enter' || e.key === 'Tab') {
                const selectedItem = items[selectedIndex];
                if (selectedItem) {
                    e.preventDefault();
                    const nickname = selectedItem.dataset.nickname;
                    insertMention(nickname);
                }
            } else if (e.key === 'Escape') {
                e.preventDefault();
                hideMentionAutocomplete();
            }
        });

        // Закрытие при клике вне
        document.addEventListener('click', (e) => {
            if (!autocomplete.contains(e.target) && e.target !== input) {
                hideMentionAutocomplete();
            }
        });

        function showMentionAutocomplete(filteredUsers) {
            selectedIndex = 0;

            autocomplete.innerHTML = filteredUsers.map((user, index) => {
                const avatarContent = user.avatar_url
                    ? `<img src="${user.avatar_url}" alt="${user.nickname}">`
                    : user.nickname.charAt(0).toUpperCase();

                const displayName = user.display_name || '';
                const isSpecial = user.isSpecial || false;

                return `
                    <div class="mention-autocomplete-item ${index === 0 ? 'selected' : ''}"
                         data-nickname="${user.nickname}"
                         data-index="${index}">
                        <div class="user-avatar">${avatarContent}</div>
                        <div class="user-info">
                            <div class="user-nickname">@${user.nickname}</div>
                            ${displayName && !isSpecial ? `<div class="user-display-name">${displayName}</div>` : ''}
                            ${isSpecial ? `<div class="user-display-name">${displayName}</div>` : ''}
                        </div>
                    </div>
                `;
            }).join('');

            // Добавляем обработчики клика
            autocomplete.querySelectorAll('.mention-autocomplete-item').forEach(item => {
                item.addEventListener('click', () => {
                    const nickname = item.dataset.nickname;
                    insertMention(nickname);
                });
            });

            autocomplete.classList.add('visible');
        }

        function hideMentionAutocomplete() {
            autocomplete.classList.remove('visible');
            autocomplete.innerHTML = '';
            currentMentionStart = -1;
            currentMentionText = '';
            selectedIndex = 0;
        }

        function updateSelection(items) {
            items.forEach((item, index) => {
                if (index === selectedIndex) {
                    item.classList.add('selected');
                    item.scrollIntoView({ block: 'nearest' });
                } else {
                    item.classList.remove('selected');
                }
            });
        }

        function insertMention(nickname) {
            const text = input.value;
            const before = text.substring(0, currentMentionStart);
            const after = text.substring(input.selectionStart);

            input.value = `${before}@${nickname} ${after}`;

            // Устанавливаем курсор после вставленного упоминания
            const newCursorPos = before.length + nickname.length + 2; // +2 для @ и пробела
            input.setSelectionRange(newCursorPos, newCursorPos);

            // Обновляем высоту
            input.style.height = 'auto';
            input.style.height = input.scrollHeight + 'px';

            hideMentionAutocomplete();
            input.focus();
        }
    }

    // Экспортируем функции в window для доступа из HTML
    window.chatApp = {
        renameSpace,
        addUserToSpace,
        showParticipants,
        kickUserFromSpace,
        banUserFromSpace,
        unbanUserFromSpace,
        assignRoleToUser,
        leaveSpace,
        deleteSpace,
        loadSpaceRoles,
        openAssignRoleModal,
        openRestrictModal
    };

    // Запускаем приложение
    init();
});
