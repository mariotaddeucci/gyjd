import inspect
from abc import ABC, abstractmethod
from functools import cached_property, wraps
from typing import Generic, Type, TypeVar

T = TypeVar("T")


class Dependency(ABC, Generic[T]):
    @classmethod
    @abstractmethod
    def get_instance(cls) -> T:
        pass


class LazyDependencyProxy:
    def __init__(self, cls: Type[Dependency]):
        self.__proxyed_cls = cls

    @cached_property
    def __instance(self):
        return self.__proxyed_cls.get_instance()

    def __getattr__(self, name):
        return getattr(self.__instance, name)


def inject_dependencies(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_signature = inspect.signature(func)
        bound_arguments = func_signature.bind_partial(*args, **kwargs)

        for param_name, param in func_signature.parameters.items():
            param_type = param.annotation

            if (
                param_type is not param.empty
                and issubclass(param_type, Dependency)
                and param_name not in bound_arguments.arguments
            ):
                # Inject dependency if not already provided
                kwargs.setdefault(param_name, LazyDependencyProxy(param_type))

        return func(*args, **kwargs)

    return wrapper
