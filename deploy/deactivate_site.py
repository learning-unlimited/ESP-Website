#!/usr/bin/env python3

"""Helper script to deactivate a deployed site safely.

By default this script does a dry run: it reports which lines in each config
file would be commented out and where the site directory would be moved.
Pass --apply to make changes.
"""

import argparse
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
import shutil
import sys
from pathlib import Path
from typing import List


CONFIG_PATHS = OrderedDict(
    [
        ("Apache vhosts", Path("/etc/apache2/sites-available/esp_sites.conf")),
        ("System crontab", Path("/etc/crontab")),
        ("Exim config", Path("/etc/exim4/update-exim4.conf.conf")),
    ]
)
DEFAULT_SITES_ROOT = Path("/lu/sites")
DEFAULT_ARCHIVE_DIR = DEFAULT_SITES_ROOT / "archive"


@dataclass
class Match:
    line_number: int
    line_text: str


@dataclass
class FileAnalysis:
    path: Path
    active_matches: List[Match]
    commented_matches: List[Match]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Deactivate a site by commenting matching lines in known config files "
            "and moving the site directory to the archive."
        )
    )
    parser.add_argument(
        "site",
        help="Site directory name under /lu/sites (for example: mit).",
    )
    parser.add_argument(
        "--token",
        dest="tokens",
        action="append",
        default=[],
        help=(
            "Additional token to match in config lines. "
            "Use more than once to add multiple tokens."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes. Without this flag, runs in dry-run mode.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help=(
            "Allow apply mode to continue if a config file has no active matching "
            "lines."
        ),
    )
    parser.add_argument(
        "--sites-root",
        default=str(DEFAULT_SITES_ROOT),
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--archive-dir",
        default=str(DEFAULT_ARCHIVE_DIR),
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def normalize_tokens(site: str, extra_tokens: List[str]) -> List[str]:
    tokens = [site]
    tokens.extend(extra_tokens)
    return [token for token in OrderedDict((token.strip(), None) for token in tokens) if token]


def analyze_config_file(path: Path, tokens: List[str]) -> FileAnalysis:
    active_matches: List[Match] = []
    commented_matches: List[Match] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line_text = line.rstrip("\n")
            if not any(token in line_text for token in tokens):
                continue
            match = Match(line_number=line_number, line_text=line_text)
            if line_text.lstrip().startswith("#"):
                commented_matches.append(match)
            else:
                active_matches.append(match)

    return FileAnalysis(path=path, active_matches=active_matches, commented_matches=commented_matches)


def print_analysis(label: str, analysis: FileAnalysis) -> None:
    print(f"{label}: {analysis.path}")
    print(f"  active matching lines: {len(analysis.active_matches)}")
    print(f"  already commented matching lines: {len(analysis.commented_matches)}")
    for match in analysis.active_matches:
        print(f"    L{match.line_number}: {match.line_text}")
    print()


def comment_matching_lines(path: Path, matches: List[Match], site: str, stamp: str) -> Path:
    if not matches:
        return path

    target_lines = {match.line_number for match in matches}
    updated_lines = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line_number in target_lines and not line.lstrip().startswith("#"):
                updated_lines.append(f"# deactivated {site} {stamp} {line}")
            else:
                updated_lines.append(line)

    backup_path = Path(f"{path}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}")
    shutil.copy2(path, backup_path)
    with path.open("w", encoding="utf-8") as handle:
        handle.writelines(updated_lines)
    return backup_path


def choose_archive_target(archive_dir: Path, site: str) -> Path:
    base_target = archive_dir / site
    if not base_target.exists():
        return base_target
    suffix = datetime.now().strftime("%Y%m%d%H%M%S")
    return archive_dir / f"{site}-{suffix}"


def main() -> int:
    args = parse_args()
    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"Mode: {mode}")

    tokens = normalize_tokens(args.site, args.tokens)
    print(f"Matching tokens: {', '.join(tokens)}")
    print()

    config_analyses = []
    blocking_errors = []
    for label, path in CONFIG_PATHS.items():
        if not path.exists():
            blocking_errors.append(f"Missing config file: {path}")
            continue
        analysis = analyze_config_file(path, tokens)
        config_analyses.append((label, analysis))
        print_analysis(label, analysis)
        if args.apply and not args.allow_missing and not analysis.active_matches:
            blocking_errors.append(
                f"No active matching lines found in {path}. "
                "Use --allow-missing to skip this safety check."
            )

    sites_root = Path(args.sites_root)
    archive_dir = Path(args.archive_dir)
    source_site_dir = sites_root / args.site
    archive_target = choose_archive_target(archive_dir, args.site)

    print(f"Site directory: {source_site_dir}")
    print(f"Archive target: {archive_target}")
    print()

    if not source_site_dir.exists():
        blocking_errors.append(f"Site directory does not exist: {source_site_dir}")
    elif source_site_dir.resolve().parent == archive_dir.resolve():
        blocking_errors.append(f"Site directory is already under archive: {source_site_dir}")

    if blocking_errors:
        print("Cannot continue:")
        for error in blocking_errors:
            print(f"  - {error}")
        return 2

    if not args.apply:
        print("Dry run complete. Re-run with --apply to make changes.")
        return 0

    stamp = datetime.now().strftime("%Y-%m-%d")
    print("Applying changes...")
    for _, analysis in config_analyses:
        backup_path = comment_matching_lines(analysis.path, analysis.active_matches, args.site, stamp)
        if analysis.active_matches:
            print(f"  Updated {analysis.path} (backup: {backup_path})")
        else:
            print(f"  No updates needed in {analysis.path}")

    archive_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source_site_dir), str(archive_target))
    print(f"  Moved {source_site_dir} -> {archive_target}")
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
