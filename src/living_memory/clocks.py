from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass(frozen=True)
class FixedClock:
    instant: datetime

    def __post_init__(self) -> None:
        if self.instant.tzinfo is None or self.instant.utcoffset() != UTC.utcoffset(None):
            raise ValueError("clock requires a UTC instant")

    def now(self) -> datetime:
        return self.instant


class GameTime(BaseModel):
    """Game-relative elapsed microseconds, independent of wall time."""

    model_config = ConfigDict(frozen=True)
    elapsed_microseconds: int = Field(ge=0)
