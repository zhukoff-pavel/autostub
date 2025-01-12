from types import NoneType
from typing import Any

from autostub._request import Request
from autostub._cache import BaseCache, CompositeCacheKey, NO_CACHE

import openapi_parser.specification as spec
from frozendict import frozendict

import copy
import random
import sys
import string



class GeneratableEntity:
    def __init__(self, spec: spec.Schema, name: str | None = None) -> None:
        self._spec = spec
        self._cacheable = False
        self._name = name

    def _read_cache(self, request: Request, cache: BaseCache) -> Any:
        if self._cacheable:
            key = CompositeCacheKey(
                key=request,
                model=self._spec
            )
            if cache.has(key):
                return cache.get(key)
        else:
            if self._name and self._name in request.query_params:
                return request.query_params[self._name]
        return None

    def __call__(self, request: Request, cache: BaseCache) -> Any:
        return self._read_cache(request, cache)

    def is_valid(self, item: Any) -> bool:
        raise NotImplementedError

    def from_val(self, val: Any) -> Any:
        return val


class Integer(GeneratableEntity):
    _spec: spec.Integer

    def __init__(self, spec: spec.Integer, name: str | None = None) -> NoneType:
        super().__init__(spec, name)
        if self._spec.minimum is not None:
            self._lower_bound = self._spec.minimum
        elif self._spec.exclusive_minimum is not None:
            self._lower_bound = self._spec.exclusive_minimum + 1
        else:
            self._lower_bound = -sys.maxsize - 1

        if self._spec.maximum is not None:
            self._upper_bound = self._spec.maximum
        elif self._spec.exclusive_maximum is not None:
            self._upper_bound = self._spec.exclusive_maximum - 1
        else:
            self._upper_bound = sys.maxsize

    def __call__(self, *args: Any, **kwds: Any) -> int:
        r = super()._read_cache(*args, **kwds)

        if r:
            return r

        return random.randint(
            self._lower_bound,
            self._upper_bound,
        )

    def is_valid(self, item: int | str) -> bool:
        try:
            item = int(item)
        except ValueError:
            return False
        return self._lower_bound <= item <= self._upper_bound

    def from_val(self, val: str) -> int:
        assert self.is_valid(val)
        return int(val)


class Number(Integer):
    def __call__(self, *args: Any, **kwds: Any) -> float:
        r = super()._read_cache(*args, **kwds)

        if r:
            return r

        return random.uniform(
            self._lower_bound,
            self._upper_bound,
        )

    def is_valid(self, item: str) -> bool:
        try:
            converted = float(item)
        except ValueError:
            return False
        return self._lower_bound <= converted <= self._upper_bound

    def from_val(self, val: str) -> float:
        assert self.is_valid(val)
        return float(val)


class String(GeneratableEntity):
    _spec: spec.String

    def __init__(self, spec: spec.String, name: str | None = None) -> NoneType:
        super().__init__(spec, name)
        self._lower_bound = self._spec.min_length or 1
        self._upper_bound = self._spec.max_length or 100

    def __call__(self, *args: Any, **kwds: Any) -> str:
        # TODO support formats

        r = super()._read_cache(*args, **kwds)

        if r:
            return r

        allowed_letters = string.ascii_letters + string.digits + " "
        return "".join(
            random.choices(
                allowed_letters,
                k=random.randint(
                    self._lower_bound,
                    self._upper_bound,
                ),
            )
        )

    def is_valid(self, item: str) -> bool:
        # TODO support formats
        if not isinstance(item, str):
            return False
        return self._lower_bound <= len(item) <= self._upper_bound


class Boolean(GeneratableEntity):
    def __call__(self, *args: Any, **kwds: Any) -> bool:
        r = super()._read_cache(*args, **kwds)

        if r:
            return r

        return random.choice([True, False])

    def is_valid(self, item: bool) -> bool:
        return item in [True, False]


class Null(GeneratableEntity):
    def __call__(self, *args: Any, **kwds: Any) -> NoneType:
        return None

    def is_valid(self, item: NoneType) -> bool:
        return item is None


class Array(GeneratableEntity):
    _spec: spec.Array

    def __call__(self, request: Request, cache: BaseCache, *args: Any, **kwds: Any) -> Any:
        limit = random.randint(
            self._spec.min_items or 0,
            self._spec.max_items or 100,
        )

        key = CompositeCacheKey(
            key=copy.deepcopy(request),
            model=self._spec.items
        )

        obj = SCHEMA_MAP[type(self._spec.items)](self._spec.items)
        if cache.has_by_model():
            if len(cache.get_all_by_model(key)) < limit:
                for _ in range(len(cache.get_all_by_model(key)), limit):
                    obj(request, cache, read_from_cache=False)

            items = cache.get_all_by_model(key)

            return [
                random.sample(list(items.values()), limit)
            ]
        else:
            return [
                obj(request, NO_CACHE) for _ in range(limit)
            ]

    def is_valid(self, item: list[Any]) -> bool:
        return all([isinstance(x, self._spec.items) for x in item])


class Object(GeneratableEntity):
    def __init__(self, spec: spec.Object, name: str | None = None) -> NoneType:
        super().__init__(spec, name)
        self._cacheable = True
        self.properties: dict[str, Any] = {}
        self.required = set(spec.required)
        for prop in spec.properties:
            self.properties[prop.name] = SCHEMA_MAP[type(prop.schema)](prop.schema, prop.name)

    def _transform_parameters(self, q_params: frozendict[str, str]) -> frozendict[str, Any]:
        result = {}
        for name, val in q_params.items():
            if name in self.properties:
                result[name] = self.properties[name].from_val(val)
            else:
                result[name] = val
        return frozendict(result)

    def __call__(self, request: Request, cache: BaseCache, *args: Any, read_from_cache: bool = True, **kwds: Any) -> dict[str, Any]:
        res = {}

        inner_req = copy.deepcopy(request)
        inner_req.query_params = self._transform_parameters(inner_req.query_params)

        cache_key = CompositeCacheKey(
            key=inner_req,
            model=self._spec,
        )

        if read_from_cache and cache.has(cache_key):
            return cache.get(cache_key)

        put_fields = dict()
        for prop in self.properties:
            if prop in self.required or random.choice([True, False]):
                res[prop] = self.properties[prop](inner_req, cache, *args, **kwds)
                put_fields[prop] = res[prop]

        cache_key.put_fields = frozendict(put_fields)

        cache.put(cache_key, res)

        return res

    def is_valid(self, item: dict) -> bool:
        object_keys = set(item.keys())

        if object_keys & self.required != self.required:
            return False

        res = True

        for key in item:
            res &= self.properties[key].is_valid(item[key])

        return res


class AnyOf(GeneratableEntity):
    _spec: spec.AnyOf

    def __init__(self, spec: spec.AnyOf, name: str | None = None) -> NoneType:
        super().__init__(spec, name)
        self._available_schemas = []
        for schema in self._spec.schemas:
            self._available_schemas.append(SCHEMA_MAP[type(schema)](schema))

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        schema = random.choice(self._available_schemas)
        return schema(*args, **kwds)

    def is_valid(self, item: Any) -> bool:
        res = False

        for schema in self._available_schemas:
            res |= schema.is_valid(item)

        return res


class OneOf(AnyOf):
    pass


SCHEMA_MAP = {
    spec.Integer: Integer,
    spec.Number: Number,
    spec.String: String,
    spec.Boolean: Boolean,
    spec.Null: Null,
    spec.Array: Array,
    spec.Object: Object,
    spec.OneOf: OneOf,
    spec.AnyOf: AnyOf,
}
