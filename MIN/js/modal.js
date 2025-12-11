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
            this._showCreateRoomForm(resolve);
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

    // Закрыть все открытые модальные окна
    closeAll() {
        const overlays = document.querySelectorAll('.modal-overlay');
        overlays.forEach(overlay => this._close(overlay));
    },

    // Экранирование HTML
    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    // Показать info
    info(message, title = 'Информация') {
        return this.alert(message, title, 'info');
    },

    // Показать prompt (ввод текста)
    prompt(message, defaultValue = '', title = 'Введите значение') {
        return new Promise((resolve) => {
            this._showForm({
                title,
                message,
                fields: [
                    { id: 'prompt-input', label: '', type: 'text', required: true, value: defaultValue, placeholder: message }
                ],
                buttons: [
                    {
                        text: 'Отмена',
                        class: 'modal-button-secondary',
                        onClick: () => resolve(null)
                    },
                    {
                        text: 'OK',
                        class: 'modal-button-primary',
                        onClick: () => {
                            const input = document.getElementById('prompt-input');
                            resolve(input ? input.value : null);
                        }
                    }
                ]
            });
        });
    },

    // Показать кастомный контент
    custom(htmlContent, title = '', onReady = null) {
        return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.className = 'modal-overlay';

            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                ${title ? `<div class="modal-header"><h2>${this._escapeHtml(title)}</h2></div>` : ''}
                <div class="modal-body">
                    ${htmlContent}
                </div>
                <div class="modal-footer">
                    <button class="modal-button modal-button-primary">Закрыть</button>
                </div>
            `;

            overlay.appendChild(modal);
            document.body.appendChild(overlay);

            // Обработчики закрытия
            const closeBtn = modal.querySelector('.modal-button');
            closeBtn.addEventListener('click', () => {
                this._close(overlay);
                resolve(true);
            });

            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    this._close(overlay);
                    resolve(false);
                }
            });

            // Вызываем колбэк после отрисовки
            if (onReady) {
                setTimeout(() => onReady(modal), 0);
            }
        });
    },

    // Форма создания комнаты с участниками
    _showCreateRoomForm(resolve) {
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';

        const modal = document.createElement('div');
        modal.className = 'modal-window';

        // Массив для хранения добавленных участников
        const participantsList = [];
        let selectedAvatarFile = null;

        modal.innerHTML = `
            <div class="modal-header">
                <h3 class="modal-title">Создать новую комнату</h3>
            </div>
            <div class="modal-body">
                <form id="create-room-form">
                    <div class="modal-form-group">
                        <label for="room-name">Название комнаты</label>
                        <input type="text"
                               id="room-name"
                               required
                               placeholder="Введите название..."
                               title="От 3 до 100 символов"
                               minlength="3"
                               maxlength="100"/>
                    </div>
                    <div class="modal-form-group">
                        <label for="room-description">Описание (необязательно)</label>
                        <textarea id="room-description"
                                  placeholder="Описание комнаты..."
                                  title="Максимум 500 символов"
                                  maxlength="500"
                                  rows="3"></textarea>
                    </div>
                    <div class="modal-form-group">
                        <label for="room-avatar">Аватар комнаты (необязательно)</label>
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div id="avatar-preview" style="width: 60px; height: 60px; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; align-items: center; justify-content: center; color: white; font-size: 24px; font-weight: bold;">?</div>
                            <div style="flex: 1;">
                                <input type="file" id="room-avatar" accept="image/jpeg,image/png,image/webp,image/gif" style="display: none;"/>
                                <button type="button" id="select-avatar-btn" class="modal-button modal-button-secondary" style="width: 100%;">Выбрать файл</button>
                                <div id="avatar-filename" style="margin-top: 4px; font-size: 12px; color: #666;"></div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-form-group">
                        <label>Добавить участников (необязательно)</label>
                        <div style="display: flex; gap: 8px; margin-bottom: 8px;">
                            <input type="text" id="participant-input" placeholder="Никнейм или ID пользователя" style="flex: 1;"/>
                            <button type="button" id="add-participant-btn" class="modal-button modal-button-primary" style="min-width: auto; padding: 10px 16px;">Добавить</button>
                        </div>
                        <div id="participant-error" style="color: #dc3545; font-size: 13px; margin-bottom: 8px; display: none;"></div>
                        <div id="participants-list" style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px;"></div>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button class="modal-button modal-button-secondary" id="cancel-btn">Отмена</button>
                <button class="modal-button modal-button-primary" id="create-btn">Создать</button>
            </div>
        `;

        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        const participantInput = modal.querySelector('#participant-input');
        const addParticipantBtn = modal.querySelector('#add-participant-btn');
        const participantsListDiv = modal.querySelector('#participants-list');
        const participantError = modal.querySelector('#participant-error');

        // Обработчики для загрузки аватара
        const avatarInput = modal.querySelector('#room-avatar');
        const selectAvatarBtn = modal.querySelector('#select-avatar-btn');
        const avatarPreview = modal.querySelector('#avatar-preview');
        const avatarFilename = modal.querySelector('#avatar-filename');

        selectAvatarBtn.addEventListener('click', () => {
            avatarInput.click();
        });

        avatarInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) return;

            // Проверка типа файла
            if (!file.type.startsWith('image/')) {
                Modal.error('Выберите изображение');
                return;
            }

            // Проверка размера (макс 10MB)
            if (file.size > 10 * 1024 * 1024) {
                Modal.error('Размер файла не должен превышать 10MB');
                return;
            }

            selectedAvatarFile = file;
            avatarFilename.textContent = file.name;

            // Показываем превью
            const reader = new FileReader();
            reader.onload = (event) => {
                avatarPreview.innerHTML = '';
                avatarPreview.style.backgroundImage = `url(${event.target.result})`;
                avatarPreview.style.backgroundSize = 'cover';
                avatarPreview.style.backgroundPosition = 'center';
            };
            reader.readAsDataURL(file);
        });

        // Добавление участника
        addParticipantBtn.addEventListener('click', async () => {
            const identifier = participantInput.value.trim();
            if (!identifier) return;

            participantError.style.display = 'none';
            addParticipantBtn.disabled = true;
            addParticipantBtn.textContent = '...';

            try {
                const user = await API.checkUser(identifier);

                // Проверяем, не добавлен ли уже
                if (participantsList.find(p => p.id === user.id)) {
                    participantError.textContent = 'Этот пользователь уже добавлен';
                    participantError.style.display = 'block';
                    return;
                }

                // Добавляем в список
                participantsList.push(user);

                // Создаем чип
                const chip = document.createElement('div');
                chip.className = 'participant-chip';
                chip.innerHTML = `
                    <span>${this._escapeHtml(user.nickname)}</span>
                    <button type="button" class="remove-participant" data-user-id="${user.id}">×</button>
                `;
                participantsListDiv.appendChild(chip);

                // Очищаем input
                participantInput.value = '';

                // Обработчик удаления
                chip.querySelector('.remove-participant').addEventListener('click', () => {
                    const index = participantsList.findIndex(p => p.id === user.id);
                    if (index > -1) {
                        participantsList.splice(index, 1);
                    }
                    chip.remove();
                });

            } catch (error) {
                console.error('Check user error:', error);
                participantError.textContent = error.message || 'Пользователь не найден';
                participantError.style.display = 'block';
            } finally {
                addParticipantBtn.disabled = false;
                addParticipantBtn.textContent = 'Добавить';
            }
        });

        // Enter для добавления участника
        participantInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                addParticipantBtn.click();
            }
        });

        // Кнопка "Создать"
        modal.querySelector('#create-btn').addEventListener('click', (e) => {
            e.preventDefault();

            const name = modal.querySelector('#room-name').value.trim();
            const description = modal.querySelector('#room-description').value.trim();

            // Валидация названия
            if (!name) {
                Modal.error('Введите название комнаты');
                return;
            }

            if (name.length < 3 || name.length > 100) {
                Modal.error('Название комнаты должно содержать от 3 до 100 символов');
                return;
            }

            // Валидация описания
            if (description && description.length > 500) {
                Modal.error('Описание не должно превышать 500 символов');
                return;
            }

            this._close(overlay);
            resolve({
                name,
                description,
                participants: participantsList,
                avatarFile: selectedAvatarFile
            });
        });

        // Кнопка "Отмена"
        modal.querySelector('#cancel-btn').addEventListener('click', () => {
            this._close(overlay);
            resolve(null);
        });

        // Закрытие по клику на overlay
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                this._close(overlay);
                resolve(null);
            }
        });

        // ESC для закрытия
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                this._close(overlay);
                resolve(null);
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
    }
};

// Экспортируем для использования
window.Modal = Modal;
