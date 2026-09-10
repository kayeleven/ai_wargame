import hashlib
import json
import re

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from sqlalchemy.exc import OperationalError, TimeoutError

from living_memory.app import ASSETS, create_app
from living_memory.config import Settings, load_settings


class FakeDatabase:
    available = True
    error = None
    closed = False

    def ready(self):
        if self.error:
            raise self.error
        return self.available

    def close(self):
        self.closed = True


def token(client):
    response = client.get("/dev/forms")
    return re.search(r'name="csrf_token" value="([^"]+)"', response.text)[1]


@pytest.mark.parametrize("htmx", [False, True])
def test_form_round_trip(settings, htmx):
    db = FakeDatabase()
    with TestClient(create_app(settings, db)) as client:
        csrf = token(client)
        headers = {"HX-Request": "true"} if htmx else {}
        data = {"csrf_token": csrf, "title": "", "actions": [" Second\nline ", "<first>"]}
        response = client.post("/dev/forms", data=data, headers=headers)
        assert response.status_code == 422
        assert ("<!doctype html>" in response.text) is not htmx
        assert " Second\nline " in response.text
        assert "&lt;first&gt;" in response.text
        assert response.text.index(" Second") < response.text.index("&lt;first&gt;")
        assert 'aria-invalid="true"' in response.text
        blank = client.post("/dev/forms", data={**data, "title": " "}, headers=headers)
        assert blank.status_code == 422
        assert "Enter a title and both actions." in blank.text
        data["title"] = " accepted "
        response = client.post("/dev/forms", data=data, headers=headers, follow_redirects=False)
        assert response.status_code == (200 if htmx else 303)
        assert response.headers["HX-Redirect" if htmx else "location"] == "/dev/forms"
        assert "Form accepted." in client.get("/dev/forms").text
        assert "Form accepted." not in client.get("/dev/forms").text
        assert "accepted" not in client.cookies["lm_session"]
    assert db.closed


@pytest.mark.parametrize("headers", [{}, {"HX-Request": "true"}])
def test_csrf(settings, headers):
    with TestClient(create_app(settings, FakeDatabase())) as client:
        csrf = token(client)
        data = {"title": "a", "actions": ["x", "y"]}
        assert client.post("/dev/forms", data=data, headers=headers).status_code == 403
        for wrong in ("invalid", "é"):
            assert (
                client.post(
                    "/dev/forms", data={**data, "csrf_token": wrong}, headers=headers
                ).status_code
                == 403
            )
        response = client.post(
            "/dev/forms",
            data=data,
            headers={**headers, "X-CSRF-Token": csrf},
            follow_redirects=False,
        )
        assert response.status_code in (200, 303)


def test_sessions_and_development_boundary(settings):
    with TestClient(create_app(settings, FakeDatabase())) as client:
        response = client.get("/dev/forms")
        cookie = response.headers["set-cookie"].lower()
        assert "httponly" in cookie and "samesite=lax" in cookie
        assert client.get("/docs").status_code == 200
    production = settings.model_copy(update={"environment": "production", "secure_cookies": True})
    with TestClient(
        create_app(production, FakeDatabase()), base_url="https://testserver"
    ) as client:
        assert client.get("/dev/forms").status_code == 404
        assert "form demonstration" not in client.get("/").text


def test_health_and_safe_diagnostics(settings, caplog):
    db = FakeDatabase()
    with TestClient(create_app(settings, db)) as client, caplog.at_level("INFO"):
        assert client.get("/health/ready").status_code == 200
        db.available = False
        assert client.get("/health/ready").status_code == 503
        for error, category in [
            (TimeoutError("secret SQL params"), "pool_checkout"),
            (OperationalError("secret SQL", {}, Exception("password")), "database_unavailable"),
        ]:
            db.error = error
            response = client.get("/health/ready?password=hidden")
            assert response.status_code == 503
            assert client.get("/health/live").status_code == 200
            assert response.json()["request_id"] == response.headers["x-request-id"]
            records = [
                json.loads(r.message) for r in caplog.records if r.name == "living_memory.requests"
            ]
            assert any(r["database_timeout_category"] == category for r in records)
        db.error = RuntimeError("private content")
        response = client.get("/health/ready")
        assert response.status_code == 500
        assert "private" not in response.text
        assert all(
            s
            not in " ".join(r.message for r in caplog.records if r.name == "living_memory.requests")
            for s in ("secret SQL", "password", "private content")
        )
        db.error = None
        db.available = True
        assert client.get("/health/ready").status_code == 200


def test_configuration_redacts_secrets(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LM_SESSION_SECRET", "sensitive")
    with pytest.raises(RuntimeError) as exc:
        load_settings()
    assert "sensitive" not in str(exc.value)
    assert "session_secret" in str(exc.value)
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            session_secret=SecretStr("x" * 32),
            database_url=SecretStr("sqlite:///bad"),
        )
    with pytest.raises(ValidationError):
        Settings(_env_file=None, session_secret=SecretStr("x" * 32), environment="production")


def test_asset_integrity(settings):
    asset = ASSETS / "static/vendor/htmx-2.0.4.min.js"
    assert hashlib.sha256(asset.read_bytes()).hexdigest() == (
        "e209dda5c8235479f3166defc7750e1dbcd5a5c1808b7792fc2e6733768fb447"
    )
    with TestClient(create_app(settings, FakeDatabase())) as client:
        assert client.get("/static/vendor/htmx-2.0.4.min.js").status_code == 200
        assert client.get("/static/app.css").status_code == 200
