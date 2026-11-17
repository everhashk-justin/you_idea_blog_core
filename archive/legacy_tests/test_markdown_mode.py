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

    # 다이얼로그 자동 확인
    page.on("dialog", lambda d: d.accept())

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

    # 모드 버튼 클릭
    print("모드 드롭다운 열기...")
    page.locator("#editor-mode-layer-btn-open, #editor-mode-layer-btn button").first.click()
    time.sleep(1)

    # 마크다운 모드 클릭
    print("마크다운 모드 선택...")
    page.locator("#editor-mode-markdown, div:has-text('마크다운')").last.click()
    time.sleep(2)

    page.screenshot(path=str(BASE_DIR / "screenshots" / "switched_to_markdown.png"))

    # 마크다운 모드에서 CodeMirror 상태 확인
    cm_info = page.evaluate("""() => {
        const cmEl = document.querySelector('.CodeMirror');
        if (cmEl && cmEl.CodeMirror) {
            cmEl.CodeMirror.setValue('# 마크다운 모드 정상 작동 확인\\n\\n본문이 제대로 들어갑니다!');
            return {
                ready: true,
                val: cmEl.CodeMirror.getValue()
            };
        }
        return { ready: false };
    }""")
    print("CodeMirror ready in Markdown mode:", cm_info)
    page.screenshot(path=str(BASE_DIR / "screenshots" / "markdown_cm_injected.png"))

    ctx.close()
