import dataclasses
import http


@dataclasses.dataclass
class _BaseHTTPResponse:
    status_code: int = http.HTTPStatus.NOT_FOUND.value
    content: str | bytes = ""
    content_type: str | None = None
    headers: dict[str, str] = dataclasses.field(default_factory=dict)
    encoding: str | None = "utf-8"


class JsonHTTPResponse(_BaseHTTPResponse):
    content_type = "application/json"
    content: dict[str, str] = dataclasses.field(default_factory=dict)
