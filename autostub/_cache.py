import enum
import typing as tp
import collections


class CachingLevel(enum.Enum):
    NONE = enum.auto()
    BASIC = enum.auto()
    ADVANCED = enum.auto()


class CacheFactory:
    @staticmethod
    def get_cache(cache_level: CachingLevel):
        match cache_level:
            case CachingLevel.NONE:
                return DummyCache()
            case CachingLevel.BASIC:
                return SimpleCache()
            case CachingLevel.ADVANCED:
                return ResponseCache()


class CacheKey(tp.TypedDict):
    key: tp.Hashable


class ModelCacheKey(CacheKey):
    model: str


class BaseCache:
    def __init__(self) -> None:
        self._storage = {}

    def has(self, key: CacheKey) -> bool:
        raise NotImplementedError

    def put(self, key: CacheKey, value: tp.Any) -> None:
        raise NotImplementedError

    def get(self, key: CacheKey) -> tp.Any:
        raise NotImplementedError


class DummyCache(BaseCache):
    def __init__(self) -> None:
        pass

    def has(self, key: CacheKey) -> bool:
        return False

    def put(self, key: CacheKey, value: tp.Any) -> None:
        return

    def get(self, key: CacheKey) -> tp.Any:
        return None


class SimpleCache(BaseCache):
    def __init__(self) -> None:
        super().__init__()

    def has(self, key: CacheKey) -> bool:
        return key["key"] in self._storage

    def put(self, key: CacheKey, value: tp.Any) -> None:
        self._storage[key["key"]] = value

    def get(self, key: CacheKey) -> tp.Any:
        if self.has(key):
            return self._storage[key["key"]]
        return None

    def all(self) -> dict:
        return self._storage


class ModelCache(BaseCache):
    def __init__(self) -> None:
        self._storage: collections.defaultdict[str, SimpleCache] = (
            collections.defaultdict(SimpleCache)
        )

    def has(self, key: ModelCacheKey) -> bool:
        if self.has_model(key):
            return self._storage[key["model"]].has(key)
        return False

    def has_model(self, key: ModelCacheKey) -> bool:
        return key["model"] in self._storage

    def put(self, key: ModelCacheKey, value: tp.Any) -> None:
        self._storage[key["model"]].put(key, value)

    def get(self, key: ModelCacheKey) -> tp.Any:
        if self.has(key):
            return self._storage[key["model"]].get(key)
        return None

    def get_all_by_model(self, key: ModelCacheKey) -> dict:
        if self.has_model(key):
            return self._storage[key["model"]].all()

        return {}


class ResponseCache(BaseCache):
    def __init__(self) -> None:
        self.models = ModelCache()
        self.headers = SimpleCache()

    def has(self, key: ModelCacheKey) -> bool:
        return self.models.has(key) and self.headers.has(key)

    def put(self, key: ModelCacheKey, model: tp.Any, headers: tp.Any):
        self.models.put(key, model)
        self.headers.put(key, headers)

    def get_model(self, key: ModelCacheKey) -> tp.Any:
        return self.models.get(key)

    def get_headers(self, key: ModelCacheKey) -> tp.Any:
        return self.headers.get(key)

    def get(self, key: ModelCacheKey) -> dict[str, tp.Any]:
        return {
            "headers": self.get_headers(key),
            "models": self.get_model(key),
        }
