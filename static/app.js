// State management
let currentSessionId = null;
let sessions = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadSessions();
});

// Create a new session
async function createNewSession() {
    try {
        const response = await fetch('/sessions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ title: 'New Chat' })
        });

        if (!response.ok) throw new Error('Failed to create session');

        const session = await response.json();
        currentSessionId = session.id;
        await loadSessions();
        clearMessages();
        enableInput();
        updateChatHeader();
    } catch (error) {
        console.error('Error creating session:', error);
        showError('Failed to create new chat session');
    }
}

// Load all sessions
async function loadSessions() {
    try {
        const response = await fetch('/sessions');
        if (!response.ok) throw new Error('Failed to load sessions');

        const newSessions = await response.json();
        
        sessions = newSessions;
        renderSessionsList();
    } catch (error) {
        console.error('Error loading sessions:', error);
    }
}

// Render sessions list
function renderSessionsList() {
    const sessionsList = document.getElementById('sessionsList');

    if (sessions.length === 0) {
        sessionsList.innerHTML = '<p class="no-sessions">No sessions yet</p>';
        return;
    }

    sessionsList.innerHTML = sessions.map(session => `
        <div class="session-item ${session.id === currentSessionId ? 'active' : ''}" 
             onclick="selectSession('${session.id}')">
            <div class="session-details">
                <strong>${session.title || 'Untitled Chat'}</strong>
                <p>${new Date(session.created_at).toLocaleDateString()}</p>
            </div>
            <details class="chat-actions" onclick="event.stopPropagation()">
                <summary aria-label="Chat actions" title="Chat actions">&#8942;</summary>
                <div class="chat-actions-menu">
                    <button class="btn-delete-chat" type="button"
                            onclick="deleteSession(event, '${session.id}')">Delete chat</button>
                </div>
            </details>
        </div>
    `).join('');
}

// Delete a chat and its messages. The server cascades the message deletion.
async function deleteSession(event, sessionId) {
    event.stopPropagation();

    if (!window.confirm('Delete this chat and all of its messages? This cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`/sessions/${sessionId}`, { method: 'DELETE' });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || 'Failed to delete chat');
        }

        const deletedActiveSession = currentSessionId === sessionId;
        sessions = sessions.filter(session => session.id !== sessionId);

        if (deletedActiveSession) {
            currentSessionId = null;
            clearMessages();
            updateChatHeader();
            enableInput();
        }

        renderSessionsList();
    } catch (error) {
        console.error('Error deleting session:', error);
        showError(`Error: ${error.message}`);
    }
}

// Select a session
function selectSession(sessionId) {
    currentSessionId = sessionId;
    renderSessionsList();
    loadMessages();
    clearMessages();
    updateChatHeader();
    enableInput();
}

// Load messages for current session
async function loadMessages() {
    if (!currentSessionId) return;

    try {
        const response = await fetch(`/sessions/${currentSessionId}/messages`);
        if (!response.ok) throw new Error('Failed to load messages');

        const messages = await response.json();
        displayMessages(messages);
    } catch (error) {
        console.error('Error loading messages:', error);
    }
}

