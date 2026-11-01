import pytest
from fastapi.testclient import TestClient

from ai_service.app import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c
