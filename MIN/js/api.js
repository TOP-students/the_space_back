// API клиент для работы с backend
const API = {
    // Базовый метод для HTTP запросов
    async request(endpoint, options = {}) {
        const url = `${CONFIG.API_BASE_URL}${endpoint}`;
        const token = AuthService.getToken();

        // Настройки по умолчанию
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
                // Если 401 - токен невалиден, разлогиниваем
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
    },

    // GET запрос
    get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    },

    // POST запрос
    post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    // PATCH запрос
    patch(endpoint, data) {
        return this.request(endpoint, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    },

    // DELETE запрос
    delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    },

    // === AUTH ENDPOINTS ===

    // Регистрация
    async register(nickname, email, password) {
        return this.post('/auth/register', { nickname, email, password });
    },

    // Вход (возвращает токен)
    async login(username, password) {
        // FastAPI OAuth2 ожидает form data
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
    },

    // Получить текущего пользователя
    async getCurrentUser() {
        return this.get('/auth/me');
    },

    // Проверить существование пользователя
    async checkUser(identifier) {
        return this.get(`/auth/check-user?identifier=${encodeURIComponent(identifier)}`);
    },

    // === SPACES ENDPOINTS ===

    // Получить все пространства
    async getSpaces() {
        return this.get('/spaces/');
    },

    // Создать пространство
    async createSpace(name, description = '', background_url = '') {
        return this.post('/spaces/', { name, description, background_url });
    },

    // Войти в пространство
    async joinSpace(spaceId) {
        return this.post(`/spaces/${spaceId}/join`, {});
    },

    // Получить участников пространства
    async getSpaceParticipants(spaceId) {
        return this.get(`/spaces/${spaceId}/participants`);
    },

    // Добавить пользователя в пространство
    async addUserToSpace(spaceId, userIdentifier) {
        return this.post(`/spaces/${spaceId}/add-user?user_identifier=${encodeURIComponent(userIdentifier)}`);
    },

    // Загрузить аватар пространства
    async uploadSpaceAvatar(spaceId, file) {
        const formData = new FormData();
        formData.append('file', file);

        const token = AuthService.getToken();
        const url = `${CONFIG.API_BASE_URL}/spaces/${spaceId}/upload-avatar`;

        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Ошибка загрузки аватара');
        }

        return response.json();
    },

    // Изменить название пространства
    async updateSpaceName(spaceId, newName) {
        return this.patch(`/spaces/${spaceId}/name?new_name=${encodeURIComponent(newName)}`);
    },

    // Удалить пользователя из пространства
    async kickUser(spaceId, userId) {
        return this.delete(`/spaces/${spaceId}/kick/${userId}`);
    },

    // Удалить пространство
    async deleteSpace(spaceId) {
        return this.delete(`/spaces/${spaceId}/delete`);
    },

    // Покинуть пространство
    async leaveSpace(spaceId) {
        return this.post(`/spaces/${spaceId}/leave`, {});
    },

    // === MESSAGES ENDPOINTS ===

    // Получить сообщения чата
    async getMessages(chatId, limit = 50, offset = 0) {
        return this.get(`/messages/${chatId}?limit=${limit}&offset=${offset}`);
    },

    // Получить информацию о сообщении
    async getMessageInfo(messageId) {
        return this.get(`/messages/message/${messageId}`);
    },

    // Отправить сообщение
    async sendMessage(chatId, content, type = 'text') {
        return this.post(`/messages/${chatId}`, { content, type });
    },

    // Поиск сообщений
    async searchMessages(chatId, query, limit = 50, offset = 0) {
        return this.get(`/messages/${chatId}/search?q=${encodeURIComponent(query)}&limit=${limit}&offset=${offset}`);
    },

    // Редактировать сообщение
    async updateMessage(chatId, messageId, content) {
        return this.patch(`/messages/${chatId}/${messageId}`, { content });
    },

    // Удалить сообщение
    async deleteMessage(chatId, messageId) {
        return this.delete(`/messages/${chatId}/${messageId}`);
    },

    // Загрузить изображение
    async uploadImage(chatId, file) {
        const token = AuthService.getToken();
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${CONFIG.API_BASE_URL}/messages/${chatId}/upload-image`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            if (response.status === 401) {
                AuthService.logout();
                throw new Error('Сессия истекла. Войдите снова.');
            }
            throw new Error(data.detail || 'Ошибка загрузки изображения');
        }

        return data;
    },

    // Загрузить аудио
    async uploadAudio(chatId, file) {
        const token = AuthService.getToken();
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${CONFIG.API_BASE_URL}/messages/${chatId}/upload-audio`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            if (response.status === 401) {
                AuthService.logout();
                throw new Error('Сессия истекла. Войдите снова.');
            }
            throw new Error(data.detail || 'Ошибка загрузки аудио');
        }

        return data;
    },

    // Загрузить документ
    async uploadDocument(chatId, file) {
        const token = AuthService.getToken();
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${CONFIG.API_BASE_URL}/messages/${chatId}/upload-document`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            if (response.status === 401) {
                AuthService.logout();
                throw new Error('Сессия истекла. Войдите снова.');
            }
            throw new Error(data.detail || 'Ошибка загрузки документа');
        }

        return data;
    },

    // Добавить реакцию на сообщение
    async addReaction(chatId, messageId, reaction) {
        return this.post(`/messages/${chatId}/${messageId}/react?reaction=${encodeURIComponent(reaction)}`, {});
    },

    // Получить реакции на сообщение
    async getReactions(chatId, messageId) {
        return this.get(`/messages/${chatId}/${messageId}/reactions`);
    },

    // === PROFILE ENDPOINTS ===

    // Получить свой профиль
    async getMyProfile() {
        return this.get('/profile/me');
    },

    // Получить профиль пользователя по ID
    async getUserProfile(userId) {
        return this.get(`/profile/${userId}`);
    },

    // Обновить профиль
    async updateProfile(data) {
        return this.patch('/profile/me', data);
    },

    // Загрузить аватар
    async uploadAvatar(file) {
        const token = AuthService.getToken();
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${CONFIG.API_BASE_URL}/profile/upload-avatar`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            if (response.status === 401) {
                AuthService.logout();
                throw new Error('Сессия истекла. Войдите снова.');
            }
            throw new Error(data.detail || 'Ошибка загрузки аватара');
        }

        return data;
    },

    // Загрузить баннер профиля
    async uploadBanner(file) {
        const token = AuthService.getToken();
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${CONFIG.API_BASE_URL}/profile/upload-banner`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            if (response.status === 401) {
                AuthService.logout();
                throw new Error('Сессия истекла. Войдите снова.');
            }
            throw new Error(data.detail || 'Ошибка загрузки баннера');
        }

        return data;
    },

    // === РОЛИ И ПРАВА ===

    // Получить роли пространства с иерархией
    async getSpaceRoles(spaceId) {
        return this.get(`/spaces/${spaceId}/roles`);
    },

    // Создать роль
    async createRole(spaceId, roleData) {
        return this.post(`/spaces/${spaceId}/roles`, roleData);
    },

    // Обновить роль
    async updateRole(spaceId, roleId, roleData) {
        return this.patch(`/spaces/${spaceId}/roles/${roleId}`, roleData);
    },

    // Удалить роль
    async deleteRole(spaceId, roleId) {
        return this.delete(`/spaces/${spaceId}/roles/${roleId}`);
    },

    // Назначить роль участнику
    async assignRoleToMember(spaceId, userId, roleId) {
        return this.post(`/spaces/${spaceId}/members/${userId}/role?role_id=${roleId}`, {});
    },

    // Получить участников с определённой ролью
    async getRoleMembers(spaceId, roleId) {
        return this.get(`/spaces/${spaceId}/roles/${roleId}/members`);
    },

    // Кикнуть пользователя
    async kickUser(spaceId, userId) {
        return this.delete(`/spaces/${spaceId}/kick/${userId}`);
    },

    // Забанить пользователя
    async banUser(spaceId, userId, banData) {
        return this.post(`/spaces/${spaceId}/ban/${userId}`, banData);
    },

    async unbanUser(spaceId, userId) {
        return this.delete(`/spaces/${spaceId}/unban/${userId}`);
    },

    // === СТАТУСЫ ПОЛЬЗОВАТЕЛЕЙ ===

    // Получить свой статус
    async getMyStatus() {
        return this.get('/status/my-status');
    },

    // Установить статус (online, offline, away, dnd)
    async setStatus(status) {
        return this.post(`/status/set-status?status=${status}`, {});
    },

    // Получить статус пользователя
    async getUserStatus(userId) {
        return this.get(`/status/user/${userId}`);
    },

    // Получить список онлайн пользователей
    async getOnlineUsers(spaceId = null) {
        const url = spaceId ? `/status/online?space_id=${spaceId}` : '/status/online';
        return this.get(url);
    },

    // Heartbeat для поддержания онлайн статуса
    async heartbeat() {
        return this.post('/status/heartbeat', {});
    },

    // === ДОСТУПНЫЕ РАЗРЕШЕНИЯ ===

    // Получить список всех доступных разрешений
    async getAvailablePermissions(spaceId) {
        return this.get(`/spaces/${spaceId}/permissions`);
    },

    // Получить мои разрешения в пространстве
    async getMyPermissions(spaceId) {
        return this.get(`/spaces/${spaceId}/my-permissions`);
    },

    // === УВЕДОМЛЕНИЯ ===

    // Получить список уведомлений
    async getNotifications(unreadOnly = false, limit = 50) {
        const params = new URLSearchParams();
        if (unreadOnly) params.append('unread_only', 'true');
        if (limit) params.append('limit', limit.toString());
        const query = params.toString() ? `?${params.toString()}` : '';
        return this.get(`/notifications/${query}`);
    },

    // Получить количество непрочитанных уведомлений
    async getUnreadNotificationsCount() {
        return this.get('/notifications/unread-count');
    },

    // Пометить уведомление как прочитанное
    async markNotificationAsRead(notificationId) {
        return this.post(`/notifications/${notificationId}/read`, {});
    },

    // Пометить все уведомления как прочитанные
    async markAllNotificationsAsRead() {
        return this.post('/notifications/mark-all-read', {});
    }
};

window.API = API;
