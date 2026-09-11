"""PostgreSQL custom-format backup and guarded operational restore."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from pydantic import SecretStr
from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session

from living_memory.db import Database, DevelopmentArtifact, migration_config, recovery_blocked
from living_memory.identity import AuthSession, revoke_all_sessions_after_restore
from living_memory.memory import Dataset, RebuildState

# 0005 intentionally rejects populated 0004 databases.  Archives are therefore
# only compatible within the rebuilt Phase 1D format.
APP_VERSION = "0.2.0"


@dataclass(frozen=True)
class BackupManifest:
    created_at: str
    application_version: str
    schema_heads: list[str]
    postgres_tool_version: str
    source_database: dict[str, str | int | None]
    archive_sha256: str
    domain_inventory: dict[str, Any]
    archive_format: str = "postgresql-custom"


def _process_environment(url: URL) -> dict[str, str]:
    environment = os.environ.copy()
    if url.password:
        environment["PGPASSWORD"] = url.password
    return environment


def _connection_arguments(url: URL) -> list[str]:
    result: list[str] = []
    if url.host:
        result += ["--host", url.host]
    if url.port:
        result += ["--port", str(url.port)]
    if url.username:
        result += ["--username", url.username]
    if not url.database:
        raise ValueError("database URL requires an explicit database")
    result += ["--dbname", url.database]
    return result


def _run(arguments: list[str], url: URL) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        check=True,
        shell=False,
        env=_process_environment(url),
        text=True,
        capture_output=True,
    )


def _tool_version(tool: str) -> str:
    result = subprocess.run(
        [tool, "--version"], check=True, shell=False, text=True, capture_output=True
    )
    return result.stdout.strip()


def create_backup(database_url: str, archive: Path) -> Path:
    url = make_url(database_url)
    if archive.exists() or archive.with_suffix(archive.suffix + ".json").exists():
        raise FileExistsError("backup output already exists")
    tool_version = _tool_version("pg_dump")
    from living_memory.config import Settings

    database = Database(
        Settings.model_validate(
            {"session_secret": SecretStr("x" * 32), "database_url": SecretStr(database_url)}
        )
    )
    try:
        with database.engine.connect() as connection:
            with connection.begin():
                if recovery_blocked(connection):
                    raise ValueError("Cannot back up a blocked recovery target")
                tables = inspect(connection).get_table_names(schema="public")
                if tables:
                    quote = connection.dialect.identifier_preparer.quote
                    locked = ", ".join(quote(table) for table in tables)
                    connection.exec_driver_sql(f"LOCK TABLE {locked} IN SHARE MODE")
                archive.parent.mkdir(parents=True, exist_ok=True)
                archive.touch(mode=0o600, exist_ok=False)
                try:
                    _run(
                        [
                            "pg_dump",
                            "--format=custom",
                            "--no-owner",
                            "--no-acl",
                            "--exclude-schema=lm_recovery",
                            "--file",
                            str(archive),
                            *_connection_arguments(url),
                        ],
                        url,
                    )
                except Exception:
                    archive.unlink(missing_ok=True)
                    raise
                heads = sorted(MigrationContext.configure(connection).get_current_heads())
                server = str(connection.scalar(text("SHOW server_version")))
                with Session(bind=connection) as db_session:
                    inventory = _domain_inventory_session(db_session)
    finally:
        database.close()
    archive.chmod(0o600)
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest = BackupManifest(
        created_at=datetime.now(UTC).isoformat(),
        application_version=APP_VERSION,
        schema_heads=heads,
        postgres_tool_version=tool_version,
        source_database={
            "database": url.database,
            "host": url.host,
            "port": url.port,
            "server_version": server,
        },
        archive_sha256=checksum,
        domain_inventory=inventory,
    )
    sidecar = archive.with_suffix(archive.suffix + ".json")
    sidecar.touch(mode=0o600, exist_ok=False)
    sidecar.write_text(json.dumps(asdict(manifest), indent=2) + "\n", encoding="utf-8")
    sidecar.chmod(0o600)
    return sidecar


def _read_manifest(archive: Path) -> BackupManifest:
    data: Any = json.loads(
        archive.with_suffix(archive.suffix + ".json").read_text(encoding="utf-8")
    )
    return BackupManifest(**data)


def verify_backup(archive: Path) -> BackupManifest:
    manifest = _read_manifest(archive)
    if manifest.archive_format != "postgresql-custom" or archive.read_bytes()[:5] != b"PGDMP":
        raise ValueError("backup is not a PostgreSQL custom-format archive")
    if not secrets_compare(
        manifest.archive_sha256, hashlib.sha256(archive.read_bytes()).hexdigest()
    ):
        raise ValueError("backup checksum does not match its manifest")
    expected = set(ScriptDirectory.from_config(migration_config()).get_heads())
    if set(manifest.schema_heads) != expected or manifest.application_version != APP_VERSION:
        raise ValueError("backup schema or application version is incompatible")
    dump_major = _version_major(manifest.postgres_tool_version)
    restore_major = _version_major(_tool_version("pg_restore"))
    if restore_major < dump_major:
        raise ValueError("pg_restore is older than the pg_dump that created this archive")
    return manifest


def secrets_compare(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode(), right.encode())


def _version_major(value: str) -> int:
    for word in value.replace("(", " ").replace(")", " ").split():
        if word[0:1].isdigit():
            return int(word.split(".", 1)[0])
    raise ValueError("could not determine PostgreSQL tool version")


def _prove_empty(database: Database) -> None:
    """Accept template0 defaults and our empty recovery schema, no other user objects."""
    with database.engine.connect() as connection:
        unexpected = connection.scalar(
            text("""
            SELECT EXISTS (
              SELECT 1 FROM pg_namespace
              WHERE nspname NOT IN ('public', 'information_schema', 'lm_recovery')
                AND nspname NOT LIKE 'pg_%'
              UNION ALL
              SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
              WHERE n.nspname IN ('public', 'lm_recovery')
              UNION ALL
              SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
              WHERE n.nspname IN ('public', 'lm_recovery')
              UNION ALL
              SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
              WHERE n.nspname IN ('public', 'lm_recovery')
              UNION ALL SELECT 1 FROM pg_extension WHERE extname <> 'plpgsql'
              UNION ALL SELECT 1 FROM pg_foreign_server
              UNION ALL SELECT 1 FROM pg_foreign_data_wrapper
              UNION ALL SELECT 1 FROM pg_event_trigger
              UNION ALL SELECT 1 FROM pg_publication
              UNION ALL SELECT 1 FROM pg_language
                WHERE lanname NOT IN ('internal', 'c', 'sql', 'plpgsql')
              UNION ALL SELECT 1 FROM pg_operator x JOIN pg_namespace n ON n.oid=x.oprnamespace
                WHERE n.nspname IN ('public', 'lm_recovery')
              UNION ALL SELECT 1 FROM pg_collation x JOIN pg_namespace n ON n.oid=x.collnamespace
                WHERE n.nspname IN ('public', 'lm_recovery')
              UNION ALL SELECT 1 FROM pg_conversion x JOIN pg_namespace n ON n.oid=x.connamespace
                WHERE n.nspname IN ('public', 'lm_recovery')
              UNION ALL SELECT 1 FROM pg_ts_config x JOIN pg_namespace n ON n.oid=x.cfgnamespace
                WHERE n.nspname IN ('public', 'lm_recovery')
              UNION ALL SELECT 1 FROM pg_ts_dict x JOIN pg_namespace n ON n.oid=x.dictnamespace
                WHERE n.nspname IN ('public', 'lm_recovery')
            )
        """)
        )
        if unexpected:
            raise ValueError("Restore requires an empty template0 database")


class RecoveryFailure(RuntimeError):
    """The target was guarded and must not be served after failed recovery."""


def _domain_inventory(database: Database) -> dict[str, Any]:
    with database.transaction() as db_session:
        return _domain_inventory_session(db_session)


def _domain_inventory_session(db_session: Session) -> dict[str, Any]:
    from living_memory.administration import AdminGame, ConfigurationRevision
    from living_memory.identity import (
        AdministratorAlert,
        ExternalIdentityBinding,
        GameRole,
        GlobalRole,
        PendingAccessRequest,
        ProviderGroupMapping,
        TeamMembership,
        User,
    )
    from living_memory.workspace import (
        Amendment,
        AmendmentDecision,
        Coordination,
        CoordinationLink,
        Draft,
        DraftAction,
        DraftComment,
        DraftRevision,
        RequestKey,
        Rfi,
        RfiLink,
        SubmissionVersion,
        SubmittedAction,
        WorkspaceImport,
    )

    models = {
        "users": User,
        "global_roles": GlobalRole,
        "game_roles": GameRole,
        "memberships": TeamMembership,
        "external_bindings": ExternalIdentityBinding,
        "pending_requests": PendingAccessRequest,
        "provider_mappings": ProviderGroupMapping,
        "alerts": AdministratorAlert,
        "games": AdminGame,
        "configuration_revisions": ConfigurationRevision,
        "memory_datasets": Dataset,
        "sessions": AuthSession,
        "request_keys": RequestKey,
        "drafts": Draft,
        "draft_actions": DraftAction,
        "draft_revisions": DraftRevision,
        "draft_comments": DraftComment,
        "amendments": Amendment,
        "submitted_actions": SubmittedAction,
        "submission_versions": SubmissionVersion,
        "imports": WorkspaceImport,
        "amendment_decisions": AmendmentDecision,
        "rfis": Rfi,
        "rfi_links": RfiLink,
        "coordinations": Coordination,
        "coordination_links": CoordinationLink,
    }
    counts = {
        name: int(db_session.scalar(select(func.count()).select_from(model)) or 0)
        for name, model in models.items()
    }
    counts["deactivated_users"] = int(
        db_session.scalar(select(func.count()).select_from(User).where(User.active.is_(False))) or 0
    )
    packages = [
        {
            "package": artifact.package,
            "checksum": artifact.checksum,
            "rebuild_status": rebuild.status if rebuild else None,
            "rebuild_detail": rebuild.detail if rebuild else None,
        }
        for artifact, rebuild in db_session.execute(
            select(DevelopmentArtifact, RebuildState)
            .outerjoin(RebuildState, RebuildState.artifact_id == DevelopmentArtifact.id)
            .order_by(DevelopmentArtifact.package, DevelopmentArtifact.checksum)
        )
    ]
    return {"counts": counts, "staged_packages": packages}


def _verify_domain(database: Database) -> dict[str, Any]:
    if not database.schema_ready():
        raise ValueError("restored Alembic heads do not match the application")
    from living_memory.administration import ConfigurationRevision, ScenarioConfiguration

    with database.transaction() as db_session:
        for revision in db_session.scalars(select(ConfigurationRevision)):
            ScenarioConfiguration.model_validate(revision.configuration)
        duplicate_artifacts = db_session.execute(
            select(DevelopmentArtifact.package, DevelopmentArtifact.checksum)
            .group_by(DevelopmentArtifact.package, DevelopmentArtifact.checksum)
            .having(func.count() > 1)
        ).first()
        orphan_rebuild = db_session.scalars(
            select(RebuildState.artifact_id)
            .outerjoin(DevelopmentArtifact, DevelopmentArtifact.id == RebuildState.artifact_id)
            .where(DevelopmentArtifact.id.is_(None))
        ).first()
        orphan_dataset = db_session.scalars(
            select(Dataset.id)
            .outerjoin(DevelopmentArtifact, DevelopmentArtifact.id == Dataset.id)
            .where(DevelopmentArtifact.id.is_(None))
        ).first()
        if duplicate_artifacts or orphan_rebuild or orphan_dataset:
            raise ValueError("restored domain invariants failed")
    return _domain_inventory(database)


def restore_backup(database_url: str, archive: Path) -> int:
    """Guard an explicit empty target until restore, revocation and verification succeed."""
    manifest = verify_backup(archive)
    url = make_url(database_url)
    database = _database_for_url(database_url)
    try:
        with database.engine.connect() as guard:
            locked = guard.scalar(text("SELECT pg_try_advisory_lock(724103, 1)"))
            guard.commit()
            if not locked:
                raise ValueError("Another recovery owns this target")
            try:
                _prove_empty(database)
                guard.execute(text("CREATE SCHEMA IF NOT EXISTS lm_recovery"))
                guard.commit()
                try:
                    _run(
                        [
                            "pg_restore",
                            "--no-owner",
                            "--no-acl",
                            "--exit-on-error",
                            "--single-transaction",
                            "--exclude-schema=lm_recovery",
                            *_connection_arguments(url),
                            str(archive),
                        ],
                        url,
                    )
                    with database.transaction() as session:
                        revoked = revoke_all_sessions_after_restore(session, datetime.now(UTC))
                    # Keep this legacy inventory shape unchanged for 0004 archives.
                    restored_inventory = _verify_domain(database)
                    if restored_inventory != manifest.domain_inventory:
                        raise ValueError("Restored inventory differs from the backup manifest")
                    with database.transaction() as session:
                        if session.scalar(
                            select(func.count())
                            .select_from(AuthSession)
                            .where(AuthSession.revoked_at.is_(None))
                        ):
                            raise ValueError("Restored sessions were not revoked")
                    # No CASCADE: unexpected recovery objects must prevent unblocking.
                    guard.execute(text("DROP SCHEMA lm_recovery"))
                    guard.commit()
                    return revoked
                except Exception as exc:
                    guard.rollback()
                    raise RecoveryFailure(
                        "Recovery target remains blocked. Dispose of this target and retry "
                        "into a fresh template0 database."
                    ) from exc
            finally:
                guard.execute(text("SELECT pg_advisory_unlock(724103, 1)"))
                guard.commit()
    finally:
        database.close()


def _database_for_url(database_url: str) -> Database:
    from living_memory.config import Settings

    return Database(
        Settings.model_validate(
            {"session_secret": SecretStr("x" * 32), "database_url": SecretStr(database_url)}
        )
    )
