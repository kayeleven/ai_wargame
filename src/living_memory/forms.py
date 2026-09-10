import secrets
from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field, ValidationError, model_validator
from starlette.datastructures import FormData


class DemoInput(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    actions: list[str] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def nonblank(self) -> "DemoInput":
        if not self.title.strip() or not all(action.strip() for action in self.actions):
            raise ValueError("Enter a title and both actions.")
        return self


@dataclass
class BoundForm:
    values: dict[str, Any] = field(default_factory=lambda: {"title": "", "actions": ["", ""]})
    errors: dict[str, list[str]] = field(default_factory=dict)
    valid: BaseModel | None = None


def bind_form(model: type[BaseModel], fields: FormData, repeated: set[str]) -> BoundForm:
    values = {
        name: fields.getlist(name) if name in repeated else fields.get(name, "")
        for name in model.model_fields
    }
    bound = BoundForm(values=values)
    try:
        bound.valid = model.model_validate(values)
    except ValidationError as exc:
        for error in exc.errors(include_input=False, include_url=False):
            location = ".".join(map(str, error["loc"])) or "_form"
            bound.errors.setdefault(location, []).append(error["msg"])
    return bound


def csrf_token(request: Request) -> str:
    if "csrf" not in request.session:
        request.session["csrf"] = secrets.token_urlsafe(32)
    return str(request.session["csrf"])


async def require_csrf(request: Request) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    supplied = request.headers.get("x-csrf-token")
    if supplied is None:
        form = await request.form(max_files=0, max_fields=100, max_part_size=64 * 1024)
        value = form.get("csrf_token")
        supplied = value if isinstance(value, str) else None
    expected = request.session.get("csrf")
    if (
        not isinstance(expected, str)
        or not supplied
        or not secrets.compare_digest(expected.encode(), supplied.encode())
    ):
        raise HTTPException(403, "Invalid or missing CSRF token")


FLASH_MESSAGES = {"demo_saved": "Form accepted. No game data was changed."}


def flash(request: Request, code: str) -> None:
    if code not in FLASH_MESSAGES:
        raise ValueError("unknown flash code")
    request.session["flash"] = code


def pop_flash(request: Request) -> str | None:
    return FLASH_MESSAGES.get(request.session.pop("flash", None))
