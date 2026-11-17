"""
find_tistory_edit_links.py
"""
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
    time.sleep(2)

    # 카카오 로그인
    if "login" in page.url or "auth" in page.url:
        try:
            page.locator(".btn_login, a:has-text('카카오계정으로 로그인')").first.click()
            time.sleep(2)
            page.locator(".wrap_profile, .item_account").first.click()
            time.sleep(3)
        except Exception:
            pass

    page.goto(f"https://{blog_name}.tistory.com/manage/posts", wait_until="networkidle", timeout=20000)
    time.sleep(2)

    # 예약 탭 클릭 시도
    # HTML 내 탭 요소 탐색
    tab_info = page.evaluate("""() => {
        const tabs = [];
        document.querySelectorAll('a, button').forEach(el => {
            const txt = el.innerText.trim();
            if (txt.includes('예약') || txt.includes('전체') || txt.includes('발행') || txt.includes('비공개')) {
                tabs.push({ text: txt, tag: el.tagName, href: el.getAttribute('href') });
            }
        });
        return tabs;
    }""")
    print("Tabs found:", tab_info)

    # 만약 예약 탭이 있으면 클릭
    res_tab = page.locator("a:has-text('예약'), button:has-text('예약')").first
    if res_tab.is_visible():
        print("Clicking reserved tab...")
        res_tab.click()
        time.sleep(2)

    # 글 목록 아이템들 덤프
    posts_data = page.evaluate("""() => {
        const posts = [];
        // 티스토리 관리자 목록 행들
        document.querySelectorAll('.list_post li, .tbl_post tbody tr, .table_list tr, .item_post').forEach(el => {
            const titleEl = el.querySelector('.tit_post, .link_tit, .title, a[href*=\"/manage/post/\"], a[href*=\"/manage/newpost\"]');
            const editEl = el.querySelector('a[href*=\"/manage/post/\"]');
            posts.push({
                fullText: el.innerText.replace(/\\s+/g, ' ').trim(),
                title: titleEl ? titleEl.innerText.trim() : '',
                editUrl: editEl ? editEl.href : ''
            });
        });
        return posts;
    }""")

    print(f"\nPosts found on page: {len(posts_data)}")
    for idx, p in enumerate(posts_data[:20]):
        print(f"[{idx+1}] Title: {p['title']} | Edit: {p['editUrl']}")
        print(f"     Text: {p['fullText'][:100]}")

    page.screenshot(path=str(BASE_DIR / "screenshots" / "manage_posts_table.png"))
    context.close()
