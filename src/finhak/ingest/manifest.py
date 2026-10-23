"""data/manifest.json: one entry per document with provenance and checksums.

Entries are built offline from data/raw/ (no network), so the manifest can be rebuilt and
verified at any time. Curated expectations in sources.yaml are checked against what the
official page says; any disagreement aborts the build instead of being silently recorded.
"""

import datetime as dt
import hashlib
import json
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from finhak.fsutil import atomic_write_text
from finhak.ingest.fetch import (
    FETCH_LOG_NAME,
    PAGE_NAME,
    TEXT_NAME,
    CorruptFetchLog,
    FetchLog,
    detect_file_format,
    read_fetch_log,
    sha256_hex,
    source_file_name,
)
from finhak.ingest.http import FetchError
from finhak.ingest.scrape import PageInfo, TextInfo, decode_html, parse_page, parse_text
from finhak.ingest.sources import DocType, Origin, SourceSpec
from finhak.ingest.tcmb import find_listing_link, version_date_from_url
from finhak.textnorm import tr_casefold

SCHEMA_VERSION: Final = 1
# doc_html: a ".doc" download that is really a Word "web page" HTML export.
FileFormat = Literal["html_page", "html_text", "doc", "doc_html", "docx", "pdf"]
_FROZEN = ConfigDict(frozen=True, extra="forbid")


class ManifestError(RuntimeError):
    """The raw directory or the manifest file cannot be used."""


class ManifestMismatch(ManifestError):
    """sources.yaml and the official page disagree."""


class FileEntry(BaseModel):
    model_config = _FROZEN

    format: FileFormat
    path: str = Field(
        pattern=r"^[a-z0-9][a-z0-9-]*/[a-z_]+\.[a-z]+$", description="relative to data/raw"
    )
    url: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bytes: int = Field(ge=0)
    fetched_at: dt.datetime


class RejectedFile(BaseModel):
    """A linked Word/PDF file that was downloaded but refused (bytes did not match)."""

    model_config = _FROZEN

    name: str
    url: str
    reason: str
    fetched_at: dt.datetime


class LastAmendment(BaseModel):
    model_config = _FROZEN

    date: dt.date = Field(
        description=(
            "for kind 'rg' the Resmî Gazete date of the amending text; for kind 'law' the "
            "adoption date of the amending law or decree as printed in the note"
        )
    )
    kind: Literal["rg", "law"]
    reference: str


class ManifestEntry(BaseModel):
    model_config = _FROZEN

    id: str
    label: str
    origin: Origin
    title: str = Field(
        description=(
            "mevzuat: as printed at the top of the consolidated text; "
            "tcmb: the link text on the TCMB listing page"
        )
    )
    doc_type: DocType
    number: str | None
    mevzuat_no: int | None
    mevzuat_tur: int | None
    issuer: str
    rg_date: dt.date | None = Field(description="None for texts not published in the RG")
    rg_number: str | None
    version_date: dt.date | None = Field(
        description="tcmb: the version date in the file name on the issuer's site"
    )
    source_page_url: str
    files: tuple[FileEntry, ...]
    rejected_files: tuple[RejectedFile, ...]
    last_amendment: LastAmendment | None = Field(
        description="latest dated amendment note found in the consolidated text"
    )
    amendment_note_count: int | None = Field(
        description="None when the notes are not read at collection time (tcmb PDFs)"
    )
    status: Literal["in_force"] = Field(
        description=(
            "declared in sources.yaml: the text was listed as current on the official site "
            "when collected; not machine-checked"
        )
    )


class Manifest(BaseModel):
    model_config = _FROZEN

    schema_version: Literal[1]
    documents: tuple[ManifestEntry, ...]


def build_manifest(specs: Iterable[SourceSpec], raw_dir: Path) -> Manifest:
    return Manifest(
        schema_version=SCHEMA_VERSION,
        documents=tuple(build_entry(spec, raw_dir) for spec in specs),
    )


def build_entry(spec: SourceSpec, raw_dir: Path) -> ManifestEntry:
    doc_dir = raw_dir / spec.id
    try:
        log = read_fetch_log(doc_dir)
    except CorruptFetchLog as exc:
        raise ManifestError(f"{spec.id}: {exc}") from exc
    if not log.files:
        raise ManifestError(f"{spec.id}: {doc_dir / FETCH_LOG_NAME} missing; run the fetcher")
    if spec.origin == "tcmb":
        return _tcmb_entry(spec, doc_dir, log)
    return _mevzuat_entry(spec, doc_dir, log)


def _tcmb_entry(spec: SourceSpec, doc_dir: Path, log: FetchLog) -> ManifestEntry:
    link = find_listing_link(_read_html(doc_dir / PAGE_NAME), spec.page_url, spec.link_text or "")
    version = version_date_from_url(link.url)
    problems: list[str] = []
    if spec.expected_title and tr_casefold(spec.expected_title) != tr_casefold(link.text):
        problems.append(f"title: listing {link.text!r} vs sources.yaml {spec.expected_title!r}")
    if spec.expected_version_date and spec.expected_version_date != version:
        problems.append(
            f"version_date: file on the site is {version} "
            f"vs sources.yaml {spec.expected_version_date} ({link.url})"
        )
    if problems:
        raise ManifestMismatch(f"{spec.id}: " + "; ".join(problems))

    name = source_file_name(link.url)
    document = _file_entry(spec.id, doc_dir, None, name, log)
    if document.url != link.url:
        raise ManifestError(f"{spec.id}: {name} is not the file the listing links; run the fetcher")
    return ManifestEntry(
        **_curated_fields(spec),
        title=link.text,
        rg_date=None,
        rg_number=None,
        version_date=version,
        files=(_file_entry(spec.id, doc_dir, "html_page", PAGE_NAME, log), document),
        rejected_files=(),
        last_amendment=None,
        amendment_note_count=None,
    )


