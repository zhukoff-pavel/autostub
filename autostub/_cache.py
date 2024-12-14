import enum
import random
import typing as tp
from dataclasses import dataclass, field

from frozendict import frozendict
from autostub._request import Request

from openapi_parser import specification


class CachingLevel(enum.Enum):
    NONE = enum.auto()
    BASIC = enum.auto()
    ADVANCED = enum.auto()


class CacheFactory:
    @staticmethod
    def get_cache(cache_level: CachingLevel, models: dict[str, specification.Schema] | None = None):
        match cache_level:
            case CachingLevel.NONE:
                return DummyCache()
            case CachingLevel.BASIC:
                return SimpleCache()
            case CachingLevel.ADVANCED:
                assert models, "Models are required to be set in OAPI spec"
                return CompositeCache(models)


@dataclass
class CacheKey:
    key: tp.Hashable


@dataclass
class RequestCacheKey(CacheKey):
    key: Request


@dataclass
class ModelCacheKey(RequestCacheKey):
    put_fields: frozendict | None = None


@dataclass
class CompositeCacheKey(ModelCacheKey):
    model: specification.Schema | None = None


type AcceptableKeys = CacheKey | RequestCacheKey | ModelCacheKey | CompositeCacheKey


class BaseCache:
    def __init__(self) -> None:
        self._storage = {}

    def has(self, key: AcceptableKeys) -> bool:
        raise NotImplementedError

    def put(self, key: AcceptableKeys, value: tp.Any) -> None:
        raise NotImplementedError

    def get(self, key: AcceptableKeys) -> tp.Any:
        raise NotImplementedError

    def all(self) -> dict:
        return self._storage

    def get_all_by_model(self, key: CompositeCacheKey) -> dict:
        return self.all()

    def has_by_model(self):
        return False


class DummyCache(BaseCache):
    def __init__(self) -> None:
        pass

    def has(self, key: AcceptableKeys) -> bool:
        return False

    def put(self, key: AcceptableKeys, value: tp.Any) -> None:
        return

    def get(self, key: AcceptableKeys) -> tp.Any:
        return None


class SimpleCache(BaseCache):
    def __init__(self) -> None:
        super().__init__()

    def has(self, key: AcceptableKeys) -> bool:
        return key.key in self._storage

    def put(self, key: AcceptableKeys, value: tp.Any) -> None:
        self._storage[key.key] = value

    def get(self, key: AcceptableKeys) -> tp.Any:
        if self.has(key):
            return self._storage[key.key]
        return None


class RequestCache(SimpleCache):
    def _resolve_key(self, key: RequestCacheKey) -> CacheKey:
        return CacheKey(
            key=frozendict(
                url=key.key.url,
                method=key.key.method,
                parameters=key.key.query_params,
            )
        )

    def has(self, key: RequestCacheKey):
        return super().has(self._resolve_key(key))

    def put(self, key: RequestCacheKey, value: tp.Any):
        super().put(self._resolve_key(key), value)

    def get(self, key: RequestCacheKey):
        return super().get(self._resolve_key(key))


class ModelCache(SimpleCache):
    def _resolve_key(self, key: ModelCacheKey) -> frozendict:
        result = dict()
        # 1. If put_keys is set, use it
        if key.put_fields:
            for field, value in key.put_fields.items():
                if field in self._required_fields:
                    result[field] = value
            if result:
                return frozendict(result)

        # 2. If any necessary fields present in key, take only them
        for field, value in key.key.query_params.items():
            if field in self._required_fields:
                result[field] = value

        if result:
            return frozendict(result)

        # 3. If above is not present, take all fields with the same names as in model_description
        for field, value in key.key.query_params.items():
            if field in self._all_fields:
                result[field] = value

        # 4. Return empty key if nothing above is true
        return frozendict(result)

    def _search_by_part(self, key: frozendict) -> tp.Any | None:
        if not key:
            return None

        candidates = []

        for storage_key, value in self._storage.items():
            if set(key.items()) & set(storage_key.items()) == set(key.items()):
                candidates.append(value)

        return random.choice(candidates)

    def __init__(self, model_description: specification.Object | None) -> None:
        super().__init__()
        self._model_description = model_description
        self._required_fields: list[str] = []
        self._all_fields: list[str] = []
        if model_description:
            self._required_fields = model_description.required
            self._all_fields = [i.name for i in model_description.properties]

    def has(self, key: ModelCacheKey):
        return self._search_by_part(self._resolve_key(key)) is not None

    def put(self, key: ModelCacheKey, value: tp.Any):
        self._storage[self._resolve_key(key)] = value

    def get(self, key: ModelCacheKey):
        return self._search_by_part(self._resolve_key(key))


class CompositeCache(BaseCache):
    def __init__(self, models: dict[str, specification.Schema]) -> None:
        self._storage: dict[str, ModelCache] = dict()
        self._models: dict[str, specification.Schema] = models

    def _resolve_model_name(self, model: specification.Schema | None) -> str:
        if not model:
            return ""
        for m_name, spec in self._models.items():
            if spec == model:
                return m_name
        return ""

    def has(self, key: CompositeCacheKey) -> bool:
        model_name = self._resolve_model_name(key.model)
        if self.has_model(model_name):
            return self._storage[model_name].has(key)
        return False

    def has_model(self, model: str) -> bool:
        return model in self._storage

    def put(self, key: CompositeCacheKey, value: tp.Any) -> None:
        model_name = self._resolve_model_name(key.model)
        if not model_name:
            return

        if not self.has_model(model_name):
            self._storage[model_name] = ModelCache(self._models[model_name])

        self._storage[model_name].put(key, value)

    def get(self, key: CompositeCacheKey) -> tp.Any:
        if self.has(key):
            model_name = self._resolve_model_name(key.model)
            return self._storage[model_name].get(key)
        return None

    def get_all_by_model(self, key: CompositeCacheKey) -> dict:
        model_name = self._resolve_model_name(key.model)
        if self.has_model(model_name):
            return self._storage[model_name].all()

        return {}

    def has_by_model(self):
        return True


NO_CACHE = DummyCache()