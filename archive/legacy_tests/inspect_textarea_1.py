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

    info = page.evaluate("""() => {
        const textareas = document.querySelectorAll('textarea');
        const target = textareas[1];
        return {
            outerHTML: target.outerHTML,
            parentHTML: target.parentElement ? target.parentElement.outerHTML.substring(0, 500) : null,
            name: target.name,
            id: target.id,
            className: target.className
        };
    }""")
    print("Textarea[1] Details:")
    print(info)
    ctx.close()
