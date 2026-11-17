"""
Test suite for master frontend web assets and synchronization pipeline.

Verifies:
1. Master asset file presence and non-empty size.
2. lightbox.js syntax validation (via Node.js and AST/token inspection).
3. lightbox.css syntax and required styling rules.
4. sync_to_blogs.py CLI parser and options.
5. sync_to_blogs.py in --dry-run mode against temporary directories.
6. Timestamped .bak backup creation before overwriting.
7. SHA-256 pre-check and skip-identical behavior.
8. Custom target path synchronization.
9. Post-verification hash integrity checks.
10. CLI main entry point execution.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

CORE_ROOT = Path(__file__).resolve().parent.parent
if str(CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(CORE_ROOT))

import pytest

from sync_to_blogs import (
    SyncVerificationError,
    build_parser,
    compute_sha256,
    main,
    resolve_master_assets,
    resolve_target_destinations,
    sync_assets,
)

MASTER_JS = CORE_ROOT / "web_assets" / "js" / "lightbox.js"
MASTER_CSS = CORE_ROOT / "web_assets" / "css" / "lightbox.css"


def test_master_assets_exist_and_non_empty():
    """Verify master lightbox.js and lightbox.css exist and have positive byte sizes."""
    assert MASTER_JS.exists(), f"Master JS file not found: {MASTER_JS}"
    assert MASTER_CSS.exists(), f"Master CSS file not found: {MASTER_CSS}"

    assert MASTER_JS.stat().st_size > 500, "Master JS file is unexpectedly small"
    assert MASTER_CSS.stat().st_size > 500, "Master CSS file is unexpectedly small"


def test_lightbox_js_syntax_via_node():
    """Verify lightbox.js has valid JavaScript syntax using node --check."""
    node_path = shutil.which("node")
    if not node_path:
        pytest.skip("Node.js executable not found in PATH")

    res = subprocess.run(
        [node_path, "--check", str(MASTER_JS)],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Node --check failed on lightbox.js:\n{res.stderr}"


def test_lightbox_js_features_and_tokens():
    """Verify lightbox.js contains all required constitutional features and guards."""
    content = MASTER_JS.read_text(encoding="utf-8")

    # 1. Drag threshold patch and delay reset
    assert "DRAG_THRESHOLD = 5" in content, "Missing DRAG_THRESHOLD = 5"
    assert "50" in content, "Missing 50ms delay reset for hasDragged"
    assert "hasDragged" in content, "Missing hasDragged state tracking"

    # 2. Continuous wheel zoom formula and transform origin
    assert "-e.deltaY * 0.002" in content, "Missing continuous wheel zoom formula"

    # 3. Smooth animation on toolbar button clicks
    assert "updateTransform(true)" in content, "Missing updateTransform(true) for smooth animation"

    # 4. Double-click 2.5x smart zoom with toolbar guard & finite scale guard
    assert 'closest(".panzoom-toolbar' in content, "Missing panzoom-toolbar double-click guard"
    assert "zoomAt(2.5" in content, "Missing 2.5x double-click zoom"
    assert "Number.isFinite(targetScale)" in content, "Missing Number.isFinite safeguard in zoomAt"

    # 5. Full keyboard navigation
    for key_token in ["Escape", "+", "-", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"]:
        assert key_token in content, f"Missing keyboard shortcut support for {key_token}"

    # 6. Mobile pinch and pan
    assert "touches.length === 1" in content, "Missing single-touch drag pan logic"
    assert "touches.length === 2" in content, "Missing two-finger pinch-to-zoom logic"

    # 7. Bilingual i18n auto-detection
    assert "기술 다이어그램" in content, "Missing Korean defaultAlt text"
    assert "Technical Diagram" in content, "Missing English defaultAlt text"
    assert "detectLanguage" in content, "Missing language detection function"

    # 8. Idempotency guard and UMD export
    assert "__panZoomLightboxInitialized" in content, "Missing idempotency guard"
    assert "window.initPanZoomLightbox" in content, "Missing global init function export"
    assert "typeof define === \"function\"" in content, "Missing AMD definition check in UMD"
    assert "typeof module === \"object\"" in content, "Missing CommonJS definition check in UMD"


def test_lightbox_css_syntax_and_rules():
    """Verify lightbox.css includes required selectors, z-index, and HUD styling."""
    content = MASTER_CSS.read_text(encoding="utf-8")

    # Target selectors with zoom-in cursor
    assert "cursor: zoom-in;" in content
    assert ".entry-content img" in content
    assert "article.post-content img" in content
    assert ".markdown-body img" in content

    # Modal container with z-index 999999 and dark glassmorphism
    assert "z-index: 999999;" in content
    assert "rgba(10, 15, 29, 0.94)" in content
    assert "backdrop-filter: blur(12px)" in content

    # HUD circular buttons and scale badge
    assert ".panzoom-btn" in content
    assert "border-radius: 50%" in content
    assert "transform: scale(1.1)" in content
    assert ".panzoom-scale-badge" in content
    assert "#38bdf8" in content

    # Viewport grab/grabbing support
    assert ".panzoom-viewport.grabbing" in content
    assert ".panzoom-viewport.dragging" in content
    assert "cursor: grabbing;" in content


def test_sync_cli_parser_options():
    """Verify sync_to_blogs.py argument parser configuration."""
    parser = build_parser()

    # Default options
    args = parser.parse_args([])
    assert args.target == "all"
    assert not args.dry_run
    assert not args.backup
    assert args.verify is True

    # Custom options
    args = parser.parse_args([
        "--target", "dev",
        "--dry-run",
        "--backup",
        "--verbose",
        "--ecosystem-root", "/custom/eco/path",
    ])
    assert args.target == "dev"
    assert args.dry_run is True
    assert args.backup is True
    assert args.verbose is True
    assert args.ecosystem_root == "/custom/eco/path"

    # --no-verify option
    args = parser.parse_args(["--no-verify"])
    assert args.verify is False


def test_resolve_master_assets():
    """Verify resolve_master_assets helper properly finds master files."""
    js_path, css_path = resolve_master_assets(CORE_ROOT)
    assert js_path.name == "lightbox.js"
    assert css_path.name == "lightbox.css"
    assert js_path.exists()
    assert css_path.exists()


def test_resolve_target_destinations():
    """Verify destination resolution for predefined targets and custom paths."""
    eco_root = Path("D:/test_eco")

    # All targets
    dests = resolve_target_destinations("all", eco_root)
    assert len(dests) == 4
    keys = [d[0] for d in dests]
    assert keys == ["dev", "markets", "gear", "stock"]

    # Single target
    dests_dev = resolve_target_destinations("dev", eco_root)
    assert len(dests_dev) == 1
    assert dests_dev[0][0] == "dev"
    assert dests_dev[0][2].name == "lightbox.js"
    assert dests_dev[0][3].name == "lightbox.css"

    # Custom path
    custom_dir = Path("D:/test_eco/custom_blog")
    dests_custom = resolve_target_destinations(str(custom_dir), eco_root)
    assert len(dests_custom) == 1
    assert dests_custom[0][0] == "custom"


def test_sync_dry_run_against_mock_ecosystem(tmp_path: Path):
    """Verify --dry-run mode plans actions without creating any files on disk."""
    results = sync_assets(
        target="all",
        ecosystem_root=tmp_path,
        core_root=CORE_ROOT,
        dry_run=True,
    )
    assert len(results) == 8  # 4 targets * 2 files
    for r in results:
        assert r.status == "WOULD_CREATE"
        assert not r.dest_path.exists(), "Dry run must not create files on disk"


def test_sync_real_copy_and_verification(tmp_path: Path):
    """Verify actual file copy, directory creation, and SHA-256 integrity."""
    results = sync_assets(
        target="dev",
        ecosystem_root=tmp_path,
        core_root=CORE_ROOT,
        dry_run=False,
        verify=True,
    )
    assert len(results) == 2
    for r in results:
        assert r.status == "SYNCED"
        assert r.dest_path.exists()
        assert compute_sha256(r.dest_path) == r.master_sha256


def test_sync_skip_identical_pre_check(tmp_path: Path):
    """Verify pre-check identifies already synchronized files and skips writes."""
    # First sync
    sync_assets(
        target="markets",
        ecosystem_root=tmp_path,
        core_root=CORE_ROOT,
        dry_run=False,
    )

    # Second sync on identical files
    second_results = sync_assets(
        target="markets",
        ecosystem_root=tmp_path,
        core_root=CORE_ROOT,
        dry_run=False,
    )
    assert len(second_results) == 2
    for r in second_results:
        assert r.status == "IDENTICAL"


def test_sync_backup_creation_when_target_modified(tmp_path: Path):
    """Verify timestamped .bak backup file is created before overwriting."""
    # Initial sync
    sync_assets(
        target="gear",
        ecosystem_root=tmp_path,
        core_root=CORE_ROOT,
        dry_run=False,
    )

    gear_js = tmp_path / "blogs" / "gear" / "assets" / "js" / "lightbox.js"
    assert gear_js.exists()

    # Modify gear_js with dummy content
    gear_js.write_text("// legacy version 0.1", encoding="utf-8")

    # Sync again with backup=True
    results = sync_assets(
        target="gear",
        ecosystem_root=tmp_path,
        core_root=CORE_ROOT,
        dry_run=False,
        backup=True,
        verify=True,
    )

    # Check JS item
    js_result = [r for r in results if r.file_type == "JS"][0]
    assert js_result.status == "SYNCED"
    assert js_result.backup_path is not None
    assert js_result.backup_path.exists()
    assert js_result.backup_path.name.endswith(".bak")
    assert js_result.backup_path.read_text(encoding="utf-8") == "// legacy version 0.1"

    # Check that dest file now matches master
    assert compute_sha256(gear_js) == js_result.master_sha256


def test_sync_custom_target_path(tmp_path: Path):
    """Verify synchronizing to an arbitrary custom directory path."""
    custom_dir = tmp_path / "external_custom_blog"
    results = sync_assets(
        target=str(custom_dir),
        core_root=CORE_ROOT,
        dry_run=False,
        verify=True,
    )
    assert len(results) == 2
    for r in results:
        assert r.status == "SYNCED"
        assert r.dest_path.exists()
        assert compute_sha256(r.dest_path) == r.master_sha256


def test_sync_cli_main_success(tmp_path: Path):
    """Verify CLI main entry point exits with code 0 on dry run and real sync."""
    # Dry run
    exit_code = main(["--target", "stock", "--dry-run", "--ecosystem-root", str(tmp_path)])
    assert exit_code == 0

    # Real sync
    exit_code = main(["--target", "stock", "--ecosystem-root", str(tmp_path)])
    assert exit_code == 0


def test_sync_missing_master_error(tmp_path: Path):
    """Verify FileNotFoundError is raised when master asset is missing."""
    empty_dir = tmp_path / "empty_core"
    empty_dir.mkdir()
    with pytest.raises(FileNotFoundError):
        sync_assets(core_root=empty_dir)


def test_sync_directory_collision_resilience(tmp_path: Path):
    """
    Verify that if a target destination path already exists as a directory,
    the sync does not crash with PermissionError. The collided item is recorded
    as FAILED, and the remaining files and blogs continue to synchronize normally.
    """
    eco = tmp_path / "mock_eco"
    # Create directory collision on dev JS
    collided_dir = eco / "blogs" / "dev" / "assets" / "js" / "lightbox.js"
    collided_dir.mkdir(parents=True)

    results = sync_assets(
        target="all",
        ecosystem_root=eco,
        core_root=CORE_ROOT,
        dry_run=False,
    )
    assert len(results) == 8

    # dev JS must be marked FAILED with a clear directory collision error message
    dev_js = [r for r in results if r.target_key == "dev" and r.file_type == "JS"][0]
    assert dev_js.status == "FAILED"
    assert "directory" in dev_js.error_message.lower()

    # dev CSS must be SYNCED successfully
    dev_css = [r for r in results if r.target_key == "dev" and r.file_type == "CSS"][0]
    assert dev_css.status == "SYNCED"
    assert dev_css.dest_path.is_file()

    # All other targets (markets, gear, stock) must also be SYNCED
    for target_key in ["markets", "gear", "stock"]:
        target_results = [r for r in results if r.target_key == target_key]
        assert len(target_results) == 2
        for r in target_results:
            assert r.status == "SYNCED"
            assert r.dest_path.is_file()

    # Running main CLI must return exit code 1 due to the failed item
    cli_code = main(["--target", "all", "--ecosystem-root", str(eco)])
    assert cli_code == 1


def test_sync_trailing_slash_normalization(tmp_path: Path):
    """
    Verify that targets with trailing slashes/backslashes (e.g. 'dev/', 'markets/', 'all/')
    are normalized to predefined targets rather than misidentified as custom relative paths.
    """
    eco = tmp_path / "mock_eco"

    # 1. Check resolve_target_destinations normalization
    dests_dev = resolve_target_destinations("dev/", eco)
    assert len(dests_dev) == 1
    assert dests_dev[0][0] == "dev"
    assert "blogs" in str(dests_dev[0][2])

    dests_markets = resolve_target_destinations("markets\\", eco)
    assert len(dests_markets) == 1
    assert dests_markets[0][0] == "markets"
    assert "blogs" in str(dests_markets[0][2])

    dests_all = resolve_target_destinations("all/", eco)
    assert len(dests_all) == 4
    assert [d[0] for d in dests_all] == ["dev", "markets", "gear", "stock"]

    # 2. Check sync_assets with trailing slash target
    results = sync_assets(
        target="markets/",
        ecosystem_root=eco,
        core_root=CORE_ROOT,
        dry_run=False,
    )
    assert len(results) == 2
    for r in results:
        assert r.status == "SYNCED"
        assert r.dest_path.is_file()
        assert "blogs" in str(r.dest_path)

    # Verify no dummy 'markets' directory was created in current working directory
    assert not (Path("markets") / "js" / "lightbox.js").exists()


def test_sync_invalid_target_rejection(tmp_path: Path):
    """
    Verify that invalid or misspelled target names (e.g. 'invalid_blog', 'devv', 'market')
    are rejected with ValueError and CLI exit code 2, without creating dummy directories.
    """
    eco = tmp_path / "mock_eco"

    # resolve_target_destinations must raise ValueError
    for bad_target in ["invalid_blog", "devv", "market", "foobar"]:
        with pytest.raises(ValueError) as excinfo:
            resolve_target_destinations(bad_target, eco)
        assert "Unknown target" in str(excinfo.value)

    # CLI main must return exit code 2
    exit_code = main(["--target", "invalid_blog", "--ecosystem-root", str(eco)])
    assert exit_code == 2

    # Verify no dummy directory was created in CWD
    assert not Path("invalid_blog").exists()
    assert not Path("devv").exists()
    assert not Path("market").exists()


def test_lightbox_js_finite_scale_guard():
    """
    Verify that lightbox.js includes finite scale input guard (Number.isFinite)
    in zoomAt() to safely reject NaN/Infinity from abnormal wheel events.
    """
    content = MASTER_JS.read_text(encoding="utf-8")
    assert "Number.isFinite(targetScale)" in content, "Missing Number.isFinite check in zoomAt"

    # Test via Node.js if available
    node_path = shutil.which("node")
    if not node_path:
        pytest.skip("Node.js executable not found in PATH")

    eval_script = f"""
    const fs = require('fs');
    const code = fs.readFileSync({repr(str(MASTER_JS))}, 'utf-8');
    if (!code.includes('Number.isFinite(targetScale)')) {{
      process.exit(1);
    }}
    process.exit(0);
    """
    res = subprocess.run([node_path, "-e", eval_script], capture_output=True, text=True)
    assert res.returncode == 0, f"Node verification failed: {res.stderr}"
