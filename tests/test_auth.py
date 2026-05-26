from fastapi.testclient import TestClient

from app.api.auth import router as auth_router
from app.auth.jwt import create_token
from app.auth.security import hash_password
from app.db.models import User
from app.db.session import get_db
from fastapi import FastAPI


class _FakeQuery:
    def __init__(self, user):
        self.user = user

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.user


class _FakeDB:
    def __init__(self):
        self.user = User(username="demo", password_hash=hash_password("demo123"))

    def query(self, _model):
        return _FakeQuery(self.user)

    def add(self, user):
        self.user = user

    def commit(self):
        return None


def _client():
    app = FastAPI()
    app.include_router(auth_router)
    fake_db = _FakeDB()
    app.dependency_overrides[get_db] = lambda: fake_db
    return TestClient(app)


def test_login_returns_jwt():
    client = _client()
    response = client.post("/api/v1/login", json={"username": "demo", "password": "demo123"})
    assert response.status_code == 200
    body = response.json()
    assert body["token"]
    assert body["user_id"] == "demo"


def test_create_token_has_user_id_claim():
    token = create_token("demo")
    assert isinstance(token, str)
    assert token.count(".") == 2

