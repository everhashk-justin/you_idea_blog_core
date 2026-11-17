import sys
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
profile_dir = BASE_DIR / "browser_profile"

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=str(profile_dir),
        headless=True,
        viewport={"width": 1280, "height": 1200}
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://softwin.tistory.com/manage/posts", wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    
    if "login" in page.url or "auth" in page.url:
        page.locator(".btn_login, a:has-text('카카오계정으로 로그인')").first.click()
        page.wait_for_timeout(2000)
        prof = page.locator(".wrap_profile, .item_account").first
        if prof.is_visible(timeout=3000):
            prof.click()
            page.wait_for_timeout(3000)
        page.goto("https://softwin.tistory.com/manage/posts", wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

    for p_num in range(1, 5):
        print(f"\n==================== [PAGE {p_num}] ====================")
        rows = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('.tbl_board tbody tr, ul.list_board li, ul.list_post > li')).map(r => {
                const t = r.querySelector('.tit_post, .txt_title, a[href*="/manage/newpost"], .link_title');
                const d = r.querySelector('.txt_date, .date, .time_post');
                return {
                    title: t ? t.innerText.trim() : "",
                    date: d ? d.innerText.trim() : "",
                    text: r.innerText.replace(/\\s+/g, ' ').trim()
                };
            });
        }""")
        for idx, r in enumerate(rows):
            print(f"[{idx+1:02d}] {r['title']} | {r['text']}")

        # 다음 페이지 클릭
        next_btn = page.locator(f"a.link_page:has-text('{p_num + 1}'), a[href*='page={p_num + 1}']").first
        if next_btn.is_visible():
            next_btn.click()
            page.wait_for_timeout(3000)
        else:
            print(f"No next page button found for page {p_num + 1}")
            break

    ctx.close()

