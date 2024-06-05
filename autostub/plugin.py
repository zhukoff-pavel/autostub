from typing import Any

import pytest


class AutoStub:
    def __init__(self, config: Any) -> None:
        pass

    def generate_and_patch(oapi_spec: str) -> None:
        """
        Generate requests.get stub and patch the function
        """
        pass


def _autostub(pytestconfig: Any):
    result = AutoStub(config=pytestconfig)
    yield result


autostub = pytest.fixture()(_autostub)