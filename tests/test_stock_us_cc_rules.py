# -*- coding: utf-8 -*-
"""
tests/test_stock_us_cc_rules.py - Tests for StockUSCoveredCallMandatorySectionsRule and StockUSCoveredCallAntiCopyRule
"""

import pytest
from blog_core.engine.context import create_context
from blog_core.engine.gatekeeper import IroncladGatekeeper
from blog_core.rules.platforms.stock import (
    StockUSCoveredCallMandatorySectionsRule,
    StockUSCoveredCallAntiCopyRule,
)


COMPLIANT_US_CC_POST = """---
layout: post
title: '[2026년 11월] 미국 S&P 500 커버드콜 4대장 실측 비교: JEPI vs SPYI vs GPIX vs XYLD'
date: 2026-11-19 09:00:00 +0900
category: '미국 커버드콜'
categories: ['미국 커버드콜']
tags: [미국커버드콜, JEPI, SPYI, GPIX, XYLD]
---

# 미국 S&P 500 커버드콜 4대장 실측 비교

월스트리트 대표 커버드콜 ETF인 JEPI, SPYI, GPIX, XYLD의 1년 실측 성과를 정밀하게 분석합니다. 이번 조사는 단순한 표면적 분배율 비교를 넘어서서 실제 투자자가 체감하는 자본 손익과 분배금 수령액의 총합을 기준으로 측정되었습니다.

## 1. ETF 기본 정보 및 구조적 아키텍처

각 ETF의 운용 구조는 콜옵션 매도 비중과 기초자산 편입 방식에서 결정적인 차이를 보입니다. JEPI는 저변동성 주식 포트폴리오에 주가연계증권(ELN)을 통한 외가격 콜옵션을 매도하며, SPYI는 S&P 500 원주를 보유하면서 상하방 콜스프레드를 구사하여 상방 잠재력을 2~3% 열어둡니다. 반면 GPIX는 시장 국면에 따라 콜옵션 커버리지를 25%에서 75%까지 능동적으로 조절하는 동적 탄력 전략을 취합니다. XYLD는 전통적인 등가격(ATM) 100% 콜매도 원칙을 고수합니다.

이러한 구조적 차이는 상승장과 하락장에서 전혀 다른 수익률 궤적을 만들어냅니다. 특히 옵션 매도 방식에서 ELN 파생결합증권을 활용하는 경우 발행 증권사의 신용 위험에 간접적으로 노출될 수 있으므로, 자산운용사의 운용 규모와 건전성을 함께 확인해야 합니다. 반면 원주 직접 보유 기반의 콜옵션 매도는 실물 자산이 계좌에 고스란히 담겨 있어 상대적으로 투명성이 높다는 평가를 받습니다. 투자자는 자신이 선호하는 위험 감수 성향과 현금흐름 목표에 맞추어 적절한 종목을 선택해야 합니다.

## 2. 1년 실측 성과 비교 분석

단순 보유와 재투자 전략에 따른 누적 성과는 옵션 매도 프리미엄의 복리 재투자 효과를 극명하게 보여줍니다. 시장 상승기에는 옵션 행사가격 상방 제한으로 인해 벤치마크 지수 대비 언더퍼폼할 수 있으나, 횡보장 및 완만한 상승장에서는 두 자리 수의 높은 분배금이 자본 하락을 완벽히 방어하는 강력한 방패 역할을 수행합니다. 실제로 GPIX는 지수 상승분을 탄력적으로 추종하면서 총수익률 12.31%를 기록하여 지수를 초과 달성하는 기염을 토했습니다.

반면 전통적인 등가격 100% 매도 구조를 취하는 XYLD의 경우 지속적인 원금 침식(NAV Decay) 현상이 관측되었습니다. 이는 지수가 급락한 이후 반등할 때 상방 캡이 꽉 닫혀 있어 원금 회복 탄력성이 현저히 떨어지기 때문입니다. 따라서 장기 투자 관점에서는 단순 분배율이 높은 상품보다 상방 잠재력을 일부 열어두거나 능동적으로 콜비중을 조절하는 선진형 스프레드 전략 ETF가 자산 보존 측면에서 훨씬 우수한 성과를 보였습니다.

## 3. 원화 환율 변동 영향 분석 (Currency FX Impact)

미국 상장 커버드콜 ETF에 직접 투자하는 서학개미에게 원/달러 환율 변동성은 최종 원화 수익률을 결정짓는 핵심적인 독립 변수입니다. 미국 주식 계좌를 통한 직투는 100% 달러 환노출 구조를 가지므로, 환율 상승 국면에서는 강력한 환쿠션 효과가 발생하여 달러 자산 가치 하락을 방어하고 막대한 원화 환차익을 안겨줍니다. 반대로 원화 강세 국면에서는 달러 환차손이 발생하여 배당 수익률의 상당 부분이 침식될 수 있습니다. 실질 원화 수익률은 달러 기준 자산 수익률과 환율 변동률의 기하학적 결합으로 산출되므로, 매월 수령하는 달러 분배금을 즉시 원화로 환전할 것인지, 아니면 달러 예수금으로 유지하여 재투자할 것인지에 대한 통화 관리 전략이 필수적입니다.

## 4. 한국 세금 및 계좌별 절세 비교: 해외 직투 vs 국내 상장 커버드콜

국내 개인 투자자가 미국 커버드콜 전략을 실행할 때 반드시 직면하는 세법상 갈림길은 해외 직투와 국내 상장 커버드콜의 세제 혜택 차이입니다. 해외 직투 시에는 연간 매매차익에 대해 250만 원의 기본공제가 적용된 후 22%의 양도소득세가 분류과세되며, 배당금에 대해서는 15%의 배당소득세가 원천징수되고 연 2,000만 원 초과 시 금융소득종합과세 대상에 포함됩니다.

반면 국내 상장 커버드콜 ETF를 개인종합자산관리계좌(ISA)에서 운용할 경우, 순손익 200만 원(서민형 400만 원)까지 비과세 혜택이 주어지며 초과분은 9.9%로 분리과세되어 절세 효과가 극대화됩니다. 또한 연금저축펀드 및 IRP 계좌에서는 배당소득세 원천징수 없이 100% 과세이연 복리 효과를 누릴 수 있으며, 향후 55세 이후 연금 수령 시 3.3%에서 5.5%의 저율 연금소득세만 부담하면 됩니다. 따라서 자신의 과세표준 구간과 자금 인출 계획에 따라 직투와 절세계좌를 전략적으로 선택해야 합니다.

## 5. 결론 및 실전 포트폴리오 가이드

성공적인 월배당 커버드콜 투자는 단순한 고배당률 숫자에 매몰되지 않고, 하방 방어력과 환율 노출, 그리고 절세계좌를 통한 세금 통제를 종합적으로 설계할 때 비로소 달성될 수 있습니다. 특히 매크로 환경 변화에 민감하게 반응하는 환율 변동성은 서학개미의 자산 건전성을 지키는 데 있어 매우 강력한 변수입니다. 원/달러 환율이 박스권 상단에 도달했을 때는 추가적인 환노출 리스크를 방어하기 위해 국내 상장 환헤지 상품이나 연금계좌 분할 매수를 검토하는 것이 현명한 방법론이 될 수 있습니다. 반대로 원화 강세 구간에서는 미국 직투를 통해 달러 표시 원자산을 매력적인 단가에 축적하고, 향후 경기 변동에 따른 환쿠션 혜택을 온전히 향유하는 전략적 접근이 유효합니다.

옵션 프리미엄을 기반으로 하는 인컴 자산은 매월 일정한 현금흐름을 창출하는 장점이 명확하지만, 상승장에서는 지수 대비 초과 수익이 제한된다는 구조적 한계 역시 존재합니다. 따라서 투자자는 단기적인 시세 차익을 노리기보다는 안정적인 배당 재투자를 통해 자산의 복리 증식을 극대화하는 중장기적인 호흡을 견지해야 합니다. 또한 자산 배분 차원에서 성장주나 지수 추종 ETF와 적절한 비율로 혼합하여 포트폴리오의 탄력성을 유지하는 것이 중요합니다. 철저한 데이터 기반의 원칙 매매만이 장기적인 생존을 담보합니다. 감정에 흔들리지 않고 통계적 우위를 신뢰하는 투자자가 시장의 최종 승자가 됩니다.

본 글은 정보 제공을 목적으로 하며 특정 금융상품의 매수·매도를 권유하지 않습니다. 모든 투자의 책임과 원금 손실 위험은 투자자 본인에게 있습니다.
"""


