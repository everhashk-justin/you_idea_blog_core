"""
map_posts_to_files.py - 25개 예약 글과 로컬 마크다운 파일 1:1 매핑 확인
"""
import json
import glob
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MAPPING_FILE = BASE_DIR / "scratch" / "tistory_reserved_mapping.json"
POSTS_DIR = BASE_DIR / "posts"

with open(MAPPING_FILE, "r", encoding="utf-8") as f:
    reserved_posts = json.load(f)

md_files = list(POSTS_DIR.glob("*.md"))

mapping_result = []

for p in reserved_posts:
    post_id = p["postId"]
    title = p["title"]
    # [예약]85. 클린 아키텍처... 에서 숫자 추출
    # 예: '[예약]85.' -> 85
    import re
    m = re.search(r'\[예약\](\d+)\.', title)
    if not m:
        m = re.search(r'(\d+)\.', title)
    
    num = m.group(1) if m else None
    matched_file = None
    if num:
        # posts 폴더에서 num_ 으로 시작하는 파일 찾기
        for mf in md_files:
            fname = mf.name
            if fname.startswith(f"{num}_"):
                matched_file = mf
                break
    
    mapping_result.append({
        "postId": post_id,
        "num": num,
        "title": title,
        "editUrl": p["editUrl"],
        "matchedFile": str(matched_file) if matched_file else None,
        "matchedFileName": matched_file.name if matched_file else None
    })

print(f"Total mapped: {len(mapping_result)}")
all_matched = True
for m in mapping_result:
    status = "OK" if m["matchedFile"] else "MISSING"
    if not m["matchedFile"]:
        all_matched = False
    print(f"[{status}] Post ID {m['postId']} (No.{m['num']}) -> {m['matchedFileName']}")

print(f"\nAll files matched 100%: {all_matched}")

with open(BASE_DIR / "scratch" / "final_update_plan.json", "w", encoding="utf-8") as f:
    json.dump(mapping_result, f, ensure_ascii=False, indent=2)
