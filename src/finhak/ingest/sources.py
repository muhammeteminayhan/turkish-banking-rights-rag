"""The curated document list (data/sources.yaml).

Two kinds of source, told apart by `origin` (default `mevzuat`):
- `MevzuatSource`: a consolidated text on mevzuat.gov.tr, identified by MevzuatNo /
  MevzuatTur; every expectation must be written out (an unverified one as explicit null);
- `TcmbSource`: a document published only on www.tcmb.gov.tr, found on a listing page by
  its link text (the file URL changes with every version, so it is never hard-coded).
"""

from datetime import date
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    Tag,
    TypeAdapter,
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


class SourcesError(ValueError):
    """data/sources.yaml is malformed or inconsistent."""


class _Source(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    label: str
    number: str | None
    issuer: str

    @field_validator("id")
    @classmethod
    def _id_is_a_usable_directory_name(cls, value: str) -> str:
        if value in WINDOWS_RESERVED_NAMES:
            raise ValueError(f"{value!r} is a reserved file name on Windows")
        return value


class MevzuatSource(_Source):
    origin: Literal["mevzuat"] = "mevzuat"
    doc_type: Literal["kanun", "yonetmelik", "teblig"]
    mevzuat_no: int = Field(gt=0)
    mevzuat_tur: Literal[1, 7, 9]
    expected_title: str | None
    expected_rg_date: date | None
    expected_rg_number: str | None

    @model_validator(mode="after")
    def _tur_matches_doc_type(self) -> "MevzuatSource":
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


class TcmbSource(_Source):
    origin: Literal["tcmb"]
    doc_type: Literal["talimat"]
    listing_url: str
    link_text: str
    expected_version_date: date

    @field_validator("link_text")
    @classmethod
    def _link_text_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("link_text must not be blank")
        return value

    @field_validator("listing_url")
    @classmethod
    def _listing_is_on_tcmb(cls, value: str) -> str:
        parts = urlsplit(value)
        try:
            port = parts.port
        except ValueError:
            port = -1
        if (
            parts.scheme != "https"
            or parts.hostname != TCMB_HOST
            or port not in (None, 443)
            or parts.username is not None
        ):
            raise ValueError(f"listing_url must be an https URL on {TCMB_HOST}")
        return value

    @property
    def page_url(self) -> str:
        return self.listing_url


def _origin_of(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("origin", "mevzuat"))
    return str(getattr(value, "origin", "mevzuat"))


AnySource = MevzuatSource | TcmbSource
# Validation type: entries without `origin` are mevzuat sources.
SourceSpec = Annotated[
    Annotated[MevzuatSource, Tag("mevzuat")] | Annotated[TcmbSource, Tag("tcmb")],
    Discriminator(
        _origin_of,
        custom_error_type="invalid_origin",
        custom_error_message="origin must be 'mevzuat' (default) or 'tcmb'",
    ),
]
_SPEC_ADAPTER: TypeAdapter[AnySource] = TypeAdapter(SourceSpec)


def load_sources(path: Path) -> tuple[AnySource, ...]:
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
        specs = tuple(_SPEC_ADAPTER.validate_python(item) for item in raw["sources"])
    except ValidationError as exc:
        raise SourcesError(f"{path}: {exc}") from exc

    seen: set[str] = set()
    for spec in specs:
        if spec.id in seen:
            raise SourcesError(f"{path}: duplicate id {spec.id!r}")
        seen.add(spec.id)
    return specs
