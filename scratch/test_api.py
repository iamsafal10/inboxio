import requests

url = "http://127.0.0.1:8000/chat"
payload = {
    "question": "What recent job opportunities did I receive?",
    "chat_history": []
}
# Need to authenticate or provide user_id? 
# Usually auth is handled via headers or cookies if the endpoint expects it.
# Let's see the routers/chat.py
