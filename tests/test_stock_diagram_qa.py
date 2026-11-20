# -*- coding: utf-8 -*-
"""
tests/test_stock_diagram_qa.py - Unit tests for StockDiagramVisualQARule
"""

import json
from pathlib import Path
import pytest
from blog_core.engine.context import create_context
from blog_core.rules.platforms.stock import StockDiagramVisualQARule


def test_stock_diagram_visual_qa_passes_when_audited(tmp_path):
    # 포스트 마크다운 생성
    post_file = tmp_path / "_posts" / "2026-11-20-test-post.md"
    post_file.parent.mkdir(parents=True, exist_ok=True)

    img_dir = tmp_path / "assets" / "img" / "posts"
    img_dir.mkdir(parents=True, exist_ok=True)
    test_img = img_dir / "group03_schd_covered_call_comparison_v2.png"
    test_img.write_text("fake binary")

    audit_dir = tmp_path / "reports" / "stock_blog_audits"
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_file = audit_dir / "layout_audit.json"
    audit_data = {
        "group03_schd_covered_call_comparison_v2.png": {
            "resolution": [1920, 1080],
            "defects_count": 0,
            "verdict": "PASSED_ZERO_DEFECTS"
        }
    }
    audit_file.write_text(json.dumps(audit_data), encoding="utf-8")

    body = "---\nlayout: post\ntitle: '테스트'\n---\n\n![비교 차트](/assets/img/posts/group03_schd_covered_call_comparison_v2.png)\n"
    post_file.write_text(body, encoding="utf-8")

    ctx = create_context(str(post_file), body, platform="stock")

    rule = StockDiagramVisualQARule()
    violations = rule.check(ctx)
    assert len(violations) == 0


def test_stock_diagram_visual_qa_rejects_missing_image(tmp_path):
    post_file = tmp_path / "_posts" / "2026-11-20-test-post.md"
    post_file.parent.mkdir(parents=True, exist_ok=True)

    body = "---\nlayout: post\ntitle: '테스트'\n---\n\n![비교 차트](/assets/img/posts/non_existent_chart.png)\n"
    post_file.write_text(body, encoding="utf-8")

    ctx = create_context(str(post_file), body, platform="stock")

    rule = StockDiagramVisualQARule()
    violations = rule.check(ctx)
    assert any(v.rule_id == "G6_STOCK_MISSING_IMAGE_FILE" for v in violations)


def test_stock_diagram_visual_qa_rejects_unaudited_diagram(tmp_path):
    post_file = tmp_path / "_posts" / "2026-11-20-test-post.md"
    post_file.parent.mkdir(parents=True, exist_ok=True)

    img_dir = tmp_path / "assets" / "img" / "posts"
    img_dir.mkdir(parents=True, exist_ok=True)
    test_img = img_dir / "group99_chart_unaudited.png"
    test_img.write_text("fake binary")

    audit_dir = tmp_path / "reports" / "stock_blog_audits"
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_file = audit_dir / "layout_audit.json"
    audit_file.write_text("{}", encoding="utf-8")

    body = "---\nlayout: post\ntitle: '테스트'\n---\n\n![비교 차트](/assets/img/posts/group99_chart_unaudited.png)\n"
    post_file.write_text(body, encoding="utf-8")

    ctx = create_context(str(post_file), body, platform="stock")

    rule = StockDiagramVisualQARule()
    violations = rule.check(ctx)
    assert any(v.rule_id == "G6_STOCK_DIAGRAM_UNAUDITED" for v in violations)
