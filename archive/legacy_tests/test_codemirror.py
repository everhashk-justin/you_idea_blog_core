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

    # CodeMirror 인스턴스 탐색 및 테스트
    cm_test = page.evaluate("""() => {
        const cmEl = document.querySelector('.CodeMirror');
        if (cmEl && cmEl.CodeMirror) {
            const cm = cmEl.CodeMirror;
            const testHtml = '<p data-ke-size=\"size16\"><strong>CodeMirror 주입 성공 테스트!</strong></p><p data-ke-size=\"size16\">본문이 정상적으로 반영됩니다.</p>';
            cm.setValue(testHtml);
            return {
                found: true,
                value: cm.getValue()
            };
        }
        
        // 만약 .CodeMirror 요소가 여러 개라면
        const allCm = document.querySelectorAll('.CodeMirror');
        return {
            found: false,
            count: allCm.length
        };
    }""")

    print("CodeMirror Test Result:", cm_test)
    time.sleep(2)
    page.screenshot(path=str(BASE_DIR / "screenshots" / "codemirror_inject_test.png"))
    ctx.close()
