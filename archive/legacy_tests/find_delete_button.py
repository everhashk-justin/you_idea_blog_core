import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=str(BASE_DIR / "browser_profile"),
        headless=True
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    page.on("dialog", lambda d: d.accept())

    page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle")
    if "login" in page.url or "auth" in page.url:
        page.locator(".btn_login").first.click()
        time.sleep(2)
        page.locator(".wrap_profile").first.click()
        time.sleep(3)
        page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle")
    time.sleep(2)

    # 행에 hover
    rows = page.locator("li:has(.tit_post)")
    row_count = rows.count()
    print(f"Total rows: {row_count}")

    if row_count > 1:
        # 2번째 행 hover
        target_row = rows.nth(1)
        target_row.hover()
        time.sleep(1)
        page.screenshot(path=str(BASE_DIR / "screenshots" / "hover_row_1.png"))

        # 행 내부의 모든 버튼 정보
        btn_details = target_row.evaluate("""el => {
            const list = [];
            el.querySelectorAll('button, a').forEach(b => {
                list.push({
                    text: b.innerText.trim(),
                    tag: b.tagName,
                    className: b.className,
                    outerHTML: b.outerHTML
                });
            });
            return list;
        }""")
        print("Row elements during hover:")
        for b in btn_details:
            print(b)

    ctx.close()
