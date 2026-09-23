import os

os.environ["USE_MOCKS"] = "true"  # tests never call a real LLM

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.state import store

HR = {"X-Role": "hr"}


@pytest.fixture()
def client():
    store.reset()
    yield TestClient(app)
    store.reset()