// Display messages
function displayMessages(messages) {
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.innerHTML = '';

    if (messages.length === 0) {
        chatMessages.innerHTML = '<div class="welcome-message"><h3>Start the conversation!</h3></div>';
        return;
    }

    messages.forEach(msg => {
        addMessageToDOM(msg.content, msg.role);
    });

    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Add message to DOM
function addMessageToDOM(content, role) {
    const chatMessages = document.getElementById('chatMessages');

    // Remove welcome message if exists
    const welcomeMsg = chatMessages.querySelector('.welcome-message');
    if (welcomeMsg) welcomeMsg.remove();

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = parseMessageContent(content);

    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Parse message content (handle markdown formatting)
function parseMessageContent(content) {
    // Use marked.js to render markdown
    if (typeof marked !== 'undefined') {
        return marked.parse(content);
    }
    
    // Fallback: basic HTML escaping if marked not loaded
    return content
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\n/g, '<br>');
}

// Generate title from first message
async function generateAndUpdateSessionTitle(message) {
    if (!currentSessionId) return;

    // Use the first user message as a concise, durable chat title.
    const normalizedMessage = message.replace(/\s+/g, ' ').trim();
    const title = normalizedMessage.length > 50
        ? `${normalizedMessage.substring(0, 50)}...`
        : normalizedMessage;

    try {
        const sessionId = currentSessionId;
        const response = await fetch(`/sessions/${sessionId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title })
        });
        if (!response.ok) throw new Error('Failed to update chat title');

        const updatedSession = await response.json();
        sessions = sessions.map(session =>
            session.id === updatedSession.id ? updatedSession : session
        );
        renderSessionsList();
        updateChatHeader();
    } catch (error) {
        console.error('Error updating session title:', error);
    }
}

// Send message
async function sendMessage() {
    if (!currentSessionId) {
        showError('Please create or select a chat session first');
        return;
    }

    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();

    if (!message) return;

    // Check if this is the first message (no messages in DOM yet, excluding loading indicator)
    const isFirstMessage = document.querySelectorAll('.message:not(.loading)').length === 0;

    // Clear input
    messageInput.value = '';

    // Add user message to DOM
    addMessageToDOM(message, 'user');

    // Generate title from first message
    if (isFirstMessage) {
        generateAndUpdateSessionTitle(message);
    }

    // Show loading indicator while the SSE response is being established.
    showLoadingIndicator();

    try {
        const response = await fetch('/chat/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: currentSessionId,
                message: message
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to send message');
        }

        if (!response.body) throw new Error('Streaming is not supported by this browser');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let assistantText = '';
        let completed = false;
        let assistantContent;

        const appendToken = (content) => {
            if (!assistantContent) {
                removeLoadingIndicator();
                addMessageToDOM('', 'assistant');
                assistantContent = document.querySelector('.message.assistant:last-child .message-content');
            }
            assistantText += content;
            assistantContent.innerHTML = parseMessageContent(assistantText);
            document.getElementById('chatMessages').scrollTop = document.getElementById('chatMessages').scrollHeight;
        };

        while (true) {
            const { value, done } = await reader.read();
            buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
            const events = buffer.split('\n\n');
            buffer = events.pop();
            for (const rawEvent of events) {
                const eventName = rawEvent.match(/^event: (.+)$/m)?.[1];
                const dataLine = rawEvent.match(/^data: (.+)$/m)?.[1];
                if (!dataLine) continue;
                const data = JSON.parse(dataLine);
                if (eventName === 'token') appendToken(data.content);
                if (eventName === 'error') throw new Error(data.message || 'The stream failed');
                if (eventName === 'done') completed = true;
            }
            if (done) break;
        }
        if (!completed) throw new Error('The response stream ended unexpectedly');
        if (!assistantText) throw new Error('The AI returned an empty response');

        removeLoadingIndicator();

        // Refresh sessions to update timestamps (this won't overwrite our custom title)
        await loadSessions();
    } catch (error) {
        console.error('Error sending message:', error);
        removeLoadingIndicator();
        showError(`Error: ${error.message}`);
    }
}

// Show loading indicator
function showLoadingIndicator() {
    const chatMessages = document.getElementById('chatMessages');
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message loading';
    loadingDiv.id = 'loadingIndicator';
    loadingDiv.innerHTML = `
        <div class="loading-dots">
            <div class="loading-dot"></div>
            <div class="loading-dot"></div>
            <div class="loading-dot"></div>
        </div>
    `;
    chatMessages.appendChild(loadingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Remove loading indicator
function removeLoadingIndicator() {
    const loading = document.getElementById('loadingIndicator');
    if (loading) loading.remove();
}

// Clear messages from DOM
function clearMessages() {
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.innerHTML = '<div class="welcome-message"><h3>Start the conversation!</h3></div>';
}

// Update chat header
function updateChatHeader() {
    const chatHeader = document.getElementById('chatTitle');
    const sessionInfo = document.getElementById('sessionInfo');

    if (!currentSessionId) {
        chatHeader.textContent = 'Start a new conversation';
        sessionInfo.textContent = '';
        return;
    }

    const session = sessions.find(s => s.id === currentSessionId);
    if (session) {
        chatHeader.textContent = session.title || 'Untitled Chat';
        sessionInfo.textContent = `Created: ${new Date(session.created_at).toLocaleString()}`;
    }
}

// Enable/Disable input
function enableInput() {
    const input = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    input.disabled = !currentSessionId;
    sendBtn.disabled = !currentSessionId;
}

// Handle key press in input
function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// Show error message
function showError(message) {
    const chatMessages = document.getElementById('chatMessages');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'message error';
    errorDiv.innerHTML = `<div class="message-content">⚠️ ${message}</div>`;
    chatMessages.appendChild(errorDiv);
}

// Initial setup
enableInput();
