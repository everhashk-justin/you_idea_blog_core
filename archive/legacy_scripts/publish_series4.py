"""
publish_series4.py - 제4탄 11개 챕터 잔여 포스트 (39번 ~ 45번) 연속 자동 발행 스크립트
"""

import sys
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
POSTS_DIR = BASE_DIR / "posts"

from post_publisher import publish_post, parse_markdown_post

POSTS_TO_PUBLISH = [
    ("39_fe_reflow_repaint.md", "프론트엔드 & 클라이언트"),
    ("40_db_redis_caching.md", "데이터베이스 & 스토리지"),
    ("41_cloud_cicd_github_actions.md", "클라우드, DevOps & 인프라"),
    ("42_sec_zero_trust.md", "보안 & 인증 기술"),
    ("43_ai_rag_architecture.md", "AI, 머신러닝 & 빅데이터"),
    ("44_se_tdd_clean_architecture.md", "소프트웨어 공학 & 아키텍처"),
    ("45_emb_blockchain_consensus.md", "임베디드 & 차세대 기술")
]

def main():
    print("=" * 65)
    print("🚀 제4탄 11대 카테고리 잔여 7편 연속 자동 공개 발행 시작")
    print("=" * 65)

    results = []

    for idx, (filename, category_name) in enumerate(POSTS_TO_PUBLISH, start=5):
        target_file = POSTS_DIR / filename
        if not target_file.exists():
            print(f"❌ 파일을 찾을 수 없습니다: {filename}")
            results.append((filename, False, "파일 없음"))
            continue

        meta, content = parse_markdown_post(str(target_file))
        category = category_name or meta.get("category", "")
        tags = meta.get("tags", [])
        title = meta.get("title", "")

        print(f"\n============================================================")
        print(f"[{idx}/11] 발행 시작: {filename}")
        print(f"📌 제목: {title}")
        print(f"📂 카테고리: {category}")
        print(f"🏷️  태그: {', '.join(tags)}")
        print(f"============================================================")

        try:
            publish_post(
                title=title,
                content=content,
                tags=tags,
                visibility="public",
                category=category,
                headless=True
            )
            print(f"✅ [{idx}/11] 발행 완료: {filename}")
            results.append((filename, True, "발행 성공"))
        except Exception as e:
            print(f"❌ [{idx}/11] 발행 중 오류: {e}")
            results.append((filename, False, str(e)))

        print("⏳ 다음 포스트 발행 전 3초 대기...")
        time.sleep(3)

    print("\n" + "=" * 65)
    print("📊 [제4탄 연속 발행 최종 결과]")
    print("=" * 65)
    for fn, success, msg in results:
        status_icon = "✅" if success else "❌"
        print(f"  {status_icon} {fn}: {msg}")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    main()

