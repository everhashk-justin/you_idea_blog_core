#!/usr/bin/env python3
"""
Multi-Blog Master Web Asset Synchronization Tool

Synchronizes master Pan & Zoom Lightbox frontend assets (lightbox.js, lightbox.css)
from the core repository to the target blog repositories in the ecosystem.

Features:
- Multi-target synchronization (dev, markets, gear, stock, all, or custom path)
- SHA-256 pre-check: skips redundant writes if destination file is already identical
- Post-verification: guarantees target file hash matches master copy 100%
- Safe backup: creates timestamped .bak backups of existing target files
- Dry-run mode: previews planned copy actions, diffs, and hashes without writing
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class SyncVerificationError(Exception):
    """Raised when post-copy SHA-256 hash verification fails."""
    pass


TARGET_MAP: Dict[str, Dict[str, str]] = {
    "dev": {
        "name": "Global Dev Blog (dev.ideaspot360.com)",
        "subpath": "blogs/dev/assets",
        "js": "js/lightbox.js",
        "css": "css/lightbox.css",
    },
    "markets": {
        "name": "Market Context 360 (markets.ideaspot360.com)",
        "subpath": "blogs/markets/assets",
        "js": "js/lightbox.js",
        "css": "css/lightbox.css",
    },
    "gear": {
        "name": "Gear Studio (gear.ideaspot360.com)",
        "subpath": "blogs/gear/assets",
        "js": "js/lightbox.js",
        "css": "css/lightbox.css",
    },
    "stock": {
        "name": "Stock Context (stock.ideaspot360.com)",
        "subpath": "blogs/stock/assets",
        "js": "js/lightbox.js",
        "css": "css/lightbox.css",
    },
}


@dataclass
class SyncItemResult:
    target_key: str
    target_name: str
    file_type: str
    master_path: Path
    dest_path: Path
    master_sha256: str
    dest_sha256_before: Optional[str]
    dest_sha256_after: Optional[str]
    status: str
    backup_path: Optional[Path] = None
    error_message: Optional[str] = None


def compute_sha256(filepath: Path) -> str:
    """Compute the SHA-256 hexadecimal hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def resolve_master_assets(core_root: Optional[Path] = None) -> Tuple[Path, Path]:
    """Locate master lightbox.js and lightbox.css in core web_assets/ directory."""
    if core_root is None:
        core_root = Path(__file__).resolve().parent

    master_js = core_root / "web_assets" / "js" / "lightbox.js"
    master_css = core_root / "web_assets" / "css" / "lightbox.css"

    if not master_js.exists() or master_js.stat().st_size == 0:
        raise FileNotFoundError(f"Master JS asset missing or empty: {master_js}")
    if not master_css.exists() or master_css.stat().st_size == 0:
        raise FileNotFoundError(f"Master CSS asset missing or empty: {master_css}")

    return master_js, master_css


def resolve_target_destinations(
    target: str,
    ecosystem_root: Path,
) -> List[Tuple[str, str, Path, Path]]:
    """
    Resolve (target_key, target_name, dest_js_path, dest_css_path) tuples.
    Supports predefined target keys ('dev', 'markets', 'gear', 'stock', 'all')
    as well as custom directory paths.
    """
    results = []
    target_clean = target.strip().strip("/\\").lower()

    if target_clean == "all":
        targets_to_process = list(TARGET_MAP.keys())
    elif target_clean in TARGET_MAP:
        targets_to_process = [target_clean]
    else:
        # Check if target is a legitimate custom path
        target_path = Path(target)
        is_explicit_path = ("/" in target) or ("\\" in target) or target_path.is_dir()
        if not is_explicit_path:
            valid_targets = sorted(list(TARGET_MAP.keys())) + ["all"]
            raise ValueError(
                f"Unknown target '{target}'. Valid predefined targets: {valid_targets}, "
                f"or specify an explicit directory path containing path separators."
            )

        # Custom directory path
        custom_path = target_path.resolve()
        # If custom path ends with 'assets' or contains assets/
        if custom_path.name == "assets":
            dest_js = custom_path / "js" / "lightbox.js"
            dest_css = custom_path / "css" / "lightbox.css"
        elif (custom_path / "assets").is_dir():
            dest_js = custom_path / "assets" / "js" / "lightbox.js"
            dest_css = custom_path / "assets" / "css" / "lightbox.css"
        else:
            dest_js = custom_path / "js" / "lightbox.js"
            dest_css = custom_path / "css" / "lightbox.css"

        return [("custom", f"Custom Target ({custom_path})", dest_js, dest_css)]

    for key in targets_to_process:
        info = TARGET_MAP[key]
        base_dir = ecosystem_root / info["subpath"]
        dest_js = base_dir / info["js"]
        dest_css = base_dir / info["css"]
        results.append((key, info["name"], dest_js, dest_css))

    return results


