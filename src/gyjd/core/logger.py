import logging
from dataclasses import dataclass

from gyjd.core.simple_injector import inject_dependencies


class GYJDLogger(logging.Logger): ...


@dataclass
class GYJDLoggerConfig:
    name: str = "gyjd"
    level: str = "INFO"
    default_to_console: bool = True
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@inject_dependencies
def get_default_logger(config: GYJDLoggerConfig):
    logger = logging.getLogger(config.name)
    if not logger.handlers and config.default_to_console:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(config.format)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, config.level.upper()))
    return logger
