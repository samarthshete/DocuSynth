from io import BytesIO

import app.api.documents as documents_api
import httpx


class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {
            "doc_id": "doc-1",
            "chunk_count": 3,
            "metadata": {"page_count": 2},
            "message": "ok",
        }

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://python-rag:8000/ingest")
            raise httpx.HTTPStatusError("mock error", request=request, response=None)
        return None

    def json(self):
        return self._payload


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, *, files=None, data=None, headers=None):
        assert url.endswith("/ingest")
        assert files is not None and "file" in files
        assert data is not None and "doc_id" in data
        return _FakeResponse()


def test_ingest_accepts_pdf(client, monkeypatch):
    monkeypatch.setattr(documents_api.httpx, "AsyncClient", _FakeAsyncClient)
    response = client.post(
        "/api/v1/ingest",
        files={"file": ("sample.pdf", BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["chunk_count"] == 3

