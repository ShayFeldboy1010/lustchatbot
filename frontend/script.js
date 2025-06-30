// LustBot Frontend JavaScript
class LustBot {
    constructor() {
        this.apiEndpoint = '/lustbot';
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.chatMessages = document.getElementById('chatMessages');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.leadModal = document.getElementById('leadModal');
        this.leadForm = document.getElementById('leadForm');
        this.userId = this.generateUserId();
        
        this.initializeEventListeners();
        this.updateSendButton();
    }
    
    generateUserId() {
        // Generate a unique user ID for this session
        let userId = localStorage.getItem('lustbot_user_id');
        if (!userId) {
            userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('lustbot_user_id', userId);
        }
        return userId;
    }
    
    initializeEventListeners() {
        // Send button click
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Enter key to send
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Update send button state
        this.messageInput.addEventListener('input', () => this.updateSendButton());
        
        // Lead modal handlers
        document.getElementById('closeModal').addEventListener('click', () => this.hideLeadModal());
        this.leadModal.addEventListener('click', (e) => {
            if (e.target === this.leadModal) this.hideLeadModal();
        });
        
        // Lead form submission
        this.leadForm.addEventListener('submit', (e) => this.handleLeadSubmission(e));
        
        // Auto-resize textarea
        this.messageInput.addEventListener('input', this.autoResize.bind(this));
    }
    
    updateSendButton() {
        const hasText = this.messageInput.value.trim().length > 0;
        this.sendButton.disabled = !hasText;
    }
    
    autoResize() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = this.messageInput.scrollHeight + 'px';
    }
    
    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.sendButton.disabled) return;
        
        // Add user message to chat
        this.addMessage(message, 'user');
        
        // Clear input and disable send button
        this.messageInput.value = '';
        this.updateSendButton();
        this.messageInput.style.height = 'auto';
        
        // Show typing indicator
        this.showTyping();
        
        try {
            const response = await fetch(this.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    user_id: this.userId
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // Hide typing and add bot response
            this.hideTyping();
            this.addMessage(data.reply || 'Sorry, I didn\'t understand that.', 'bot');
            
            // Check if the response contains lead capture suggestion
            this.checkForLeadCapture(data.reply);
            
        } catch (error) {
            console.error('Chat error:', error);
            this.hideTyping();
            this.addMessage(
                'Sorry, I\'m having technical difficulties. Please try again in a moment.',
                'bot',
                true
            );
        }
        
        // Focus back on input
        this.messageInput.focus();
    }
    
    addMessage(text, sender, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        if (isError) {
            messageDiv.classList.add('error-message');
        }
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = sender === 'user' ? '👤' : '🤖';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        const messageText = document.createElement('div');
        messageText.className = 'message-text';
        
        // Process message text for product cards and links
        messageText.innerHTML = this.processMessageText(text);
        
        const messageTime = document.createElement('div');
        messageTime.className = 'message-time';
        messageTime.textContent = this.formatTime(new Date());
        
        content.appendChild(messageText);
        content.appendChild(messageTime);
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Animate message appearance
        messageDiv.style.opacity = '0';
        messageDiv.style.transform = 'translateY(10px)';
        setTimeout(() => {
            messageDiv.style.transition = 'all 0.3s ease';
            messageDiv.style.opacity = '1';
            messageDiv.style.transform = 'translateY(0)';
        }, 50);
    }
    
    processMessageText(text) {
        // Convert URLs to links
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        text = text.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener">$1</a>');
        
        // Remove newlines - let text flow naturally
        text = text.replace(/\n/g, ' ');
        
        // Look for product information patterns and format them
        // This is a simple example - you can enhance this based on your product response format
        if (text.includes('**') && text.includes('Price:')) {
            text = this.formatProductCard(text);
        }
        
        return text;
    }
    
    formatProductCard(text) {
        // Simple product card formatting
        // You can enhance this based on your actual product response format
        return text
            .replace(/\*\*(.*?)\*\*/g, '<div class="product-name">$1</div>')
            .replace(/Price: ([^\n]*)/g, '<div class="product-price">$1</div>')
            .replace(/Link: (https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" class="product-link">View Product →</a>');
    }
    
    formatTime(date) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    
    showTyping() {
        this.typingIndicator.style.display = 'block';
        this.scrollToBottom();
    }
    
    hideTyping() {
        this.typingIndicator.style.display = 'none';
    }
    
    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    checkForLeadCapture(message) {
        // Simple patterns to detect when we should show lead capture
        const leadPatterns = [
            /would you like.*(contact|call|email)/i,
            /our team.*(reach|contact)/i,
            /leave.*details/i,
            /personal.*consultant/i,
            /connect.*with.*sales/i
        ];
        
        const shouldShowLead = leadPatterns.some(pattern => pattern.test(message));
        
        if (shouldShowLead) {
            setTimeout(() => this.showLeadModal(), 1000);
        }
    }
    
    showLeadModal() {
        this.leadModal.style.display = 'flex';
        document.getElementById('leadName').focus();
    }
    
    hideLeadModal() {
        this.leadModal.style.display = 'none';
        this.leadForm.reset();
    }
    
    async handleLeadSubmission(e) {
        e.preventDefault();
        
        const formData = new FormData(this.leadForm);
        const leadData = {
            name: document.getElementById('leadName').value,
            email: document.getElementById('leadEmail').value,
            phone: document.getElementById('leadPhone').value,
            product: document.getElementById('leadProduct').value
        };
        
        // Validate required fields
        if (!leadData.name || !leadData.email || !leadData.product) {
            alert('Please fill in all required fields.');
            return;
        }
        
        try {
            // Send lead capture message to the bot
            const leadMessage = `Please capture this lead: ${JSON.stringify(leadData)}`;
            
            const response = await fetch(this.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: leadMessage,
                    user_id: this.userId
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.hideLeadModal();
                this.addMessage(
                    `Thank you ${leadData.name}! Your information has been submitted. Our team will contact you soon about ${leadData.product}.`,
                    'bot'
                );
            } else {
                throw new Error('Failed to submit lead');
            }
            
        } catch (error) {
            console.error('Lead submission error:', error);
            alert('Sorry, there was an error submitting your information. Please try again.');
        }
    }
}

// Initialize the chat when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.lustBot = new LustBot();
    
    // Add some helpful quick actions
    const quickActions = [
        'Show me silk products',
        'I need a romantic gift',
        'What\'s popular this week?',
        'Help me choose lingerie'
    ];
    
    // You can add quick action buttons here if desired
    console.log('LustBot initialized with quick actions:', quickActions);
});

// Service Worker for offline functionality (optional)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => console.log('SW registered'))
            .catch(error => console.log('SW registration failed'));
    });
}
