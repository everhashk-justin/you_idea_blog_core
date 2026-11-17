# -*- coding: utf-8 -*-
"""
blog_core.rules.platforms.gear - Gear & Hardware Blog Platform Rules (gear.ideaspot360.com)
"""

import os
import re
from pathlib import Path
from typing import List
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


class GearFrontmatterRule(BaseRule):
    """기어 블로그 Frontmatter 메타데이터 검증 규칙 (Gate 1)"""

    rule_id = "G1_GEAR_REQ_FRONTMATTER"
    gate_id = "GATE_1"
    gate_name = "구조 및 메타데이터 무결성"
    description = "기어 블로그의 경우 'category' 대신 'series' 필드가 있어도 허용"
    platforms = ["gear"]
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        if ctx.fm_data.get("template") == "splash" or ctx.file_path.replace("\\", "/").endswith(("/index.md", "/index.mdx", "index.md", "index.mdx")):
            return []
        has_category = bool(ctx.fm_data.get("category", "").strip())
        has_series = bool(ctx.fm_data.get("series", "").strip())

        if not has_category and not has_series:
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id="G1_REQ_FRONTMATTER",
                severity=self.default_severity,
                line_number=1,
                snippet="Missing both 'category' and 'series'",
                message="기어 블로그 Frontmatter에 'category' 또는 'series' 필드가 누락되었습니다.",
                fix_hint="Frontmatter에 'category: <값>' 또는 'series: <시리즈명>'을 명시하십시오."
            ))

        return violations


class GearDiagramImageFormatRule(BaseRule):
    """기어 공학 도안 이미지 포맷 검증 규칙 (Gate 6)"""

    rule_id = "G6_GEAR_INVALID_IMAGE_EXT"
    gate_id = "GATE_6"
    gate_name = "기어 공학 블로그 규격 검증"
    description = "도안 이미지는 고해상도 PNG 또는 벡터 SVG/WebP 포맷 필수"
    platforms = ["gear"]
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        img_refs = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', ctx.body)
        for alt_text, img_src in img_refs:
            # 외부 URL(http/https)은 확장자 검사 제외
            if img_src.startswith("http://") or img_src.startswith("https://"):
                continue
            clean_src = img_src.split("?")[0].split("#")[0].lower()
            if not any(clean_src.endswith(ext) for ext in [".png", ".svg", ".webp"]):
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=0,
                    snippet=f"![{alt_text}]({img_src})",
                    message=f"도안 이미지 경로 '{img_src}'의 확장자가 정규 포맷(.png, .svg, .webp)이 아닙니다.",
                    fix_hint="정규 벡터 SVG 또는 고해상도 300DPI PNG 포맷을 사용하십시오."
                ))
        return violations


class GearDiagramImageFileExistRule(BaseRule):
    """기어 공학 도안 이미지 실존 여부 검증 규칙 (Gate 6)"""

    rule_id = "G6_GEAR_MISSING_IMAGE_FILE"
    gate_id = "GATE_6"
    gate_name = "기어 공학 블로그 규격 검증"
    description = "마크다운에서 참조하는 로컬 도안 이미지 파일이 디스크에 실제 존재하는지 검증"
    platforms = ["gear"]
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        if not ctx.file_path:
            return violations

        target_file = Path(ctx.file_path).resolve()
        # 가상 파일(메모리 검증 등)인 경우 디스크 실존 검사 스킵
        if not target_file.exists():
            return violations

        # 프로젝트/블로그 루트 추정
        candidate_roots = [
            target_file.parent,
            target_file.parent.parent,
            target_file.parent.parent.parent,
            target_file.parent.parent.parent.parent,
            Path.cwd(),
            Path("blog"),
            Path("d:/01_ag_gear/01_gear/blog"),
        ]

        img_refs = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', ctx.body)
        for alt_text, img_src in img_refs:
            if img_src.startswith("http://") or img_src.startswith("https://"):
                continue

            clean_src = img_src.split("?")[0].split("#")[0]
            # /images/... 형태
            found = False
            if clean_src.startswith("/"):
                rel_path = clean_src.lstrip("/")
                for root in candidate_roots:
                    if (root / "public" / rel_path).is_file() or (root / rel_path).is_file():
                        found = True
                        break
            else:
                for root in candidate_roots:
                    if (target_file.parent / clean_src).is_file() or (root / clean_src).is_file():
                        found = True
                        break

            if not found:
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=0,
                    snippet=f"![{alt_text}]({img_src})",
                    message=f"도안 이미지 파일 '{img_src}'이 디스크의 public 또는 참조 디렉토리에 실제로 존재하지 않습니다.",
                    fix_hint="도안 생성 스크립트를 실행하여 정규 이미지를 public 디렉토리에 생성하십시오."
                ))

        return violations


class GearZeroOverlapMandateRule(BaseRule):
    """기어 맞물림 도안 치형 오버랩 0.000 mm 무간섭 입증 수치 명시 의무 규칙 (Gate 6, 헌법 제10조)"""

    rule_id = "G6_GEAR_ZERO_OVERLAP_MANDATE"
    gate_id = "GATE_6"
    gate_name = "기어 공학 블로그 규격 검증"
    description = "맞물림 치형 도안이 포함된 글은 치면 오버랩 0.000 mm 무간섭 입증 수치를 본문에 명시해야 함"
    platforms = ["gear"]
    default_severity = "WARNING"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        mesh_keywords = ["asymmetric_mesh_profile", "실측 2D 맞물림 치형", "Conjugate Meshing Profile", "치형 맞물림", "맞물림 치형"]
        if any(kw in ctx.body for kw in mesh_keywords):
            proof_keywords = ["0.000", "오버랩", "Zero-overlap", "zero-overlap", "overlap", "オーバーラップ", "Hinterschnittfreiheit"]
            has_proof = any(term in ctx.body for term in proof_keywords)
            if not has_proof:
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.default_severity,
                    line_number=0,
                    snippet="Conjugate Meshing Profile without zero-overlap verification proof",
                    message="맞물림 치형 도안이 포함된 글에서 치면 오버랩 0.000 mm 무간섭 입증 수치가 기술되지 않았습니다.",
                    fix_hint="순수 위상각 정렬에 따른 오버랩 0.000000 mm² 완전 소멸 실측치를 본문에 명시하십시오."
                ))
        return violations
