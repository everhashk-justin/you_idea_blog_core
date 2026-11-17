import json
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
    if "login" in page.url or "auth" in page.url:
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

    # 에디터 내의 hidden input, form, textarea 요소 조사
    form_elements = page.evaluate("""() => {
        const inputs = [];
        document.querySelectorAll("form, input, textarea").forEach(el => {
            inputs.push({
                tag: el.tagName,
                id: el.id,
                name: el.name,
                type: el.type,
                valueLen: el.value ? el.value.length : 0,
                className: el.className
            });
        });
        return inputs;
    }""")

    print("=== FORM ELEMENTS IN EDITOR ===")
    for el in form_elements:
        if el["name"] or el["id"] or el["valueLen"] > 0:
            print(el)

    ctx.close()