def sync_assets(
    target: str = "all",
    ecosystem_root: Optional[Path | str] = None,
    core_root: Optional[Path | str] = None,
    dry_run: bool = False,
    backup: bool = False,
    verify: bool = True,
    verbose: bool = False,
) -> List[SyncItemResult]:
    """
    Execute asset synchronization workflow across selected targets.
    """
    if ecosystem_root is None:
        ecosystem_root = Path(r"D:\00_antigravity\01_you_idea_blog")
    else:
        ecosystem_root = Path(ecosystem_root).resolve()

    if core_root is not None:
        core_root = Path(core_root).resolve()

    master_js, master_css = resolve_master_assets(core_root)
    master_js_sha = compute_sha256(master_js)
    master_css_sha = compute_sha256(master_css)

    targets = resolve_target_destinations(target, ecosystem_root)
    results: List[SyncItemResult] = []

    pairs = [
        ("JS", master_js, master_js_sha),
        ("CSS", master_css, master_css_sha),
    ]

    for target_key, target_name, dest_js, dest_css in targets:
        dest_files = [dest_js, dest_css]
        for (file_type, master_path, master_sha), dest_path in zip(pairs, dest_files):
            dest_sha_before = None
            dest_sha_after = None
            backup_path = None
            status = "PENDING"
            err_msg = None

            if dest_path.is_dir():
                status = "FAILED"
                err_msg = f"Destination path is a directory: {dest_path}"
            else:
                is_identical = False
                if dest_path.is_file():
                    try:
                        dest_sha_before = compute_sha256(dest_path)
                        is_identical = (dest_sha_before == master_sha)
                    except Exception as ex:
                        is_identical = False
                        err_msg = f"Failed to compute pre-sync hash: {ex}"

                if dry_run:
                    if is_identical:
                        status = "IDENTICAL"
                    elif dest_path.is_file():
                        status = "WOULD_UPDATE"
                    else:
                        status = "WOULD_CREATE"
                else:
                    try:
                        if is_identical:
                            status = "IDENTICAL"
                            dest_sha_after = dest_sha_before
                        else:
                            # Backup if requested and target file exists
                            if backup and dest_path.is_file():
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                backup_file = dest_path.with_name(
                                    f"{dest_path.name}.{timestamp}.bak"
                                )
                                # Ensure parent exists
                                backup_file.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(dest_path, backup_file)
                                backup_path = backup_file

                            # Ensure target directory exists
                            dest_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(master_path, dest_path)

                            # Post-verification
                            dest_sha_after = compute_sha256(dest_path)
                            if verify and dest_sha_after != master_sha:
                                raise SyncVerificationError(
                                    f"Hash mismatch after sync for {dest_path}: "
                                    f"expected {master_sha}, got {dest_sha_after}"
                                )
                            status = "SYNCED"

                    except Exception as ex:
                        status = "FAILED"
                        err_msg = str(ex)

            result = SyncItemResult(
                target_key=target_key,
                target_name=target_name,
                file_type=file_type,
                master_path=master_path,
                dest_path=dest_path,
                master_sha256=master_sha,
                dest_sha256_before=dest_sha_before,
                dest_sha256_after=dest_sha_after,
                status=status,
                backup_path=backup_path,
                error_message=err_msg,
            )
            results.append(result)

            if verbose:
                print(
                    f"[{status}] {target_name} ({file_type}) -> {dest_path} "
                    f"(SHA: {master_sha[:10]}...)"
                )
                if backup_path:
                    print(f"  └─ Backup created at: {backup_path}")
                if err_msg:
                    print(f"  └─ Error: {err_msg}", file=sys.stderr)

    return results


