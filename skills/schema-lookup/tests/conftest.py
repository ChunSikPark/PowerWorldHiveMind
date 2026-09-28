import sys
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE))


@pytest.fixture(scope="session")
def fields():
    import schema
    return schema.load_fields()
