from autostub.adapters import requests as requests_adapter
from autostub._response import JsonHTTPResponse

import requests
import pytest


class MockServer:
    def __init__(self, return_object=False):
        self.return_object = return_object

    def __call__(self, *args, **kwds):
        if not self.return_object:
            return None

        return JsonHTTPResponse(
            status_code=200,
            content={},
            content_type='application/json',
        )


@pytest.mark.parametrize(
    'servers',
    [
        {},
        {'https://example.com': MockServer(return_object=False)},
    ]
)
def test_requests_adapter_no_suitable_servers(mocker, servers):
    get_mock = mocker.patch.object(requests, 'request', autospec=True)

    adapter = requests_adapter.RequestsAdapter()

    adapter.mock(servers, 'get', 'https://example.com')

    get_mock.assert_called_once_with(
        'get',
        'https://example.com',
    )


@pytest.mark.parametrize(
    'servers',
    [
        {'https://example.com': MockServer(return_object=True)},
    ]
)
def test_requests_adapter_suitable_servers(mocker, servers):
    get_mock = mocker.patch.object(requests, 'request', autospec=True)

    adapter = requests_adapter.RequestsAdapter()

    response = adapter.mock(servers, 'get', 'https://example.com')

    assert get_mock.call_count == 0
    assert response is not None
    assert isinstance(response, requests.Response)
    assert response.ok
    assert response.content == b'{}'
