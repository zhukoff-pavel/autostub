import pathlib
import frozendict

import autostub._cache as cache
import autostub._request as request
import autostub._generator as generator

import openapi_parser as oapi_parser

TEST_DATA_DIR = pathlib.Path(__file__).resolve().parent / "data"


class PetStore:
    def __init__(self, cache_instance):
        self.service = generator.OAPISpec(
            oapi_parser.parse(str(TEST_DATA_DIR / "oapi_spec.yaml")),
            cache=cache_instance,
        )
        self.url = "http://petstore.swagger.io/v1"

    def __call__(self, path, **kwargs):
        url = "/".join([self.url, path])
        req = request.Request(
            url=url,
            method="get",
            data=frozendict.frozendict(kwargs.pop("data", dict())),
            parameters=frozendict.frozendict(kwargs.pop("parameters", dict())),
            headers=frozendict.frozendict(kwargs.pop("headers", dict())),
        )

        return req, self.service(req)


class TestDummyCache:
    def test_in_cache(self):
        cache_instance = cache.DummyCache()

        service = PetStore(cache_instance)

        _, res = service("pets/1")

        assert res
        assert not cache_instance._storage


class TestBasicCache:
    def test_in_cache(self):
        cache_instance = cache.RequestCache()

        service = PetStore(cache_instance)

        req, res = service("pets/1")

        assert res
        assert len(cache_instance._storage.keys()) == 1

        key = list(cache_instance._storage.keys())[0]

        assert "url" in key
        assert "method" in key

        assert req.url == key["url"]
        assert req.method == key["method"]

    def test_multiple_identical_requests(self):
        cache_instance = cache.RequestCache()

        service = PetStore(cache_instance)

        _, res1 = service("pets/1")
        assert res1
        assert len(cache_instance._storage.keys()) == 1

        _, res2 = service("pets/1")
        assert res2
        assert res2 == res1
        assert len(cache_instance._storage.keys()) == 1

    def test_different_requests(self):
        cache_instance = cache.RequestCache()

        service = PetStore(cache_instance)

        _, res1 = service("pets/1")
        assert res1
        assert len(cache_instance._storage.keys()) == 1

        _, res2 = service("pets")
        assert res2
        assert res1 != res2
        assert len(cache_instance._storage.keys()) == 2


class TestAdvancedCache:
    def test_in_cache(self):
        cache_instance = cache.CompositeCache(
            oapi_parser.parse(str(TEST_DATA_DIR / "oapi_spec.yaml")).schemas
        )

        service = PetStore(cache_instance)

        req, res1 = service("pets/1")
        assert res1
        model_store = cache_instance._storage["Pet"]

        key = cache.ModelCacheKey(
            req,
            put_fields=frozendict.frozendict(
                id=1
            ),  # Using this to override req parsing
        )
        assert model_store.has(key)

        assert model_store.get(key) == res1.content

    def test_req_returning_multiple(self):
        cache_instance = cache.CompositeCache(
            oapi_parser.parse(str(TEST_DATA_DIR / "oapi_spec.yaml")).schemas
        )

        service = PetStore(cache_instance)

        req, res = service("pets")
        assert res

        model_store = cache_instance._storage["Pet"]
        assert model_store.all()

        for content in res.content:
            for pet_entry in content:
                pid = pet_entry["id"]
                key = cache.ModelCacheKey(
                    req,
                    put_fields=frozendict.frozendict(
                        id=pid
                    ),  # Using this to override req parsing
                )

                assert model_store.has(key)

                assert pet_entry == model_store.get(key)
