import argparse

from alembic import command
from sqlalchemy.exc import SQLAlchemyError

from living_memory.clocks import SystemClock
from living_memory.config import load_settings
from living_memory.db import Database, migration_config
from living_memory.seed import seed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["migrate", "seed"])
    args = parser.parse_args()
    db = None
    try:
        settings = load_settings()
        db = Database(settings)
        if args.command == "migrate":
            config = migration_config()
            with db.engine.begin() as connection:
                config.attributes["connection"] = connection
                command.upgrade(config, "head")
            print("Migrations applied.")
        else:
            print("Package staged." if seed(settings, db, SystemClock()) else "Package unchanged.")
    except SQLAlchemyError:
        parser.exit(1, "Database operation failed. Check database availability and migrations.\n")
    except (ValueError, RuntimeError, OSError):
        parser.exit(
            1, "Invalid configuration or fixture package. Check .env.example and sources.\n"
        )
    finally:
        if db is not None:
            db.close()


if __name__ == "__main__":
    main()
