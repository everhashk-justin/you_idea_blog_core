# -*- coding: utf-8 -*-
"""
blog_core.rules.platforms.stock - Stock & Context Trading Blog Platform Rules (stock.ideaspot360.com)
"""

import os
import re
from pathlib import Path
from typing import List, Set
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


KO_FINANCIAL_DISCLAIMER_PATTERNS = [
    r"투자\s*(?:유의사항|경고|참고)",
    r"면책\s*(?:고지|문구)",
    r"투자를?\s*(?:권유|자문|추천|판단|책임)",
    r"권유가\s*아닙",
    r"자문이\s*아닙",
    r"추천이\s*아닙",
    r"원금\s*손실",
    r"손실\s*(?:의\s*)?위험",
    r"본\s*(?:글|포스팅|아티클|자료|콘텐츠)은?는?\s*.*?(?:참고|정보\s*제공)",
    r"정보\s*제공\s*목적",
    r"투자\s*결정은\s*본인",
    r"투자의\s*책임은\s*(?:투자자|본인)",
    r"금융소비자보호법",
    r"금소법",
]


class StockDisclaimerRule(BaseRule):
    """맥락트레이딩 국문 증시 블로그 필수 투자 유의사항 및 면책고지 검증 규칙 (Gate 8)"""

    rule_id = "G8_FIN_MISSING_DISCLAIMER"
    gate_id = "GATE_8"
    gate_name = "자본시장법·금소법 방벽"
    description = "맥락트레이딩 국문 증시 블로그(stock) 필수 투자 면책고지(Disclaimer) 강제"
    platforms = ["stock"]
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        has_fin_disclaimer = any(re.search(p, ctx.body) for p in KO_FINANCIAL_DISCLAIMER_PATTERNS)

        if not has_fin_disclaimer:
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id=self.rule_id,
                severity=self.default_severity,
                line_number=0,
                snippet="No investment disclaimer found in financial content",
                message="[자본시장법·금소법 방벽] 금융/증시/재테크 관련 포스팅 최하단에 필수적인 '투자 유의사항 및 면책고지(Disclaimer)'가 누락되었습니다.",
                fix_hint="포스팅 최하단에 '본 글은 정보 제공을 목적으로 하며 특정 금융상품의 매수·매도를 권유하지 않습니다. 모든 투자의 책임과 원금 손실 위험은 투자자 본인에게 있습니다.'를 명시하십시오."
            ))

        return violations


def _is_us_covered_call_post(ctx: RuleContext) -> bool:
    """미국 커버드콜 포스트 여부 판별."""
    category = str(ctx.fm_data.get("category", ""))
    categories = str(ctx.fm_data.get("categories", ""))
    tags = str(ctx.fm_data.get("tags", ""))
    title = str(ctx.fm_data.get("title", ""))

    if any(k in category for k in ["미국 커버드콜", "coveredcall-us", "미국커버드콜"]) or \
       any(k in categories for k in ["미국 커버드콜", "coveredcall-us", "미국커버드콜"]):
        return True

    us_tickers = ["JEPI", "SPYI", "GPIX", "XYLD"]
    has_ticker = any(t in title or t in tags or t in category for t in us_tickers)
    is_cc = any(k in title or k in tags or k in category for k in ["커버드콜", "covered call", "Covered Call"])
    is_us = any(k in title or k in tags or k in category for k in ["미국", "S&P", "S&P500", "US", "월스트리트", "서학개미"])

    return has_ticker and (is_cc or is_us)


def _get_paragraphs_with_keywords(body: str, keywords: List[str]) -> List[str]:
    """본문에서 특정 키워드가 포함된 문단(줄바꿈 2회 기준)들을 추출."""
    paragraphs = re.split(r"\n\s*\n", body)
    matched = []
    for p in paragraphs:
        p_clean = p.strip()
        if not p_clean or p_clean.startswith("#") or p_clean.startswith("|"):
            continue
        if any(k in p_clean for k in keywords):
            matched.append(p_clean)
    return matched


