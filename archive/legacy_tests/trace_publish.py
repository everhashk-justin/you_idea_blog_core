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

    requests_log = []
    def on_req(req):
        if req.method == "POST":
            requests_log.append({
                "url": req.url,
                "method": req.method,
                "data": req.post_data
            })
    page.on("request", on_req)

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
    except:
        pass

    # 제목 입력
    page.locator("#post-title-inp").first.fill("네트워크 페이로드 테스트")

    # 본문 주입
    html = "<p>이것은 네트워크 테스트 본문입니다. 티스토리 에디터에 제대로 들어가는지 확인합니다.</p>"
    page.evaluate("""html => {
        window.tinymce.activeEditor.setContent(html);
        window.tinymce.activeEditor.fire('change');
        window.tinymce.activeEditor.fire('input');
        window.tinymce.activeEditor.save();
    }""", html)
    time.sleep(1)

    # 완료 버튼
    page.locator("#publish-layer-btn").first.click()
    time.sleep(2)

    # 비공개 선택
    try:
        page.locator("#open0, label[for='open0']").first.click()
    except:
        pass
    time.sleep(1)

    requests_log.clear()

    # 최종 발행
    page.locator("#publish-btn").first.click()
    time.sleep(5)

    print("=== CAPTURED POST REQUESTS ===")
    for r in requests_log:
        print(f"URL: {r['url']}")
        data_str = str(r['data'])
        print(f"Data length: {len(data_str)}")
        print(f"Snippet: {data_str[:300]}")
        print("-" * 50)

    ctx.close()
