from typing import Any, Optional
import io
import json
import random

from requests import Response
import openapi_parser.specification as specification

from ._schemas import SCHEMA_MAP


class _BaseEntity:
    def __init__(self, spec: Any) -> None:
        self._spec = spec
        pass

    def __call__(self, method: str, url: str , **kwds: Any) -> Optional[Response]:
        raise NotImplementedError


class OAPISpec(_BaseEntity):
    def __init__(self, spec: specification.Specification) -> None:
        super(OAPISpec).__init__(spec)

    def __call__(self, method: str, url: str, **kwds: Any) -> Optional[Response]:
        return super().__call__(method, url, **kwds)


class Server(_BaseEntity):
    def __init__(self, spec: specification.Server) -> None:
        super().__init__(spec)

    def __call__(self, method: str, url: str, **kwds: Any) -> Optional[Response]:
        return super().__call__(method, url, **kwds)


class Path(_BaseEntity):
    def __init__(self, spec: specification.Path) -> None:
        super().__init__(spec)

    def __call__(self, method: str, url: str, **kwds: Any) -> Optional[Response]:
        return super().__call__(method, url, **kwds)


class Get(_BaseEntity):
    def __init__(self, spec: specification.Operation) -> None:
        super().__init__(spec)

    def __call__(self, method: str, url: str, **kwds: Any) -> Optional[Response]:
        assert method == "get"
        return super().__call__(method, url, **kwds)


class InputValidation(_BaseEntity):
    def __init__(self, spec: specification.Parameter) -> None:
        super().__init__(spec)

    def __call__(self, method: str, url: str, **kwds: Any) -> Optional[Response]:
        return super().__call__(method, url, **kwds)


class JSONResponse(_BaseEntity):
    def __init__(self, spec: specification.Response) -> None:
        super().__init__(spec)

    def __call__(self, method: str, url: str, **kwds: Any) -> Optional[Response]:
        res = Response()
        res.status_code = self._spec.code or 504

        cont = self._spec.content

        assert cont.type == 'application/json'

        data = SCHEMA_MAP[type(cont.schema)](cont.schema)()

        res.raw = io.StringIO(json.dumps(data))

        for header in self._spec.headers:
            if random.choice([True, header.required]):
                res.headers[header.name] = SCHEMA_MAP[type(header.schema)](header.schema)()
