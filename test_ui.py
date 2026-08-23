from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=True)
try:
    response = client.get("/cold_email/ui")
    print(response.status_code)
except Exception as e:
    import traceback
    traceback.print_exc()
