import io
import json

import requests
from .base import BaseAdapter
from autostub._response import _BaseHTTPResponse


class RequestsAdapter(BaseAdapter):
    def __init__(self):
        super().__init__()

    @staticmethod
    def from_response(resp: _BaseHTTPResponse) -> requests.Response:
        r = requests.Response()

        r.status_code = resp.status_code
        r.raw = io.BytesIO(json.dumps(resp.content).encode())

        for k, v in resp.headers:
            r.headers[k] = v

        return r

    @staticmethod
    def mock(servers, *args, **kwargs) -> requests.Response:
        r = None
        for s in servers.values():
            r = s(*args, **kwargs)
            if r is not None:
                return RequestsAdapter.from_response(r)

        return requests.request(*args, **kwargs)


ADAPTER_MAP = {
    'replace_name': 'requests.api.requests',  # XXX
    'replace_with': RequestsAdapter.mock,
}