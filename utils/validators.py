import re
from typing import Tuple

class Validators:
    # паттерны
    NICKNAME_PATTERN = r'^[a-zA-Z0-9_]{3,20}$'
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    # минимальные требования
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 128
    MIN_NICKNAME_LENGTH = 3
    MAX_NICKNAME_LENGTH = 20
    MIN_DISPLAY_NAME_LENGTH = 1
    MAX_DISPLAY_NAME_LENGTH = 50
    MAX_BIO_LENGTH = 500
    MAX_MESSAGE_LENGTH = 2000
    MAX_SPACE_NAME_LENGTH = 100
    MAX_SPACE_DESCRIPTION_LENGTH = 500
    
    @staticmethod
    def validate_nickname(nickname: str) -> Tuple[bool, str]:
        """
        Валидация никнейма
        - 3-20 символов
        - Только буквы, цифры, подчёркивания
        - Без пробелов
        """
        if not nickname:
            return False, "Никнейм не может быть пустым"
        
        if len(nickname) < Validators.MIN_NICKNAME_LENGTH:
            return False, f"Никнейм должен быть не менее {Validators.MIN_NICKNAME_LENGTH} символов"
        
        if len(nickname) > Validators.MAX_NICKNAME_LENGTH:
            return False, f"Никнейм должен быть не более {Validators.MAX_NICKNAME_LENGTH} символов"
        
        if not re.match(Validators.NICKNAME_PATTERN, nickname):
            return False, "Никнейм может содержать только латинские буквы, цифры и подчёркивания"
        
        # проверка на зарезервированные слова
        reserved = ['admin', 'moderator', 'system', 'bot', 'api', 'root']
        if nickname.lower() in reserved:
            return False, "Этот никнейм зарезервирован"
        
        return True, ""
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """
        Валидация пароля
        - Минимум 8 символов
        - Содержит буквы и цифры
        - Содержит хотя бы одну заглавную букву
        - Содержит хотя бы один спецсимвол
        """
        if not password:
            return False, "Пароль не может быть пустым"
        
        if len(password) < Validators.MIN_PASSWORD_LENGTH:
            return False, f"Пароль должен быть не менее {Validators.MIN_PASSWORD_LENGTH} символов"
        
        if len(password) > Validators.MAX_PASSWORD_LENGTH:
            return False, f"Пароль слишком длинный (максимум {Validators.MAX_PASSWORD_LENGTH})"
        
        # проверка на наличие букв
        if not re.search(r'[a-zA-Z]', password):
            return False, "Пароль должен содержать буквы"
        
        # проверка на наличие цифр
        if not re.search(r'\d', password):
            return False, "Пароль должен содержать хотя бы одну цифру"
        
        # проверка на заглавные буквы
        if not re.search(r'[A-Z]', password):
            return False, "Пароль должен содержать хотя бы одну заглавную букву"
        
        # проверка на спецсимволы
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Пароль должен содержать хотя бы один спецсимвол (!@#$%^&* и т.д.)"
        
        # проверка на слабые пароли
        weak_passwords = ['password', 'password123', '12345678', 'qwerty123']
        if password.lower() in weak_passwords:
            return False, "Этот пароль слишком простой"
        
        return True, ""
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """Валидация email"""
        if not email:
            return True, ""  # email опциональный
        
        if not re.match(Validators.EMAIL_PATTERN, email):
            return False, "Некорректный формат email"
        
        if len(email) > 255:
            return False, "Email слишком длинный"
        
        return True, ""
    
    @staticmethod
    def validate_display_name(display_name: str) -> Tuple[bool, str]:
        """Валидация отображаемого имени"""
        if not display_name:
            return True, ""  # опционально
        
        if len(display_name) < Validators.MIN_DISPLAY_NAME_LENGTH:
            return False, "Имя слишком короткое"
        
        if len(display_name) > Validators.MAX_DISPLAY_NAME_LENGTH:
            return False, f"Имя не должно превышать {Validators.MAX_DISPLAY_NAME_LENGTH} символов"
        
        return True, ""
    
    @staticmethod
    def validate_bio(bio: str) -> Tuple[bool, str]:
        """Валидация описания профиля"""
        if not bio:
            return True, ""
        
        if len(bio) > Validators.MAX_BIO_LENGTH:
            return False, f"Описание не должно превышать {Validators.MAX_BIO_LENGTH} символов"
        
        return True, ""
    
    @staticmethod
    def validate_message_content(content: str) -> Tuple[bool, str]:
        """Валидация содержимого сообщения"""
        if not content or not content.strip():
            return False, "Сообщение не может быть пустым"
        
        if len(content) > Validators.MAX_MESSAGE_LENGTH:
            return False, f"Сообщение не должно превышать {Validators.MAX_MESSAGE_LENGTH} символов"
        
        return True, ""
    
    @staticmethod
    def validate_space_name(name: str) -> Tuple[bool, str]:
        """Валидация названия комнаты"""
        if not name or not name.strip():
            return False, "Название комнаты не может быть пустым"
        
        if len(name) > Validators.MAX_SPACE_NAME_LENGTH:
            return False, f"Название не должно превышать {Validators.MAX_SPACE_NAME_LENGTH} символов"
        
        return True, ""
    
    @staticmethod
    def validate_space_description(description: str) -> Tuple[bool, str]:
        """Валидация описания комнаты"""
        if not description:
            return True, ""
        
        if len(description) > Validators.MAX_SPACE_DESCRIPTION_LENGTH:
            return False, f"Описание не должно превышать {Validators.MAX_SPACE_DESCRIPTION_LENGTH} символов"
        
        return True, ""
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Очистка пользовательского ввода от опасных символов"""
        if not text:
            return text
        
        # удаляем потенциально опасные HTML теги
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<iframe[^>]*>.*?</iframe>', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # удаляем NULL байты
        text = text.replace('\x00', '')
        
        # обрезаем пробелы
        text = text.strip()
        
        return text