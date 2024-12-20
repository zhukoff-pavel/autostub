from typing import Any
import importlib
import collections

from autostub._generator import OAPISpec
from autostub._cache import CachingLevel, CacheFactory
import openapi_parser as oapi_parser

import pytest
import pytest_mock


SUPPORTED_MODULES = {"requests": "autostub.adapters.requests"}


class AutoStub:
    def __init__(self, config: Any) -> None:
        self._servers: collections.defaultdict[str, dict[str, OAPISpec]] = (
            collections.defaultdict(dict)
        )
        self._config = config
        self._mock: dict[str, pytest_mock.MockType | None] = {}
        self._mocker = pytest_mock.MockFixture(self._config)

        self.adapters_map = self._get_adapter_map()

    @staticmethod
    def _get_adapter_map():
        a_map = {}
        for m_name, path in SUPPORTED_MODULES.items():
            try:
                module = importlib.import_module(path)
                adapter = getattr(module, "ADAPTER_MAP")
            except ImportError:
                continue
            else:
                a_map[m_name] = adapter
        return a_map

    def _stop_mock_if_needed(self, module):
        if self._mock.get(module):
            self._mocker.stop(self._mock[module])
            self._mock[module] = None

    def _generate_mock(self, module, source_mock):
        def func(*args, **kwargs):
            return source_mock(self._servers[module], *args, **kwargs)

        return func

    def _create_mock(self, module: str | None = None):
        self._stop_mock_if_needed(module)
        if module:
            replace_name = self.adapters_map[module]["replace_name"]
            replace_with = self._generate_mock(
                module, self.adapters_map[module]["replace_with"]
            )
            self._mock[module] = self._mocker.patch(replace_name, new=replace_with)
        return self._mock

    def stub(self, oapi_spec: str, module: str, caching_level: CachingLevel):
        """
        Generate requests.get stub and patch the function
        """
        spec = oapi_parser.parse(oapi_spec)
        self._servers[module][oapi_spec] = OAPISpec(
            spec, CacheFactory.get_cache(caching_level, spec.schemas)
        )
        return self._create_mock(module)

    def unstub(self, oapi_spec: str, module):
        self._servers[module].pop(oapi_spec, None)
        return self._create_mock(module)

    def stop(self):
        self._mocker.stopall()


def _autostub(pytestconfig: Any):
    result = AutoStub(config=pytestconfig)
    yield result
    result.stop()


autostub = pytest.fixture()(_autostub)
