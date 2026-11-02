"""Bridges the synchronous Django ORM into FastAPI's thread pool safely.

FastAPI runs plain `def` endpoints in worker threads. Django keeps one DB
connection per thread, so every endpoint closes stale/obsolete connections
before and after it runs, in the same thread that used them.
"""
import functools
import inspect

from django.db import close_old_connections
from fastapi.routing import APIRoute


def with_db_cleanup(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        close_old_connections()
        try:
            return fn(*args, **kwargs)
        finally:
            close_old_connections()

    return wrapper


class DBRoute(APIRoute):
    """Route class that wraps every sync endpoint with connection cleanup."""

    def __init__(self, path, endpoint, **kwargs):
        if not inspect.iscoroutinefunction(endpoint):
            endpoint = with_db_cleanup(endpoint)
        super().__init__(path, endpoint, **kwargs)
