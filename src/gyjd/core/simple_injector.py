import functools
import inspect
from functools import cached_property, wraps
from typing import Callable, Literal, Type

_DEPENDENCIES_REGISTER = {}
IF_EXISTS_TYPE = Literal["raise", "skip", "overwrite"]


class LazyDependencyProxy:
    def __init__(self, instance_builder: Callable):
        self.__instance_builder = instance_builder

    @cached_property
    def __instance(self):
        return self.__instance_builder()

    def __getattr__(self, name):
        return getattr(self.__instance, name)


def register_dependency(
    func=None, singleton: bool = True, cls: type | None = None, if_exists: IF_EXISTS_TYPE = "raise"
):
    if func is None:
        return functools.partial(register_dependency, singleton=singleton, cls=cls)

    if cls is None:
        if inspect.isclass(func):
            cls = func
        else:
            cls = func.__annotations__.get("return")
            if cls is None:
                raise ValueError("No return type annotation found, please provide a class type")

    if singleton:
        func = functools.lru_cache(maxsize=None)(func)

    if if_exists == "raise" and cls in _DEPENDENCIES_REGISTER:
        raise ValueError(f"Dependency of type {cls} already registered")

    if if_exists == "skip" and cls in _DEPENDENCIES_REGISTER:
        return func

    _DEPENDENCIES_REGISTER[cls] = LazyDependencyProxy(func)

    return func


def inject_dependencies(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_signature = inspect.signature(func)
        bound_arguments = func_signature.bind_partial(*args, **kwargs)

        for param_name, param in func_signature.parameters.items():
            param_type = param.annotation

            if param_type is not param.empty and param_name not in bound_arguments.arguments:
                found_dependency = _DEPENDENCIES_REGISTER.get(param_type)
                if found_dependency:
                    kwargs.setdefault(param_name, found_dependency)

        return func(*args, **kwargs)

    return wrapper


def get_registered_dependencies() -> set[Type]:
    return set(_DEPENDENCIES_REGISTER)