def _mevzuat_entry(spec: SourceSpec, doc_dir: Path, log: FetchLog) -> ManifestEntry:
    page = parse_page(_read_html(doc_dir / PAGE_NAME), spec.page_url)
    text = parse_text(_read_html(doc_dir / TEXT_NAME))
    problems = _disagreements(spec, page, text)
    if problems:
        raise ManifestMismatch(f"{spec.id}: " + "; ".join(problems))

    linked = [source_file_name(url) for url in page.file_urls]
    files = [
        _file_entry(spec.id, doc_dir, "html_page", PAGE_NAME, log),
        _file_entry(spec.id, doc_dir, "html_text", TEXT_NAME, log),
        *(
            _file_entry(spec.id, doc_dir, None, name, log)
            for name in linked
            if name not in log.rejected
        ),
    ]
    rejected = tuple(
        RejectedFile(
            name=name,
            url=log.rejected[name].url,
            reason=log.rejected[name].reason,
            fetched_at=log.rejected[name].fetched_at,
        )
        for name in linked
        if name in log.rejected
    )
    latest = text.latest_amendment
    return ManifestEntry(
        **_curated_fields(spec),
        title=text.title,
        rg_date=page.rg_date,
        rg_number=page.rg_number,
        version_date=None,
        files=tuple(files),
        rejected_files=rejected,
        last_amendment=(
            LastAmendment(date=latest.date, kind=latest.kind, reference=latest.reference)
            if latest
            else None
        ),
        amendment_note_count=len(text.amendments),
    )


def _curated_fields(spec: SourceSpec) -> dict[str, object]:
    """Fields copied from sources.yaml; the rest come from the downloaded files."""
    return {
        "id": spec.id,
        "label": spec.label,
        "origin": spec.origin,
        "doc_type": spec.doc_type,
        "number": spec.number,
        "mevzuat_no": spec.mevzuat_no,
        "mevzuat_tur": spec.mevzuat_tur,
        "issuer": spec.issuer,
        "source_page_url": spec.page_url,
        "status": "in_force",
    }


def _read_html(path: Path) -> str:
    if not path.exists():
        raise ManifestError(f"{path} missing; run the fetcher")
    return decode_html(path.read_bytes(), str(path))


def _disagreements(spec: SourceSpec, page: PageInfo, text: TextInfo) -> list[str]:
    problems: list[str] = []
    if spec.expected_title and tr_casefold(spec.expected_title) != tr_casefold(text.title):
        problems.append(f"title: page {text.title!r} vs sources.yaml {spec.expected_title!r}")
    if spec.expected_rg_date and spec.expected_rg_date != page.rg_date:
        problems.append(f"rg_date: page {page.rg_date} vs sources.yaml {spec.expected_rg_date}")
    if spec.expected_rg_number and spec.expected_rg_number != page.rg_number:
        problems.append(
            f"rg_number: page {page.rg_number} vs sources.yaml {spec.expected_rg_number}"
        )
    if spec.number != text.declared_number:
        problems.append(f"number: page {text.declared_number!r} vs sources.yaml {spec.number!r}")
    return problems


def _file_entry(
    source_id: str, doc_dir: Path, fmt: FileFormat | None, name: str, log: FetchLog
) -> FileEntry:
    """`fmt=None` means: detect the format from the downloaded bytes."""
    path = doc_dir / name
    record = log.files.get(name)
    if record is None or not path.exists():
        raise ManifestError(f"{source_id}: {name} not downloaded; run the fetcher")
    content = path.read_bytes()
    digest = sha256_hex(content)
    if digest != record.sha256:
        raise ManifestError(f"{source_id}: {name} changed since download; run the fetcher")
    try:
        detected: FileFormat = fmt or detect_file_format(name, content)
    except FetchError as exc:
        raise ManifestError(f"{source_id}: {exc}") from exc
    return FileEntry(
        format=detected,
        path=str(PurePosixPath(source_id, name)),
        url=record.url,
        sha256=digest,
        bytes=len(content),
        fetched_at=record.fetched_at,
    )


def write_manifest(manifest: Manifest, path: Path) -> None:
    atomic_write_text(path, manifest.model_dump_json(indent=2) + "\n")


def write_json_schema(path: Path) -> None:
    atomic_write_text(path, json.dumps(manifest_json_schema(), ensure_ascii=False, indent=2) + "\n")


def read_manifest(path: Path) -> Manifest:
    if not path.exists():
        raise ManifestError(f"{path}: manifest not found; run the fetcher first")
    try:
        return Manifest.model_validate_json(path.read_bytes())
    except ValidationError as exc:
        raise ManifestError(f"{path}: invalid manifest: {exc}") from exc


def manifest_json_schema() -> dict[str, object]:
    return Manifest.model_json_schema()


def verify_manifest(path: Path, raw_dir: Path) -> list[str]:
    """Recompute every checksum; returns a list of problems (empty when all files match)."""
    problems: list[str] = []
    for document in read_manifest(path).documents:
        for file in document.files:
            local = raw_dir / file.path
            if not local.exists():
                problems.append(f"missing: {file.path}")
            elif hashlib.sha256(local.read_bytes()).hexdigest() != file.sha256:
                problems.append(f"sha256 mismatch: {file.path}")
    return problems
