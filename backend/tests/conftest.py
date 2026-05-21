import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.user import UserInfo
from app.models.prompt_version import PromptVersion

@pytest.fixture(autouse=True)
def clear_users():
    db = SessionLocal()
    # Full cleanup for deterministic tests.
    db.query(PromptVersion).delete(synchronize_session=False)
    db.query(UserInfo).delete(synchronize_session=False)
    db.commit()
    db.close()
    yield
    db = SessionLocal()
    db.query(PromptVersion).delete(synchronize_session=False)
    db.query(UserInfo).delete(synchronize_session=False)
    db.commit()
    db.close()

@pytest.fixture
def client():
    return TestClient(app)
