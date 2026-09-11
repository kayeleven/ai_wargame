from alembic import context

from living_memory import (  # noqa: F401 — register admin metadata
    administration,
    identity,
    memory,  # noqa: F401 — register read-store metadata
)
from living_memory.config import load_settings
from living_memory.db import Base, Database

target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):
    # Migration 0003 owns this expression index. Catalog tests verify it separately.
    return not (
        type_ == "index"
        and name == "ix_memory_record_search"
        and obj.table.name == "memory_record_revision"
        and obj.table.schema in (None, "public")
    )


def run_migrations():
    supplied = context.config.attributes.get("connection")
    if supplied is not None:
        context.configure(
            connection=supplied, target_metadata=target_metadata, include_object=include_object
        )
        with context.begin_transaction():
            context.run_migrations()
        return
    db = Database(load_settings())
    try:
        with db.engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                include_object=include_object,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        db.close()


run_migrations()
