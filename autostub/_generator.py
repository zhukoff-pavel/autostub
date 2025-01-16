from typing import Any, Optional
import random
import urllib.parse

import http
import openapi_parser.specification as specification
import frozendict

from autostub._cache import BaseCache, NO_CACHE
from autostub._schemas import SCHEMA_MAP
from autostub._response import JsonHTTPResponse, _BaseHTTPResponse
from autostub._request import Request


class _BaseEntity:
    def __init__(self, spec: Any, cache: BaseCache) -> None:
        self._spec = spec
        self._cache = cache

    def __call__(self, request: Request) -> Optional[_BaseHTTPResponse]:
        raise NotImplementedError

    def _validate_call(self, request: Request) -> bool:
        raise NotImplementedError


class OAPISpec(_BaseEntity):
    # Check if suitable server exists in spec.
    # Route to path if any is available
    def __init__(self, spec: specification.Specification, cache: BaseCache) -> None:
        super().__init__(spec, cache)
        self._cache = cache
        self._paths = {i.url: Path(i, cache) for i in spec.paths}

        self._servers = [i.url for i in spec.servers]
        self._models = spec.schemas

    def _compare_and_parse_paths(
        self, p_requested: str, p_internal: str
    ) -> Optional[frozendict.frozendict[str, str]]:
        split_requested_path = p_requested.split("/")
        split_internal_path = p_internal.split("/")

        result = {}

        if len(split_internal_path) != len(split_requested_path):
            return None

        for i in range(len(split_requested_path)):
            if split_requested_path[i] != split_internal_path[i]:
                if split_internal_path[i].startswith("{") and split_internal_path[
                    i
                ].endswith("}"):
                    param_name = split_internal_path[i][1:-1]
                    result[param_name] = split_requested_path[i]
                    continue

                return None
        return frozendict.frozendict(result)

    def _get_path_candidates(self, url: str) -> list[str]:
        res = []
        for serv_url in self._servers:
            if url.startswith(serv_url):
                res.append(url[len(serv_url) :])
        return res

    def _get_valid_paths(self, url: str) -> list[str]:
        candidates = self._get_path_candidates(url)
        result = []

        for path in candidates:
            path = urllib.parse.urlparse(path).path

            for internal_path in self._paths:
                if self._compare_and_parse_paths(path, internal_path) is not None:
                    result.append((path, internal_path))

        return result

    def _validate_call(self, request: Request) -> bool:
        if not any([request.url.startswith(i) for i in self._servers]):
            return False

        if not self._get_valid_paths(request.url):
            return False

        return True

    def __call__(self, request: Request) -> _BaseHTTPResponse | None:
        if not self._validate_call(request):
            return None

        responses = []

        for path, ipath in self._get_valid_paths(request.url):
            # TODO use candidates function
            request.path_params = self._compare_and_parse_paths(path, ipath)
            response = self._paths[ipath](request)
            if response is not None:
                responses.append(response)

        if responses:
            return random.choice(responses)
        else:
            # Send default 404 answer
            return None


class Path(_BaseEntity):
    # Check if specific method of this path exists.
    def __init__(self, spec: specification.Path, cache: BaseCache) -> None:
        super().__init__(spec, cache)

        self._ops = {}
        for item in spec.operations:
            if item.method == specification.OperationMethod.GET:
                self._ops["get"] = Get(item, cache)

    def _validate_call(self, request: Request) -> bool:
        return request.method in self._ops

    def __call__(self, request: Request) -> _BaseHTTPResponse | None:
        if self._validate_call(request):
            return self._ops[request.method](request)

        return None


class Get(_BaseEntity):
    # Check parameters in query (i.e ?param1=foo&param2=bar)
    def __init__(self, spec: specification.Operation, cache: BaseCache) -> None:
        super().__init__(spec, cache)
        self._responses = []
        self._default_response = None
        self._parameters = {}
        self._required = set()
        for param in spec.parameters:
            if param.location in {
                specification.ParameterLocation.QUERY,
                specification.ParameterLocation.PATH,
            }:
                self._parameters[param.name] = SCHEMA_MAP[type(param.schema)](
                    param.schema, param.name
                )
                if param.required:
                    self._required.add(param.name)

        for resp in spec.responses:
            if not (isinstance(resp.content, list) and len(resp.content) == 1):
                continue

            obj = None
            if resp.content[0].type == specification.ContentType.JSON:
                obj = JSONResponse(resp, cache)

            if obj is None:
                continue

            if resp.is_default:
                self._default_response = obj
            else:
                self._responses.append(obj)

    def _get_query_params(self, request: Request) -> frozendict.frozendict[str, str]:
        parsed_url = urllib.parse.urlparse(request.url)

        query_params = dict(urllib.parse.parse_qsl(parsed_url.query))

        query_params.update(request.path_params or {})
        query_params.update(request.parameters or {})

        return frozendict.frozendict(query_params)

    def _transform_parameters(
        self, q_params: frozendict.frozendict[str, str]
    ) -> frozendict.frozendict[str, Any]:
        result = {}
        for name, val in q_params.items():
            if name in self._parameters:
                result[name] = self._parameters[name].from_val(val)
            else:
                result[name] = val
        return frozendict.frozendict(result)

    def _validate_call(self, request: Request) -> bool:
        query_params = self._get_query_params(request)

        if self._required & set(query_params.keys()) != self._required:
            return False

        for name, val in query_params.items():
            if name in self._parameters:
                if not self._parameters[name].is_valid(val):
                    return False

        return True

    def __call__(self, request: Request) -> _BaseHTTPResponse | None:
        # TODO send a default response if whatever goes wrong, and a random other if anything is ok
        response = None
        if self._validate_call(request):
            response = random.choice(self._responses)
        else:
            if not self._default_response:
                return None
            return self._default_response(request)

        request.query_params = self._transform_parameters(
            self._get_query_params(request)
        )
        return response(request)


class JSONResponse(_BaseEntity):
    def __init__(self, spec: specification.Response, cache: BaseCache) -> None:
        super().__init__(spec, cache)

    def __call__(self, request: Request) -> JsonHTTPResponse:
        res = JsonHTTPResponse()
        res.status_code = self._spec.code or http.HTTPStatus.NOT_FOUND.value

        cont: specification.Content = self._spec.content[0]

        assert cont.type == specification.ContentType.JSON

        data = SCHEMA_MAP[type(cont.schema)](cont.schema)(request, self._cache)

        res.content = data

        for header in self._spec.headers:
            if random.choice([True, header.required]):
                res.headers[header.name] = SCHEMA_MAP[type(header.schema)](
                    header.schema, header.name
                )(request, NO_CACHE)

        return res
