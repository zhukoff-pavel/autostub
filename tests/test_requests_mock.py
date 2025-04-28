import pathlib
import pytest
import requests
import io

import autostub._cache as cache
from autostub.plugin import AutoStub


@pytest.fixture
def data_dir():
    res = pathlib.Path(__file__).resolve().parent / "data"
    assert res.exists()

    return res


def get_bad_response():
    r = requests.Response()

    r.status_code = 404
    r.raw = io.BytesIO(b"Tried to go to internet")
    return r


@pytest.mark.parametrize(
    "cache_level", [i for i in cache.CachingLevel]
)
def test_requests_mock(data_dir, cache_level):
    plugin = AutoStub(config=None)

    plugin.stub(
        oapi_spec=str(data_dir / "oapi_spec.yaml"),
        module="requests",
        caching_level=cache_level,
    )

    result = requests.get(url="http://petstore.swagger.io/v1/pets/1")

    assert result.ok

    item = result.json()
    assert "id" in item
    assert item["id"] == 1


@pytest.mark.parametrize(
    "cache_level", [i for i in cache.CachingLevel]
)
def test_requests_mock_fallback(mocker, data_dir, cache_level):
    mock = mocker.patch("requests.request", return_value=get_bad_response())

    plugin = AutoStub(config=None)

    plugin.stub(
        oapi_spec=str(data_dir / "oapi_spec.yaml"),
        module="requests",
        caching_level=cache_level,
    )

    result = requests.get(url="http://petstore.swagger.io/v1/not_pets/1")

    assert not result.ok
    assert "Tried to go to internet" in result.text
    mock.assert_called_once_with(
        "get", "http://petstore.swagger.io/v1/not_pets/1", params=None
    )
