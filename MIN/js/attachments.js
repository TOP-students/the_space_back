// Функции для работы с вложениями и реакциями

// Рендер вложения в зависимости от типа
function renderAttachment(attachment, messageType) {
    if (!attachment) return '';

    const { file_url, file_type, file_size, file_name } = attachment;

    // Изображения
    if (messageType === 'image' || ['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(file_type)) {
        return `
            <div class="message-attachment message-image">
                <img src="${file_url}"
                     alt="Изображение"
                     class="attachment-image"
                     data-url="${file_url}"
                     title="Кликните для просмотра">
                <div class="image-actions">
                    <button class="image-download-btn" title="Скачать" onclick="event.stopPropagation(); AttachmentUtils.downloadFile('${file_url}', '${file_name || 'image.jpg'}')">
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M21 15V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            <path d="M7 10L12 15L17 10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            <path d="M12 15V3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </button>
                    <button class="image-open-btn" title="Открыть в новой вкладке" onclick="event.stopPropagation(); window.open('${file_url}', '_blank')">
                        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            <path d="M15 3h6v6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                            <path d="M10 14L21 3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </button>
                </div>
            </div>
        `;
    }

    // Аудио
    if (messageType === 'audio' || ['mp3', 'wav', 'ogg', 'mpeg'].includes(file_type)) {
        return `
            <div class="message-attachment message-audio">
                <audio controls controlsList="nodownload">
                    <source src="${file_url}" type="audio/${file_type}">
                    Ваш браузер не поддерживает аудио.
                </audio>
                <button class="audio-download-btn" title="Скачать" onclick="AttachmentUtils.downloadFile('${file_url}', '${file_name || 'audio.mp3'}')">
                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M21 15V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M7 10L12 15L17 10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M12 15V3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </button>
            </div>
        `;
    }

    // Документы
    if (messageType === 'file' || ['pdf', 'doc', 'docx', 'txt'].includes(file_type)) {
        const sizeStr = file_size ? formatFileSize(file_size) : '';
        const displayName = file_name || getFileNameFromUrl(file_url);
        const downloadFileName = file_name || displayName || 'document';
        return `
            <div class="message-attachment message-document">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="document-icon">
                    <path d="M13 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V9L13 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M13 2V9H20" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <div class="document-info">
                    <span class="document-name">${displayName}</span>
                    ${sizeStr ? `<span class="document-size">${sizeStr}</span>` : ''}
                </div>
                <button class="document-download" title="Скачать" onclick="AttachmentUtils.downloadFile('${file_url}', '${downloadFileName}')">
                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M21 15V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M7 10L12 15L17 10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M12 15V3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </button>
            </div>
        `;
    }

    return '';
}

// Рендер реакций под сообщением
function renderReactions(reactions, myReaction, messageId) {
    if (!reactions || reactions.length === 0) {
        return '';
    }

    const reactionsHTML = reactions.map(reaction => {
        const isMy = myReaction === reaction.reaction;
        return `
            <button class="reaction-item ${isMy ? 'my-reaction' : ''}"
                    data-message-id="${messageId}"
                    data-reaction="${reaction.reaction}"
                    title="${reaction.users.map(u => u.nickname).join(', ')}">
                <span class="reaction-emoji">${reaction.reaction}</span>
                <span class="reaction-count">${reaction.count}</span>
            </button>
        `;
    }).join('');

    return `
        <div class="message-reactions">
            ${reactionsHTML}
        </div>
    `;
}

// Открыть изображение в lightbox
function openImageLightbox(imageUrl) {
    // Создаём lightbox overlay
    const lightbox = document.createElement('div');
    lightbox.className = 'image-lightbox';
    lightbox.innerHTML = `
        <button class="lightbox-close" title="Закрыть (ESC)">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        </button>
        <div class="lightbox-content">
            <img src="${imageUrl}" alt="Изображение" class="lightbox-image">
        </div>
        <div class="lightbox-actions">
            <a href="${imageUrl}" download class="lightbox-download" title="Скачать">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M21 15V19C21 19.5304 20.7893 20.0391 20.4142 20.4142C20.0391 20.7893 19.5304 21 19 21H5C4.46957 21 3.96086 20.7893 3.58579 20.4142C3.21071 20.0391 3 19.5304 3 19V15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M7 10L12 15L17 10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M12 15V3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                Скачать
            </a>
            <button class="lightbox-open-new" onclick="window.open('${imageUrl}', '_blank')" title="Открыть в новой вкладке">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M15 3h6v6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M10 14L21 3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                Открыть в новой вкладке
            </button>
        </div>
    `;

    document.body.appendChild(lightbox);

    // Плавное появление
    setTimeout(() => lightbox.classList.add('active'), 10);

    // Закрытие по клику на overlay или кнопку
    const closeLightbox = () => {
        lightbox.classList.remove('active');
        setTimeout(() => lightbox.remove(), 300);
    };

    // Клик на сам lightbox (фон) закрывает окно
    lightbox.addEventListener('click', (e) => {
        // Закрываем только если клик был по самому lightbox, а не по контенту внутри
        if (e.target === lightbox) {
            closeLightbox();
        }
    });

    lightbox.querySelector('.lightbox-close').addEventListener('click', (e) => {
        e.stopPropagation();
        closeLightbox();
    });

    // Предотвращаем закрытие при клике на картинку или кнопки действий
    lightbox.querySelector('.lightbox-content').addEventListener('click', (e) => {
        e.stopPropagation();
    });

    lightbox.querySelector('.lightbox-actions').addEventListener('click', (e) => {
        e.stopPropagation();
    });

    // Закрытие по ESC
    const handleEsc = (e) => {
        if (e.key === 'Escape') {
            closeLightbox();
            document.removeEventListener('keydown', handleEsc);
        }
    };
    document.addEventListener('keydown', handleEsc);
}

// Форматировать размер файла
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Получить имя файла из URL
function getFileNameFromUrl(url) {
    try {
        const parts = url.split('/');
        const lastPart = parts[parts.length - 1];
        // Удаляем query параметры если есть
        return lastPart.split('?')[0] || 'Файл';
    } catch {
        return 'Файл';
    }
}

// Определить тип файла по MIME type
function getFileType(file) {
    const mimeType = file.type;

    if (mimeType.startsWith('image/')) return 'image';
    if (mimeType.startsWith('audio/')) return 'audio';
    if (mimeType.startsWith('application/pdf') ||
        mimeType.startsWith('application/msword') ||
        mimeType.startsWith('application/vnd.openxmlformats-officedocument') ||
        mimeType.startsWith('text/plain')) return 'document';

    return null;
}

// Валидация файла
function validateFile(file) {
    const maxSize = 10 * 1024 * 1024; // 10MB

    const allowedTypes = [
        // Images
        'image/jpeg', 'image/png', 'image/gif', 'image/webp',
        // Audio
        'audio/mpeg', 'audio/wav', 'audio/ogg',
        // Documents
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain'
    ];

    if (!allowedTypes.includes(file.type)) {
        throw new Error('Неподдерживаемый тип файла');
    }

    if (file.size > maxSize) {
        throw new Error('Файл слишком большой. Максимум: 10MB');
    }

    return true;
}

// Скачать файл с правильным именем
async function downloadFile(url, filename) {
    try {
        const response = await fetch(url);
        const blob = await response.blob();
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);
    } catch (error) {
        console.error('Error downloading file:', error);
        // Fallback: открыть в новой вкладке
        window.open(url, '_blank');
    }
}

// Экспорт функций
window.AttachmentUtils = {
    renderAttachment,
    renderReactions,
    openImageLightbox,
    formatFileSize,
    getFileNameFromUrl,
    getFileType,
    validateFile,
    downloadFile
};
