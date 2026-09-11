"""Read-only rollout report; does not revoke grants or rewrite legacy configuration."""

import json

from sqlalchemy import select

from living_memory.administration import AdminGame, ensure_compatible
from living_memory.clocks import SystemClock
from living_memory.config import load_settings
from living_memory.db import Database
from living_memory.identity import GameRole


def main():
    database = Database(load_settings())
    now = SystemClock().now()
    try:
        if not database.schema_ready():
            raise SystemExit(
                "Report requires schema head 0004. No data was changed; "
                "select an already migrated database before running this report."
            )
        with database.transaction() as session:
            games = []
            for game in session.scalars(select(AdminGame).order_by(AdminGame.id)):
                problem = None
                try:
                    ensure_compatible(session, game, now)
                except (ValueError, LookupError) as exc:
                    problem = str(exc)
                games.append({"game_id": game.id, "configuration_problem": problem})
            grants = [
                {
                    "game_id": role.game_id,
                    "user_id": str(role.user_id),
                    "granted_by": str(role.granted_by) if role.granted_by else None,
                    "granted_at": role.granted_at.isoformat(),
                }
                for role in session.scalars(
                    select(GameRole)
                    .where(GameRole.role == "adjudicator")
                    .order_by(GameRole.game_id, GameRole.user_id)
                )
            ]
        print(
            json.dumps(
                {
                    "recorded_at": now.isoformat(),
                    "games": games,
                    "retained_adjudicator_grants": grants,
                },
                indent=2,
            )
        )
    finally:
        database.close()


if __name__ == "__main__":
    main()
