"""One page of a list, able to fetch the pages after it."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from typing import Generic, TypeVar

from ._resources._base import ApiResource

T = TypeVar("T", bound=ApiResource)


class Page(Generic[T]):
    """One page of a list, able to fetch the pages after it."""

    __slots__ = ("_fetch", "current_page", "data", "last_page", "per_page", "total")

    data: list[T]
    """The objects on this page."""

    current_page: int
    """The number of this page, from 1."""

    last_page: int
    """The number of the last page."""

    per_page: int
    """How many objects a page holds."""

    total: int
    """How many objects the whole list holds."""

    def __init__(
        self,
        data: Sequence[T],
        *,
        current_page: int,
        last_page: int,
        per_page: int,
        total: int,
        fetch: Callable[[int], Page[T]],
    ) -> None:
        self.data = list(data)
        self.current_page = current_page
        self.last_page = last_page
        self.per_page = per_page
        self.total = total
        self._fetch = fetch

    def __repr__(self) -> str:
        return f"<Page {self.current_page} of {self.last_page}: {len(self.data)} of {self.total}>"

    def __iter__(self) -> Iterator[T]:
        """Iterate over the objects on this page."""
        return iter(self.data)

    def __len__(self) -> int:
        """How many objects this page holds."""
        return len(self.data)

    def has_more(self) -> bool:
        """Whether there are pages after this one."""
        return self.current_page < self.last_page

    def next_page(self) -> Page[T] | None:
        """Fetch the next page, or None when this is the last."""
        return self._fetch(self.current_page + 1) if self.has_more() else None

    def auto_paging_iterator(self) -> Iterator[T]:
        """Iterate over the objects on this page and every page after it, fetching each as it is reached."""
        seen: set[str] = set()
        page: Page[T] = self

        while True:
            for item in page.data:
                identifier = item.get("id")

                # A record created while paging pushes older ones onto the next page, so they can come round twice.
                if isinstance(identifier, str):
                    if identifier in seen:
                        continue

                    seen.add(identifier)

                yield item

            following = page.next_page()

            if following is None or following.current_page <= page.current_page:
                return

            page = following

    def is_empty(self) -> bool:
        """Whether this page holds no objects."""
        return not self.data