class StockUSCoveredCallMandatorySectionsRule(BaseRule):
    """미국 커버드콜 필수 분석 섹션(원화 환율 영향, 세금/절세 비교) 강제 검증 규칙 (Gate 6)"""

    rule_id = "G6_STOCK_US_CC_MANDATORY_SECTIONS"
    gate_id = "GATE_6"
    gate_name = "미국 커버드콜 현지화 및 필수 분석 방벽"
    description = "미국 커버드콜 포스트 필수 분석 섹션(원화 환율 변동 영향, 한국 세금/절세 비교) 누락 차단"
    platforms = ["stock"]
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        if not _is_us_covered_call_post(ctx):
            return []

        violations: List[Violation] = []

        # 1. 원화 환율 변동 영향 분석 검증
        fx_main_keywords = ["환율"]
        fx_sub_keywords = ["원화", "달러", "환노출", "환쿠션", "환차익", "환차손", "원/달러", "USD/KRW"]

        has_fx_main = any(k in ctx.body for k in fx_main_keywords)
        has_fx_sub = any(k in ctx.body for k in fx_sub_keywords)
        fx_paragraphs = _get_paragraphs_with_keywords(ctx.body, fx_main_keywords + ["환노출", "환쿠션", "USD/KRW"])
        fx_text = " ".join(fx_paragraphs)
        fx_ko_len = len(re.findall(r"[가-힣]", fx_text))

        if not (has_fx_main and has_fx_sub) or fx_ko_len < 200:
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id="G6_STOCK_US_CC_MISSING_EXCHANGE_RATE",
                severity=self.default_severity,
                line_number=0,
                snippet=f"환율 분석 한글 글자수: {fx_ko_len}자 (최소 200자 필요)",
                message="[미국 커버드콜 필수 분석 방벽] 원화 환율 변동 영향 분석(Currency FX Impact: 달러 100% 환노출, 환쿠션 효과, 환차손 리스크 등) 섹션이 누락되었거나 최소 분량(200자)에 미달합니다.",
                fix_hint="원화 환율(USD/KRW) 변동이 실질 원화 수익률 및 분배금에 미치는 영향(달러 100% 환노출, 환쿠션 효과 vs 환차손 리스크)을 최소 200자 이상 심층 분석하십시오."
            ))

        # 2. 한국 세금 및 절세 비교 검증
        tax_kw_capital_gains = ["양도세", "양도소득세", "22%"]
        tax_kw_deduction = ["250만", "250만원"]
        tax_kw_isa = ["ISA"]
        tax_kw_pension = ["연금", "연금저축", "연금계좌"]
        tax_kw_tax_saving = ["비과세", "과세이연", "절세"]

        has_cg = any(k in ctx.body for k in tax_kw_capital_gains)
        has_ded = any(k in ctx.body for k in tax_kw_deduction)
        has_isa = any(k in ctx.body for k in tax_kw_isa)
        has_pension = any(k in ctx.body for k in tax_kw_pension)
        has_ts = any(k in ctx.body for k in tax_kw_tax_saving)

        tax_paragraphs = _get_paragraphs_with_keywords(ctx.body, ["양도세", "양도소득세", "ISA", "연금저축", "절세", "과세이연", "비과세"])
        tax_text = " ".join(tax_paragraphs)
        tax_ko_len = len(re.findall(r"[가-힣]", tax_text))

        if not (has_cg and has_ded and has_isa and has_pension and has_ts) or tax_ko_len < 250:
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id="G6_STOCK_US_CC_MISSING_TAX_STRATEGY",
                severity=self.default_severity,
                line_number=0,
                snippet=f"세금/절세 분석 한글 글자수: {tax_ko_len}자 (최소 250자 필요)",
                message="[미국 커버드콜 필수 분석 방벽] 한국 세금 및 계좌별 절세 비교(해외 직투 양도세 22%/250만 공제 vs 국내 상장 커버드콜 ISA/연금계좌 비과세·과세이연) 섹션이 누락되었거나 최소 분량(250자)에 미달합니다.",
                fix_hint="해외 직투 양도소득세(22%, 기본공제 250만 원)와 국내 상장 커버드콜의 ISA(비과세/분리과세) 및 연금저축/IRP(과세이연 복리) 절세 혜택을 1:1로 비교 분석하는 섹션을 최소 250자 이상 작성하십시오."
            ))

        return violations


