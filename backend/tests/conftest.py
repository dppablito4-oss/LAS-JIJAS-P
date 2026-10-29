import os
import tempfile
from pathlib import Path
import pytest

# Set before importing application modules. Offline tests never touch the personal history.
_test_dir=tempfile.TemporaryDirectory(prefix='las-jijas-tests-')
os.environ['DATABASE_URL']='sqlite:///'+(Path(_test_dir.name)/'test.db').as_posix()
os.environ['APP_MODE']='demo'


@pytest.fixture(autouse=True)
def no_external_ai(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings,'app_mode','demo')
    monkeypatch.setattr(settings,'openai_api_key','')
    monkeypatch.setattr(settings,'deepseek_api_key','')
    monkeypatch.setattr(settings,'ai_profile','hybrid')
    monkeypatch.setattr(settings,'deepseek_model','deepseek-v4-pro')


def pytest_sessionfinish(session,exitstatus):
    from app.db import engine
    engine.dispose()
    _test_dir.cleanup()
