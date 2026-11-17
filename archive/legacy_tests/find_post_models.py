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

    # 에디터 내부의 post 관련 모델/함수 탐색
    res = page.evaluate("""() => {
        // window 또는 글로벌 스코프에서 tistory 또는 blog 관련 객체
        const info = {};
        for (let k of Object.keys(window)) {
            if (k.toLowerCase().includes('tistory') || k.toLowerCase().includes('entry') || k.toLowerCase().includes('post')) {
                info[k] = typeof window[k];
            }
        }
        
        // 티스토리 config 변수
        if (window.TISTORY) info['TISTORY'] = window.TISTORY;
        if (window.tistory) info['tistory'] = window.tistory;
        if (window.T) info['T'] = window.T;

        return info;
    }""")
    print("Post objects found:", res)
    ctx.close()
