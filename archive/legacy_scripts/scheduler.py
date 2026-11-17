"""
scheduler.py - 하루 1편 자동 발행 스케줄러

사용법:
  python scheduler.py                  → 오늘 예약된 글 발행
  python scheduler.py --list           → 발행 큐 현황 출력
  python scheduler.py --publish <id>   → 특정 ID 즉시 발행
  python scheduler.py --publish-all    → 대기 중인 모든 글 즉시 발행

Windows 작업 스케줄러 등록:
  schtasks /create /tn "BlogAutoPublish" /tr "python d:\\00_antigravity\\01_you_idea_blog\\scheduler.py" /sc DAILY /st 09:00
"""

import sys
import os
import json
import argparse
from datetime import date
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
QUEUE_FILE = BASE_DIR / "publish_queue.json"

def load_queue():
    if not QUEUE_FILE.exists():
        print(f"❌ 발행 큐 파일을 찾을 수 없습니다: {QUEUE_FILE}")
        return []
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_queue(queue):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

def print_queue_status(queue):
    print("\n" + "=" * 70)
    print("📋 블로그 발행 큐 현황")
    print("=" * 70)
    
    status_icon = {"pending": "⏳", "published": "✅", "failed": "❌", "skipped": "⏭️"}
    
    for item in queue:
        icon = status_icon.get(item["status"], "❓")
        print(f"  {icon} [{item['id']:2d}] {item['scheduled_date']} | {item['category']}")
        print(f"       📌 {item['title'][:50]}...")
        print()
    
    pending = sum(1 for i in queue if i["status"] == "pending")
    published = sum(1 for i in queue if i["status"] == "published")
    print(f"  📊 총 {len(queue)}편 | 대기 {pending}편 | 발행완료 {published}편")
    print("=" * 70 + "\n")

def publish_item(item):
    """단일 큐 아이템을 발행합니다."""
    from post_publisher import parse_markdown_post, publish_post
    
    md_path = BASE_DIR / item["file"]
    if not md_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {md_path}")
        return False
    
    print(f"\n🚀 발행 시작: [{item['id']}] {item['title']}")
    print(f"   📂 카테고리: {item['category']}")
    print(f"   📅 예약 날짜: {item['scheduled_date']}")
    
    meta, content = parse_markdown_post(str(md_path))
    
    try:
        result = publish_post(
            title=meta["title"],
            content=content,
            tags=meta.get("tags", []),
            visibility=item.get("visibility", "public"),
            category=item["category"]
        )
        return result
    except Exception as e:
        print(f"❌ 발행 실패: {e}")
        return False

def run_today():
    """오늘 예약된 글을 발행합니다."""
    queue = load_queue()
    today = date.today().strftime("%Y-%m-%d")
    
    today_items = [
        item for item in queue 
        if item["scheduled_date"] == today and item["status"] == "pending"
    ]
    
    if not today_items:
        print(f"📅 오늘({today}) 예약된 글이 없습니다.")
        print_queue_status(queue)
        return
    
    print(f"📅 오늘({today}) 발행 예정 글: {len(today_items)}편")
    
    for item in today_items:
        success = publish_item(item)
        
        # 큐 상태 업데이트
        for q_item in queue:
            if q_item["id"] == item["id"]:
                q_item["status"] = "published" if success else "failed"
                q_item["published_at"] = today
                break
        
        save_queue(queue)
        
        if success:
            print(f"✅ 발행 성공: {item['title']}")
        else:
            print(f"❌ 발행 실패: {item['title']}")

def run_publish_id(target_id):
    """특정 ID의 글을 즉시 발행합니다."""
    queue = load_queue()
    
    item = next((i for i in queue if i["id"] == target_id), None)
    if not item:
        print(f"❌ ID {target_id}를 찾을 수 없습니다.")
        return
    
    success = publish_item(item)
    
    for q_item in queue:
        if q_item["id"] == target_id:
            q_item["status"] = "published" if success else "failed"
            q_item["published_at"] = date.today().strftime("%Y-%m-%d")
            break
    
    save_queue(queue)

def run_publish_all():
    """대기 중인 모든 글을 순서대로 발행합니다."""
    queue = load_queue()
    pending = [i for i in queue if i["status"] == "pending"]
    
    print(f"🚀 대기 중인 글 {len(pending)}편을 순서대로 발행합니다...", flush=True)
    
    for item in pending:
        success = publish_item(item)
        
        for q_item in queue:
            if q_item["id"] == item["id"]:
                q_item["status"] = "published" if success else "failed"
                q_item["published_at"] = date.today().strftime("%Y-%m-%d")
                break
        
        save_queue(queue)
        
        if success:
            print(f"✅ 완료: {item['title']}", flush=True)
        else:
            print(f"❌ 실패: {item['title']}", flush=True)
        
        # 글 간 안정적인 쿨다운
        import time
        time.sleep(3)

def setup_windows_scheduler():
    """Windows 작업 스케줄러에 매일 오전 9시 자동 발행을 등록합니다."""
    script_path = str(BASE_DIR / "scheduler.py")
    python_path = sys.executable
    
    cmd = (
        f'schtasks /create /f /tn "SoftwinBlogAutoPublish" '
        f'/tr "\\"{python_path}\\" \\"{script_path}\\"" '
        f'/sc DAILY /st 09:00 /rl HIGHEST'
    )
    
    print("🔧 Windows 작업 스케줄러 등록 중...")
    print(f"   명령어: {cmd}")
    ret = os.system(cmd)
    if ret == 0:
        print("✅ 스케줄러 등록 완료! 매일 오전 9시에 자동 발행됩니다.")
    else:
        print("⚠️  스케줄러 등록 실패. 관리자 권한으로 실행하거나 수동으로 등록하세요.")
        print(f"   수동 명령어: {cmd}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="블로그 자동 발행 스케줄러")
    parser.add_argument("--list", action="store_true", help="발행 큐 목록 출력")
    parser.add_argument("--publish", type=int, metavar="ID", help="특정 ID 즉시 발행")
    parser.add_argument("--publish-all", action="store_true", help="대기 중 모든 글 발행")
    parser.add_argument("--setup-scheduler", action="store_true", help="Windows 작업 스케줄러 등록")
    
    args = parser.parse_args()
    
    if args.list:
        queue = load_queue()
        print_queue_status(queue)
    elif args.publish:
        run_publish_id(args.publish)
    elif args.publish_all:
        run_publish_all()
    elif args.setup_scheduler:
        setup_windows_scheduler()
    else:
        # 기본: 오늘 예약된 글 발행
        run_today()