def test_compliant_us_cc_post_passes():
    rule_sections = StockUSCoveredCallMandatorySectionsRule()
    rule_anticopy = StockUSCoveredCallAntiCopyRule()

    ctx = create_context("growth_engine/03_blog_hub/stock_blog/_posts/test.md", COMPLIANT_US_CC_POST, "stock")
    v_sections = rule_sections.check(ctx)
    v_anticopy = rule_anticopy.check(ctx)

    assert len(v_sections) == 0, f"Expected 0 violations, got: {v_sections}"
    assert len(v_anticopy) == 0, f"Expected 0 violations, got: {v_anticopy}"


def test_missing_exchange_rate_triggers_reject():
    rule = StockUSCoveredCallMandatorySectionsRule()
    # Remove exchange rate section
    bad_post = COMPLIANT_US_CC_POST.replace("## 3. 원화 환율 변동 영향 분석 (Currency FX Impact)", "## 3. 기타 분석")
    bad_post = bad_post.replace("환율", "가격").replace("환노출", "노출").replace("환쿠션", "쿠션").replace("환차익", "차익").replace("환차손", "손실")

    ctx = create_context("growth_engine/03_blog_hub/stock_blog/_posts/test.md", bad_post, "stock")
    violations = rule.check(ctx)

    fx_violations = [v for v in violations if v.rule_id == "G6_STOCK_US_CC_MISSING_EXCHANGE_RATE"]
    assert len(fx_violations) >= 1
    assert fx_violations[0].severity == "REJECT"


