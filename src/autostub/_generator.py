import ast
from typing import Any

import openapi_parser.specification as specification

class _BaseGenerator:
    def __init__(self, spec: Any) -> None:
        pass

    def generate(self) -> ast.AST:
        raise NotImplementedError


class OAPISpecGenerator(_BaseGenerator):
    def __init__(self, spec: specification.Specification) -> None:
        super(OAPISpecGenerator).__init__()


class ServerGenerator(_BaseGenerator):
    def __init__(self, spec: specification.Server) -> None:
        super().__init__()


class PathGenerator(_BaseGenerator):
    def __init__(self, spec: specification.Path) -> None:
        super().__init__()


class GetGenerator(_BaseGenerator):
    def __init__(self, spec: specification.Operation) -> None:
        super().__init__()


class InputValidationGenerator(_BaseGenerator):
    def __init__(self, spec: specification.Parameter) -> None:
        super().__init__()


class ResponseGenerator(_BaseGenerator):
    def __init__(self, spec: specification.Response) -> None:
        super().__init__()
