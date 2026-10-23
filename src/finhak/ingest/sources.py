"""The curated document list (data/sources.yaml)."""

from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

DocType = Literal["kanun", "yonetmelik", "teblig"]

MEVZUAT_PAGE_URL = (
    "https://www.mevzuat.gov.tr/mevzuat?MevzuatNo={no}&MevzuatTur={tur}&MevzuatTertip=5"
)
# MevzuatTur codes used by mevzuat.gov.tr for each document type in the corpus.
TUR_FOR_DOC_TYPE: dict[str, int] = {"kanun": 1, "yonetmelik": 7, "teblig": 9}
# The id becomes a directory name under data/raw/, so it must be valid on Windows too.
WINDOWS_RESERVED_NAMES = frozenset(
    {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{i}" for i in range(1, 10)),
        *(f"lpt{i}" for i in range(1, 10)),
    }
)


class SourcesError(ValueError):
    """data/sources.yaml is malformed or inconsistent."""


class SourceSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    label: str
    expected_title: str | None
    doc_type: DocType
    mevzuat_no: int = Field(gt=0)
    mevzuat_tur: Literal[1, 7, 9]
    number: str | None
    issuer: str
    expected_rg_date: date | None
    expected_rg_number: str | None

    @field_validator("id")
    @classmethod
    def _id_is_a_usable_directory_name(cls, value: str) -> str:
        if value in WINDOWS_RESERVED_NAMES:
            raise ValueError(f"{value!r} is a reserved file name on Windows")
        return value

    @model_validator(mode="after")
    def _tur_matches_doc_type(self) -> "SourceSpec":
        expected = TUR_FOR_DOC_TYPE[self.doc_type]
        if self.mevzuat_tur != expected:
            raise ValueError(
                f"{self.id}: doc_type {self.doc_type!r} needs mevzuat_tur {expected}, "
                f"got {self.mevzuat_tur}"
            )
        return self

    @property
    def page_url(self) -> str:
        return MEVZUAT_PAGE_URL.format(no=self.mevzuat_no, tur=self.mevzuat_tur)


def load_sources(path: Path) -> tuple[SourceSpec, ...]:
    """Load and validate the source list; ids must be unique."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SourcesError(f"{path}: cannot read: {exc}") from exc
    except yaml.YAMLError as exc:
        raise SourcesError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("sources"), list):
        raise SourcesError(f"{path}: expected a top-level 'sources' list")

    try:
        specs = tuple(SourceSpec.model_validate(item) for item in raw["sources"])
    except ValidationError as exc:
        raise SourcesError(f"{path}: {exc}") from exc

    seen: set[str] = set()
    for spec in specs:
        if spec.id in seen:
            raise SourcesError(f"{path}: duplicate id {spec.id!r}")
        seen.add(spec.id)
    return specs
