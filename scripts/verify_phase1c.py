"""Run the isolated fresh-copy/empty-volume Phase 1C gate; never reuse a project volume."""

import io
import os
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
LEGACY = "0b781de949e999f36358079ee361f7f1ded5893d"


def main():
    workspace = Path(tempfile.mkdtemp(prefix="lm-phase1c-gate-"))
    checkout = workspace / "checkout"
    checkout.mkdir()
    names = (
        subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        .stdout.decode()
        .split("\0")
    )
    for name in filter(None, names):
        source = ROOT / name
        if source.is_file():
            target = checkout / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    legacy = workspace / "legacy"
    legacy.mkdir()
    contents = subprocess.run(
        ["git", "archive", LEGACY, "src"], cwd=ROOT, check=True, capture_output=True
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(contents)) as archive:
        archive.extractall(legacy, filter="data")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    compose_file = checkout / "compose.yaml"
    compose_file.write_text(
        compose_file.read_text().replace("127.0.0.1:5432:5432", f"127.0.0.1:{port}:5432")
    )
    project = "lm_correction_gate_" + uuid4().hex[:12]
    environment = os.environ.copy()
    environment.update(
        {
            "LM_SESSION_SECRET": uuid4().hex + uuid4().hex,
            "LM_DATABASE_URL": f"postgresql+psycopg://living_memory:local-development-only@127.0.0.1:{port}/living_memory_dev",
            "LM_TEST_DATABASE_URL": f"postgresql+psycopg://living_memory_test:local-test-only@127.0.0.1:{port}/living_memory_test",
            "LM_TEST_DB_CONTAINER": f"{project}-db-1",
            "LM_LEGACY_SOURCE": str(legacy),
        }
    )
    compose = ["docker", "compose", "-p", project, "-f", str(compose_file)]
    log = workspace / "verification.log"
    with log.open("w") as transcript:

        def run(args):
            print("Running:", " ".join(args), flush=True)
            subprocess.run(
                args,
                cwd=checkout,
                env=environment,
                stdout=transcript,
                stderr=subprocess.STDOUT,
                check=True,
            )
            transcript.flush()

        try:
            run([sys.executable, "scripts/setup.py"])
            python = str(checkout / ".venv/bin/python")
            run(compose + ["up", "-d", "--wait", "db"])
            for _ in range(2):
                run([python, "-m", "living_memory.cli", "migrate"])
            for _ in range(2):
                for fixture in ("phase0", "orchid-accord"):
                    run([python, "-m", "living_memory.cli", "seed", "--fixture", fixture])
            run([str(checkout / ".venv/bin/ruff"), "check", "."])
            run([str(checkout / ".venv/bin/mypy")])
            run([python, "-m", "pytest", "tests", "-q", "--tb=short"])
            run(compose + ["restart", "db"])
            run(compose + ["up", "-d", "--wait", "db"])
            run(
                [
                    python,
                    "-c",
                    "from living_memory.config import load_settings; "
                    "from living_memory.db import Database; from sqlalchemy import text; "
                    "d=Database(load_settings()); assert d.ready(); "
                    "c=d.engine.connect(); "
                    "assert c.scalar(text('SELECT count(*) FROM development_artifact')) == 2; "
                    "c.close(); d.close(); print('Restart: two staged artifacts persisted')",
                ]
            )
            print("Gate passed. Evidence:", log, flush=True)
        finally:
            run(compose + ["down", "-v", "--remove-orphans"])
            print("Gate transcript:", log, flush=True)


if __name__ == "__main__":
    main()
