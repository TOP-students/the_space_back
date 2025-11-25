# Глобальный инстанс Socket.IO сервера
# Используется для доступа к sio из различных частей приложения

sio = None

def set_sio(socketio_instance):
    """Установить глобальный инстанс Socket.IO"""
    global sio
    sio = socketio_instance

def get_sio():
    """Получить глобальный инстанс Socket.IO"""
    return sio
