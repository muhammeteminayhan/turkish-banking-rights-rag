"""Parse every document in data/manifest.json into data/processed/chunks.jsonl.

    python scripts/parse_sources.py               # verify checksums, parse, write chunks + report
    python scripts/parse_sources.py --no-pages    # skip the (slower) PDF page lookup

Writes data/processed/chunks.jsonl, parse_report.json and parse_report.md.
Exit codes: 0 success, 1 the raw data does not match the manifest or a document failed.
"""

import argparse
import logging
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from finhak.fsutil import atomic_write_text
from finhak.ingest.manifest import ManifestEntry, ManifestError, read_manifest, verify_manifest
from finhak.ingest.scrape import ScrapeError, decode_html
from finhak.parsing.blocks import html_blocks
from finhak.parsing.chunker import MAX_CHUNK_CHARS, Chunk, DocInfo, chunk_mevzuat, chunk_talimat
from finhak.parsing.pages import PageIndex, count_madde_headings
from finhak.parsing.report import (
    DocReport,
    ParseReport,
    chunk_stats,
    page_coverage,
    render_markdown,
)
from finhak.parsing.structure import ParsedText, parse_structure
from finhak.parsing.talimat import parse_talimat, pdf_lines

logger = logging.getLogger("finhak.parse_sources")

EXIT_OK, EXIT_FAILED = 0, 1


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.json"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--out-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--max-chars", type=int, default=MAX_CHUNK_CHARS)
    parser.add_argument("--no-pages", action="store_true", help="skip PDF page lookup")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        problems = verify_manifest(args.manifest, args.raw_dir)
        entries = read_manifest(args.manifest).documents
    except ManifestError as exc:
        logger.error("%s", exc)
        return EXIT_FAILED
    if problems:
        for problem in problems:
            logger.error("%s", problem)
        logger.error("raw data does not match %s; run scripts/fetch_sources.py", args.manifest)
        return EXIT_FAILED

    chunks: list[Chunk] = []
    reports: list[DocReport] = []
    for entry in entries:
        try:
            doc_chunks, report = _parse_entry(entry, args)
        except (ScrapeError, OSError, ValueError) as exc:
            logger.error("%s: %s", entry.id, exc)
            return EXIT_FAILED
        chunks.extend(doc_chunks)
        reports.append(report)
        logger.info("%s: %d chunks", entry.id, len(doc_chunks))

    duplicates = sorted(cid for cid, count in Counter(c.id for c in chunks).items() if count > 1)
    if duplicates:
        logger.error("duplicate chunk ids: %s", duplicates[:10])
        return EXIT_FAILED
    parse_report = ParseReport(documents=tuple(reports))
    out = args.out_dir
    atomic_write_text(out / "chunks.jsonl", "".join(c.model_dump_json() + "\n" for c in chunks))
    atomic_write_text(out / "parse_report.json", parse_report.model_dump_json(indent=2) + "\n")
    atomic_write_text(out / "parse_report.md", render_markdown(parse_report))
    logger.info("wrote %d chunks for %d documents to %s", len(chunks), len(reports), out)
    return EXIT_OK


def _doc_info(entry: ManifestEntry) -> DocInfo:
    return DocInfo(
        doc_id=entry.id,
        title=entry.title,
        label=entry.label,
        doc_type=entry.doc_type,
        origin=entry.origin,
        number=entry.number,
        source_url=entry.source_page_url,
        rg_date=entry.rg_date,
        version_date=entry.version_date,
        collected_on=max(file.fetched_at for file in entry.files).date(),
    )


