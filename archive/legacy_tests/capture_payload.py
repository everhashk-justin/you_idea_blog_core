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

    # 모든 POST 요청 캡처
    saved_requests = []
    def handle_request(req):
        if req.method == "POST":
            saved_requests.append({
                "url": req.url,
                "headers": req.headers,
                "post_data": req.post_data
            })
    page.on("request", handle_request)

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

    # 제목 입력
    page.locator("#post-title-inp").first.fill("네트워크 페이로드 정밀 추적")
    time.sleep(1)

    # 본문 에디터 iframe 클릭 및 키보드 타이핑
    iframe_element = page.wait_for_selector("#editor-tistory_ifr", timeout=5000)
    iframe = iframe_element.content_frame()
    if iframe:
        body = iframe.locator("body#tinymce").first
        body.click()
        time.sleep(0.5)
        # 키보드로 직접 문자열 타이핑 (가장 순수한 사용자 액션)
        page.keyboard.type("Hello world this is the actual content body!")
        time.sleep(1)

    # 발행 직전 리퀘스트 리셋
    saved_requests.clear()

    # 완료 버튼
    page.locator("#publish-layer-btn, button:has-text('완료')").first.click()
    time.sleep(2)

    # 비공개 선택
    try:
        page.locator("#open0, label[for='open0']").first.click()
    except:
        pass
    time.sleep(1)

    # 발행 버튼 클릭
    page.locator("#publish-btn, button:has-text('비공개발행')").first.click()
    time.sleep(5)

    print("=== CAPTURED REQUESTS ===")
    for r in saved_requests:
        if "tistory.com" in r["url"]:
            print(f"URL: {r['url']}")
            print(f"Post Data: {r['post_data']}")
            print("-" * 50)

    ctx.close()
