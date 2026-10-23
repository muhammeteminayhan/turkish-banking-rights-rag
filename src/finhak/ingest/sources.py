"""The curated document list (data/sources.yaml).

Two origins are supported:
- `mevzuat`: a consolidated text on mevzuat.gov.tr, identified by MevzuatNo / MevzuatTur;
- `tcmb`: a document published only on www.tcmb.gov.tr, found by its link text on a TCMB
  listing page (the file URL changes with every new version, so it is never hard-coded).
"""

from datetime import date
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

DocType = Literal["kanun", "yonetmelik", "teblig", "talimat"]
Origin = Literal["mevzuat", "tcmb"]

MEVZUAT_PAGE_URL = (
    "https://www.mevzuat.gov.tr/mevzuat?MevzuatNo={no}&MevzuatTur={tur}&MevzuatTertip=5"
)
TCMB_HOST = "www.tcmb.gov.tr"
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
_MEVZUAT_ONLY = ("mevzuat_no", "mevzuat_tur", "expected_rg_date", "expected_rg_number")
_TCMB_ONLY = ("listing_url", "link_text", "expected_version_date")


class SourcesError(ValueError):
    """data/sources.yaml is malformed or inconsistent."""


class SourceSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    label: str
    expected_title: str | None
    doc_type: DocType
    number: str | None
    issuer: str
    origin: Origin = "mevzuat"
    # origin: mevzuat
    mevzuat_no: int | None = Field(default=None, gt=0)
    mevzuat_tur: Literal[1, 7, 9] | None = None
    expected_rg_date: date | None = None
    expected_rg_number: str | None = None
    # origin: tcmb
    listing_url: str | None = None
    link_text: str | None = None
    expected_version_date: date | None = None

    @field_validator("id")
    @classmethod
    def _id_is_a_usable_directory_name(cls, value: str) -> str:
        if value in WINDOWS_RESERVED_NAMES:
            raise ValueError(f"{value!r} is a reserved file name on Windows")
        return value

    @model_validator(mode="after")
    def _fields_match_origin(self) -> "SourceSpec":
        if self.origin == "mevzuat":
            self._check_mevzuat()
        else:
            self._check_tcmb()
        return self

    def _check_mevzuat(self) -> None:
        self._forbid(_TCMB_ONLY)
        if self.doc_type not in TUR_FOR_DOC_TYPE:
            raise ValueError(f"{self.id}: doc_type {self.doc_type!r} documents come from tcmb")
        if self.mevzuat_no is None or self.mevzuat_tur is None:
            raise ValueError(f"{self.id}: mevzuat sources need mevzuat_no and mevzuat_tur")
        expected = TUR_FOR_DOC_TYPE[self.doc_type]
        if self.mevzuat_tur != expected:
            raise ValueError(
                f"{self.id}: doc_type {self.doc_type!r} needs mevzuat_tur {expected}, "
                f"got {self.mevzuat_tur}"
            )

    def _check_tcmb(self) -> None:
        self._forbid(_MEVZUAT_ONLY)
        if self.doc_type != "talimat":
            raise ValueError(f"{self.id}: tcmb sources must have doc_type 'talimat'")
        if not self.link_text:
            raise ValueError(f"{self.id}: tcmb sources need link_text")
        parts = urlsplit(self.listing_url or "")
        if parts.scheme != "https" or parts.hostname != TCMB_HOST:
            raise ValueError(f"{self.id}: listing_url must be an https URL on {TCMB_HOST}")

    def _forbid(self, names: tuple[str, ...]) -> None:
        present = [name for name in names if getattr(self, name) is not None]
        if present:
            fields = ", ".join(present)
            raise ValueError(f"{self.id}: {fields} not allowed for origin {self.origin}")

    @property
    def page_url(self) -> str:
        if self.origin == "tcmb":
            assert self.listing_url is not None  # guaranteed by _check_tcmb
            return self.listing_url
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