class StockUSCoveredCallAntiCopyRule(BaseRule):
    """미국 커버드콜 단순 번역/영문 복사 방지 및 한국 현지화 분량 검증 규칙 (Gate 6)"""

    rule_id = "G6_STOCK_US_CC_ANTI_COPY"
    gate_id = "GATE_6"
    gate_name = "미국 커버드콜 현지화 및 필수 분석 방벽"
    description = "글로벌 영문 원본 글 단순 번역/복사 검출 및 한국 투자자 현지화 분량 강제"
    platforms = ["stock"]
    default_severity = "REJECT"

    def _find_global_post_content(self, ctx: RuleContext) -> str:
        """글로벌 영문 원본 포스트 텍스트 탐색."""
        candidate_paths = [
            Path(ctx.file_path).parents[3] / "stock_blog_global" / "_posts",
            Path(r"d:\00_antigravity\01_stock_alram_longform_blog\growth_engine\03_blog_hub\stock_blog_global\_posts"),
            Path("growth_engine/03_blog_hub/stock_blog_global/_posts"),
        ]
        for dir_path in candidate_paths:
            if dir_path.exists():
                matches = list(dir_path.glob("*sp500-covered-call*"))
                if matches:
                    try:
                        return matches[0].read_text(encoding="utf-8")
                    except Exception:
                        pass
        return ""

    def check(self, ctx: RuleContext) -> List[Violation]:
        if not _is_us_covered_call_post(ctx):
            return []

        violations: List[Violation] = []

        # 1. 영문 원본 문장 무단 직복사 검출
        global_content = self._find_global_post_content(ctx)
        if global_content:
            en_sentences = []
            for line in global_content.splitlines():
                line_s = line.strip()
                if not line_s or line_s.startswith(("#", "|", "```", "---", "<", "!", "*", "[")):
                    continue
                sentences = re.split(r"[.!?]\s+", line_s)
                for s in sentences:
                    s_clean = s.strip()
                    if len(s_clean) >= 35 and re.search(r"^[A-Za-z0-9 ,'\-\(\)]+$", s_clean):
                        en_sentences.append(s_clean)

            copied_found = []
            for s in en_sentences:
                if s in ctx.body:
                    copied_found.append(s)
                    if len(copied_found) >= 3:
                        break

            if copied_found:
                snippet_txt = copied_found[0][:80]
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id="G6_STOCK_US_CC_VERBATIM_COPY",
                    severity=self.default_severity,
                    line_number=0,
                    snippet=snippet_txt,
                    message=f"[단순 복사 차단 방벽] 글로벌 영문 원본 글의 영문 문장({len(copied_found)}건 감지)이 번역/현지화 없이 본문에 직복사되었습니다.",
                    fix_hint="영문 원본 문장을 모두 제거하고 한국 투자자 관점의 독자적인 국문 분석 문장으로 전면 재작성하십시오."
                ))

        # 2. 본문 내 미번역 영문 단락 검출 (영문 30단어 이상 연속 단락)
        paragraphs = re.split(r"\n\s*\n", ctx.body)
        for p in paragraphs:
            p_s = p.strip()
            if not p_s or p_s.startswith(("#", "|", "```", "---", "<", "!")):
                continue
            words = p_s.split()
            en_words = [w for w in words if re.match(r"^[A-Za-z,.\-\'\"]+$", w)]
            ko_chars = re.findall(r"[가-힣]", p_s)
            if len(en_words) >= 20 and len(ko_chars) < 5:
                violations.append(Violation(
                    gate_id=self.gate_id,
                    gate_name=self.gate_name,
                    rule_id="G6_STOCK_US_CC_VERBATIM_COPY",
                    severity=self.default_severity,
                    line_number=0,
                    snippet=p_s[:80],
                    message="[단순 복사 차단 방벽] 국문 포스트 본문에 미번역된 영문 단락(20단어 이상)이 감지되었습니다.",
                    fix_hint="영문 단락을 한국어로 번역하거나 한국 투자자 맞춤형 분석으로 재구성하십시오."
                ))
                break

        # 3. 전체 순수 한글 분량 (최소 2,000자) 및 현지화 섹션 한글 분량 (최소 600자)
        total_ko = len(re.findall(r"[가-힣]", ctx.body))
        if total_ko < 2000:
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id="G6_STOCK_US_CC_INSUFFICIENT_LOCALIZATION",
                severity=self.default_severity,
                line_number=0,
                snippet=f"전체 순수 한글 분량: {total_ko}자 (최소 2,000자 필요)",
                message=f"[한국 현지화 분량 미달] 국문 본문 전체의 순수 한글 분량({total_ko}자)이 최소 요구치(2,000자)에 미달합니다.",
                fix_hint="한국 투자자를 위한 독자적인 심층 해설과 실전 분석을 보강하여 순수 한글 2,000자 이상으로 작성하십시오."
            ))

        fx_paragraphs = _get_paragraphs_with_keywords(ctx.body, ["환율", "환노출", "환쿠션", "USD/KRW"])
        tax_paragraphs = _get_paragraphs_with_keywords(ctx.body, ["양도세", "양도소득세", "ISA", "연금저축", "절세", "과세이연", "비과세"])
        combined_text = " ".join(set(fx_paragraphs + tax_paragraphs))
        fx_tax_ko = len(re.findall(r"[가-힣]", combined_text))

        if fx_tax_ko < 600:
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id="G6_STOCK_US_CC_INSUFFICIENT_LOCALIZATION",
                severity=self.default_severity,
                line_number=0,
                snippet=f"환율 및 세금 현지화 분석 한글 분량: {fx_tax_ko}자 (최소 600자 필요)",
                message=f"[한국 현지화 분석 분량 미달] 환율 영향 및 세금/절세 분석 본문의 한글 분량({fx_tax_ko}자)이 최소 요구치(600자)에 미달합니다.",
                fix_hint="환율 변동성(환노출/환쿠션)과 한국 세법(해외직투 22% vs ISA/연금) 분석을 보강하여 600자 이상으로 작성하십시오."
            ))

        return violations


