import os
from pathlib import Path
from typing import Literal

from gyjd.database.sqlite_connection import SQLiteConnection


class ConnectionFactory:
    @classmethod
    def create_connection(cls, db_name: Literal["event_bus"]) -> SQLiteConnection:
        location = Path.home() / "gyjd" / "database" / db_name / f"{db_name}.db"
        os.makedirs(location.parent, exist_ok=True)
        conn = SQLiteConnection(str(location.absolute()))
        getattr(cls, f"_create_{db_name}_schema")(conn)
        return conn

    @classmethod
    def _create_event_bus_schema(cls, conn: SQLiteConnection) -> None:
        sql = """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                processed INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL,
                processed_at DATETIME
            );
            CREATE TABLE IF NOT EXISTS subscribers (
                task_name TEXT PRIMARY KEY,
                event_types TEXT NOT NULL,
                function_path TEXT NOT NULL,
                mode TEXT NOT NULL DEFAULT 'any',
                created_at DATETIME NOT NULL,
                max_attempts INTEGER NOT NULL DEFAULT 1,
                retry_delay INTEGER NOT NULL DEFAULT 30,
                concurrency_limit INTEGER NOT NULL DEFAULT 8
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subscriber_task_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                attempt_count INTEGER NOT NULL DEFAULT 0,
                handled_events TEXT NOT NULL,
                parameters TEXT NOT NULL,
                last_attempt_at DATETIME,
                created_at DATETIME NOT NULL,
                completed_at DATETIME,
                scheduled_at DATETIME NOT NULL,
                FOREIGN KEY(subscriber_task_name) REFERENCES subscribers(task_name)
            );
        """
        conn.conn.executescript(sql)
