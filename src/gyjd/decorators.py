import functools

from gyjd.core.gyjd_callable import GYJDCallable


def gyjd(
    func=None,
    *,
    return_exception_on_fail: bool = False,
    retry_attempts=-0,
    retry_delay=0,
    retry_max_delay=None,
    retry_backoff=1,
    retry_on_exceptions=(Exception,),
):
    if func is None:
        new_fn = functools.partial(
            gyjd,
            return_exception_on_fail=return_exception_on_fail,
            retry_attempts=retry_attempts,
            retry_delay=retry_delay,
            retry_max_delay=retry_max_delay,
            retry_backoff=retry_backoff,
            retry_on_exceptions=retry_on_exceptions,
        )

        return new_fn

    return GYJDCallable(func=func)
