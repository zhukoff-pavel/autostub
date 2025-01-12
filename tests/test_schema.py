import sys
import copy
import string
import frozendict

import pytest

import autostub._schemas as schemas
import autostub._cache as cache
import autostub._request as request

import openapi_parser.specification as oapi_spec


class BaseTest:
    @classmethod
    def setup_class(cls):
        cls.dummy_cache = cache.DummyCache()
        cls.dummy_request = request.Request(
            url="funny.service",
            method="get",
            data=frozendict.frozendict(),
            parameters=frozendict.frozendict(),
            headers=frozendict.frozendict(),
        )


class TestInteger(BaseTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()

        cls.base_spec = oapi_spec.Integer(
            type="number",
            minimum=5,
            exclusive_minimum=3,
            maximum=10,
            exclusive_maximum=12,
        )

        cls.random_func = "random.randint"
        cls.test_class = schemas.Integer

    @pytest.mark.parametrize(
        "fields_to_exclude",
        (
            [],
            ["minimum"],
            ["maximum"],
            ["minimum", "exclusive_minimum"],
            ["maximum", "exclusive_maximum"],
        ),
        ids=["all-present", "no-minimum", "no-maximum", "sys-minimum", "sys-maximum"],
    )
    def test_generate(self, mocker, fields_to_exclude):
        spec = copy.deepcopy(self.base_spec)

        for item in fields_to_exclude:
            setattr(spec, item, None)

        lower_bound = (
            spec.minimum
            or (spec.exclusive_minimum + 1 if spec.exclusive_minimum else None)
            or -sys.maxsize - 1
        )
        upper_bound = (
            spec.maximum
            or (spec.exclusive_maximum - 1 if spec.exclusive_maximum else None)
            or sys.maxsize
        )
        schema = self.test_class(spec, "abacaba")

        random_mock = mocker.patch(self.random_func, autospec=True)

        schema(
            self.dummy_request,
            self.dummy_cache,
        )

        random_mock.assert_called_once_with(lower_bound, upper_bound)

    @pytest.mark.parametrize(
        "value,expected",
        (
            ("foo", False),
            (4, False),
            (5, True),
            (6, True),
            (10, True),
            (11, False),
        ),
    )
    def test_validate_all_present(self, value, expected):
        schema = self.test_class(self.base_spec, "abacaba")

        assert schema.is_valid(value) == expected

    @pytest.mark.parametrize(
        "value,expected",
        (
            (3, False),
            (4, True),
            (5, True),
            (11, True),
            (12, False),
        ),
    )
    def test_validate_exclusive(self, value, expected):
        spec = copy.deepcopy(self.base_spec)

        spec.minimum = None
        spec.maximum = None

        schema = self.test_class(spec, "abacaba")

        assert schema.is_valid(value) == expected


class TestNumber(TestInteger):
    def setup_class(cls):
        super().setup_class()

        cls.random_func = "random.uniform"
        cls.test_class = schemas.Number


class TestString(BaseTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()

        cls.base_spec = oapi_spec.String(
            type="string",
            min_length=10,
            max_length=20,
        )

    @pytest.mark.parametrize("field_to_exclude", ["min_length", "max_length"])
    def test_generate(self, mocker, field_to_exclude):
        spec = copy.deepcopy(self.base_spec)
        setattr(spec, field_to_exclude, None)

        schema = schemas.String(spec, "fun_strings")

        allowed_letters = string.ascii_letters + string.digits + " "
        lower, upper = spec.min_length or 1, spec.max_length or 100

        choices_mock = mocker.patch("random.choices", return_value="123")

        randint_retval = 3
        randint_mock = mocker.patch("random.randint", return_value=randint_retval)

        schema(
            self.dummy_request,
            self.dummy_cache,
        )

        choices_mock.assert_called_once_with(allowed_letters, k=randint_retval)
        randint_mock.assert_called_once_with(lower, upper)

    @pytest.mark.parametrize(
        "value,expected",
        (
            (1, False),
            ("bar", False),
            ("bar" * 4, True),
            (True, False),
        ),
    )
    def test_validate(self, value, expected):
        schema = schemas.String(self.base_spec, "very_important_string")

        assert schema.is_valid(value) == expected


class TestNull(BaseTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()

        cls.base_spec = oapi_spec.Null(type="null")

    def test_generate(self):
        schema = schemas.Null(self.base_spec, "null")

        assert schema(self.dummy_request, self.dummy_cache) == None

    @pytest.mark.parametrize(
        "value,expected", ((1, False), ("bar", False), (None, True))
    )
    def test_validate(self, value, expected):
        schema = schemas.Null(self.base_spec, "null")

        assert schema.is_valid(value) == expected


class TestBoolean(BaseTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()

        cls.base_spec = oapi_spec.Boolean(type="bool")

    def test_generate(self, mocker):
        schema = schemas.Boolean(self.base_spec, "bool")

        choice_mocker = mocker.patch("random.choice", autospec=True)

        schema(self.dummy_request, self.dummy_cache)

        choice_mocker.assert_called_once_with([True, False])

    @pytest.mark.parametrize(
        "value,expected",
        (
            (2, False),
            ("bar", False),
            (False, True),
            (True, True),
        ),
    )
    def test_validate(self, value, expected):
        schema = schemas.Boolean(self.base_spec, "bool")

        assert schema.is_valid(value) == expected
