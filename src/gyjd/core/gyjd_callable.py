import concurrent.futures
import functools
import itertools
import time
from collections.abc import Callable, Generator
from typing import Any, Literal

from gyjd.exceptions import (
    GYJDException,
    GYJDFailFastException,
    GYJDMultipleException,
    GYJDValueError,
)


class GYJDCallable:
    def __init__(
        self,
        func: Callable,
        return_exception_on_fail: bool = False,
        retry_attempts=-0,
        retry_delay=0,
        retry_max_delay=None,
        retry_backoff=1,
        retry_on_exceptions=(Exception,),
    ):
        self._func = func
        self._retry_attempts = retry_attempts
        self._retry_delay = retry_delay
        self._retry_max_delay = retry_max_delay
        self._retry_backoff = retry_backoff
        self._retry_on_exceptions = retry_on_exceptions
        self._return_exception_on_fail = return_exception_on_fail

    def __call__(self, *args, **kwargs):
        return self._attempt_call(*args, **kwargs)

    def _attempt_call(self, *args, **kwargs):
        raised_exceptions = []
        attempts = self._retry_attempts + 1
        delay = self._retry_delay

        while attempts >= 0:
            try:
                return self._func(*args, **kwargs)
            except GYJDFailFastException:
                return
            except self._retry_on_exceptions as e:
                raised_exceptions.append(e)

            attempts -= 1
            if not attempts:
                prepared_exception = GYJDMultipleException(raised_exceptions)
                if self._return_exception_on_fail:
                    return prepared_exception
                raise prepared_exception

            time.sleep(delay)
            delay *= self._retry_backoff
            if self._retry_max_delay is not None:
                delay = min(delay, self._retry_max_delay)

        raise GYJDException("This should never happen")

    def _call_with_parameters(self, parameters: dict[str, Any]) -> Any:
        return self.__call__(**parameters)

    def partial(self, *args, **kwargs) -> "GYJDCallable":
        return self._recreate(func=functools.partial(self._func, *args, **kwargs))

    def _recreate(self, **new_kwargs) -> "GYJDCallable":
        new_args = {
            "func": self._func,
            "retry_attempts": self._retry_attempts,
            "retry_delay": self._retry_delay,
            "retry_max_delay": self._retry_max_delay,
            "retry_backoff": self._retry_backoff,
            "retry_on_exceptions": self._retry_on_exceptions,
            "return_exception_on_fail": self._return_exception_on_fail,
            **new_kwargs,
        }

        return self.__class__(**new_args)

    def expand(
        self,
        parameters: dict[str, list[Any]] | list[dict[str, Any]],
        *,
        max_workers: int | None = None,
        strategy: Literal[
            "sequential",
            "thread_map",
            "thread_as_completed",
            "process_map",
            "process_as_completed",
        ] = "sequential",
    ) -> Generator[Any, None, None]:
        if isinstance(parameters, dict):
            generated_parameters = (
                dict(zip(parameters.keys(), comb)) for comb in itertools.product(*parameters.values())
            )
        else:
            generated_parameters = parameters

        if strategy == "sequential":
            for generated_parameter in generated_parameters:
                yield self._call_with_parameters(generated_parameter)
            return

        executor_type, execution_mode = strategy.split("_", 1)

        executor_cls = {
            "thread": concurrent.futures.ThreadPoolExecutor,
            "process": concurrent.futures.ProcessPoolExecutor,
        }[executor_type]

        with executor_cls(max_workers=max_workers) as executor:
            if execution_mode == "map":
                for result in executor.map(self._call_with_parameters, generated_parameters):
                    yield result
            elif execution_mode == "as_completed":
                tasks = (
                    executor.submit(self._call_with_parameters, generated_parameter)
                    for generated_parameter in generated_parameters
                )
                for future in concurrent.futures.as_completed(tasks):
                    yield future.result()
            else:
                raise GYJDValueError(f"Invalid strategy: {strategy}")
