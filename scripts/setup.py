"""Report prerequisites; never install host tooling."""

import shutil
import subprocess
import sys

missing = []
for name in ("make", "python3.12", "uv", "docker", "pg_dump", "pg_restore"):
    if not shutil.which(name):
        missing.append(name)
if "docker" not in missing:
    if subprocess.run(["docker", "compose", "version"], capture_output=True).returncode:
        missing.append("Docker Compose v2")
if missing:
    sys.exit(
        "Missing host prerequisites: " + ", ".join(missing)
        + ". See docs/development.md; recovery tests require PostgreSQL 16 client tools on PATH."
    )
subprocess.run(["uv", "sync", "--locked"], check=True)
