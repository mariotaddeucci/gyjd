import functools
import inspect
from functools import wraps
from typing import Callable, Literal, Type

_DEPENDENCIES_REGISTER: dict[Type, "DependencyHandler"] = {}
IF_EXISTS_TYPE = Literal["raise", "skip", "overwrite"]


class DependencyHandler:
    def __init__(self, instance_builder: Callable, reuse_times: int = -1):
        self._instance_generator = self._build_instance_generator(
            instance_builder=instance_builder,
            reuse_times=reuse_times,
        )

    @staticmethod
    def _build_instance_generator(instance_builder: Callable, reuse_times: int):
        if reuse_times == -1:
            instance = instance_builder()
            while True:
                yield instance

        while True:
            instance = instance_builder()
            if reuse_times == 0:
                yield instance
            else:
                for _ in range(reuse_times):
                    yield instance
            del instance

    def get(self):
        return next(self._instance_generator)


def inject_dependencies(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_signature = inspect.signature(func)
        bound_arguments = func_signature.bind_partial(*args, **kwargs)

        for param_name, param in func_signature.parameters.items():
            param_type = param.annotation

            if param_type is not param.empty and param_name not in bound_arguments.arguments:
                found_dependency = _DEPENDENCIES_REGISTER.get(param_type)
                if found_dependency and param_name not in kwargs:
                    kwargs[param_name] = found_dependency.get()

        return func(*args, **kwargs)

    return wrapper


def register_dependency(
    func=None,
    reuse_times: int = -1,
    cls: type | None = None,
    if_exists: IF_EXISTS_TYPE = "raise",
):
    if func is None:
        return functools.partial(register_dependency, reuse_times=reuse_times, cls=cls)

    if cls is None:
        if inspect.isclass(func):
            cls = func
        else:
            cls = func.__annotations__.get("return")
            if cls is None:
                raise ValueError("No return type annotation found, please provide a class type")

    if if_exists == "raise" and cls in _DEPENDENCIES_REGISTER:
        raise ValueError(f"Dependency of type {cls} already registered")

    if if_exists == "skip" and cls in _DEPENDENCIES_REGISTER:
        return func

    _DEPENDENCIES_REGISTER[cls] = DependencyHandler(
        inject_dependencies(func),
        reuse_times=reuse_times,
    )

    return func


def get_registered_dependencies() -> set[Type]:
    return set(_DEPENDENCIES_REGISTER)


def clear_registered_dependencies():
    _DEPENDENCIES_REGISTER.clear()
