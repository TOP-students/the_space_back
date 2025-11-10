// Класс для работы с модальными окнами
const Modal = {
    // Показать alert (информационное сообщение)
    alert(message, title = 'Внимание', type = 'info') {
        return new Promise((resolve) => {
            this._show({
                title,
                message,
                type,
                buttons: [
                    {
                        text: 'OK',
                        class: 'modal-button-primary',
                        onClick: () => resolve(true)
                    }
                ]
            });
        });
    },

    // Показать confirm (подтверждение действия)
    confirm(message, title = 'Подтвердите действие', options = {}) {
        return new Promise((resolve) => {
            const {
                confirmText = 'Подтвердить',
                cancelText = 'Отмена',
                type = 'question',
                danger = false
            } = options;

            this._show({
                title,
                message,
                type,
                buttons: [
                    {
                        text: cancelText,
                        class: 'modal-button-secondary',
                        onClick: () => resolve(false)
                    },
                    {
                        text: confirmText,
                        class: danger ? 'modal-button-danger' : 'modal-button-primary',
                        onClick: () => resolve(true)
                    }
                ]
            });
        });
    },

    // Показать ошибку
    error(message, title = 'Ошибка') {
        return this.alert(message, title, 'error');
    },

    // Показать успех
    success(message, title = 'Успешно') {
        return this.alert(message, title, 'success');
    },

    // Показать предупреждение
    warning(message, title = 'Предупреждение') {
        return this.alert(message, title, 'warning');
    },

    // Показать форму создания комнаты
    createRoom() {
        return new Promise((resolve) => {
            this._showForm({
                title: 'Создать новую комнату',
                fields: [
                    { id: 'room-name', label: 'Название комнаты', type: 'text', required: true, placeholder: 'Введите название...' },
                    { id: 'room-description', label: 'Описание (необязательно)', type: 'textarea', required: false, placeholder: 'Описание комнаты...' }
                ],
                buttons: [
                    {
                        text: 'Отмена',
                        class: 'modal-button-secondary',
                        onClick: () => resolve(null)
                    },
                    {
                        text: 'Создать',
                        class: 'modal-button-primary',
                        onClick: (data) => resolve(data)
                    }
                ]
            });
        });
    },

    // Внутренний метод для отображения модального окна
    _show(config) {
        const { title, message, type, buttons } = config;

        // Создаем overlay
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';

        // Иконки для разных типов
        const icons = {
            info: 'ℹ️',
            question: '❓',
            error: '❌',
            success: '✅',
            warning: '⚠️'
        };

        const icon = icons[type] || icons.info;

        // Создаем модальное окно
        const modal = document.createElement('div');
        modal.className = 'modal-window';

        // Формируем HTML
        modal.innerHTML = `
            <div class="modal-header">
                <h3 class="modal-title">${this._escapeHtml(title)}</h3>
            </div>
            <div class="modal-body with-icon">
                <div class="modal-icon modal-icon-${type}">
                    ${icon}
                </div>
                <div>${this._escapeHtml(message)}</div>
            </div>
            <div class="modal-footer">
                ${buttons.map((btn, index) => `
                    <button class="modal-button ${btn.class}" data-index="${index}">
                        ${this._escapeHtml(btn.text)}
                    </button>
                `).join('')}
            </div>
        `;

        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        // Обработчики кнопок
        const buttonElements = modal.querySelectorAll('.modal-button');
        buttonElements.forEach((btnEl, index) => {
            btnEl.addEventListener('click', () => {
                buttons[index].onClick();
                this._close(overlay);
            });
        });

        // Закрытие по клику на overlay
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                // Находим кнопку "Отмена" или последнюю кнопку
                const cancelButton = buttons.find(btn =>
                    btn.class.includes('secondary') || btn.text.toLowerCase().includes('отмена')
                );
                if (cancelButton) {
                    cancelButton.onClick();
                }
                this._close(overlay);
            }
        });

        // ESC для закрытия
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                const cancelButton = buttons.find(btn =>
                    btn.class.includes('secondary') || btn.text.toLowerCase().includes('отмена')
                );
                if (cancelButton) {
                    cancelButton.onClick();
                }
                this._close(overlay);
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
    },

    // Показать форму
    _showForm(config) {
        const { title, fields, buttons } = config;

        // Создаем overlay
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';

        // Создаем модальное окно
        const modal = document.createElement('div');
        modal.className = 'modal-window';

        // Формируем HTML полей формы
        const fieldsHTML = fields.map(field => {
            if (field.type === 'textarea') {
                return `
                    <div class="modal-form-group">
                        <label for="${field.id}">${field.label}</label>
                        <textarea
                            id="${field.id}"
                            ${field.required ? 'required' : ''}
                            placeholder="${field.placeholder || ''}"
                            rows="3"
                        ></textarea>
                    </div>
                `;
            } else {
                return `
                    <div class="modal-form-group">
                        <label for="${field.id}">${field.label}</label>
                        <input
                            type="${field.type}"
                            id="${field.id}"
                            ${field.required ? 'required' : ''}
                            placeholder="${field.placeholder || ''}"
                        />
                    </div>
                `;
            }
        }).join('');

        modal.innerHTML = `
            <div class="modal-header">
                <h3 class="modal-title">${this._escapeHtml(title)}</h3>
            </div>
            <div class="modal-body">
                <form id="modal-form">
                    ${fieldsHTML}
                </form>
            </div>
            <div class="modal-footer">
                ${buttons.map((btn, index) => `
                    <button class="modal-button ${btn.class}" data-index="${index}" type="${btn.class.includes('primary') ? 'submit' : 'button'}">
                        ${this._escapeHtml(btn.text)}
                    </button>
                `).join('')}
            </div>
        `;

        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        const form = modal.querySelector('#modal-form');
        const buttonElements = modal.querySelectorAll('.modal-button');

        // Обработчики кнопок
        buttonElements.forEach((btnEl, index) => {
            btnEl.addEventListener('click', (e) => {
                e.preventDefault();

                if (!buttons[index].class.includes('primary')) {
                    // Вторичная кнопка (Отмена)
                    buttons[index].onClick();
                    this._close(overlay);
                } else {
                    // Primary кнопка (Создать)
                    // Собираем данные из формы
                    const formData = {};
                    fields.forEach(field => {
                        const input = document.getElementById(field.id);
                        formData[field.id] = input.value.trim();
                    });

                    // Вызываем callback и закрываем
                    buttons[index].onClick(formData);
                    this._close(overlay);
                }
            });
        });

        // Закрытие по клику на overlay
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                const cancelButton = buttons.find(btn => btn.class.includes('secondary'));
                if (cancelButton) {
                    cancelButton.onClick();
                }
                this._close(overlay);
            }
        });

        // ESC для закрытия
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                const cancelButton = buttons.find(btn => btn.class.includes('secondary'));
                if (cancelButton) {
                    cancelButton.onClick();
                }
                this._close(overlay);
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
    },

    // Закрыть модальное окно с анимацией
    _close(overlay) {
        overlay.classList.add('closing');
        setTimeout(() => {
            overlay.remove();
        }, 300); // Время совпадает с анимацией в CSS
    },

    // Экранирование HTML
    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

// Экспортируем для использования
window.Modal = Modal;
