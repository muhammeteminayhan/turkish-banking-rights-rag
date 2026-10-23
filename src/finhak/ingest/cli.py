"""Download every document in data/sources.yaml and rebuild data/manifest.json.

    python scripts/fetch_sources.py              # fetch missing files, build + verify manifest
    python scripts/fetch_sources.py --dry-run    # show what a real run would fetch; no network
    python scripts/fetch_sources.py --refresh    # download everything again
    python scripts/fetch_sources.py --only 6502 kart-yon
    python scripts/fetch_sources.py --verify     # only recompute checksums against the manifest

Requests go out at most once every FETCH_MIN_INTERVAL_SECONDS (default 1.1) per host.
Exit codes: 0 success, 1 a document or the manifest failed, 2 bad configuration.
"""

import argparse
import logging
import os
from collections.abc import Callable, Sequence
from pathlib import Path

from finhak.ingest.fetch import (
    PAGE_NAME,
    CorruptFetchLog,
    FetchLog,
    fetch_source,
    linked_files,
    read_fetch_log,
    sha256_hex,
)
from finhak.ingest.http import FetchError, PoliteClient, RateLimiter
from finhak.ingest.manifest import (
    ManifestError,
    build_manifest,
    verify_manifest,
    write_json_schema,
    write_manifest,
)
from finhak.ingest.scrape import ScrapeError
from finhak.ingest.sources import SourcesError, SourceSpec, load_sources

logger = logging.getLogger("finhak.fetch_sources")

INTERVAL_ENV = "FETCH_MIN_INTERVAL_SECONDS"
DEFAULT_INTERVAL_SECONDS = 1.1
EXIT_OK, EXIT_FAILED, EXIT_CONFIG = 0, 1, 2

ClientFactory = Callable[[float], PoliteClient]


def _default_client(interval: float) -> PoliteClient:
    return PoliteClient(RateLimiter(interval))


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--sources", type=Path, default=Path("data/sources.yaml"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.json"))
    parser.add_argument("--schema", type=Path, default=Path("data/manifest.schema.json"))
    parser.add_argument("--only", nargs="+", metavar="ID", help="fetch only these source ids")
    parser.add_argument("--refresh", action="store_true", help="ignore the cache")
    parser.add_argument("--dry-run", action="store_true", help="no network, no writes")
    parser.add_argument("--verify", action="store_true", help="only verify checksums")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None, client_factory: ClientFactory = _default_client) -> int:
    args = parse_args(argv)
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.verify:
        return _verify(args.manifest, args.raw_dir)
    try:
        specs = load_sources(args.sources)
        selected = _select(specs, args.only)
        interval = _interval_from_env()
        RateLimiter(interval)  # validate before anything else happens
    except (SourcesError, ValueError) as exc:
        logger.error("%s", exc)
        return EXIT_CONFIG

    try:
        if args.dry_run:
            _report_plan(selected, args.raw_dir, args.refresh)
            return EXIT_OK
        if not _fetch_all(selected, args.raw_dir, client_factory(interval), args.refresh):
            return EXIT_FAILED
        # The manifest always covers the whole source list, so --only needs the rest cached.
        return _write_and_verify_manifest(specs, args)
    except (CorruptFetchLog, ManifestError) as exc:
        logger.error("%s", exc)
        return EXIT_FAILED


def _interval_from_env() -> float:
    raw = os.environ.get(INTERVAL_ENV)
    if raw is None:
        return DEFAULT_INTERVAL_SECONDS
    try:
        interval = float(raw)
        RateLimiter(interval)
    except ValueError as exc:
        raise ValueError(f"{INTERVAL_ENV}={raw!r} is not allowed: {exc}") from exc
    return interval


def _select(specs: tuple[SourceSpec, ...], only: list[str] | None) -> tuple[SourceSpec, ...]:
    if not only:
        return specs
    unknown = set(only) - {spec.id for spec in specs}
    if unknown:
        raise ValueError(f"unknown source ids: {', '.join(sorted(unknown))}")
    return tuple(spec for spec in specs if spec.id in only)


def _report_plan(specs: tuple[SourceSpec, ...], raw_dir: Path, refresh: bool) -> None:
    """Mirror the cache rules of fetch_source without touching the network."""
    for spec in specs:
        doc_dir = raw_dir / spec.id
        log = read_fetch_log(doc_dir)
        if refresh:
            logger.info("%s: --refresh would fetch everything again", spec.id)
            continue
        if not _is_cached(doc_dir, log, PAGE_NAME):
            logger.info("%s: would fetch the page %s, then its files", spec.id, spec.page_url)
            continue
        wanted = linked_files(spec, (doc_dir / PAGE_NAME).read_bytes())
        rejected = [name for name in wanted if name in log.rejected]
        missing = [
            name for name in wanted if name not in rejected and not _is_cached(doc_dir, log, name)
        ]
        if missing:
            logger.info("%s: would fetch %s", spec.id, missing)
        else:
            logger.info("%s: up to date", spec.id)
        if rejected:
            logger.info("%s: previously rejected, skipped until --refresh: %s", spec.id, rejected)


def _is_cached(doc_dir: Path, log: FetchLog, name: str) -> bool:
    """Same rule as the fetcher: logged, present, and unchanged since download."""
    record = log.files.get(name)
    path = doc_dir / name
    return record is not None and path.exists() and sha256_hex(path.read_bytes()) == record.sha256


def _fetch_all(
    specs: tuple[SourceSpec, ...], raw_dir: Path, client: PoliteClient, refresh: bool
) -> bool:
    failures: list[str] = []
    with client:
        for spec in specs:
            try:
                outcome = fetch_source(spec, client, raw_dir, refresh=refresh)
            except (FetchError, ScrapeError, CorruptFetchLog) as exc:
                failures.append(f"{spec.id}: {exc}")
                logger.error("%s: %s", spec.id, exc)
                continue
            failures.extend(f"{spec.id}: {problem}" for problem in outcome.failed)
            logger.info(
                "%s: downloaded %s, cached %s",
                spec.id,
                list(outcome.downloaded) or "nothing",
                list(outcome.cached) or "nothing",
            )
            if outcome.rejected:
                logger.warning("%s: rejected %s (see _fetch.json)", spec.id, list(outcome.rejected))
            if outcome.kept_previous:
                logger.warning("%s: kept previous copy of %s", spec.id, list(outcome.kept_previous))
        logger.info("HTTP requests made this run: %d", client.request_count)

    for failure in failures:
        logger.error("FAILED %s", failure)
    return not failures


def _write_and_verify_manifest(specs: tuple[SourceSpec, ...], args: argparse.Namespace) -> int:
    try:
        manifest = build_manifest(specs, args.raw_dir)
    except ScrapeError as exc:
        logger.error("manifest not written: %s", exc)
        return EXIT_FAILED
    write_manifest(manifest, args.manifest)
    write_json_schema(args.schema)
    logger.info("wrote %s (%d documents)", args.manifest, len(manifest.documents))
    return _verify(args.manifest, args.raw_dir)


def _verify(manifest_path: Path, raw_dir: Path) -> int:
    try:
        problems = verify_manifest(manifest_path, raw_dir)
    except ManifestError as exc:
        logger.error("%s", exc)
        return EXIT_FAILED
    for problem in problems:
        logger.error("%s", problem)
    if problems:
        return EXIT_FAILED
    logger.info("all checksums in %s match %s", manifest_path, raw_dir)
    return EXIT_OK
