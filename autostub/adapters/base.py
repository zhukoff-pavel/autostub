import typing as tp

from autostub._response import _BaseHTTPResponse


class BaseAdapter:
    def __init__(self):
        pass

    @staticmethod
    def from_response(resp: _BaseHTTPResponse) -> tp.Any:
        raise NotImplementedError

    @staticmethod
    def mock(servers, *args, **kwargs) -> tp.Any:
        raise NotImplementedError
