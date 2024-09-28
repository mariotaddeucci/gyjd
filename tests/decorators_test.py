from gyjd.decorators import gyjd


def test_gyjd_decorator_without_parameters():
    @gyjd
    def func(a, b):
        return a + b

    assert func(1, 2) == 3


def test_gyjd_decorator_with_parameters():
    @gyjd(return_exception_on_fail=True)
    def func(a, b):
        return a + b

    assert func(1, 2) == 3
