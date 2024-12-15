import asyncio
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from typing import Literal


class SQLiteConnection:
    _MAINTENANCE_TABLE = "maintenance_metadata"

    def __init__(self, conn_str: str):
        self.conn = sqlite3.connect(conn_str, check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL;")
        self._ensure_maintenance_metadata()
        self.auto_maintenance()
        self._lock = asyncio.Lock()

    def _ensure_maintenance_metadata(self):
        sql = f"CREATE TABLE IF NOT EXISTS {self._MAINTENANCE_TABLE} (event_name VARCHAR(36) PRIMARY KEY, last_event_datetime DATETIME);"
        self.conn.execute(sql)

    def _register_event(self, event_name):
        sql = f"INSERT OR REPLACE INTO {self._MAINTENANCE_TABLE} (event_name, last_event_datetime) VALUES (?, ?);"
        with self.cursor() as c:
            c.execute(sql, (event_name, datetime.utcnow().isoformat()))

    def _get_last_event_datetime(self, event_name) -> datetime | None:
        sql = f"SELECT last_event_datetime FROM {self._MAINTENANCE_TABLE} WHERE event_name = ?;"
        with self.cursor() as c:
            c.execute(sql, (event_name,))
            result = c.fetchone()
            return datetime.fromisoformat(result[0]) if result else None

    def vacuum(self):
        self.conn.execute("VACUUM;")
        self._register_event("vacuum")

    def checkpoint(self, mode: Literal["passive", "full", "restart", "truncate"] = "full"):
        self.conn.execute(f"PRAGMA wal_checkpoint({mode});")
        self._register_event("checkpoint")

    def auto_maintenance(self):
        last_vacuum = self._get_last_event_datetime("vacuum")
        if last_vacuum is None or (datetime.utcnow() - last_vacuum).days > 7:
            self.vacuum()

        last_checkpoint = self._get_last_event_datetime("checkpoint")
        if last_checkpoint is None or (datetime.utcnow() - last_checkpoint).days > 1:
            self.checkpoint()

    @contextmanager
    def cursor(self):
        c = self.conn.cursor()
        try:
            yield c
        except Exception:
            self.conn.rollback()
            raise
        finally:
            c.close()
            self.conn.commit()

    @asynccontextmanager
    async def async_cursor(self):
        async with self._lock:
            with self.cursor() as c:
                yield c
