"""
inspect_posts_for_edit.py - 수정할 11편 글의 수정 링크 및 ID 확인
"""
import sys
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
profile_dir = BASE_DIR / "browser_profile"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=str(profile_dir),
        headless=True,
        viewport={"width": 1280, "height": 1000}
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://softwin.tistory.com/manage/posts", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    # 자동 로그인
    if "login" in page.url or "auth" in page.url:
        login_btn = page.locator(".btn_login, a:has-text('카카오계정으로 로그인')").first
        if login_btn.is_visible(timeout=3000):
            login_btn.click()
            page.wait_for_timeout(2000)
        prof = page.locator(".wrap_profile, .item_account").first
        if prof.is_visible(timeout=3000):
            prof.click()
            page.wait_for_timeout(3000)
        page.goto("https://softwin.tistory.com/manage/posts", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

    # 글 목록 전체 정보 가져오기
    posts_data = page.evaluate("""() => {
        const rows = document.querySelectorAll('.tbl_board tbody tr, ul.list_board li, ul.list_post > li');
        const results = [];
        rows.forEach((r, idx) => {
            const titleEl = r.querySelector('.tit_post, .txt_title, a[href*="/manage/newpost"], .link_title');
            const links = Array.from(r.querySelectorAll('a')).map(a => ({ text: a.innerText.trim(), href: a.href }));
            results.push({
                index: idx,
                title: titleEl ? titleEl.innerText.trim() : "",
                links: links
            });
        });
        return results;
    }""")

    print(f"총 {len(posts_data)}개 글 감지됨:")
    for p_info in posts_data:
        print(f"[{p_info['index']}] {p_info['title'][:35]}... | 전체링크: {p_info['links']}")

    ctx.close()
