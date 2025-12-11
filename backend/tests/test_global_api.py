"""
Tests for Global API endpoints
"""
import pytest
import io
import numpy as np
import cv2
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.api import global_mode


client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_controllers():
    """Clear controllers before and after each test"""
    global_mode._controllers.clear()
    yield
    global_mode._controllers.clear()


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_start_session_testing_mode():
    """Test starting a session in testing mode"""
    response = client.post(
        "/api/global/test_session_1/start",
        data={"mode": "testing"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["session_id"] == "test_session_1"
    assert data["mode"] == "testing"


def test_start_session_practising_mode():
    """Test starting a session in practising mode"""
    response = client.post(
        "/api/global/test_session_2/start",
        data={"mode": "practising"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["session_id"] == "test_session_2"
    assert data["mode"] == "practising"


def test_start_session_invalid_mode():
    """Test starting a session with invalid mode"""
    response = client.post(
        "/api/global/test_session_3/start",
        data={"mode": "invalid_mode"}
    )
    
    assert response.status_code == 422
    assert "detail" in response.json()


def test_start_session_duplicate():
    """Test starting a session that already exists"""
    # Create first session
    client.post(
        "/api/global/test_session_4/start",
        data={"mode": "testing"}
    )
    
    # Try to create duplicate
    response = client.post(
        "/api/global/test_session_4/start",
        data={"mode": "testing"}
    )
    
    assert response.status_code == 422
    assert "đã tồn tại" in response.json()["detail"]


def test_process_frame():
    """Test processing a frame"""
    # Start session
    client.post(
        "/api/global/test_session_5/start",
        data={"mode": "testing"}
    )
    
    # Create a dummy frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    _, buffer = cv2.imencode('.jpg', frame)
    frame_bytes = io.BytesIO(buffer.tobytes())
    
    # Process frame
    response = client.post(
        "/api/global/test_session_5/process-frame",
        files={"frame_data": ("frame.jpg", frame_bytes, "image/jpeg")},
        data={
            "timestamp": 0.1,
            "frame_number": 1
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["timestamp"] == 0.1
    assert data["frame_number"] == 1
    assert "score" in data
    assert "errors" in data


def test_process_frame_nonexistent_session():
    """Test processing a frame for nonexistent session"""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    _, buffer = cv2.imencode('.jpg', frame)
    frame_bytes = io.BytesIO(buffer.tobytes())
    
    response = client.post(
        "/api/global/nonexistent/process-frame",
        files={"frame_data": ("frame.jpg", frame_bytes, "image/jpeg")},
        data={
            "timestamp": 0.1,
            "frame_number": 1
        }
    )
    
    assert response.status_code == 404


def test_get_score():
    """Test getting score"""
    # Start session
    client.post(
        "/api/global/test_session_6/start",
        data={"mode": "testing"}
    )
    
    # Get score
    response = client.get("/api/global/test_session_6/score")
    
    assert response.status_code == 200
    data = response.json()
    assert "score" in data
    assert data["score"] == 100.0  # Initial score
    assert data["session_id"] == "test_session_6"


def test_get_score_nonexistent_session():
    """Test getting score for nonexistent session"""
    response = client.get("/api/global/nonexistent/score")
    assert response.status_code == 404


def test_get_errors():
    """Test getting errors"""
    # Start session
    client.post(
        "/api/global/test_session_7/start",
        data={"mode": "testing"}
    )
    
    # Get errors
    response = client.get("/api/global/test_session_7/errors")
    
    assert response.status_code == 200
    data = response.json()
    assert "errors" in data
    assert "total_errors" in data
    assert data["total_errors"] == 0  # No errors initially
    assert data["session_id"] == "test_session_7"


def test_reset_session():
    """Test resetting a session"""
    # Start session
    client.post(
        "/api/global/test_session_8/start",
        data={"mode": "testing"}
    )
    
    # Reset session
    response = client.post("/api/global/test_session_8/reset")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["session_id"] == "test_session_8"


def test_reset_nonexistent_session():
    """Test resetting nonexistent session"""
    response = client.post("/api/global/nonexistent/reset")
    assert response.status_code == 404


def test_delete_session():
    """Test deleting a session"""
    # Start session
    client.post(
        "/api/global/test_session_9/start",
        data={"mode": "testing"}
    )
    
    # Verify session exists
    assert "test_session_9" in global_mode._controllers
    
    # Delete session
    response = client.delete("/api/global/test_session_9")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["session_id"] == "test_session_9"
    
    # Verify session is deleted
    assert "test_session_9" not in global_mode._controllers


def test_delete_nonexistent_session():
    """Test deleting nonexistent session"""
    response = client.delete("/api/global/nonexistent")
    assert response.status_code == 404


def test_session_lifecycle():
    """Test complete session lifecycle"""
    session_id = "test_lifecycle"
    
    # 1. Start session
    response = client.post(
        f"/api/global/{session_id}/start",
        data={"mode": "testing"}
    )
    assert response.status_code == 200
    
    # 2. Get initial score
    response = client.get(f"/api/global/{session_id}/score")
    assert response.status_code == 200
    assert response.json()["score"] == 100.0
    
    # 3. Get initial errors
    response = client.get(f"/api/global/{session_id}/errors")
    assert response.status_code == 200
    assert response.json()["total_errors"] == 0
    
    # 4. Reset session
    response = client.post(f"/api/global/{session_id}/reset")
    assert response.status_code == 200
    
    # 5. Delete session
    response = client.delete(f"/api/global/{session_id}")
    assert response.status_code == 200
    
    # 6. Verify session is gone
    response = client.get(f"/api/global/{session_id}/score")
    assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
