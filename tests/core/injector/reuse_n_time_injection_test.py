from dataclasses import dataclass, field
from uuid import uuid4

from gyjd import gyjd


@dataclass
class MockConfig:
    mock_id: str = field(default_factory=lambda: str(uuid4()))


def gen_mock() -> MockConfig:
    return MockConfig()


@gyjd
def get_mock(mock: MockConfig = None) -> str:
    for _ in range(10):
        # Ensure that instance is reused on each attribute access
        mock.mock_id

    return mock.mock_id


def test_reuse_25_times_injection():
    gyjd.register_dependency(gen_mock, reuse_times=25)

    assert len(set([get_mock() for _ in range(100)])) == 4


def test_reuse_10_times_injection():
    gyjd.register_dependency(gen_mock, reuse_times=10)

    assert len(set([get_mock() for _ in range(100)])) == 10


def test_reuse_05_times_injection():
    gyjd.register_dependency(gen_mock, reuse_times=5)

    assert len(set([get_mock() for _ in range(100)])) == 20
