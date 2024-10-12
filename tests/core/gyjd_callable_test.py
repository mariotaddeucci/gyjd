from gyjd.core.gyjd_callable import (
    GYJDCallable,
    GYJDMultipleException,
)
from gyjd.exceptions import GYJDFailFastException


def test_return_exception_on_fail():
    def func(a, b):
        return a / b

    gyjd_callable = GYJDCallable(
        func=func,
        return_exception_on_fail=True,
    )

    assert gyjd_callable(1, 2) == 0.5
    assert isinstance(gyjd_callable(1, 0), GYJDMultipleException)
    assert isinstance(gyjd_callable(1, 0).exceptions[0], ZeroDivisionError)


def test_retries_attempts():
    def func(a, b):
        return a / b

    gyjd_callable = GYJDCallable(
        func=func,
        retry_attempts=3,
        return_exception_on_fail=True,
    )

    assert gyjd_callable(1, 2) == 0.5

    try:
        gyjd_callable(1, 0)
    except GYJDMultipleException as e:
        assert len(e.exceptions) == 4
        assert isinstance(e.exceptions[0], ZeroDivisionError)
        assert isinstance(e.exceptions[1], ZeroDivisionError)
        assert isinstance(e.exceptions[2], ZeroDivisionError)
        assert isinstance(e.exceptions[3], ZeroDivisionError)


def test_fail_fast_exception():
    def func(a, b):
        raise GYJDFailFastException("Stop")

    gyjd_callable = GYJDCallable(func=func, retry_attempts=3)

    try:
        gyjd_callable(1, 2)
    except GYJDMultipleException as e:
        assert isinstance(e.exceptions[0], GYJDFailFastException)
        assert len(e.exceptions) == 1


def test_partial():
    def func(a, b, c):
        return a + b + c

    gyjd_callable = GYJDCallable(func=func)
    partial_callable = gyjd_callable.partial(1, c=2)

    assert gyjd_callable(1, 2, 3) == 6
    assert partial_callable(3) == 6
    assert partial_callable(4) == 7


def func_simple_sum(a, b):
    return a + b


def test_expand_sequential():
    gyjd_callable = GYJDCallable(func=func_simple_sum)
    result = list(gyjd_callable.expand(parameters={"a": [1, 2], "b": [4, 5]}))
    assert result == [5, 6, 6, 7]


def test_expand_thread_map():
    gyjd_callable = GYJDCallable(func=func_simple_sum)
    result = list(
        gyjd_callable.expand(parameters={"a": [1, 2], "b": [4, 5]}, strategy="thread_map"),
    )
    assert result == [5, 6, 6, 7]


def test_expand_thread_as_completed():
    gyjd_callable = GYJDCallable(func=func_simple_sum)
    result = list(
        gyjd_callable.expand(parameters={"a": [1, 2], "b": [4, 5]}, strategy="thread_as_completed"),
    )
    result.sort()
    assert result == [5, 6, 6, 7]


def test_expand_process_map():
    gyjd_callable = GYJDCallable(func=func_simple_sum)
    result = list(
        gyjd_callable.expand(parameters={"a": [1, 2], "b": [4, 5]}, strategy="process_map"),
    )
    assert result == [5, 6, 6, 7]


def test_expand_process_as_completed():
    gyjd_callable = GYJDCallable(func=func_simple_sum)
    result = list(
        gyjd_callable.expand(parameters={"a": [1, 2], "b": [4, 5]}, strategy="process_as_completed"),
    )
    result.sort()
    assert result == [5, 6, 6, 7]
