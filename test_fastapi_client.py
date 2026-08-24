import traceback
from fastapi.testclient import TestClient
from app.main import app
from app.routers.chat import get_current_user
from app.core.database import SessionLocal
from app.models.user import User

client = TestClient(app)

with SessionLocal() as db:
    user = db.query(User).filter(User.email == "one@gmail.com").first()

def override_get_current_user():
    return user

app.dependency_overrides[get_current_user] = override_get_current_user

print("=== TRIGGERING POST /chat ===")
try:
    response = client.post("/chat", json={"message": "What recent job opportunities did I receive?"})
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Exception caught in TestClient: {e}")
    traceback.print_exc()

