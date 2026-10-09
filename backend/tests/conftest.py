import os
import tempfile

# DB temporal antes de importar la app
os.environ["DB_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["MODE"] = "local"

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _db():
    from app.db.session import init_db

    init_db()
