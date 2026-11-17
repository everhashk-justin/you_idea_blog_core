"""
publish_remaining_batch.py - 남은 포스트 30~34번 연속 자동 발행 스크립트
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

REMAINING_POSTS = [
    "30_cloud_kubernetes_orchestration.md",
    "31_sec_web_vulnerabilities_sql_xss_csrf.md",
    "32_ai_transformer_attention.md",
    "33_se_solid_principles.md",
    "34_emb_rtos_realtime.md"
]

def main():
    print("=" * 60)
    print("🚀 티스토리 3탄 잔여 포스트 5편 연속 자동 발행 시작")
    print("=" * 60)

    for idx, filename in enumerate(REMAINING_POSTS, start=7):
        target_file = POSTS_DIR / filename
        if not target_file.exists():
            print(f"❌ 파일을 찾을 수 없습니다: {filename}")
            continue

        meta, content = parse_markdown_post(str(target_file))
        category = meta.get("category", "")
        tags = meta.get("tags", [])
        title = meta.get("title", "")

        print(f"\n[{idx}/11] 발행 진행 중: {filename}")
        print(f"📌 제목: {title}")
        print(f"📂 카테고리: {category}")
        print(f"🏷️  태그: {', '.join(tags)}")

        try:
            publish_post(
                title=title,
                content=content,
                tags=tags,
                visibility="public",
                category=category,
                headless=False
            )
            print(f"✅ [{idx}/11] 발행 완료: {filename}")
        except Exception as e:
            print(f"❌ [{idx}/11] 발행 중 오류 발생 ({filename}): {e}")

        # 다음 포스트 발행 전 3초간 세션 휴식
        time.sleep(3)

    print("\n" + "=" * 60)
    print("🎉 11대 카테고리 3탄 잔여 포스트 전수 발행 완료!")
    print("=" * 60)

if __name__ == "__main__":
    main()
