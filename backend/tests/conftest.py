import os
import tempfile
from pathlib import Path

# Set before importing application modules. Offline tests never touch the personal history.
_test_dir=tempfile.TemporaryDirectory(prefix='las-jijas-tests-')
os.environ['DATABASE_URL']='sqlite:///'+(Path(_test_dir.name)/'test.db').as_posix()
os.environ['APP_MODE']='demo'


def pytest_sessionfinish(session,exitstatus):
    from app.db import engine
    engine.dispose()
    _test_dir.cleanup()
