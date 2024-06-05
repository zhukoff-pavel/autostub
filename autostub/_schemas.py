from types import NoneType
from typing import Any
import openapi_parser.specification as spec
import random
import sys
import string


class GeneratableEntity:
    def __init__(self, spec: spec.Schema) -> None:
        self._spec = spec

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        raise NotImplementedError

    def is_valid(self, item: Any) -> bool:
        raise NotImplementedError


class Integer(GeneratableEntity):
    def __init__(self, spec: spec.Integer) -> NoneType:
        super().__init__(spec)
        if self._spec.minimum is not None:
            self._lower_bound = self._spec.minimum
        elif self._spec.exclusive_minimum is not None:
            self._lower_bound = self._spec.exclusive_minimum + 1
        else:
            self._lower_bound = -sys.maxsize - 1

        if self._spec.maximum is not None:
            self._upper_bound = self._spec.maximum
        elif self._spec.exclusive_maximum is not None:
            self._upper_bound = self._spec.exclusive_maximum + 1
        else:
            self._upper_bound = sys.maxsize

    def __call__(self, *args: Any, **kwds: Any) -> int:
        return random.randint(
            self._lower_bound,
            self._upper_bound,
        )

    def is_valid(self, item: int) -> bool:
        try:
            item = int(item)
        except ValueError:
            return False
        return self._lower_bound <= item <= self._upper_bound


class Number(Integer):
    def __call__(self, *args: Any, **kwds: Any) -> int:
        return random.uniform(
            self._lower_bound,
            self._upper_bound,
        )

    def is_valid(self, item: str) -> bool:
        try:
            item = float(item)
        except ValueError:
            return False
        return self._lower_bound <= item <= self._upper_bound


class String(GeneratableEntity):
    def __init__(self, spec: spec.String) -> NoneType:
        super().__init__(spec)
        self._lower_bound = self._spec.min_length or 1
        self._upper_bound = self._spec.max_length or 100

    def __call__(self, *args: Any, **kwds: Any) -> string:
        # TODO support formats
        allowed_letters = string.ascii_letters + string.digits + ' '
        return ''.join(
            random.choices(
                allowed_letters,
                k=random.randint(
                    self._lower_bound,
                    self._upper_bound,
                )
            )
        )

    def is_valid(self, item: str) -> bool:
        # TODO support formats
        if not isinstance(item, str):
            return False
        return self._lower_bound <= len(item) <= self._upper_bound


class Boolean(GeneratableEntity):
    def __call__(self, *args: Any, **kwds: Any) -> bool:
        return random.choice([True, False])

    def is_valid(self, item: bool) -> bool:
        return item in [True, False]


class Null(GeneratableEntity):
    def __call__(self, *args: Any, **kwds: Any) -> NoneType:
        return None

    def is_valid(self, item: NoneType) -> bool:
        return item is None


class Array(GeneratableEntity):
    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return [
            SCHEMA_MAP[type(self._spec.items)](self._spec.items)() for i in range(
                random.randint(
                    self._spec.min_items or 0,
                    self._spec.max_items or 100,
                )
            )
        ]

    def is_valid(self, item: list[Any]) -> bool:
        return all([isinstance(x, self._spec.items) for x in item])


class Object(GeneratableEntity):
    def __init__(self, spec: spec.Object) -> NoneType:
        super().__init__(spec)
        self.properties = {}
        self.required = set(spec.required)
        for prop in spec.properties:
            self.properties[prop.name] = SCHEMA_MAP[type(prop.schema)](prop.schema)

    def __call__(self, *args: Any, **kwds: Any) -> dict[Any]:
        res = {}

        for prop in self.properties:
            if prop in self.required or random.choice([True, False]):
                res[prop] = self.properties[prop]()

        return res

    def is_valid(self, item: dict) -> bool:
        object_keys = set(item.keys())

        if object_keys & self.required != self.required:
            return False

        res = True

        for key in item:
            res &= self.properties[key].is_valid(item[key])

        return res


class OneOf(GeneratableEntity):
    def __call__(self, *args: Any, **kwds: Any) -> Any:
        raise NotImplementedError


class AnyOf(GeneratableEntity):
    def __init__(self, spec: spec.Schema) -> NoneType:
        super().__init__(spec)
        self._available_schemas = []
        for schema in self._spec.schemas:
            self._available_schemas.append(
                SCHEMA_MAP[type(schema)](schema)
            )

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        schema = random.choice(self._available_schemas)
        return schema()

    def is_valid(self, item: Any) -> bool:
        res = False

        for schema in self._available_schemas:
            res |= schema.is_valid(item)

        return res


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