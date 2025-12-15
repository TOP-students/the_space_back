// Управление мини-профилями при наведении на аватары

const MiniProfile = {
    element: null,
    banner: null,
    avatar: null,
    name: null,
    statusDot: null,
    statusText: null,
    hideTimeout: null,

    init() {
        this.element = document.getElementById('mini-profile');
        this.banner = document.getElementById('mini-profile-banner');
        this.avatar = document.getElementById('mini-profile-avatar');
        this.name = document.getElementById('mini-profile-name');
        this.statusDot = document.getElementById('mini-profile-status-dot');
        this.statusText = document.getElementById('mini-profile-status-text');

        // Обработчики для самого мини-профиля
        if (this.element) {
            this.element.addEventListener('mouseenter', () => {
                clearTimeout(this.hideTimeout);
            });

            this.element.addEventListener('mouseleave', () => {
                this.hide();
            });
        }
    },

    show(userData, event) {
        if (!this.element) return;

        clearTimeout(this.hideTimeout);

        // Функция генерации градиента (копия из chat.js)
        const generateGradient = (id) => {
            const seed = id || 1;
            const hue1 = (seed * 137.5) % 360;
            const hue2 = (hue1 + 60) % 360;
            const saturation = 65 + (seed % 20);
            const lightness = 45 + (seed % 15);
            const color1 = `hsl(${hue1}, ${saturation}%, ${lightness}%)`;
            const color2 = `hsl(${hue2}, ${saturation}%, ${lightness - 5}%)`;
            return `linear-gradient(135deg, ${color1} 0%, ${color2} 100%)`;
        };

        // Обновляем баннер (реальное изображение или градиент)
        if (userData.profile_background_url) {
            this.banner.src = userData.profile_background_url;
            this.banner.style.display = 'block';
            this.element.style.background = '#fff';
        } else {
            // Если нет баннера - используем градиент вместо фона
            const gradient = generateGradient(userData.id);
            this.banner.style.display = 'none';
            this.element.style.background = gradient;
        }

        // Обновляем аватар
        this.avatar.src = userData.avatar_url || 'assets/icons/avatar.svg';
        this.name.textContent = userData.nickname || userData.display_name || 'Пользователь';

        // Обновляем статус (проверяем разные варианты поля)
        const statusConfig = {
            'online': { color: '#43b581', text: 'В сети' },
            'away': { color: '#faa61a', text: 'Отошёл' },
            'dnd': { color: '#f04747', text: 'Не беспокоить' },
            'offline': { color: '#747f8d', text: 'Не в сети' }
        };
        // Проверяем разные варианты поля статуса
        const userStatusValue = userData.status || userData.userStatus || 'online';
        const status = statusConfig[userStatusValue] || statusConfig['online'];
        this.statusDot.style.backgroundColor = status.color;
        this.statusText.textContent = status.text;

        // Позиционируем относительно курсора
        const rect = event.target.getBoundingClientRect();
        const x = rect.right + 10; // Справа от аватара
        const y = rect.top;

        // Проверяем, не выходит ли за границы экрана
        const profileWidth = 280;
        const profileHeight = 180;
        let finalX = x;
        let finalY = y;

        if (x + profileWidth > window.innerWidth) {
            finalX = rect.left - profileWidth - 10; // Слева от аватара
        }

        if (y + profileHeight > window.innerHeight) {
            finalY = window.innerHeight - profileHeight - 10;
        }

        this.element.style.left = finalX + 'px';
        this.element.style.top = finalY + 'px';

        // Показываем
        this.element.classList.add('visible');
    },

    hide() {
        if (!this.element) return;

        this.hideTimeout = setTimeout(() => {
            this.element.classList.remove('visible');
        }, 200);
    }
};

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    MiniProfile.init();
});

// Экспорт для использования в других модулях
window.MiniProfile = MiniProfile;