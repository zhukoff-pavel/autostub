import typing as tp

from autostub._response import _BaseHTTPResponse
from autostub._request import Request


class BaseAdapter:
    def __init__(self):
        pass

    @staticmethod
    def from_response(resp: _BaseHTTPResponse) -> tp.Any:
        raise NotImplementedError

    @staticmethod
    def to_request(*args, **kwargs) -> Request:
        raise NotImplementedError

    @classmethod
    def mock(cls, servers, *args, **kwargs) -> tp.Any:
        response = None
        request = cls.to_request(*args, **kwargs)
        for s in servers.values():
            response = s(request)
            print(response)
            if response is not None:
                return cls.from_response(response)
