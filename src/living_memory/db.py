from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import MetaData, UniqueConstraint, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.types import DateTime

from living_memory.config import Settings

ROOT = Path(__file__).resolve().parents[2]


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class DevelopmentArtifact(Base):
    __tablename__ = "development_artifact"
    __table_args__ = (UniqueConstraint("package", "checksum"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    package: Mapped[str]
    package_version: Mapped[int]
    checksum: Mapped[str]
    staged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    contents: Mapped[dict[str, Any]] = mapped_column(JSONB)


def migration_config() -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    return config


class Database:
    def __init__(self, settings: Settings):
        self.engine = create_engine(
            settings.database_url.get_secret_value(),
            pool_size=settings.pool_size,
            max_overflow=0,
            pool_timeout=settings.pool_timeout,
            pool_pre_ping=True,
            hide_parameters=True,
            connect_args={
                "connect_timeout": settings.connect_timeout,
                "options": f"-c statement_timeout={settings.statement_timeout_ms}",
            },
        )
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    @contextmanager
    def transaction(self) -> Iterator[Session]:
        """Create, commit/rollback and close within the caller's synchronous scope."""
        with self.sessions.begin() as session:
            yield session

    def ready(self) -> bool:
        with self.engine.connect() as connection:
            current = set(MigrationContext.configure(connection).get_current_heads())
        return current == set(ScriptDirectory.from_config(migration_config()).get_heads())

    def close(self) -> None:
        self.engine.dispose()
