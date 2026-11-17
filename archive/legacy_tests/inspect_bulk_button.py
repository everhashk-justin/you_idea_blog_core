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

    page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle")
    if "login" in page.url or "auth" in page.url:
        page.locator(".btn_login").first.click()
        time.sleep(2)
        page.locator(".wrap_profile").first.click()
        time.sleep(3)
        page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle")
    time.sleep(2)

    # 1개 체크박스 선택
    chk = page.locator("li:has(.tit_post) input[type='checkbox']").nth(1)
    chk.click()
    time.sleep(1)

    # 상단 툴바의 '변경' 버튼 찾기
    btn_info = page.evaluate("""() => {
        const btns = [];
        document.querySelectorAll('.box_board button, .area_menu button, .head_board button, button').forEach(b => {
            if (b.innerText.includes('변경')) {
                btns.push({
                    text: b.innerText,
                    outerHTML: b.outerHTML,
                    className: b.className,
                    id: b.id
                });
            }
        });
        return btns;
    }""")
    print("Change button info:", btn_info)

    # 변경 버튼 클릭
    change_btn = page.locator(".head_board button:has-text('변경'), .box_board button:has-text('변경'), button:has-text('변경')").first
    change_btn.click()
    time.sleep(1)
    page.screenshot(path=str(BASE_DIR / "screenshots" / "real_change_menu.png"))

    # 드롭다운 내부 옵션 확인
    menu_items = page.evaluate("""() => {
        const items = [];
        document.querySelectorAll('.layer_menu a, .layer_menu button, ul.list_opt li, .drop_menu *').forEach(el => {
            if (el.innerText.trim()) items.push(el.innerText.trim());
        });
        return items;
    }""")
    print("Menu items in change layer:", menu_items)

    ctx.close()
