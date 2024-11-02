import random
import time
from logging import Logger
from typing import Any

import requests
from gyjd import gyjd


def get_users_urls():
    return [
        {
            "url": f"https://dummyjson.com/users/{user_id}?delay={round(random.uniform(1.5, 3) * 1000)}&select=id,firstName,lastName"
        }
        for user_id in range(1, 11)
    ]


@gyjd(retry_attempts=5)
def get_json(url: str, random_exception: bool = False, logger: Logger = None):
    logger.debug(f"GET {url}")
    if random_exception and random.random() < 0.5:
        raise ValueError("Random exception")

    response = requests.get(url)
    response.raise_for_status()
    return response.json()


@gyjd.command(alias="parallel_requests")
def example_parallel_requests(
    strategy: str,
    logger: Logger = None,
):
    logger.info("Starting delayed requests test")
    start_at = time.monotonic()

    urls: list[dict[str, Any]] = get_users_urls()
    results_generator = get_json.expand(
        urls,
        strategy=strategy,
        max_workers=5,
    )
    for result in results_generator:
        logger.info(f"Received response: {result}")

    end_at = time.monotonic()
    elapsed = end_at - start_at
    logger.info("10 requests completed with at least 1.5 seconds of delay, sequentially would take at least 15 seconds")
    if elapsed >= 15:
        logger.warning(f"Elapsed {elapsed:.2f}s is greater than 15 seconds")
        return

    logger.info(f"Elapsed {elapsed:.2f}s, whahoo!")


if __name__ == "__main__":
    gyjd.run()
