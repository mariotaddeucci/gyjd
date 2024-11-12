import pytest
from gyjd import setup_defaults


@pytest.fixture(scope="function")
def reset_injector():
    setup_defaults(clear_dependencies=True)
