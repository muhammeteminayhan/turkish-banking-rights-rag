from collections.abc import Callable
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def mevzuat_fixture() -> Callable[[str], bytes]:
    def _read(name: str) -> bytes:
        return (FIXTURES / "mevzuat" / name).read_bytes()

    return _read
