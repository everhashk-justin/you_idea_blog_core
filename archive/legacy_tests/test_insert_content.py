import json
import time
import markdown
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=str(BASE_DIR / "browser_profile"),
        headless=True,
        permissions=["clipboard-read", "clipboard-write"]
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    # post.json 요청 캡처
    captured_publish = []
    def on_req(req):
        if "manage/post" in req.url:
            captured_publish.append({
                "url": req.url,
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
    except Exception:
        pass

    # 1. 제목 입력
    page.locator("#post-title-inp").first.fill("붙여넣기 및 insertContent 테스트")
    time.sleep(1)

    # 2. 마크다운 변환
    raw_md = """# 웹 기술의 본질: 쿠키와 세션

웹 브라우저와 서버는 본래 **무상태(Stateless)** 프로토콜인 HTTP로 통신합니다.

## 세션의 강력함
세션은 비밀번호나 중요한 개인정보를 브라우저에 남겨두지 않고,
오직 **서버의 보안 금고**에만 저장합니다!
"""
    html_content = markdown.markdown(raw_md, extensions=['extra', 'tables', 'nl2br'])

    # 3. insertContent 테스트
    iframe_element = page.wait_for_selector("#editor-tistory_ifr", timeout=5000)
    iframe = iframe_element.content_frame()
    if iframe:
        body = iframe.locator("body#tinymce").first
        body.click()
        time.sleep(0.5)

        # insertContent 실행
        page.evaluate("""(html) => {
            const ed = window.tinymce.activeEditor;
            ed.focus();
            ed.execCommand('mceInsertContent', false, html);
            ed.fire('input');
            ed.fire('change');
            ed.fire('paste');
        }""", html_content)
        time.sleep(1)

    # 스크린샷
    page.screenshot(path=str(BASE_DIR / "screenshots" / "insert_content_test.png"))

    # 완료 버튼
    page.locator("#publish-layer-btn, button:has-text('완료')").first.click()
    time.sleep(2)

    # 비공개 선택
    try:
        page.locator("#open0, label[for='open0']").first.click()
    except:
        pass
    time.sleep(1)

    captured_publish.clear()

    # 발행 클릭
    page.locator("#publish-btn, button:has-text('비공개발행')").first.click()
    time.sleep(5)

    print("=== CAPTURED PUBLISH DATA ===")
    for c in captured_publish:
        print(f"URL: {c['url']}")
        if c['data']:
            try:
                d = json.loads(c['data'])
                print(f"Title: {d.get('title')}")
                print(f"Content Length: {len(d.get('content', ''))}")
                print(f"Content Snippet: {d.get('content', '')[:150]}")
            except Exception as e:
                print(f"Raw data: {c['data'][:200]}")

    ctx.close()
