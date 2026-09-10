from alembic import context

from living_memory.config import load_settings
from living_memory.db import Base, Database

target_metadata = Base.metadata


def run_migrations():
    supplied = context.config.attributes.get("connection")
    if supplied is not None:
        context.configure(connection=supplied, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        return
    db = Database(load_settings())
    try:
        with db.engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        db.close()


run_migrations()
