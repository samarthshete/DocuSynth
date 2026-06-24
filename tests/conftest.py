import pathlib
import sys
import types

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

from app.auth.jwt import get_current_user
from app.db.session import get_db
from app.main import app


class FakeDB:
    def __init__(self):
        self.items = []

    def add(self, item):
        self.items.append(item)

    def commit(self):
        return None

    def rollback(self):
        return None

    def query(self, _model):
        return self

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return None

    def execute(self, *_args, **_kwargs):
        class _ExecResult:
            def scalars(self):
                return self

            def first(self):
                return None

        return _ExecResult()


@pytest.fixture
def client():
    app.router.on_startup.clear()
    app.dependency_overrides[get_db] = lambda: FakeDB()
    app.dependency_overrides[get_current_user] = lambda: types.SimpleNamespace(username="demo")
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

