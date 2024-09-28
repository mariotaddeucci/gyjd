from gyjd.core.gyjd_callable import (
    GYJDCallable,
    GYJDFailFastException,
    GYJDMultipleException,
)


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
