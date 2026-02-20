import pytest


@pytest.fixture(scope="session")
def celery_config():
    return {
        "broker_url": "memory://",
        "result_backend": "cache+memory://",
        "task_always_eager": True,
        "task_eager_propagates": True,
    }


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    pass
