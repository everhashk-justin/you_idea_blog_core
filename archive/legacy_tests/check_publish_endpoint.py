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

    requests_all = []
    def on_request(req):
        if "tistory.com" in req.url:
            requests_all.append({
                "url": req.url,
                "method": req.method,
                "post_data": req.post_data
            })
    page.on("request", on_request)

    responses_all = []
    def on_response(res):
        if "tistory.com" in res.url and res.request.method == "POST":
            try:
                responses_all.append({
                    "url": res.url,
                    "status": res.status,
                    "text": res.text()[:200]
                })
            except:
                pass
    page.on("response", on_response)

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

    # 제목
    page.locator("#post-title-inp").first.fill("포스팅 저장 엔드포인트 분석")
    time.sleep(1)

    # 본문 입력
    iframe_element = page.wait_for_selector("#editor-tistory_ifr", timeout=5000)
    iframe = iframe_element.content_frame()
    if iframe:
        body = iframe.locator("body#tinymce").first
        body.click()
        time.sleep(0.5)
        page.keyboard.type("본문 테스트 1234567890")
        time.sleep(1)

    # 완료 클릭 전 로그 초기화
    requests_all.clear()
    responses_all.clear()

    # 완료 버튼 클릭
    page.locator("#publish-layer-btn, button:has-text('완료')").first.click()
    time.sleep(2)

    # 비공개 선택
    try:
        page.locator("#open0, label[for='open0']").first.click()
    except:
        pass
    time.sleep(1)

    # 발행 클릭
    page.locator("#publish-btn, button:has-text('비공개발행')").first.click()
    time.sleep(5)

    page.screenshot(path=str(BASE_DIR / "screenshots" / "publish_response_screen.png"))

    print("=== REQUESTS AFTER PUBLISH CLICK ===")
    for r in requests_all:
        if r["method"] == "POST":
            print(f"POST {r['url']}")
            print(f"Data: {r['post_data']}")
            print("-" * 40)

    print("=== RESPONSES AFTER PUBLISH CLICK ===")
    for res in responses_all:
        print(f"RESP {res['status']} {res['url']}: {res['text']}")

    ctx.close()
