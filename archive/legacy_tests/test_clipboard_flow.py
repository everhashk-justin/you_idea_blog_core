import time
import json
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

    # post.json 요청 가로채기
    captured = {}
    def on_request(req):
        if "manage/post.json" in req.url:
            captured["data"] = req.post_data
    page.on("request", on_request)

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
    title = "클립보드 붙여넣기 본문 주입 테스트"
    page.locator("#post-title-inp").first.fill(title)
    time.sleep(1)

    # 2. 마크다운 본문 준비
    raw_md = """# 웹 기술의 본질: 쿠키와 세션의 모든 것

왜 우리는 매번 다시 로그인하지 않아도 될까요?
그 비밀은 바로 **쿠키(Cookie)**와 **세션(Session)**에 있습니다.

## 1. 쿠키 vs 세션 비교
- **쿠키**: 클라이언트(브라우저)에 저장되는 정보 조각
- **세션**: 서버의 보안 메모리에 저장되는 사용자 상태

비유하자면 쿠키는 놀이공원 자유이용권 손목띠이고, 세션은 호텔 프론트의 금고와 방 카드키입니다.

## 2. 결론
이 방식으로 작성된 글은 티스토리 에디터의 모든 서식을 완벽하게 통과합니다!
"""

    # 3. 클립보드에 복사
    # 브라우저 컨텍스트 내에서 클립보드에 텍스트 복사
    page.evaluate("""(text) => {
        const el = document.createElement('textarea');
        el.value = text;
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
    }""", raw_md)
    time.sleep(0.5)

    # 4. 에디터 본문 영역 클릭 후 붙여넣기
    iframe_element = page.wait_for_selector("#editor-tistory_ifr", timeout=5000)
    iframe = iframe_element.content_frame()
    if iframe:
        body = iframe.locator("body#tinymce").first
        body.click()
        time.sleep(0.5)
        # Control+v 입력
        page.keyboard.press("Control+v")
        time.sleep(1.5)

    page.screenshot(path=str(BASE_DIR / "screenshots" / "after_clipboard_paste.png"))

    # 5. 완료 버튼
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

    print("=== CAPTURED post.json DATA ===")
    if "data" in captured:
        d = json.loads(captured["data"])
        print(f"Title: {d.get('title')}")
        print(f"Content Length: {len(d.get('content', ''))}")
        print(f"Content Snippet: {d.get('content', '')[:200]}")
    else:
        print("post.json was not captured!")

    ctx.close()
