"""HTTP client utilities."""
import httpx


def get_async_client() -> httpx.AsyncClient:
    """Get an async HTTP client."""
    return httpx.AsyncClient(timeout=30.0)

