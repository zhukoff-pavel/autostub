from types import NoneType
from typing import Any
import openapi_parser.specification as spec
import random
import sys
import string

SCHEMA_MAP = {
    spec.Integer: Integer,
    spec.Number: Number,
    spec.String: String,
    spec.Boolean: Boolean,
    spec.Null: Null,
    spec.Array: Array,
    spec.Object: Object,
    spec.OneOf: OneOf,
    spec.AnyOf: AnyOf
}


class GeneratableEntity:
    def __init__(self, spec: spec.Schema) -> None:
        self._spec = spec

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        raise NotImplemented


class Integer(GeneratableEntity):
    def __call__(self, *args: Any, **kwds: Any) -> int:
        return random.randint(
            self._spec.minimum or
            self._spec.exclusive_minimum + 1 or
            -sys.maxsize - 1,
            self._spec.maximum or
            self._spec.exclusive_maximum - 1 or
            sys.maxsize,
        )


class Number(GeneratableEntity):
    def __call__(self, *args: Any, **kwds: Any) -> int:
        return random.uniform(
            self._spec.minimum or
            self._spec.exclusive_minimum + 1 or
            -sys.maxsize - 1,
            self._spec.maximum or
            self._spec.exclusive_maximum - 1 or
            sys.maxsize,
        )


class String(GeneratableEntity):
    def __call__(self, *args: Any, **kwds: Any) -> string:
        # TODO support formats
        allowed_letters = string.ascii_letters + string.digits + ' '
        return ''.join(
            random.choices(
                allowed_letters,
                k = random.randint(
                    self._spec.min_length or 1,
                    self._spec.max_length or 100,
                )
            )
        )


class Boolean(GeneratableEntity):
    def __call__(self, *args: Any, **kwds: Any) -> bool:
        return random.choice([True, False])


class Null(GeneratableEntity):
    def __call__(self, *args: Any, **kwds: Any) -> NoneType:
        return None


class Array(GeneratableEntity):
    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return [
            SCHEMA_MAP[type(self._spec.items)]()() for i in range(
                random.randint(
                    self._spec.min_items or 0,
                    self._spec.max_items or 100,
                )
            )
        ]


class Object(GeneratableEntity):
    def __call__(self, *args: Any, **kwds: Any) -> dict[Any]:
        res = {}

        for property in self._spec.properties:
            if property.name in self._spec.required:
                res[property.name] = SCHEMA_MAP[type(property.schema)](property.schema)()
            else:
                if random.choice([True, False]):
                    res[property.name] = SCHEMA_MAP[type(property.schema)](property.schema)()

        return res


class OneOf(GeneratableEntity):
    def __call__(self, *args: Any, **kwds: Any) -> Any:
        raise NotImplementedError


class AnyOf(GeneratableEntity):
    def __call__(self, *args: Any, **kwds: Any) -> Any:
        schema = random.choice(self._spec.schemas)
        return SCHEMA_MAP[
            type(schema)
        ](schema)()
