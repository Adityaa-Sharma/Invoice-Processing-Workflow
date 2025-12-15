"""Retry utilities with exponential backoff."""
import asyncio
from functools import wraps
from typing import Type, Callable, Any
from .logger import get_logger

logger = get_logger("retry")


def with_retry(
    max_attempts: int = 3,
    backoff_seconds: float = 2.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    """
    Retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        backoff_seconds: Initial backoff duration in seconds
        exceptions: Tuple of exception types to catch
        
    Returns:
        Decorated function
        
    Usage:
        @with_retry(max_attempts=3, backoff_seconds=2)
        async def my_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        wait_time = backoff_seconds * (2 ** (attempt - 1))
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator
