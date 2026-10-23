"""Small filesystem helpers."""

import os
from pathlib import Path


def atomic_write_bytes(path: Path, content: bytes) -> None:
    """Write via a temporary sibling and rename, so readers never see a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_bytes(content)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def atomic_write_text(path: Path, text: str) -> None:
    """UTF-8 with LF line endings, written atomically."""
    atomic_write_bytes(path, text.encode("utf-8"))
