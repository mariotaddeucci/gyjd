import asyncio
import importlib
import json
import logging
from datetime import datetime, timedelta
from typing import List, Literal, TypedDict

from gyjd.database.connection_factory import ConnectionFactory

DEFAULT_RETRY_DELAY = 30

logger = logging.getLogger("gyjd")


class MappedEventDict(TypedDict):
    event_id: str
    event_name: str
    payload: dict
    event_date: str


MappedEvent = List[MappedEventDict]


class EventBus:
    def __init__(self, polling_interval=10):
        self._conn = ConnectionFactory.create_connection("event_bus")
        self.polling_interval = polling_interval

    def add_event(self, event_type: str, payload: dict):
        self._conn.conn.execute(
            "INSERT INTO events (event_type, payload, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (event_type, json.dumps(payload)),
        )

    def subscribe(
        self,
        event_types: List[str],
        function_path: str,
        task_name: str,
        mode: Literal["any", "batch"] = "any",
        max_attempts: int = 1,
        retry_delay: int = DEFAULT_RETRY_DELAY,
        concurrency_limit: int | None = None,
    ):
        if concurrency_limit is None:
            concurrency_limit = 8 if mode == "any" else 1

        if mode == "batch" and concurrency_limit > 1:
            raise ValueError("concurrency_limit must be 1 for batch mode")

        with self._conn.cursor() as c:
            sql = """
                INSERT OR REPLACE INTO subscribers (task_name, event_types, function_path, mode, max_attempts, retry_delay, concurrency_limit, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """
            c.execute(
                sql,
                (
                    task_name,
                    json.dumps(event_types),
                    function_path,
                    mode,
                    max_attempts,
                    retry_delay,
                    concurrency_limit,
                ),
            )

    async def process_events(self) -> bool:
        logger.info("Looking for events to process")
        async with self._conn.async_cursor() as c:
            c.execute("SELECT min(id) min_id, max(id) max_id FROM events WHERE processed = 0")
            min_id, max_id = c.fetchone()

            if not (min_id and max_id):
                logger.info("No events to process")
                return False

            c.execute(
                """
                    INSERT INTO tasks (subscriber_task_name, handled_events, parameters, created_at, scheduled_at)
                    WITH subs as (
                        SELECT task_name, value as event_type
                        FROM subscribers, json_each(event_types)
                        WHERE mode = 'any'
                    )
                    SELECT
                        task_name as subscriber_task_name,
                        '[' || e.id || ']' as handled_events,
                        '[' || payload || ']' as parameters,
                        CURRENT_TIMESTAMP as created_at,
                        CURRENT_TIMESTAMP as scheduled_at
                    FROM events e join subs using(event_type)
                    WHERE e.processed = 0 AND e.id BETWEEN ? AND ?
                """,
                (min_id, max_id),
            )

            c.execute(
                """
                    INSERT INTO tasks (subscriber_task_name, handled_events, parameters, created_at, scheduled_at)
                    WITH subs as (
                        SELECT task_name, value as event_type
                        FROM subscribers, json_each(event_types)
                        WHERE mode = 'batch'
                    )
                    SELECT
                        task_name as subscriber_task_name,
                        '[' || GROUP_CONCAT(e.id, ', ') || ']' as handled_events,
                        '[' || GROUP_CONCAT(e.payload, ', ') || ']' as parameters,
                        CURRENT_TIMESTAMP as created_at,
                        CURRENT_TIMESTAMP as scheduled_at
                    FROM events e join subs using(event_type)
                    WHERE e.processed = 0 AND e.id BETWEEN ? AND ?
                    GROUP BY 1
                """,
                (min_id, max_id),
            )

            c.execute(
                "UPDATE events SET processed = 1, processed_at = CURRENT_TIMESTAMP WHERE processed = 0 AND id BETWEEN ? AND ?",
                (min_id, max_id),
            )

            return True

    @classmethod
    def _load_function(cls, function_path: str):
        parts = function_path.split(".")
        mod_name = ".".join(parts[:-1])
        func_name = parts[-1]
        module = importlib.import_module(mod_name)
        func = getattr(module, func_name)
        return func

    async def _run_task(self, task):
        (task_id, subscriber_task_name, attempt_count, parameters) = task

        async with self._conn.async_cursor() as c:
            c.execute(
                "SELECT function_path, max_attempts, retry_delay FROM subscribers WHERE task_name = ?",
                (subscriber_task_name,),
            )
            row = c.fetchone()
            if not row:
                c.execute("UPDATE tasks SET status = 'failed' WHERE id = ?", (task_id,))
                return

            function_path, max_attempts, retry_delay = row

        async with self._conn.async_cursor() as c:
            c.execute(
                "UPDATE tasks SET attempt_count = attempt_count + 1, last_attempt_at = CURRENT_TIMESTAMP WHERE id = ?",
                (task_id,),
            )

        try:
            func = self._load_function(function_path)
            parameters = json.loads(parameters)
        except Exception:
            async with self._conn.async_cursor() as c:
                c.execute("UPDATE tasks SET status = 'failed' WHERE id = ?", (task_id,))
            return

        try:
            if asyncio.iscoroutinefunction(func):
                await func(parameters)
            else:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, func, parameters)

            async with self._conn.async_cursor() as c:
                c.execute(
                    "UPDATE tasks SET status = 'done', completed_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (task_id,),
                )

        except Exception as e:
            print(e)
            async with self._conn.async_cursor() as c:
                c.execute("SELECT attempt_count FROM tasks WHERE id = ?", (task_id,))
                attempt_count = c.fetchone()[0]
                if attempt_count < max_attempts:
                    new_time = (datetime.utcnow() + timedelta(seconds=retry_delay)).isoformat()
                    c.execute("UPDATE tasks SET status = 'pending', scheduled_at = ? WHERE id = ?", (new_time, task_id))
                else:
                    c.execute("UPDATE tasks SET status = 'failed' WHERE id = ?", (task_id,))

    async def run_tasks(self) -> bool:
        logger.info("Looking for tasks to run")
        sql = """
            WITH bs AS (
                SELECT
                    t.id,
                    t.subscriber_task_name,
                    t.attempt_count,
                    t.parameters,
                    t.scheduled_at,
                    s.concurrency_limit,
                    row_number() OVER (PARTITION BY t.subscriber_task_name ORDER BY t.scheduled_at) AS rn
                FROM
                    tasks t
                JOIN subscribers s ON
                    t.subscriber_task_name = s.task_name
                WHERE
                    t.scheduled_at <= CURRENT_TIMESTAMP AND
                    t.status = 'pending'
            )
            SELECT
                id,
                subscriber_task_name,
                attempt_count,
                parameters
            FROM bs
            WHERE rn <= concurrency_limit
            ORDER BY scheduled_at
            LIMIT 16
        """

        async with self._conn.async_cursor() as c:
            c.execute(sql)
            tasks = c.fetchall()

        if not tasks:
            logger.info("No tasks to run")
            return False

        await asyncio.gather(*(self._run_task(t) for t in tasks))

        return True

    async def run(self):
        while await self.run_tasks() or await self.process_events():
            pass

    async def run_forever(self):
        logger.info("Event bus started")
        while True:
            await self.run()


event_bus = EventBus()


def subscribe(
    event_types: List[str],
    task_name: str | None = None,
    mode: Literal["any", "batch"] = "any",
    max_attempts: int = 1,
    retry_delay: int = DEFAULT_RETRY_DELAY,
    concurrency_limit: int = 8,
):
    def decorator(func):
        module_name: str = func.__module__
        func_name: str = func.__name__
        path = f"{module_name}.{func_name}"
        nonlocal task_name
        if task_name is None:
            task_name = func_name
        event_bus.subscribe(event_types, path, task_name, mode, max_attempts, retry_delay, concurrency_limit)
        return func

    return decorator


def emmit(*, event_type: str, payload: dict):
    event_bus.add_event(event_type, payload)