def print_summary_table(results: List[SyncItemResult], dry_run: bool) -> None:
    """Print a clean execution report table."""
    mode_str = " (DRY-RUN PREVIEW)" if dry_run else ""
    print("\n" + "=" * 90)
    print(f"📦 MASTER WEB ASSETS SYNC REPORT{mode_str}")
    print("=" * 90)
    header = f"{'Target':<22} | {'Type':<4} | {'Status':<13} | {'SHA-256 (Master)':<18} | {'Destination'}"
    print(header)
    print("-" * 90)

    for r in results:
        sha_display = f"{r.master_sha256[:8]}...{r.master_sha256[-8:]}"
        dest_display = str(r.dest_path)
        if len(dest_display) > 38:
            dest_display = "..." + dest_display[-35:]
        print(
            f"{r.target_name[:22]:<22} | {r.file_type:<4} | {r.status:<13} | "
            f"{sha_display:<18} | {dest_display}"
        )
        if r.backup_path:
            print(f"  └─ Backup: {r.backup_path.name}")
        if r.error_message:
            print(f"  └─ ❌ Error: {r.error_message}")

    print("=" * 90)
    success_count = sum(1 for r in results if r.status in ("SYNCED", "IDENTICAL", "WOULD_CREATE", "WOULD_UPDATE"))
    fail_count = sum(1 for r in results if r.status == "FAILED")
    print(f"Summary: {success_count} item(s) processed, {fail_count} failure(s).\n")


def build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="sync_to_blogs.py",
        description="Synchronize master Pan & Zoom Lightbox assets across multi-blog ecosystem.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--target", "-t",
        default="all",
        help="Target blog [dev|markets|gear|stock|all|<custom_path>] (default: all)",
    )
    parser.add_argument(
        "--ecosystem-root",
        default=r"D:\00_antigravity\01_you_idea_blog",
        help="Root path of the blogs ecosystem (default: D:\\00_antigravity\\01_you_idea_blog)",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Print planned sync actions and SHA-256 diffs without modifying files",
    )
    parser.add_argument(
        "--backup", "-b",
        action="store_true",
        help="Create timestamped .bak backups before overwriting existing files",
    )
    parser.add_argument(
        "--verify", "-v",
        action="store_true",
        default=True,
        help="Perform SHA-256 pre-check and post-verification (default: True)",
    )
    parser.add_argument(
        "--no-verify",
        action="store_false",
        dest="verify",
        help="Disable post-copy SHA-256 verification",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed logging output",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point. Returns exit code (0 for success, non-zero for failure)."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        results = sync_assets(
            target=args.target,
            ecosystem_root=args.ecosystem_root,
            dry_run=args.dry_run,
            backup=args.backup,
            verify=args.verify,
            verbose=args.verbose,
        )
        print_summary_table(results, dry_run=args.dry_run)

        # Check for any failures
        if any(r.status == "FAILED" for r in results):
            return 1
        return 0

    except ValueError as ex:
        print(f"\n❌ [ARGUMENT ERROR] {ex}", file=sys.stderr)
        return 2
    except Exception as ex:
        print(f"\n❌ [FATAL ERROR] {ex}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
