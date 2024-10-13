import logging
from collections.abc import Callable
from functools import partial

from gyjd.core.cli import CLI
from gyjd.core.config_loader import load_config_file
from gyjd.core.gyjd_callable import GYJDCallable
from gyjd.core.logger import InternalLogger, get_default_logger
from gyjd.core.simple_injector import inject_dependencies, register_dependency

register_dependency(get_default_logger, cls=InternalLogger, singleton=True)
register_dependency(get_default_logger, cls=logging.Logger, singleton=True)


class gyjd:
    def __new__(
        cls,
        func: Callable | None = None,
        *,
        return_exception_on_fail: bool = False,
        retry_attempts=-0,
        retry_delay=0,
        retry_max_delay=None,
        retry_backoff=1,
        retry_on_exceptions=(Exception,),
    ) -> GYJDCallable:
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
    def command(cls, func: Callable | None = None, alias=None):
        if func is None:
            return partial(cls.command, alias=alias)

        alias = alias or getattr(func, "__name__", None)
        CLI.registry(inject_dependencies(func), alias)

        return func

    @classmethod
    def register_config_file(
        cls,
        config_type: type,
        filepath: str,
        allow_if_file_not_found: bool = False,
        subtree: list[str] | str | None = None,
    ) -> None:
        register_dependency(
            partial(
                load_config_file,
                filepath=filepath,
                config_type=config_type,
                subtree=subtree,
                allow_if_file_not_found=allow_if_file_not_found,
            ),
            cls=config_type,
            singleton=True,
        )

    @classmethod
    def run(cls):
        CLI.executor()
