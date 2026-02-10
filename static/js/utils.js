/**
 * Utility Functions for AI Community Club
 *
 * Shared helpers used across the landing page and dashboard.
 */

'use strict';

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

/**
 * Display a toast-style notification that auto-dismisses after a few seconds.
 *
 * @param {string} message - Text to display.
 * @param {'success'|'error'} [type='success'] - Visual style of the toast.
 * @param {number} [duration=3500] - Time in ms before the toast disappears.
 */
const showNotification = (message, type = 'success', duration = 3500) => {
    // Remove any existing notification container so they do not stack
    const existing = document.getElementById('notification-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = 'notification-toast';
    toast.textContent = message;

    Object.assign(toast.style, {
        position: 'fixed',
        top: '24px',
        right: '24px',
        zIndex: '10000',
        padding: '14px 28px',
        borderRadius: '8px',
        color: '#fff',
        fontSize: '14px',
        fontFamily: 'inherit',
        lineHeight: '1.5',
        maxWidth: '420px',
        wordBreak: 'break-word',
        boxShadow: '0 4px 20px rgba(0,0,0,.25)',
        opacity: '0',
        transform: 'translateY(-12px)',
        transition: 'opacity .3s ease, transform .3s ease',
        background: type === 'error'
            ? 'linear-gradient(135deg, #e74c3c, #c0392b)'
            : 'linear-gradient(135deg, #2ecc71, #27ae60)',
    });

    document.body.appendChild(toast);

    // Trigger entrance animation
    requestAnimationFrame(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    });

    // Auto-dismiss
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-12px)';
        setTimeout(() => toast.remove(), 350);
    }, duration);
};

// ---------------------------------------------------------------------------
// Formatting
// ---------------------------------------------------------------------------

/**
 * Format a numeric amount as a Russian-style currency string.
 * Example: 3000 -> "3 000 RUB"
 *
 * @param {number|string} amount
 * @returns {string}
 */
const formatCurrency = (amount) => {
    const num = Number(amount);
    if (isNaN(num)) return '0 RUB';

    const formatted = Math.round(num)
        .toString()
        .replace(/\B(?=(\d{3})+(?!\d))/g, ' ');

    return `${formatted} RUB`;
};

/**
 * Format an ISO date string as DD.MM.YYYY.
 *
 * @param {string} isoString
 * @returns {string}
 */
const formatDate = (isoString) => {
    if (!isoString) return '';
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return '';
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    return `${day}.${month}.${year}`;
};

/**
 * Format an ISO date-time string as DD.MM.YYYY HH:MM.
 *
 * @param {string} isoString
 * @returns {string}
 */
const formatDateTime = (isoString) => {
    if (!isoString) return '';
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return '';
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    return `${day}.${month}.${year} ${hours}:${minutes}`;
};

// ---------------------------------------------------------------------------
// Clipboard
// ---------------------------------------------------------------------------

/**
 * Copy the supplied text to the system clipboard and show a notification.
 *
 * @param {string} text
 */
const copyToClipboard = async (text) => {
    try {
        await navigator.clipboard.writeText(text);
        showNotification('Скопировано в буфер обмена');
    } catch {
        // Fallback for older browsers / insecure contexts
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
            document.execCommand('copy');
            showNotification('Скопировано в буфер обмена');
        } catch {
            showNotification('Не удалось скопировать', 'error');
        }
        document.body.removeChild(textarea);
    }
};

// ---------------------------------------------------------------------------
// Partner statuses
// ---------------------------------------------------------------------------

const PARTNER_STATUS_MAP = {
    none:     { label: 'Нет статуса',  color: '#95a5a6' },
    bronze:   { label: 'Бронза',       color: '#cd7f32' },
    silver:   { label: 'Серебро',      color: '#a0a0a0' },
    gold:     { label: 'Золото',       color: '#f1c40f' },
    platinum: { label: 'Платина',      color: '#7b68ee' },
};

/**
 * Return a human-readable Russian label for a partner status code.
 *
 * @param {string} status
 * @returns {string}
 */
const getPartnerStatusLabel = (status) => {
    const entry = PARTNER_STATUS_MAP[status];
    return entry ? entry.label : status || 'Нет статуса';
};

/**
 * Return a badge-friendly colour for a partner status code.
 *
 * @param {string} status
 * @returns {string} CSS colour value.
 */
const getPartnerStatusColor = (status) => {
    const entry = PARTNER_STATUS_MAP[status];
    return entry ? entry.color : '#95a5a6';
};
