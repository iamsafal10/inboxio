"""Router for the minimal web chat UI and placeholder chat endpoint."""

from fastapi import APIRouter, Depends, HTTPException, status
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
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Inboxio | Intelligence Agent</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #f3f4f6;
            --card-bg: #ffffff;
            --primary: #2563eb;
            --primary-hover: #1d4ed8;
            --text-main: #1f2937;
            --text-muted: #6b7280;
            --border: #e5e7eb;
            --user-msg: #3b82f6;
            --agent-msg: #f3f4f6;
        }
        * { box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .container {
            background: var(--card-bg);
            width: 100%;
            max-width: 800px;
            height: 90vh;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.05);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .header {
            padding: 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 { margin: 0; font-size: 1.25rem; font-weight: 600; }
        .gmail-status { font-size: 0.875rem; color: var(--text-muted); }
        .btn {
            background-color: var(--primary);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.875rem;
            font-weight: 500;
            transition: background 0.2s;
        }
        .btn:hover { background-color: var(--primary-hover); }
        .btn:disabled { background-color: #93c5fd; cursor: not-allowed; }
        
        /* Auth Screen */
        #auth-section {
            padding: 40px;
            text-align: center;
            margin: auto;
        }
        .input-field {
            width: 100%;
            padding: 10px 12px;
            margin-bottom: 12px;
            border: 1px solid var(--border);
            border-radius: 6px;
            font-size: 0.95rem;
        }
        .toggle-auth { color: var(--primary); cursor: pointer; font-size: 0.875rem; margin-top: 10px; display: inline-block; }
        
        /* Chat Screen */
        #main-section { display: none; flex-direction: column; height: 100%; }
        #message-list {
            flex-grow: 1;
            padding: 20px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .message {
            max-width: 80%;
            padding: 12px 16px;
            border-radius: 12px;
            line-height: 1.5;
            font-size: 0.95rem;
            word-wrap: break-word;
        }
        .user-msg {
            background-color: var(--user-msg);
            color: white;
            align-self: flex-end;
            border-bottom-right-radius: 4px;
        }
        .agent-msg {
            background-color: var(--agent-msg);
            color: var(--text-main);
            align-self: flex-start;
            border-bottom-left-radius: 4px;
        }
        .citations {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 8px;
            border-top: 1px solid #e5e7eb;
            padding-top: 8px;
        }
        
        /* Input Area */
        .input-area {
            padding: 20px;
            border-top: 1px solid var(--border);
            display: flex;
            gap: 10px;
            background: #f9fafb;
        }
        .input-area input {
            flex-grow: 1;
            padding: 12px;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 0.95rem;
        }
        .input-area input:focus { outline: none; border-color: var(--primary); }
        
        /* Loading Spinner */
        .loader {
            border: 3px solid #f3f3f3;
            border-top: 3px solid var(--primary);
            border-radius: 50%;
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
            display: none;
            margin: 0 auto;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .error { color: #dc2626; font-size: 0.875rem; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <!-- AUTH SECTION -->
        <div id="auth-section">
            <h2 id="auth-title">Welcome back</h2>
            <p style="color: var(--text-muted); margin-bottom: 24px;">Sign in to your Inboxio agent</p>
            <input type="email" id="email" class="input-field" placeholder="Email address">
            <input type="password" id="password" class="input-field" placeholder="Password">
            <button class="btn" style="width: 100%;" onclick="handleAuth()">Continue</button>
            <div class="toggle-auth" onclick="toggleAuthMode()">Don't have an account? Sign up</div>
            <div id="auth-error" class="error"></div>
        </div>

        <!-- MAIN APP SECTION -->
        <div id="main-section">
            <div class="header">
                <h1>Inboxio</h1>
                <div class="gmail-status">
                    <span id="gmail-status-text">Checking Gmail connection...</span>
                    <button id="connect-gmail-btn" class="btn" style="display: none; margin-left: 10px;" onclick="connectGmail()">Connect Gmail</button>
                </div>
            </div>

            <div id="message-list">
                <div class="message agent-msg">Hello! I'm your Inboxio agent. Ask me anything about your emails.</div>
            </div>

            <div class="input-area">
                <input type="text" id="chat-input" placeholder="Ask a question..." onkeydown="if(event.key === 'Enter') sendMessage()">
                <button id="send-btn" class="btn" onclick="sendMessage()">Send</button>
                <div id="loading" class="loader"></div>
            </div>
        </div>
    </div>

    <script>
        let jwtToken = null;
        let isSignup = false;

        function toggleAuthMode() {
            isSignup = !isSignup;
            document.getElementById('auth-title').innerText = isSignup ? 'Create an account' : 'Welcome back';
            document.querySelector('.toggle-auth').innerText = isSignup ? 'Already have an account? Log in' : "Don't have an account? Sign up";
        }

        async function handleAuth() {
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const endpoint = isSignup ? '/auth/signup' : '/auth/login';
            
            try {
                const res = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || 'Authentication failed');
                
                jwtToken = data.access_token;
                document.getElementById('auth-section').style.display = 'none';
                document.getElementById('main-section').style.display = 'flex';
                checkGmailStatus();
            } catch (err) {
                document.getElementById('auth-error').innerText = err.message;
            }
        }

        async function checkGmailStatus() {
            try {
                const res = await fetch('/auth/me', { headers: { 'Authorization': 'Bearer ' + jwtToken } });
                const data = await res.json();
                
                if (data.gmail_connected) {
                    document.getElementById('gmail-status-text').innerHTML = '✅ Gmail Connected';
                    document.getElementById('connect-gmail-btn').style.display = 'none';
                } else {
                    document.getElementById('gmail-status-text').innerHTML = '⚠️ Gmail not connected';
                    document.getElementById('connect-gmail-btn').style.display = 'inline-block';
                }
            } catch (err) { console.error(err); }
        }

        async function connectGmail() {
            try {
                const res = await fetch('/gmail/oauth/connect', { headers: { 'Authorization': 'Bearer ' + jwtToken } });
                const data = await res.json();
                window.location.href = data.authorization_url;
            } catch (err) { console.error(err); }
        }

        function formatCitations(text) {
            // Very simple markdown-like citation formatting
            if (text.includes('SOURCES:')) {
                const parts = text.split('SOURCES:');
                return parts[0].replace(/\\n/g, '<br>') + '<div class="citations"><strong>Sources:</strong><br>' + parts[1].replace(/\\n/g, '<br>') + '</div>';
            }
            return text.replace(/\\n/g, '<br>');
        }

        async function sendMessage() {
            const input = document.getElementById('chat-input');
            const message = input.value.trim();
            if (!message) return;
            
            addMessageToUI('user-msg', message);
            input.value = '';
            
            document.getElementById('send-btn').style.display = 'none';
            document.getElementById('loading').style.display = 'block';

            try {
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + jwtToken },
                    body: JSON.stringify({ message })
                });
                
                if (res.ok) {
                    const data = await res.json();
                    addMessageToUI('agent-msg', formatCitations(data.response));
                } else {
                    addMessageToUI('agent-msg', '<span class="error">Failed to get response from agent.</span>');
                }
            } catch (err) {
                addMessageToUI('agent-msg', '<span class="error">Network error.</span>');
            } finally {
                document.getElementById('send-btn').style.display = 'block';
                document.getElementById('loading').style.display = 'none';
            }
        }

        function addMessageToUI(className, htmlContent) {
            const list = document.getElementById('message-list');
            const div = document.createElement('div');
            div.className = 'message ' + className;
            div.innerHTML = htmlContent;
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
from app.agent.graph import run_agent_graph

@router.post("/chat")
def chat_endpoint(payload: ChatRequest, current_user: User = Depends(get_current_user)):
    """Chat endpoint using the LangGraph agent."""
    if not is_career_question(payload.message):
        return {"response": "I can only answer questions related to your career, job applications, or interviews."}

    try:
        state = run_agent_graph(str(current_user.id), payload.message)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Agent failed: {exc}",
        )

    answer = state.get("final_answer") or "Sorry, I couldn't generate a response."

    return {"response": answer}
