"""Autogeneration and explicit checks for PostgreSQL-only schema semantics."""

from alembic import command
from sqlalchemy import text
from test_database import database  # noqa: F401

from living_memory.db import migration_config


def test_metadata_and_catalogs(database):  # noqa: F811
    db, _ = database
    config = migration_config()
    with db.engine.begin() as connection:
        config.attributes["connection"] = connection
        command.check(config)
        index = connection.execute(
            text("""
            SELECT pg_get_indexdef(i.indexrelid), i.indisvalid, am.amname
            FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid
            JOIN pg_am am ON am.oid=c.relam
            WHERE c.relname='ix_memory_record_search'
        """)
        ).one()
        assert index.indisvalid and index.amname == "gin"
        assert "to_tsvector('simple'::regconfig, (body)::text)" in index[0]
        checks = dict(
            connection.execute(
                text("""
            SELECT c.relname, pg_get_constraintdef(k.oid)
            FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid
            WHERE k.contype='c' AND c.relname IN
                ('memory_rebuild_state', 'admin_game', 'auth_team_membership', 'auth_game_role')
        """)
            ).all()
        )
        assert (
            "pending" in checks["memory_rebuild_state"]
            and "loaded" in checks["memory_rebuild_state"]
        )
        assert all(value in checks["admin_game"] for value in ("draft", "active", "completed"))
        assert "submitter" in checks["auth_team_membership"]
        assert "adjudicator" in checks["auth_game_role"]
        connection.execute(text("SET LOCAL enable_seqscan = off"))
        plan = connection.scalar(
            text("""EXPLAIN (FORMAT JSON)
            SELECT id FROM memory_record_revision WHERE
            to_tsvector('simple', CAST(body AS TEXT)) @@ plainto_tsquery('simple', 'tariff')
        """)
        )
        assert "ix_memory_record_search" in str(plan)
