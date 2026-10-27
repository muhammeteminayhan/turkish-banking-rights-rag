"""Settings read from the environment, then from a .env file, then defaults."""

import os
from collections.abc import Mapping
from pathlib import Path

# Matches docker-compose.yml (db published on 127.0.0.1:5433) and .env.example. An IP, not
# "localhost": on Windows that tries ::1 first and waits for the timeout before IPv4.
DEFAULT_DATABASE_URL = "postgresql://finhak:finhak@127.0.0.1:5433/finhak"


def read_env_file(path: Path) -> dict[str, str]:
    """KEY=VALUE lines of a .env file ("export KEY=…" too). Comments, blank and malformed
    lines are skipped; an unquoted value ends at " #"."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return {}
    values: dict[str, str] = {}
    for line in lines:
        key, sep, value = line.strip().removeprefix("export ").partition("=")
        if not sep or key.startswith("#") or not key.strip():
            continue
        values[key.strip()] = _unquote(value.strip())
    return values


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] in "'\"" and value[-1] == value[0]:
        return value[1:-1]
    return value.split(" #", 1)[0].strip()


def merged_env(
    environ: Mapping[str, str] | None = None, env_file: Path = Path(".env")
) -> dict[str, str]:
    """The .env settings overlaid with the non-empty environment variables."""
    env = os.environ if environ is None else environ
    return {**read_env_file(env_file), **{key: value for key, value in env.items() if value}}


def database_url(environ: Mapping[str, str] | None = None, env_file: Path = Path(".env")) -> str:
    env = os.environ if environ is None else environ
    return (
        env.get("DATABASE_URL")
        or read_env_file(env_file).get("DATABASE_URL")
        or DEFAULT_DATABASE_URL
    )
