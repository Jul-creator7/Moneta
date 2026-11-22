from pathlib import Path
from secrets import token_hex

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.attributes["database_url"] = url
    command.upgrade(config, "head")
    with TestClient(create_app(Settings(database_url=url, jwt_secret=token_hex(32)))) as test_client:
        yield test_client
