"""Development-only read-only memory presentation."""

from datetime import datetime
from typing import Literal
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from living_memory.clocks import GameTime
from living_memory.db import Database, DevelopmentArtifact
from living_memory.memory import (
    MemoryQuery,
    MemoryReader,
    ReadModel,
    RecordSummary,
    Timeline,
    development_principal,
)

CHECKPOINTS = {
    "t3": ("2030-04-03T23:00:00+00:00", 14),
    "review": ("2030-04-04T14:00:00+00:00", 21),
    "release": ("2030-04-04T20:00:00+00:00", 21),
}
TASKS = {
    "timeline": None,
    "continuing": {"commitment", "effect", "coordination", "ruling"},
    "review": {
        "scenario",
        "submission",
        "import",
        "review_note",
        "amendment",
        "claim",
        "observation",
        "rfi",
    },
    "feedback": {"feedback", "rfi", "rfi_response", "observation", "commitment"},
}
IDENTITIES = ("reviewer", "estuary-lead", "estuary-member", "upland-lead", "upland-member")


class ViewContext(ReadModel):
    known_at: datetime


class DatasetView(ReadModel):
    id: UUID
    label: str


def explorer_router(db: Database, templates: Jinja2Templates) -> APIRouter:
    router = APIRouter()
    reader = MemoryReader(db)

    @router.get("/dev/memory", response_class=HTMLResponse)
    def explore(
        request: Request,
        identity: str = "estuary-member",
        audience: str | None = None,
        dataset: UUID | None = None,
        checkpoint: Literal["t3", "review", "release"] = "review",
        task: Literal["timeline", "continuing", "review", "feedback"] = "timeline",
        record: str | None = None,
    ) -> Response:
        try:
            principal = development_principal(identity)
            audience = audience or principal.audiences[0]
            if audience not in principal.audiences:
                raise PermissionError()
            with db.transaction() as session:
                datasets = tuple(
                    DatasetView(id=a.id, label=f"Fixture v{a.package_version} · {a.checksum[:12]}")
                    for a in session.execute(
                        select(
                            DevelopmentArtifact.id,
                            DevelopmentArtifact.package_version,
                            DevelopmentArtifact.checksum,
                        )
                        .join(Timeline)
                        .where(Timeline.game_id == principal.game_id)
                        .order_by(DevelopmentArtifact.staged_at.desc())
                    )
                )
            dataset = dataset or (datasets[0].id if datasets else None)
            if dataset is None and record is not None:
                raise LookupError("Not found")
            view = None
            if dataset is not None:
                lineage = reader.lineage(dataset, principal.game_id)
                cutoff, days = CHECKPOINTS[checkpoint]
                view = reader.read_memory(
                    principal,
                    principal.game_id,
                    audience,
                    lineage,
                    datetime.fromisoformat(cutoff),
                    GameTime(elapsed_microseconds=days * 86400 * 1000000),
                    MemoryQuery(dataset_id=dataset, record_id=record),
                )
            allowed = TASKS[task]
            records = (
                tuple(
                    RecordSummary.model_validate(r.model_dump(exclude={"body"}))
                    for r in view.records
                    if record or allowed is None or r.kind in allowed
                )
                if view
                else ()
            )

            def link(record_id: str | None = None) -> str:
                values = {
                    "identity": identity,
                    "audience": audience,
                    "dataset": str(dataset),
                    "checkpoint": checkpoint,
                    "task": task,
                }
                if record_id is not None:
                    values["record"] = record_id
                return "/dev/memory?" + urlencode(values)

            return templates.TemplateResponse(
                request=request,
                name="memory.html",
                context={
                    "identities": IDENTITIES,
                    "identity": identity,
                    "audiences": principal.audiences,
                    "audience": audience,
                    "datasets": datasets,
                    "dataset": dataset,
                    "checkpoint": checkpoint,
                    "task": task,
                    "tasks": tuple(TASKS),
                    "view": ViewContext(known_at=view.known_at) if view else None,
                    "records": records,
                    "detail": record is not None,
                    "link": link,
                },
                headers={"Cache-Control": "no-store"},
            )
        except PermissionError:
            raise HTTPException(403, "Audience not permitted") from None
        except LookupError:
            raise HTTPException(404, "Not found") from None

    return router
