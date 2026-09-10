import argparse

from alembic import command
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from living_memory.clocks import SystemClock
from living_memory.config import DEV_DATABASE, load_settings
from living_memory.db import ROOT, Database, migration_config
from living_memory.memory import load_timeline
from living_memory.seed import read_package, seed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["migrate", "seed", "load-timeline"])
    parser.add_argument("--checksum")
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
        elif args.command == "load-timeline":
            url = make_url(settings.database_url.get_secret_value())
            if (
                settings.environment != "development"
                or url.database != DEV_DATABASE
                or url.host not in {"localhost", "127.0.0.1"}
                or not args.checksum
            ):
                raise ValueError("Development database and explicit checksum required")
            print("Timeline loaded." if load_timeline(db, args.checksum) else "Timeline unchanged.")
        else:
            print("Package staged." if seed(settings, db, SystemClock()) else "Package unchanged.")
            print("Checksum: " + read_package(ROOT / "fixtures/phase0")[1])
    except SQLAlchemyError:
        parser.exit(1, "Database operation failed. Check database availability and migrations.\n")
    except (ValueError, RuntimeError, OSError, KeyError, TypeError, StopIteration):
        parser.exit(
            1, "Invalid configuration or fixture package. Check .env.example and sources.\n"
        )
    finally:
        if db is not None:
            db.close()


if __name__ == "__main__":
    main()