def test_missing_tax_strategy_triggers_reject():
    rule = StockUSCoveredCallMandatorySectionsRule()
    # Remove tax section
    bad_post = COMPLIANT_US_CC_POST.replace("22%", "").replace("250만", "").replace("ISA", "").replace("연금저축", "").replace("비과세", "")

    ctx = create_context("growth_engine/03_blog_hub/stock_blog/_posts/test.md", bad_post, "stock")
    violations = rule.check(ctx)

    tax_violations = [v for v in violations if v.rule_id == "G6_STOCK_US_CC_MISSING_TAX_STRATEGY"]
    assert len(tax_violations) >= 1
    assert tax_violations[0].severity == "REJECT"


def test_verbatim_english_paragraph_triggers_reject():
    rule = StockUSCoveredCallAntiCopyRule()
    # Insert raw English paragraph
    raw_en_paragraph = "\n\nThis is a verbatim English paragraph copied directly from the global post without any translation or localization for Korean investors seeking deep insights.\n\n"
    bad_post = COMPLIANT_US_CC_POST + raw_en_paragraph

    ctx = create_context("growth_engine/03_blog_hub/stock_blog/_posts/test.md", bad_post, "stock")
    violations = rule.check(ctx)

    copy_violations = [v for v in violations if v.rule_id == "G6_STOCK_US_CC_VERBATIM_COPY"]
    assert len(copy_violations) >= 1
    assert copy_violations[0].severity == "REJECT"


def test_insufficient_korean_length_triggers_reject():
    rule = StockUSCoveredCallAntiCopyRule()
    # Short post
    short_post = """---
layout: post
title: '미국 커버드콜 JEPI'
category: '미국 커버드콜'
---
짧은 글입니다.
본 글은 정보 제공을 목적으로 하며 특정 금융상품의 매수·매도를 권유하지 않습니다. 모든 투자의 책임과 원금 손실 위험은 투자자 본인에게 있습니다.
"""
    ctx = create_context("growth_engine/03_blog_hub/stock_blog/_posts/test.md", short_post, "stock")
    violations = rule.check(ctx)

    len_violations = [v for v in violations if v.rule_id == "G6_STOCK_US_CC_INSUFFICIENT_LOCALIZATION"]
    assert len(len_violations) >= 1
    assert len_violations[0].severity == "REJECT"


def test_non_target_post_ignored():
    rule_sections = StockUSCoveredCallMandatorySectionsRule()
    rule_anticopy = StockUSCoveredCallAntiCopyRule()

    domestic_post = """---
layout: post
title: '코스피 200 커버드콜 분석'
category: '국내 커버드콜'
---
국내 상장 코스피 200 커버드콜 ETF 분석 리포트입니다.
본 글은 정보 제공을 목적으로 하며 특정 금융상품의 매수·매도를 권유하지 않습니다. 모든 투자의 책임과 원금 손실 위험은 투자자 본인에게 있습니다.
"""
    ctx = create_context("growth_engine/03_blog_hub/stock_blog/_posts/test.md", domestic_post, "stock")
    assert len(rule_sections.check(ctx)) == 0
    assert len(rule_anticopy.check(ctx)) == 0