def _parse_entry(entry: ManifestEntry, args: argparse.Namespace) -> tuple[list[Chunk], DocReport]:
    info = _doc_info(entry)
    pdf = next((args.raw_dir / f.path for f in entry.files if f.format == "pdf"), None)
    if entry.origin == "tcmb":
        if pdf is None:
            raise ValueError("tcmb document without a PDF")
        talimat = parse_talimat(pdf_lines(pdf))
        chunks = list(chunk_talimat(info, talimat))
        return chunks, _report(entry, chunks, args, warnings=talimat.warnings, annexes=1)

    html = decode_html((args.raw_dir / entry.id / "text.html").read_bytes(), entry.id)
    parsed = parse_structure(html_blocks(html))
    chunks = list(chunk_mevzuat(info, parsed, max_chars=args.max_chars))
    notes: list[str] = []
    pdf_headings: int | None = None
    if pdf is not None and not args.no_pages:
        try:
            index = PageIndex.from_pdf(pdf)
        except Exception as exc:  # pdfminer raises many unrelated types for broken files
            notes.append(f"PDF not readable, pages not set: {type(exc).__name__}")
        else:
            pdf_headings = count_madde_headings(index.raw_text())
            chunks = _with_pages(chunks, index)
    elif pdf is None:
        notes.append("no PDF on mevzuat.gov.tr: pages not set")
    notes.extend(
        f"not in the text (separate file on the site): {u}"
        for u in parsed.unplaced
        if "tıklayınız" in u
    )
    return chunks, _report(
        entry, chunks, args, parsed=parsed, notes=tuple(notes), pdf_headings=pdf_headings
    )


def _with_pages(chunks: list[Chunk], index: PageIndex) -> list[Chunk]:
    located: list[Chunk] = []
    last = 1
    for chunk in chunks:
        # Later parts of a split fıkra repeat its opening line; look up their own first bent.
        text = chunk.text
        if chunk.part and chunk.part > 1 and "\n" in text:
            text = text.split("\n", 1)[1]
        page = index.locate(text, start=last)
        if page is not None:
            last = page
            located.append(chunk.model_copy(update={"pages": (page,)}))
        else:
            located.append(chunk)
    return located


def _report(
    entry: ManifestEntry,
    chunks: list[Chunk],
    args: argparse.Namespace,
    parsed: ParsedText | None = None,
    warnings: tuple[str, ...] = (),
    notes: tuple[str, ...] = (),
    annexes: int = 0,
    pdf_headings: int | None = None,
) -> DocReport:
    units, oversized, unresolved, ambiguous = chunk_stats(chunks, args.max_chars)
    fikralar = [f for m in parsed.maddeler for f in m.fikralar] if parsed else []
    kinds: dict[str, int] = {}
    for madde in parsed.maddeler if parsed else ():
        kinds[madde.kind] = kinds.get(madde.kind, 0) + 1
    if not parsed:
        kinds = {"madde": len({c.madde for c in chunks if c.unit == "bent"})}
    has_pages = any(chunk.pages for chunk in chunks)
    return DocReport(
        doc_id=entry.id,
        origin=entry.origin,
        maddeler=kinds,
        fikralar=len(fikralar),
        fikralar_inferred=sum(1 for f in fikralar if f.inferred),
        mulga_maddeler=sum(1 for m in parsed.maddeler if m.mulga) if parsed else 0,
        mulga_fikralar=sum(1 for f in fikralar if f.mulga),
        chunks=units,
        oversized_chunks=oversized,
        unresolved_refs=unresolved,
        ambiguous_refs=ambiguous,
        unplaced=tuple(u for u in parsed.unplaced if "tıklayınız" not in u) if parsed else (),
        warnings=warnings,
        annexes=len(parsed.annexes) if parsed else annexes,
        pdf_madde_headings=pdf_headings,
        page_coverage=page_coverage(chunks) if has_pages else None,
        notes=notes,
        unreferenced_notes=_unreferenced(parsed) if parsed else (),
    )


def _unreferenced(parsed: ParsedText) -> tuple[str, ...]:
    cited: set[str] = set()
    for madde in parsed.maddeler:
        cited.update(madde.footnote_refs, madde.sup_refs)
        for fikra in madde.fikralar:
            cited.update(fikra.footnote_refs, fikra.sup_refs)
    numbers = [f"[{n}]" for n in parsed.footnotes if n not in cited]
    numbers += [f"({n})" for n in parsed.endnotes if n not in cited]
    return tuple(numbers)
