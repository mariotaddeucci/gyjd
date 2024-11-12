import logging
from collections.abc import Callable
from dataclasses import fields, is_dataclass
from functools import partial

from gyjd.config import LoggerConfig
from gyjd.core.config_loader import load_config_file
from gyjd.core.gyjd_callable import GYJDCallable
from gyjd.core.logger import GYJDLogger, get_default_logger
from gyjd.core.simple_injector import clear_registered_dependencies, inject_dependencies, register_dependency


def setup_defaults(clear_dependencies: bool = False):
    """
    Register default dependencies:
    - GYJDLogger
    - logging.Logger
    - LoggerConfig

    If clear_dependencies is True, clear all registered dependencies before registering the default ones.
    """

    if clear_dependencies:
        clear_registered_dependencies()

    register_dependency(get_default_logger, cls=GYJDLogger, reuse_times=-1, if_exists="skip")
    register_dependency(get_default_logger, cls=logging.Logger, reuse_times=-1, if_exists="skip")
    register_dependency(LoggerConfig, reuse_times=-1, if_exists="skip")


class gyjd:
    register_dependency = partial(register_dependency, if_exists="overwrite")

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
            wrapper = partial(
                gyjd,
                return_exception_on_fail=return_exception_on_fail,
                retry_attempts=retry_attempts,
                retry_delay=retry_delay,
                retry_max_delay=retry_max_delay,
                retry_backoff=retry_backoff,
                retry_on_exceptions=retry_on_exceptions,
            )
            return wrapper

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
    def _collect_children_config(cls, dataclass_type: type, subtree: str = ""):
        for field in fields(dataclass_type):
            full_tree = f"{subtree}.{field.name}" if subtree else field.name
            if is_dataclass(field.type):
                yield full_tree, field.type
                yield from cls._collect_children_config(field.type, full_tree)

    @classmethod
    def register_config_file(
        cls,
        *,
        config_type: type,
        filepath: str,
        allow_if_file_not_found: bool = False,
        subtree: str = "",
    ) -> None:
        subtree = subtree.strip(".")

        base_loader = partial(
            load_config_file,
            filepath=filepath,
            allow_if_file_not_found=allow_if_file_not_found,
        )

        register_dependency(
            partial(
                base_loader,
                config_type=config_type,
                subtree=subtree.split("."),
            ),
            cls=config_type,
            reuse_times=-1,
        )

        for child_subtree, child_type in cls._collect_children_config(config_type):
            register_dependency(
                partial(
                    base_loader,
                    config_type=child_type,
                    subtree=child_subtree.split("."),
                ),
                cls=child_type,
                reuse_times=-1,
                if_exists="overwrite",
            )


setup_defaults()
__all__ = ["gyjd"]
