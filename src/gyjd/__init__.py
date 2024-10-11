from functools import partial
from typing import Callable, Optional

from gyjd.core.cli import CLI
from gyjd.core.gyjd_callable import GYJDCallable
from gyjd.core.logger import Logger
from gyjd.core.simple_injector import Dependency, inject_dependencies


class gyjd:
    def __new__(
        cls,
        func: Optional[Callable] = None,
        *,
        return_exception_on_fail: bool = False,
        retry_attempts=-0,
        retry_delay=0,
        retry_max_delay=None,
        retry_backoff=1,
        retry_on_exceptions=(Exception,),
    ):
        if func is None:
            return gyjd

        return GYJDCallable(
            func=inject_dependencies(func),
            return_exception_on_fail=return_exception_on_fail,
            retry_attempts=retry_attempts,
            retry_delay=retry_delay,
            retry_max_delay=retry_max_delay,
            retry_backoff=retry_backoff,
            retry_on_exceptions=retry_on_exceptions,
        )

    @classmethod
    def command(cls, func: Optional[Callable] = None, alias=None):
        if func is None:
            return partial(cls.command, alias=alias)

        alias = alias or getattr(func, "__name__", None)
        CLI.registry(inject_dependencies(func), alias)

        return func
