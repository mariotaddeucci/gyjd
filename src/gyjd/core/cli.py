import inspect
from typing import Callable

import typer

from gyjd.core.logger import GYJDLogger
from gyjd.core.simple_injector import get_registered_dependencies, inject_dependencies


class CLI:
    __instance = None

    @inject_dependencies
    def __init__(self, logger: GYJDLogger = None):
        self.logger = logger
        self.app = typer.Typer(no_args_is_help=True)

    @classmethod
    def get_instance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    @classmethod
    def _adjust_signature(cls, func: Callable):
        sig = inspect.signature(func)
        registered_types = get_registered_dependencies()

        filtered_params = [param for param in sig.parameters.values() if param.annotation not in registered_types]
        new_signature = sig.replace(parameters=filtered_params)

        def new_func(*args, **kwargs):
            bound_args = new_signature.bind(*args, **kwargs)
            return func(*bound_args.args, **bound_args.kwargs)

        setattr(new_func, "__signature__", new_signature)
        return new_func

    @classmethod
    def registry(cls, func, name):
        instance = cls.get_instance()
        instance.app.command(name=name)(cls._adjust_signature(func))

    @classmethod
    def run(cls):
        instance = cls.get_instance()
        instance.app()
