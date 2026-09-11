"""Manifest-driven, read-only development memory presentation."""

from datetime import datetime
from urllib.parse import urlencode
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from living_memory.clocks import GameTime
from living_memory.db import Database, DevelopmentArtifact
from living_memory.memory import (
    BranchLineage,
    Dataset,
    MemoryQuery,
    MemoryReader,
    Principal,
    ReadModel,
    RebuildState,
    RecordSummary,
    VisibilityGrant,
)
from living_memory.seed import PackageManifest, SourcePackage, artifact_manifest


class ViewContext(ReadModel):
    known_at: datetime
    authorized_result_count: int
    next_cursor: str | None


class DatasetView(ReadModel):
    id: UUID
    label: str
    status: str
    manifest: PackageManifest


def _principal(manifest: PackageManifest, identity: str) -> Principal:
    source = next((item for item in manifest.development_principals if item.id == identity), None)
    if source is None:
        raise PermissionError("Unknown development principal")
    return Principal(
        identity=identity,
        grants=tuple(
            VisibilityGrant(game_id=manifest.game_id, visibility_scope_id=scope)
            for scope in source.grants
        ),
    )


def explorer_router(
    db: Database, template_engine: Jinja2Templates, cursor_secret: bytes | None = None
) -> APIRouter:
    router = APIRouter()
    templates = template_engine
    reader = MemoryReader(db, cursor_secret)

    @router.get("/dev/memory", response_class=HTMLResponse)
    def explore(
        request: Request,
        identity: str | None = None,
        audience: str | None = None,
        dataset: UUID | None = None,
        checkpoint: str | None = None,
        task: str | None = None,
        record: str | None = None,
        search: str | None = None,
        record_type: str | None = None,
        relationship_type: str | None = None,
        cursor: str | None = None,
    ) -> Response:
        try:
            with db.transaction() as session:
                rows = session.execute(
                    select(DevelopmentArtifact, Dataset, RebuildState)
                    .outerjoin(Dataset, Dataset.id == DevelopmentArtifact.id)
                    .outerjoin(RebuildState, RebuildState.artifact_id == DevelopmentArtifact.id)
                    .order_by(DevelopmentArtifact.staged_at.desc())
                )
                datasets = tuple(
                    DatasetView(
                        id=artifact.id,
                        label=(loaded.label if loaded else artifact.package),
                        status=(state.status if state else ("loaded" if loaded else "pending")),
                        manifest=artifact_manifest(
                            artifact.package,
                            SourcePackage.model_validate_json(
                                artifact.contents.get("_records.json")
                                or artifact.contents.get("source.json")
                            ),
                            artifact.contents,
                        ),
                    )
                    for artifact, loaded, state in rows
                )
            chosen = next((item for item in datasets if item.id == dataset), None)
            if chosen is None:
                chosen = next((item for item in datasets if item.status == "loaded"), None)
            if chosen is None or chosen.status != "loaded":
                return templates.TemplateResponse(
                    request=request,
                    name="memory.html",
                    context={
                        "datasets": datasets,
                        "dataset": chosen.id if chosen else None,
                        "view": None,
                        "records": (),
                        "identities": (),
                    },
                    headers={"Cache-Control": "no-store"},
                )
            manifest = chosen.manifest
            identities = tuple(item.id for item in manifest.development_principals)
            identity_was_valid = identity in identities
            selected_identity = (
                identity
                if identity_was_valid and identity is not None
                else (manifest.default_principal or identities[0])
            )
            identity = selected_identity
            principal = _principal(manifest, selected_identity)
            audiences = principal.audiences
            if audience is not None and audience not in audiences and identity_was_valid:
                raise PermissionError("Visibility scope not permitted")
            audience = audience if audience in audiences else audiences[0]
            checkpoints = {item.id: item for item in manifest.checkpoints}
            checkpoint = (
                checkpoint
                if checkpoint in checkpoints
                else (manifest.default_checkpoint or next(iter(checkpoints)))
            )
            selected_checkpoint = checkpoints[checkpoint]
            presets = {item.id: item for item in manifest.explorer_presets}
            task = (
                task
                if task in presets
                else (manifest.default_preset or (next(iter(presets)) if presets else "all"))
            )
            preset = presets.get(task)
            requested_types: tuple[str, ...] = (record_type,) if record_type else ()
            if not requested_types and preset and preset.record_types:
                requested_types = tuple(preset.record_types)
            query = MemoryQuery(
                dataset_id=chosen.id,
                record_id=record,
                text=search,
                record_types=requested_types,
                relationship_types=(relationship_type,) if relationship_type else (),
                cursor=cursor,
            )
            view = reader.read_memory(
                principal,
                manifest.game_id,
                audience,
                BranchLineage(root=manifest.root_branch_id),
                selected_checkpoint.known_at,
                GameTime(elapsed_microseconds=selected_checkpoint.effective_at),
                query,
            )
            records = tuple(
                RecordSummary.model_validate(item.model_dump(exclude={"body"}))
                for item in view.records
            )

            def link(record_id: str | None = None, next_cursor: str | None = None) -> str:
                values = {
                    "identity": identity,
                    "audience": audience,
                    "dataset": str(chosen.id),
                    "checkpoint": checkpoint,
                    "task": task,
                }
                if search:
                    values["search"] = search
                if record_type:
                    values["record_type"] = record_type
                if relationship_type:
                    values["relationship_type"] = relationship_type
                if record_id:
                    values["record"] = record_id
                if next_cursor:
                    values["cursor"] = next_cursor
                return "/dev/memory?" + urlencode(values)

            return templates.TemplateResponse(
                request=request,
                name="memory.html",
                context={
                    "identities": identities,
                    "identity": identity,
                    "audiences": audiences,
                    "audience": audience,
                    "datasets": datasets,
                    "dataset": chosen.id,
                    "checkpoints": tuple(manifest.checkpoints),
                    "checkpoint": checkpoint,
                    "task": task,
                    "tasks": tuple(manifest.explorer_presets),
                    "record_types": tuple(manifest.record_types),
                    "record_type": record_type,
                    "relationship_types": tuple(manifest.relationship_types),
                    "relationship_type": relationship_type,
                    "search": search or "",
                    "view": ViewContext(
                        known_at=view.known_at,
                        authorized_result_count=view.authorized_result_count,
                        next_cursor=view.next_cursor,
                    ),
                    "records": records,
                    "detail": record is not None,
                    "link": link,
                },
                headers={"Cache-Control": "no-store"},
            )
        except PermissionError:
            raise HTTPException(403, "Visibility scope not permitted") from None
        except LookupError:
            raise HTTPException(404, "Not found") from None
        except ValueError as exc:
            if "cursor" in str(exc).lower():
                raise HTTPException(400, "Invalid memory cursor") from None
            raise

    return router
