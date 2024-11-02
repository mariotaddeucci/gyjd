class GYJDException(Exception): ...


class GYJDMultipleException(GYJDException):
    def __init__(self, exceptions: list[Exception]):
        self.exceptions = exceptions


class GYJDFailFastException(GYJDException): ...


class GYJDValueError(GYJDException, ValueError): ...
