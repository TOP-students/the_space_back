// WebSocket клиент на Socket.IO
class WebSocketClient {
    constructor() {
        this.socket = null;
        this.connected = false;
        this.currentRoomId = null;
        this.onMessageCallback = null;
        this.onUserJoinedCallback = null;
        this.onUserLeftCallback = null;
    }

    // Подключение к серверу
    connect(userId, nickname) {
        if (this.socket) {
            console.log('Socket already connected');
            return;
        }

        // Подключаемся к Socket.IO серверу
        this.socket = io(CONFIG.API_BASE_URL, {
            transports: ['websocket', 'polling'],
            query: {
                user_id: userId,
                nickname: nickname
            }
        });

        // Обработчики событий
        this.socket.on('connect', () => {
            console.log('Socket.IO connected');
            this.connected = true;
        });

        this.socket.on('disconnect', () => {
            console.log('Socket.IO disconnected');
            this.connected = false;
        });

        this.socket.on('connected', (data) => {
            console.log('Server confirmed connection:', data);
        });

        this.socket.on('new_message', (data) => {
            console.log('New message received:', data);
            if (this.onMessageCallback) {
                this.onMessageCallback(data);
            }
        });

        this.socket.on('user_joined_room', (data) => {
            console.log('User joined room:', data);
            if (this.onUserJoinedCallback) {
                this.onUserJoinedCallback(data);
            }
        });

        this.socket.on('user_left_room', (data) => {
            console.log('User left room:', data);
            if (this.onUserLeftCallback) {
                this.onUserLeftCallback(data);
            }
        });

        this.socket.on('error', (error) => {
            console.error('Socket error:', error);
        });
    }

    // Присоединиться к комнате
    joinRoom(roomId, userId, nickname) {
        if (!this.socket || !this.connected) {
            console.error('Socket not connected');
            return;
        }

        this.currentRoomId = roomId;

        this.socket.emit('join_room', {
            room_id: roomId,
            user_id: userId,
            nickname: nickname
        });

        console.log('Joined room:', roomId);
    }

    // Покинуть комнату
    leaveRoom(roomId, userId) {
        if (!this.socket || !this.connected) {
            return;
        }

        this.socket.emit('leave_room', {
            room_id: roomId,
            user_id: userId
        });

        if (this.currentRoomId === roomId) {
            this.currentRoomId = null;
        }

        console.log('Left room:', roomId);
    }

    // Отправить сообщение (опционально, можно использовать HTTP API)
    sendMessage(roomId, userId, nickname, message) {
        if (!this.socket || !this.connected) {
            console.error('Socket not connected');
            return;
        }

        this.socket.emit('send_message', {
            room_id: roomId,
            user_id: userId,
            nickname: nickname,
            message: message
        });
    }

    // Установить обработчик новых сообщений
    onMessage(callback) {
        this.onMessageCallback = callback;
    }

    // Установить обработчик присоединения пользователей
    onUserJoined(callback) {
        this.onUserJoinedCallback = callback;
    }

    // Установить обработчик выхода пользователей
    onUserLeft(callback) {
        this.onUserLeftCallback = callback;
    }

    // Отключиться
    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
            this.connected = false;
        }
    }
}

window.WebSocketClient = WebSocketClient;
