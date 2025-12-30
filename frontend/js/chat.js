/**
 * Chat Functionality Module
 * Handles all chat UI interactions and state management
 */

// Session management
let sessionId = localStorage.getItem('chatSessionId');
if (!sessionId) {
    sessionId = generateUUID();
    localStorage.setItem('chatSessionId', sessionId);
}

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const chatForm = document.getElementById('chatForm');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const clearBtn = document.getElementById('clearBtn');
const escalationBanner = document.getElementById('escalationBanner');

/**
 * Generate a UUID v4
 * @returns {string} UUID
 */
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Format message text with line breaks and links
 * @param {string} text - Message text
 * @returns {string} Formatted HTML
 */
function formatMessage(text) {
    // Escape HTML first
    let formatted = escapeHtml(text);

    // Convert URLs to clickable links
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    formatted = formatted.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener">$1</a>');

    // Convert newlines to <br>
    formatted = formatted.replace(/\n/g, '<br>');

    return formatted;
}

/**
 * Add a message to the chat display
 * @param {string} content - Message content
 * @param {boolean} isUser - Whether this is a user message
 * @param {string} type - Message type (normal, error, system)
 */
function addMessage(content, isUser = false, type = 'normal') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'bot'} ${type === 'error' ? 'error' : ''} ${type === 'system' ? 'system' : ''}`;

    const avatar = isUser ? '👤' : '🤖';

    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">${formatMessage(content)}</div>
    `;

    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

/**
 * Show typing indicator
 */
function showTyping() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot';
    typingDiv.id = 'typingIndicator';
    typingDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="typing-indicator">
            <span></span><span></span><span></span>
        </div>
    `;
    chatMessages.appendChild(typingDiv);
    scrollToBottom();
}

/**
 * Hide typing indicator
 */
function hideTyping() {
    const typing = document.getElementById('typingIndicator');
    if (typing) {
        typing.remove();
    }
}

/**
 * Scroll chat to bottom
 */
function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Show escalation banner
 */
function showEscalation() {
    escalationBanner.style.display = 'block';
}

/**
 * Hide escalation banner
 */
function hideEscalation() {
    escalationBanner.style.display = 'none';
}

/**
 * Set UI loading state
 * @param {boolean} loading - Whether loading
 */
function setLoading(loading) {
    sendButton.disabled = loading;
    messageInput.disabled = loading;
    if (!loading) {
        messageInput.focus();
    }
}

/**
 * Send a message to the server
 * @param {string} message - Message to send
 */
async function sendMessage(message) {
    if (!message.trim()) return;

    // Add user message to chat
    addMessage(message, true);
    messageInput.value = '';
    setLoading(true);
    showTyping();

    try {
        const data = await API.sendMessage(message, sessionId);

        hideTyping();
        addMessage(data.response);

        // Handle escalation
        if (data.needs_escalation) {
            showEscalation();
        }

        // Update session ID if server returned a new one
        if (data.session_id && data.session_id !== sessionId) {
            sessionId = data.session_id;
            localStorage.setItem('chatSessionId', sessionId);
        }

    } catch (error) {
        hideTyping();
        console.error('Error:', error);
        addMessage('מצטער, יש תקלה זמנית. אנא נסה שוב 🙏', false, 'error');
    }

    setLoading(false);
}

/**
 * Load conversation history from server
 */
async function loadHistory() {
    try {
        const data = await API.getHistory(sessionId);

        if (data.messages && data.messages.length > 0) {
            // Clear default welcome message
            chatMessages.innerHTML = '';

            // Add all historical messages
            data.messages.forEach(msg => {
                addMessage(msg.content, msg.role === 'user');
            });
        }
    } catch (error) {
        console.log('No previous history or error loading:', error);
    }
}

/**
 * Clear chat and start new session
 */
async function clearChat() {
    if (!confirm('האם אתה בטוח שברצונך לנקות את השיחה?')) {
        return;
    }

    try {
        await API.clearHistory(sessionId);
    } catch (error) {
        console.log('Error clearing history:', error);
    }

    // Generate new session
    sessionId = generateUUID();
    localStorage.setItem('chatSessionId', sessionId);

    // Clear UI
    chatMessages.innerHTML = '';
    hideEscalation();

    // Add welcome message
    addMessage('היי! אני לסטי 😊 איך אפשר לעזור לך היום?', false);
}

// Event Listeners
chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    sendMessage(messageInput.value);
});

messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage(messageInput.value);
    }
});

// Auto-resize textarea
messageInput.addEventListener('input', () => {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
});

clearBtn.addEventListener('click', clearChat);

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadHistory();
    messageInput.focus();
});
