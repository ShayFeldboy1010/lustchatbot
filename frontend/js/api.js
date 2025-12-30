/**
 * API Communication Module
 * Handles all communication with the backend server
 */

const API = {
    // Base URL - change this for production
    BASE_URL: 'http://localhost:8000/api',

    /**
     * Send a chat message to the server
     * @param {string} message - The message to send
     * @param {string} sessionId - The session ID
     * @returns {Promise<Object>} - The response data
     */
    async sendMessage(message, sessionId) {
        const response = await fetch(`${this.BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    },

    /**
     * Get conversation history for a session
     * @param {string} sessionId - The session ID
     * @returns {Promise<Object>} - The conversation history
     */
    async getHistory(sessionId) {
        const response = await fetch(`${this.BASE_URL}/history/${sessionId}`);

        if (!response.ok) {
            if (response.status === 404) {
                return { session_id: sessionId, messages: [] };
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    },

    /**
     * Clear conversation history for a session
     * @param {string} sessionId - The session ID
     * @returns {Promise<Object>} - The result
     */
    async clearHistory(sessionId) {
        const response = await fetch(`${this.BASE_URL}/history/${sessionId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    },

    /**
     * Check server health
     * @returns {Promise<Object>} - Health status
     */
    async checkHealth() {
        const response = await fetch(`${this.BASE_URL}/admin/health`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }
};

// Export for use in other modules
window.API = API;
