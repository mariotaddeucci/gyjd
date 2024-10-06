import logging

from gyjd.core.simple_injector import Dependency


class Logger(logging.Logger, Dependency):
    @classmethod
    def get_instance(cls):
        logger = logging.getLogger("gyjd")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
