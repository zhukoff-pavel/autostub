from typing import Any
from autostub._generator import OAPISpec
import openapi_parser as oapi_parser

import requests
import pytest
import pytest_mock


class AutoStub:
    def __init__(self, config: Any) -> None:
        self._servers = {}
        self._config = config
        self._mock = None
        self._mocker = pytest_mock.MockFixture(self._config)

    def request(self, *args, **kwargs):
        r = None
        for s in self._servers.values():
            r = s(*args, **kwargs)
            if r is not None:
                return r

        return requests.request(*args, **kwargs)

    def _stop_mock_if_needed(self):
        if self._mock is not None:
            self._mocker.stop(self._mock)
            self._mock = None

    def _create_mock(self):
        self._stop_mock_if_needed()
        self._mock = self._mocker.patch("requests.api.request", new=self.request)
        return self._mock

    def stub(self, oapi_spec: str) -> None:
        """
        Generate requests.get stub and patch the function
        """
        self._servers[oapi_spec] = OAPISpec(oapi_parser.parse(oapi_spec))
        return self._create_mock()

    def unstub(self, oapi_spec: str):
        self._servers.pop(oapi_spec, None)
        return self._create_mock()

    def stop(self):
        self._mocker.stopall()


def _autostub(pytestconfig: Any):
    result = AutoStub(config=pytestconfig)
    yield result
    result.stop()


autostub = pytest.fixture()(_autostub)