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
    if "login" in page.url:
        page.locator(".btn_login").first.click()
        time.sleep(2)
        page.locator(".wrap_profile").first.click()
        time.sleep(3)
        page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle")
    time.sleep(3)

    # 더미 글 목록 파악 (제목에 '테스트' 또는 '분석' 또는 빈 제목 글)
    dummy_ids = page.evaluate("""() => {
        const ids = [];
        document.querySelectorAll('li:has(.tit_post)').forEach(li => {
            const titleEl = li.querySelector('.tit_post a');
            if (titleEl) {
                const title = titleEl.innerText;
                const href = titleEl.href;
                const m = href.match(/\\/(\\d+)$/);
                // 56번(최신 정상 글) 제외하고, 테스트 글들 선별
                if (m && m[1] !== '56') {
                    if (title.includes('테스트') || title.includes('분석') || title.includes('추적')) {
                        ids.push(m[1]);
                    }
                }
            }
        });
        return ids;
    }""")
    print("정리할 더미 글 번호들:", dummy_ids)

    # 각 더미 글 삭제
    for entry_id in dummy_ids:
        print(f"더미 글 {entry_id} 삭제 중...")
        # 체크박스 선택 후 일괄 삭제 또는 개별 삭제
        page.evaluate(f"""() => {{
            fetch('/manage/post/delete/{entry_id}', {{ method: 'POST' }});
        }}""")
        time.sleep(1)

    page.reload(wait_until="networkidle")
    time.sleep(2)
    page.screenshot(path=str(BASE_DIR / "screenshots" / "cleanup_posts.png"))
    ctx.close()
