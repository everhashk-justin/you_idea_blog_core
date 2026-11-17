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
    time.sleep(2)

    try:
        page.locator("button:has-text('취소')").first.click(timeout=1000)
    except Exception:
        pass

    # 기본모드 버튼 찾기
    mode_btn = page.locator("#editor-mode-layer-btn-open, button:has-text('기본모드')").first
    print("Mode button visible:", mode_btn.is_visible())
    mode_btn.click()
    time.sleep(1)
    page.screenshot(path=str(BASE_DIR / "screenshots" / "mode_dropdown.png"))

    modes = page.evaluate("""() => {
        const results = [];
        document.querySelectorAll("button, a, li").forEach(el => {
            const txt = el.innerText.trim();
            if (txt === "마크다운" || txt === "HTML" || txt === "기본모드") {
                results.push({ text: txt, id: el.id, class: el.className, tag: el.tagName });
            }
        });
        return results;
    }""")
    print("Modes found:", modes)
    ctx.close()
