import io
import json

import requests
import frozendict

from autostub._request import Request
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

        for k, v in resp.headers.items():
            r.headers[k] = v

        return r

    @staticmethod
    def to_request(*args, **kwargs) -> Request:
        method = kwargs.get("method") or args[0]
        url = (kwargs.get("url") or args[1]).lower()
        params = frozendict.frozendict(kwargs.get("params", {}))
        body = frozendict.frozendict(kwargs.get("data", {}))
        headers = frozendict.frozendict(kwargs.get("headers", {}))
        return Request(url, method, body, params, headers)

    @classmethod
    def mock(cls, servers, *args, **kwargs) -> requests.Response:
        inner_result = super().mock(servers, *args, **kwargs)
        if inner_result:
            return inner_result

        return requests.request(*args, **kwargs)


ADAPTER_MAP = {
    "replace_name": "requests.api.requests",  # XXX
    "replace_with": RequestsAdapter.mock,
}
