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
    page.goto("https://softwin.tistory.com/manage/newpost", wait_until="networkidle")
    if "login" in page.url:
        page.locator(".btn_login").first.click()
        time.sleep(2)
        page.locator(".wrap_profile").first.click()
        time.sleep(3)
        page.goto("https://softwin.tistory.com/manage/newpost", wait_until="networkidle")
    time.sleep(3)

    try:
        page.locator("button:has-text('취소')").first.click(timeout=1000)
    except Exception:
        pass

    # 상단 툴바 우측의 모든 버튼/드롭다운 분석
    top_buttons = page.evaluate("""() => {
        const btns = [];
        document.querySelectorAll('header *, .header_write *, .edit_header *, div[class*=\"header\"] button, div[class*=\"header\"] a').forEach(el => {
            if (el.innerText && el.innerText.trim().length > 0 && el.innerText.trim().length < 20) {
                btns.push({
                    text: el.innerText.trim(),
                    tag: el.tagName,
                    id: el.id,
                    className: el.className
                });
            }
        });
        return btns;
    }""")
    print("Top Header Elements:")
    for b in top_buttons:
        print(b)
    ctx.close()
