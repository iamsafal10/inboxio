"""Router for the minimal web chat UI and placeholder chat endpoint."""

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(tags=["chat"])

class ChatRequest(BaseModel):
    """Schema for incoming chat messages."""
    message: str

# Minimal HTML template embedded directly for simplicity in Phase 0.
CHAT_UI_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Inboxio Chat</title>
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
        #chat-section, #gmail-section { display: none; margin-top: 20px; }
        .message { margin: 5px 0; padding: 10px; border-radius: 5px; }
        .user-msg { background: #e3f2fd; text-align: right; }
        .agent-msg { background: #f5f5f5; text-align: left; }
        #message-list { height: 300px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; }
        .error { color: red; }
    </style>
</head>
<body>
    <h1>Inboxio Chat UI (Phase 0)</h1>

    <div id="auth-section">
        <h3>Login</h3>
        <input type="email" id="email" placeholder="Email"><br><br>
        <input type="password" id="password" placeholder="Password"><br><br>
        <button onclick="login()">Login</button>
        <div id="login-error" class="error"></div>
    </div>

    <div id="gmail-section">
        <h3>Gmail Status</h3>
        <p>Status: <span id="gmail-status">Checking...</span></p>
        <button id="connect-gmail-btn" style="display: none;" onclick="connectGmail()">Connect Gmail</button>
    </div>

    <div id="chat-section">
        <h3>Chat</h3>
        <div id="message-list"></div>
        <input type="text" id="chat-input" placeholder="Type a message..." style="width: 70%;" onkeydown="if(event.key === 'Enter') sendMessage()">
        <button onclick="sendMessage()">Send</button>
    </div>

    <script>
        // Stored in-memory only for security, as per Task 5 requirements.
        let jwtToken = null; 

        async function login() {
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            
            try {
                const res = await fetch('/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                
                if (!res.ok) {
                    const errData = await res.json();
                    throw new Error(errData.detail || 'Login failed');
                }
                
                const data = await res.json();
                jwtToken = data.access_token;
                
                document.getElementById('auth-section').style.display = 'none';
                document.getElementById('gmail-section').style.display = 'block';
                document.getElementById('chat-section').style.display = 'block';
                
                checkGmailStatus();
            } catch (err) {
                document.getElementById('login-error').innerText = err.message;
            }
        }

        async function checkGmailStatus() {
            try {
                const res = await fetch('/auth/me', {
                    headers: { 'Authorization': 'Bearer ' + jwtToken }
                });
                const data = await res.json();
                
                if (data.gmail_connected) {
                    document.getElementById('gmail-status').innerText = 'Connected';
                    document.getElementById('connect-gmail-btn').style.display = 'none';
                } else {
                    document.getElementById('gmail-status').innerText = 'Not connected';
                    document.getElementById('connect-gmail-btn').style.display = 'inline-block';
                }
            } catch (err) {
                console.error(err);
            }
        }

        async function connectGmail() {
            try {
                const res = await fetch('/gmail/oauth/connect', {
                    headers: { 'Authorization': 'Bearer ' + jwtToken }
                });
                const data = await res.json();
                window.open(data.authorization_url, '_blank');
            } catch (err) {
                console.error(err);
            }
        }

        async function sendMessage() {
            const input = document.getElementById('chat-input');
            const message = input.value.trim();
            if (!message) return;
            
            addMessageToUI('user-msg', 'You: ' + message);
            input.value = '';

            try {
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + jwtToken
                    },
                    body: JSON.stringify({ message })
                });
                
                if (res.ok) {
                    const data = await res.json();
                    addMessageToUI('agent-msg', 'Agent: ' + data.response);
                } else {
                    addMessageToUI('error', 'Error sending message');
                }
            } catch (err) {
                console.error(err);
            }
        }

        function addMessageToUI(className, text) {
            const list = document.getElementById('message-list');
            const div = document.createElement('div');
            div.className = 'message ' + className;
            div.innerText = text;
            list.appendChild(div);
            list.scrollTop = list.scrollHeight;
        }
    </script>
</body>
</html>
"""

@router.get("/chat-ui", response_class=HTMLResponse)
def get_chat_ui():
    """Serve the minimal web chat UI."""
    return HTMLResponse(content=CHAT_UI_HTML)


from app.services.domain_filter import is_career_question

@router.post("/chat")
def chat_endpoint(payload: ChatRequest, current_user: User = Depends(get_current_user)):
    """Placeholder chat endpoint. 
    
    Phase 2 Note: Replace this placeholder echo logic with real agent/LLM logic.
    """
    if not is_career_question(payload.message):
        return {"response": "I can only answer questions related to your career, job applications, or interviews."}
        
    return {"response": f"Agent not built yet. You said: {payload.message}"}
