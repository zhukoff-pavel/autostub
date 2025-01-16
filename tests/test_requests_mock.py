import pathlib
import requests
import io

import autostub._cache as cache
from autostub.plugin import AutoStub

TEST_DATA_DIR = pathlib.Path(__file__).resolve().parent / "data"


def get_bad_response():
    r = requests.Response()

    r.status_code = 404
    r.raw = io.BytesIO(b"Tried to go to internet")
    return r


def test_requests_mock():
    plugin = AutoStub(config=None)

    plugin.stub(
        oapi_spec=str(TEST_DATA_DIR / "oapi_spec.yaml"),
        module="requests",
        caching_level=cache.CachingLevel.NONE,
    )

    result = requests.get(url="http://petstore.swagger.io/v1/pets/1")

    assert result.ok

    item = result.json()
    assert "id" in item
    assert item["id"] == 1


def test_requests_mock_fallback(mocker):
    mock = mocker.patch("requests.request", return_value=get_bad_response())

    plugin = AutoStub(config=None)

    plugin.stub(
        oapi_spec=str(TEST_DATA_DIR / "oapi_spec.yaml"),
        module="requests",
        caching_level=cache.CachingLevel.NONE,
    )

    result = requests.get(url="http://petstore.swagger.io/v1/not_pets/1")

    assert not result.ok
    assert "Tried to go to internet" in result.text
    mock.assert_called_once_with(
        "get", "http://petstore.swagger.io/v1/not_pets/1", params=None
    )
