"""
audit_all_blogs_complete.py - SQLite DB(data/posts.db) 기반 전 생태계 블로그 전수 종합 감사
"""
import sys
import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from ironclad_gatekeeper import IroncladGatekeeper

gk = IroncladGatekeeper()

conn = sqlite3.connect(os.path.join(BASE_DIR, 'data', 'posts.db'))
c = conn.cursor()

platforms = [
    ("dev", "글로벌 개발 블로그 (dev.ideaspot360.com)"),
    ("tistory", "티스토리 기술 블로그 (softwin.tistory.com)"),
    ("naver", "네이버 3대 전문 블로그 (solidlog / tidynote / infopiece)"),
    ("gear", "H-GEAR STUDIO 기어 블로그 (gear.ideaspot360.com)"),
    ("stock", "증시 맥락 1분 주식 블로그 (stock.ideaspot360.com)"),
    ("markets", "글로벌 매크로·증시 블로그 (markets.ideaspot360.com)")
]

print("=" * 80)
print("🛡️ [Ironclad Gatekeeper v2.0] DB 기반 전 생태계 블로그 전수 검증 종합 감사")
print("=" * 80)

total_checked = 0
total_passed = 0
total_rejected = 0

for plat_key, plat_name in platforms:
    # 정적 html/about 페이지 제외하고 순수 포스팅 파일만 필터링
    c.execute(
        """
        SELECT id, title, file_path, status, track 
        FROM blog_posts 
        WHERE platform = ? AND file_path LIKE '%.md' AND file_path NOT LIKE '%about.md' AND file_path NOT LIKE '%privacy.md'
        ORDER BY id
        """,
        (plat_key,)
    )
    rows = c.fetchall()
    
    print(f"\n📂 [{plat_name}]")
    print(f"  • DB 등록 포스트 수: {len(rows)}편")
    
    scores = []
    passed = 0
    rejected = 0
    missing = 0
    rejected_details = []

    for row in rows:
        post_id, title, fpath, status, track = row
        abs_path = os.path.join(BASE_DIR, fpath)
        
        if not os.path.exists(abs_path):
            missing += 1
            continue
            
        total_checked += 1
        rep = gk.verify(abs_path, platform_override=plat_key)
        scores.append(rep.score)
        
        if rep.is_passed:
            passed += 1
            total_passed += 1
        else:
            rejected += 1
            total_rejected += 1
            reject_items = [v for v in rep.violations if v.severity == "REJECT"]
            rejected_details.append((os.path.basename(fpath), rep.score, reject_items))

    avg_score = sum(scores) / len(scores) if scores else 0
    print(f"  • 실사 검증: {len(scores)}편 (로컬 미존재: {missing}편)")
    print(f"  • 통과: {passed}편 | 차단: {rejected}편")
    print(f"  • 평균 점수: {avg_score:.1f} / 100점")
    
    if rejected_details:
        print("  ⚠️ 차단된 글 목록 및 위반 사유:")
        for fname, sc, reasons in rejected_details:
            print(f"    - [{sc}점] {fname}")
            for r in reasons:
                print(f"      * [REJECT] {r.gate_name} ({r.rule_id}): {r.message}")

conn.close()

print("\n" + "=" * 80)
print("📊 [DB 기반 전 생태계 최종 통합 검증 결과 요약]")
print("=" * 80)
print(f"  총 검증 글 수 : {total_checked}편")
print(f"  통과 (PASSED) : {total_passed}편 ({(total_passed / total_checked * 100 if total_checked else 0):.1f}%)")
print(f"  차단 (REJECT) : {total_rejected}편")
print("=" * 80)
