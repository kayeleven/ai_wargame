import argparse
import getpass
import subprocess
from pathlib import Path

from alembic import command
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from living_memory.backup import create_backup, restore_backup
from living_memory.clocks import SystemClock
from living_memory.config import DEV_DATABASE, load_settings
from living_memory.db import ROOT, Database, migration_config
from living_memory.identity import (
    GlobalRole,
    User,
    create_local_user,
    normalize_username,
    reset_password,
)
from living_memory.memory import load_timeline
from living_memory.seed import read_package, seed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=[
            "migrate",
            "seed",
            "load-memory",
            "load-timeline",
            "create-admin",
            "reset-password",
            "backup",
            "restore",
        ],
    )
    parser.add_argument("--checksum")
    parser.add_argument("--fixture", choices=["phase0", "orchid-accord"], default="phase0")
    parser.add_argument("--username")
    parser.add_argument("--display-name")
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--target-database")
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
        elif args.command in {"load-memory", "load-timeline"}:
            url = make_url(settings.database_url.get_secret_value())
            if (
                settings.environment != "development"
                or url.database != DEV_DATABASE
                or url.host not in {"localhost", "127.0.0.1"}
                or not args.checksum
            ):
                raise ValueError("Development database and explicit checksum required")
            print("Memory loaded." if load_timeline(db, args.checksum) else "Memory unchanged.")
        elif args.command == "seed":
            directory = ROOT / "fixtures" / args.fixture
            print(
                "Package staged."
                if seed(settings, db, SystemClock(), directory)
                else "Package unchanged."
            )
            print("Checksum: " + read_package(directory)[1])
        elif args.command in {"create-admin", "reset-password"}:
            if not args.username:
                raise ValueError("username is required")
            password = getpass.getpass("Password: ")
            confirmation = getpass.getpass("Confirm password: ")
            if password != confirmation:
                raise ValueError("password confirmation does not match")
            with db.transaction() as db_session:
                if args.command == "create-admin":
                    if db_session.scalar(select(func.count()).select_from(GlobalRole)):
                        raise ValueError("an initial system administrator already exists")
                    create_local_user(
                        db_session,
                        args.username,
                        args.display_name or args.username,
                        password,
                        SystemClock().now(),
                        system_admin=True,
                    )
                    print("Initial system administrator created.")
                else:
                    user = db_session.scalars(
                        select(User).where(User.username == normalize_username(args.username))
                    ).one()
                    reset_password(db_session, user, password, SystemClock().now())
                    print("Password reset and existing sessions revoked.")
        elif args.command == "backup":
            if args.archive is None:
                raise ValueError("archive is required")
            create_backup(settings.database_url.get_secret_value(), args.archive)
            print("Backup and manifest created.")
        else:
            if args.archive is None or not args.target_database:
                raise ValueError("archive and explicit target database are required")
            source_url = make_url(settings.database_url.get_secret_value())
            if any(char in args.target_database for char in "/:@"):
                raise ValueError("target database must be a database name, not a URL")
            target_url = source_url.set(database=args.target_database)
            revoked = restore_backup(target_url.render_as_string(hide_password=False), args.archive)
            print(f"Restore verified; {revoked} restored active sessions revoked.")
    except SQLAlchemyError:
        parser.exit(1, "Database operation failed. Check database availability and migrations.\n")
    except (
        ValueError,
        RuntimeError,
        OSError,
        KeyError,
        TypeError,
        StopIteration,
        subprocess.SubprocessError,
    ):
        parser.exit(
            1, "Invalid configuration or fixture package. Check .env.example and sources.\n"
        )
    finally:
        if db is not None:
            db.close()


if __name__ == "__main__":
    main()
