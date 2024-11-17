import logging

from gyjd.config import LoggerConfig
from gyjd.core.simple_injector import inject_dependencies


class GYJDLogger(logging.Logger): ...


@inject_dependencies
def get_default_logger(config: LoggerConfig):
    logger = logging.getLogger(config.name)
    if not logger.handlers and config.default_to_console:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(config.formatter)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, config.level.upper()))
    return logger
