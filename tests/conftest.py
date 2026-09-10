import pytest
from pydantic import SecretStr

from living_memory.config import Settings


@pytest.fixture
def settings():
    return Settings(_env_file=None, session_secret=SecretStr("test-secret-" * 4))
