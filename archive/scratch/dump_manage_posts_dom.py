"""
dump_manage_posts_dom.py - 관리자 페이지 DOM 구조 분석
"""
import sys
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
PROFILE_DIR = BASE_DIR / "browser_profile"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

blog_name = config.get("blog_name", "softwin")

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=True,
        viewport={"width": 1280, "height": 900},
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
    )
    page = context.pages[0] if context.pages else context.new_page()

    page.goto(f"https://{blog_name}.tistory.com/manage/posts", wait_until="networkidle", timeout=30000)
    time.sleep(3)

    # 링크와 텍스트들을 덤프
    links = page.evaluate("""() => {
        const result = [];
        document.querySelectorAll('a').forEach(a => {
            const txt = a.innerText.trim();
            const href = a.getAttribute('href');
            if (txt || href) {
                result.push({ text: txt, href: href, className: a.className });
            }
        });
        return result;
    }""")
    
    print(f"Total links: {len(links)}")
    for l in links:
        if any(keyword in l['text'] for keyword in ['글', '예약', '공개', '발행', '비공개', '수정', '84', '85', '86', 'PostgreSQL', '클린']):
            print(f"  * {l['text']} -> {l['href']} ({l['className']})")

    context.close()
