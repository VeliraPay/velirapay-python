"""The base of every object the API answers with, and how their attributes are read."""

from __future__ import annotations

import copy
import math
import re
from collections.abc import Mapping
from datetime import UTC, date, datetime
from enum import Enum
from typing import Any, TypeVar

from .._errors import InvalidArgumentError

E = TypeVar("E", bound=Enum)

_DAY = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
# No count of anything has 19 digits, and int() refuses strings of more than 4,300.
_DIGITS = re.compile(r"0*([0-9]{1,18})")


class ApiResource:
    """An object returned by the API, keeping every attribute it was sent with."""

    __slots__ = ("_attributes",)

    def __init__(self, attributes: Mapping[str, Any]) -> None:
        """Read an object from its attributes, as the API sends them."""
        if not isinstance(attributes, Mapping):
            raise InvalidArgumentError(
                f"A {type(self).__name__} is read from the dict of attributes the API sent, not a {type(attributes).__name__}."
            )

        self._attributes: dict[str, Any] = copy.deepcopy(dict(attributes))

    def __repr__(self) -> str:
        meta = getattr(self, "_meta", None)

        return f"{type(self).__name__}({self._attributes!r}{f', {meta!r}' if meta else ''})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ApiResource) or type(other) is not type(self):
            return NotImplemented

        return self._attributes == other._attributes and getattr(self, "_meta", None) == getattr(other, "_meta", None)

    def get(self, key: str, default: Any = None) -> Any:
        """One attribute as the API sent it, including any this library does not know yet."""
        return copy.deepcopy(self._attributes[key]) if key in self._attributes else default

    def to_dict(self) -> dict[str, Any]:
        """The attributes as the API sent them, such as to store the object or encode it as JSON."""
        return copy.deepcopy(self._attributes)


def string(data: Mapping[str, Any], key: str, fallback: str = "") -> str:
    """Read a string attribute."""
    value = nullable_string(data, key)

    return fallback if value is None else value


def nullable_string(data: Mapping[str, Any], key: str) -> str | None:
    """Read a string attribute that may be None."""
    return _text(data.get(key))


def boolean(data: Mapping[str, Any], key: str, fallback: bool = False) -> bool:
    """Read a boolean attribute."""
    value = nullable_bool(data, key)

    return fallback if value is None else value


def nullable_bool(data: Mapping[str, Any], key: str) -> bool | None:
    """Read a boolean attribute that may be None."""
    value = data.get(key)

    return value if isinstance(value, bool) else None


def integer(data: Mapping[str, Any], key: str, fallback: int = 0) -> int:
    """Read an integer attribute."""
    value = nullable_int(data, key)

    return fallback if value is None else value


def nullable_int(data: Mapping[str, Any], key: str) -> int | None:
    """Read an integer attribute that may be None."""
    return whole_number(data.get(key))


def nullable_number(data: Mapping[str, Any], key: str) -> float | None:
    """Read a number attribute that may be None."""
    value = data.get(key)

    if isinstance(value, bool) or not isinstance(value, int | float):
        return None

    try:
        number = float(value)
    except OverflowError:
        return None

    return number if math.isfinite(number) else None


def timestamp(data: Mapping[str, Any], key: str) -> datetime | None:
    """Read a moment, in UTC when it says no offset; a bare date is taken as midnight UTC."""
    value = data.get(key)

    if not isinstance(value, str) or value == "":
        return None

    try:
        if _DAY.fullmatch(value):
            day = date.fromisoformat(value)

            return datetime(day.year, day.month, day.day, tzinfo=UTC)

        moment = datetime.fromisoformat(value)
    except ValueError:
        return None

    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def calendar_day(data: Mapping[str, Any], key: str) -> date | None:
    """Read a day, such as a due date."""
    value = data.get(key)

    if isinstance(value, str) and _DAY.fullmatch(value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    moment = timestamp(data, key)

    return None if moment is None else moment.astimezone(UTC).date()


def strings(data: Mapping[str, Any], key: str) -> list[str]:
    """Read a list of strings."""
    value = nullable_strings(data, key)

    return [] if value is None else value


def nullable_strings(data: Mapping[str, Any], key: str) -> list[str] | None:
    """Read a list of strings that may be None."""
    value = data.get(key)

    if not isinstance(value, list):
        return None

    return [text for text in (_text(item) for item in value) if text is not None]


def mapping(data: Mapping[str, Any], key: str) -> dict[str, Any]:
    """Read an object attribute; an empty one arrives from the API as an empty list."""
    value = data.get(key)

    if isinstance(value, dict):
        return copy.deepcopy(value)

    if isinstance(value, list):
        return {str(index): copy.deepcopy(item) for index, item in enumerate(value)}

    return {}


def records(data: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    """Read a list of objects."""
    value = data.get(key)

    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def record(data: Mapping[str, Any], key: str) -> dict[str, Any] | None:
    """Read an object attribute that may be None."""
    value = data.get(key)

    return value if isinstance(value, dict) else None


def reference(data: Mapping[str, Any], key: str) -> str | None:
    """Read the code of a related object, sent either as the code itself or as an object carrying it."""
    value = data.get(key)

    if isinstance(value, dict):
        value = value.get("id") if value.get("id") is not None else value.get("code")

    return value if isinstance(value, str) and value != "" else None


def one_of(enum: type[E], value: object) -> E | None:
    """Read a value only when it is one of the enum's."""
    for member in enum:
        if isinstance(value, str) and member.value == value:
            return member

    return None


def whole_number(value: object) -> int | None:
    """Read an integer, also from a string of digits."""
    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, float) and value.is_integer():
        return int(value)

    digits = _DIGITS.fullmatch(value) if isinstance(value, str) else None

    return None if digits is None else int(digits[1])


def _text(value: object) -> str | None:
    """Read a string, also from a number, as the API sends some amounts."""
    if isinstance(value, str):
        return value

    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return str(value)

    if isinstance(value, float) and math.isfinite(value):
        return str(int(value)) if value.is_integer() and abs(value) < 2**53 else repr(value)

    return None
