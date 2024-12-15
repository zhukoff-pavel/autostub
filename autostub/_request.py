import dataclasses
from frozendict import frozendict


@dataclasses.dataclass(unsafe_hash=True)
class Request:
    url: str
    method: str
    data: frozendict[str, str]
    parameters: frozendict[str, str]
    headers: frozendict[str, str]
    path_params: frozendict[str, str] = frozendict()
    query_params: frozendict[str, str] = frozendict()
