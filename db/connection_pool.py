"""
Centralized database connection pool for the application.
Simplified version without Redis dependencies.
"""

import os
from psycopg_pool import AsyncConnectionPool

from finsense.settings import settings, DATABASE_URL
from utils.logging import logger

_pool: AsyncConnectionPool | None = None

is_pytest_env = os.getenv("PYTEST_VERSION") is not None


async def get_pool(connection_string: str | None = None) -> AsyncConnectionPool:
    """
    Get the global connection pool instance.
    If the pool doesn't exist yet, it will be created.

    Args:
        connection_string: Optional custom connection string to use instead of the default

    Returns:
        The global connection pool instance
    """
    global _pool
    if _pool is None:
        conn_string = connection_string or DATABASE_URL
        if is_pytest_env:
            conn_string = f"postgres://postgres:{os.environ.get('DB_PASSWORD', 'postgres')}@localhost:5432/finsense_test"
        logger.info(
            f"Creating new connection pool with min_size={settings.MIN_DB_CONNECTION_POOL_SIZE}, max_size={settings.MAX_DB_CONNECTION_POOL_SIZE}"
        )
        _pool = AsyncConnectionPool(
            conn_string,
            min_size=settings.MIN_DB_CONNECTION_POOL_SIZE,
            max_size=settings.MAX_DB_CONNECTION_POOL_SIZE,
            open=False,
        )
        await _pool.open()
    return _pool


async def close_pool() -> None:
    """
    Close the global connection pool if it exists.
    This should be called during application shutdown.
    """
    global _pool
    if _pool is not None:
        logger.info("Closing database connection pool")
        await _pool.close()
        _pool = None

