from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    # It redirects to /static/index.html
    assert response.status_code == 200
    assert response.url.path == "/static/index.html"

def test_get_lists():
    response = client.get("/lists/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_analyze_text():
    response = client.post("/lists/analyze", json={"text": "こんにちは", "lang": "jp"})
    assert response.status_code == 200
    data = response.json()
    assert "sentences" in data
    assert len(data["sentences"]) > 0
    # Check that "こんにちは" is recognized
    # Usually sudachipy splits it or treats as one token depending on mode
    # Just checking we got a response is enough for a basic smoke test
