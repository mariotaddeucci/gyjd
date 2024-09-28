import concurrent.futures
import functools
import itertools
import time
from typing import Any, Callable, Dict, Generator, List, Literal, Optional

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
        self._func: Callable = func
        self._retry_attempts = retry_attempts
        self._retry_delay = retry_delay
        self._retry_max_delay = retry_max_delay
        self._retry_backoff = retry_backoff
        self._retry_on_exceptions = retry_on_exceptions
        self._return_exception_on_fail = return_exception_on_fail

    def __call__(self, *args, **kwargs):
        raised_exceptions = []
        attempts = self._retry_attempts + 1
        delay = self._retry_delay

        while attempts >= 0:
            try:
                return self._func(*args, **kwargs)
            except self._retry_on_exceptions as e:
                raised_exceptions.append(e)

            attempts -= 1
            if not attempts or isinstance(raised_exceptions[-1], GYJDFailFastException):
                prepared_exception = GYJDMultipleException(raised_exceptions)
                if not self._return_exception_on_fail:
                    raise prepared_exception
                return prepared_exception

            time.sleep(delay)
            delay *= self._retry_backoff

            if self._retry_max_delay is not None:
                delay = min(delay, self._retry_max_delay)

        raise GYJDException("This should never happen")

    def __getattr__(self, attr):
        return getattr(self._func, attr)

    def partial(self, *args, **kwargs) -> "GYJDCallable":
        return self._recreate(func=functools.partial(self._func, *args, **kwargs))

    def _recreate(self, **new_krawgs) -> "GYJDCallable":
        new_args = {
            "func": self._func,
            "retry_attempts": self._retry_attempts,
            "retry_delay": self._retry_delay,
            "retry_max_delay": self._retry_max_delay,
            "retry_backoff": self._retry_backoff,
            "retry_on_exceptions": self._retry_on_exceptions,
            "return_exception_on_fail": self._return_exception_on_fail,
            **new_krawgs,
        }

        return self.__class__(**new_args)

    def retry(
        self,
        exceptions=(Exception,),
        attempts=-0,
        delay=0,
        max_delay=None,
        backoff=1,
    ) -> "GYJDCallable":
        return self._recreate(
            retry_on_exceptions=exceptions,
            retry_attempts=attempts,
            retry_delay=delay,
            retry_max_delay=max_delay,
            retry_backoff=backoff,
        )

    def return_exception_on_fail(
        self, return_exception_on_fail: bool = True
    ) -> "GYJDCallable":
        return self._recreate(return_exception_on_fail=return_exception_on_fail)

    def expand(
        self,
        parameters: Dict[str, List[Any]],
        max_workers: Optional[int] = None,
        strategy: Literal[
            "sequential",
            "thread_map",
            "process_map",
            "thread_as_complete",
            "process_as_complete",
        ] = "sequential",
    ) -> Generator[Any, None, None]:
        combinations = (
            dict(zip(parameters.keys(), comb))
            for comb in itertools.product(*parameters.values())
        )

        if strategy == "sequential":
            for combination in combinations:
                yield self.__call__(**combination)
            return

        executor_type, execution_mode = strategy.split("_", 1)

        executor_cls = {
            "thread": concurrent.futures.ThreadPoolExecutor,
            "process": concurrent.futures.ProcessPoolExecutor,
        }[executor_type]

        with executor_cls(max_workers=max_workers) as executor:
            if execution_mode == "map":
                for result in executor.map(self.__call__, combinations):
                    yield result
            elif execution_mode == "as_complete":
                tasks = (
                    executor.submit(self.__call__, combination)
                    for combination in combinations
                )
                for future in concurrent.futures.as_completed(tasks):
                    yield future.result()
            else:
                raise GYJDValueError(f"Invalid strategy: {strategy}")
