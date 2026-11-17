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

    # 에디터의 주요 객체 및 에디터 컴포넌트 분석
    analysis = page.evaluate("""() => {
        // Redux store 또는 React fiber 탐색
        let reduxState = null;
        let root = document.querySelector('#root') || document.querySelector('#editor-root') || document.querySelector('#kakaoContent');
        
        // window 객체 탐색
        const winProps = [];
        for (let k in window) {
            if (k.startsWith('__') || k.includes('store') || k.includes('Store') || k.includes('Editor') || k.includes('post') || k.includes('publish')) {
                winProps.push(k);
            }
        }

        // React Root Fiber 탐색
        let reactProps = [];
        if (root) {
            for (let k in root) {
                if (k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance') || k.startsWith('__reactContainer')) {
                    reactProps.push(k);
                }
            }
        }

        return {
            winProps: winProps,
            reactProps: reactProps,
            hasTinymce: !!window.tinymce,
            tinymceContent: window.tinymce && window.tinymce.activeEditor ? window.tinymce.activeEditor.getContent() : null
        };
    }""")
    print("Analysis:", analysis)
    ctx.close()
