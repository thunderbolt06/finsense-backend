"""HTTP client utilities."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx

from finsense.settings import settings


@asynccontextmanager
async def get_async_client(
    *, timeout: float | None = None, **kwargs
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Asynchronous HTTP client session as context manager.
    
    Usage:
    async with get_async_client() as client:
        response = await client.get('https://example.com')
        data = response.json()
    """
    if timeout is None:
        timeout = settings.HTTP_TIMEOUT
    
    async with httpx.AsyncClient(timeout=timeout, **kwargs) as client:
        yield client

