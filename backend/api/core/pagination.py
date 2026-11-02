from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

from api.core.errors import ApiError

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class PageParams:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="1-based page number"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    ):
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def paginate(queryset, params: PageParams) -> tuple[list, int]:
    total = queryset.count()
    return list(queryset[params.offset: params.offset + params.page_size]), total


def make_page(items: list, total: int, params: PageParams) -> dict:
    pages = (total + params.page_size - 1) // params.page_size if total else 0
    return {"items": items, "total": total, "page": params.page, "page_size": params.page_size, "pages": pages}


def apply_ordering(queryset, ordering: str, allowed: dict[str, str]):
    """`ordering` is e.g. "name" or "-name"; `allowed` maps public names to ORM fields."""
    desc = ordering.startswith("-")
    key = ordering.lstrip("-")
    if key not in allowed:
        raise ApiError(400, "invalid_ordering", f"Cannot order by '{key}'. Allowed: {', '.join(sorted(allowed))}.")
    field = allowed[key]
    return queryset.order_by(f"-{field}" if desc else field, "id")