class StockDiagramVisualQARule(BaseRule):
    """증시 블로그 차트 도안 이미지 실존 및 layout_audit.json 시각 무결성(1920x1080, 결함 0) 강제 검증 규칙 (Gate 6)"""

    rule_id = "G6_STOCK_DIAGRAM_VISUAL_QA"
    gate_id = "GATE_6"
    gate_name = "증시 블로그 도안 및 이미지 시각 무결성 방벽"
    description = "포스트 참조 로컬 도안 이미지 실존 및 layout_audit.json 1920x1080 해상도·결함 0건 기계적 검증"
    platforms = ["stock", "markets"]
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        violations: List[Violation] = []
        if not ctx.file_path:
            return violations

        target_file = Path(ctx.file_path).resolve()
        if not target_file.exists():
            return violations

        candidate_roots = [
            target_file.parent,
            target_file.parent.parent,
            target_file.parent.parent.parent,
            target_file.parent.parent.parent.parent,
            Path.cwd(),
            Path("growth_engine/03_blog_hub/stock_blog"),
            Path("growth_engine/03_blog_hub/stock_blog_global"),
            Path(r"d:\00_antigravity\01_stock_alram_longform_blog\growth_engine\03_blog_hub\stock_blog"),
            Path(r"d:\00_antigravity\01_stock_alram_longform_blog\growth_engine\03_blog_hub\stock_blog_global"),
            Path(r"d:\00_antigravity\01_stock_alram_longform_blog"),
        ]

        # layout_audit.json 파일 탐색 (국내 및 글로벌 블로그 감사 데이터 통합 로드)
        layout_audit_paths = [
            Path.cwd() / "reports" / "stock_blog_audits" / "layout_audit.json",
            Path(r"d:\00_antigravity\01_stock_alram_longform_blog\reports\stock_blog_audits\layout_audit.json"),
            Path.cwd() / "reports" / "stock_blog_global_audits" / "layout_audit.json",
            Path(r"d:\00_antigravity\01_stock_alram_longform_blog\reports\stock_blog_global_audits\layout_audit.json"),
            target_file.parents[3] / "reports" / "stock_blog_audits" / "layout_audit.json" if len(target_file.parents) > 3 else None,
            target_file.parents[3] / "reports" / "stock_blog_global_audits" / "layout_audit.json" if len(target_file.parents) > 3 else None,
        ]
        layout_audit_data = {}
        import json
        for lap in layout_audit_paths:
            if lap and lap.is_file():
                try:
                    loaded = json.loads(lap.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict):
                        layout_audit_data.update(loaded)
                except Exception:
                    pass

        img_refs = re.findall(r'!\[([^\]]*)\]\(([^)]+)\)', ctx.body)
        for alt_text, img_src in img_refs:
            if img_src.startswith("http://") or img_src.startswith("https://"):
                continue

            clean_src = img_src.split("?")[0].split("#")[0]
            file_name = Path(clean_src).name

            # 1. 파일 실존 여부 확인
            found = False
            if clean_src.startswith("/"):
                rel_path = clean_src.lstrip("/")
                for root in candidate_roots:
                    candidate = root / rel_path
                    if candidate.is_file():
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
                    rule_id="G6_STOCK_MISSING_IMAGE_FILE",
                    severity=self.default_severity,
                    line_number=0,
                    snippet=f"![{alt_text}]({img_src})",
                    message=f"[도안 실존 검증 실패] 본문에서 참조하는 이미지 파일 '{clean_src}'이 디스크에 실제로 존재하지 않습니다.",
                    fix_hint="도안 생성 스크립트를 실행하여 정규 이미지를 assets/img/posts/ 디렉토리에 생성하십시오."
                ))
                continue

            # 2. 차트 도안/인포그래픽인 경우 layout_audit.json 검증
            is_diagram = any(k in file_name.lower() for k in ["chart", "comparison", "pullback", "spoofing", "group", "diagram", "capex", "roic", "decompilation", "infographic"]) or file_name in layout_audit_data
            if is_diagram:
                if not layout_audit_data or file_name not in layout_audit_data:
                    violations.append(Violation(
                        gate_id=self.gate_id,
                        gate_name=self.gate_name,
                        rule_id="G6_STOCK_DIAGRAM_UNAUDITED",
                        severity=self.default_severity,
                        line_number=0,
                        snippet=f"도안 파일명: {file_name}",
                        message=f"[도안 육안검수 누락] 차트 도안 '{file_name}'의 layout_audit.json 감사 기록이 존재하지 않습니다.",
                        fix_hint="VisualQAGuard 또는 도안 검증 스크립트를 가동하여 layout_audit.json에 1920x1080 및 무결성 감사 기록을 등록하십시오."
                    ))
                else:
                    entry = layout_audit_data[file_name]
                    # 해상도 확인
                    res = entry.get("resolution") or [entry.get("width_px", 0), entry.get("height_px", 0)]
                    if res != [1920, 1080]:
                        violations.append(Violation(
                            gate_id=self.gate_id,
                            gate_name=self.gate_name,
                            rule_id="G6_STOCK_DIAGRAM_INVALID_RESOLUTION",
                            severity=self.default_severity,
                            line_number=0,
                            snippet=f"실측 해상도: {res}",
                            message=f"[도안 해상도 규격 미달] 차트 도안 '{file_name}'의 해상도가 1920x1080이 아닙니다 (실측: {res}).",
                            fix_hint="도안 렌더러의 DPI 및 figsize 설정을 수정하여 1920x1080 고해상도로 렌더링하십시오."
                        ))

                    # 결함 수 확인
                    defects = entry.get("defects_count", 0)
                    verdict = entry.get("verdict", "")
                    qa_status = entry.get("qa_status", "")
                    if defects > 0 or (verdict != "PASSED_ZERO_DEFECTS" and qa_status != "PASS"):
                        violations.append(Violation(
                            gate_id=self.gate_id,
                            gate_name=self.gate_name,
                            rule_id="G6_STOCK_DIAGRAM_DEFECTS_FOUND",
                            severity=self.default_severity,
                            line_number=0,
                            snippet=f"결함 수: {defects}, 상태: {verdict or qa_status}",
                            message=f"[도안 시각 결함 감지] 차트 도안 '{file_name}'에서 시각적 결함({defects}건)이 발견되었습니다.",
                            fix_hint="타이틀 충돌, 캔버스 이탈, 패딩 부족 등의 결함을 수정한 후 재검증하십시오."
                        ))

                    # 텍스트 오버플로우 결함 검증
                    text_overflow = entry.get("TEXT_OVERFLOW_DEFECTS", entry.get("text_overflow_defects", 0))
                    if text_overflow > 0:
                        violations.append(Violation(
                            gate_id=self.gate_id,
                            gate_name=self.gate_name,
                            rule_id="G6_DIAGRAM_TEXT_OVERFLOW",
                            severity=self.default_severity,
                            line_number=0,
                            snippet=f"오버플로우 결함 수: {text_overflow}",
                            message=f"[도안 텍스트 오버플로우 감지] 차트 도안 '{file_name}'에서 컨테이너 경계를 이탈한 텍스트 결함({text_overflow}건)이 발견되었습니다.",
                            fix_hint="텍스트에 textwrap 줄바꿈을 적용하고 카드 컨테이너 내부 최소 20px 이상의 안전 여백을 확보하십시오."
                        ))

                    # 헤더 컨테이너 무결성 검증
                    header_integrity = entry.get("HEADER_CONTAINER_INTEGRITY", entry.get("header_container_integrity", "PASS"))
                    if header_integrity != "PASS":
                        violations.append(Violation(
                            gate_id=self.gate_id,
                            gate_name=self.gate_name,
                            rule_id="G6_DIAGRAM_HEADER_CONTAINER_BREACH",
                            severity=self.default_severity,
                            line_number=0,
                            snippet=f"헤더 무결성 상태: {header_integrity}",
                            message=f"[도안 헤더 컨테이너 이탈 감지] 차트 도안 '{file_name}'의 섹션 제목/부제가 전용 헤더 컨테이너 박스 외부에 배치되었습니다.",
                            fix_hint="create_modular_box 등을 활용하여 섹션 상단에 전용 헤더 배너 컨테이너를 탑재하고 제목/부제를 100% 포섭하십시오."
                        ))

        return violations
