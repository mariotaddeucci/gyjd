from typing import List


class GYJDException(Exception): ...


class GYJDMultipleException(GYJDException):
    def __init__(self, exceptions: List[Exception]):
        self.exceptions = exceptions


class GYJDFailFastException(GYJDException): ...


class GYJDValueError(GYJDException, ValueError): ...
