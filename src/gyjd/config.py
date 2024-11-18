import time
from dataclasses import dataclass, field
from datetime import datetime
from os import getenv
from uuid import uuid4


@dataclass
class LoggerConfig:
    name: str = "gyjd"
    level: str = field(default_factory=lambda: getenv("LOG_LEVEL", "INFO"))
    default_to_console: bool = True
    formatter: str = field(
        default_factory=lambda: getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )


@dataclass
class Config:
    logger: LoggerConfig
    node_id: str = field(default_factory=lambda: f"{hex(int(time.time()*1000))[2:]}-{uuid4()}")
    start_time: datetime = field(default_factory=datetime.now)
