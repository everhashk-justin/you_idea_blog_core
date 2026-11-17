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
    time.sleep(2)

    try:
        page.locator("button:has-text('취소')").first.click(timeout=1000)
    except Exception:
        pass

    # 제목 입력
    title_inp = page.locator("#post-title-inp, textarea.textarea_tit").first
    title_inp.fill("키보드 입력 테스트 포스트")
    time.sleep(1)

    # 본문 iframe 찾기
    iframe_element = page.wait_for_selector("#editor-tistory_ifr, iframe[id*='tinymce']", timeout=10000)
    iframe = iframe_element.content_frame()
    
    print("iframe 찾음:", iframe is not None)
    if iframe:
        # 본문 영역 클릭하여 포커스
        body = iframe.locator("body#tinymce").first
        body.click()
        time.sleep(0.5)

        # 텍스트 직접 입력
        test_text = "이것은 키보드 이벤트를 통한 본문 입력 테스트입니다.\n두 번째 줄도 잘 들어가는지 확인합니다.\n세션과 쿠키의 핵심 원리를 완벽하게 전달합니다."
        for line in test_text.split("\n"):
            page.keyboard.insert_text(line)
            page.keyboard.press("Enter")
            time.sleep(0.2)
        
        print("키보드 본문 입력 완료!")
        time.sleep(1)

    # 스크린샷
    page.screenshot(path=str(BASE_DIR / "screenshots" / "test_keyboard_screen.png"))

    # 완료 버튼
    page.locator("#publish-layer-btn, button:has-text('완료')").first.click()
    time.sleep(2)

    # 비공개 선택
    try:
        page.locator("#open0, label[for='open0'], label:has-text('비공개')").first.click(timeout=2000)
    except Exception:
        pass
    time.sleep(1)

    # 발행
    page.locator("#publish-btn, button:has-text('비공개발행'), button:has-text('발행')").first.click()
    time.sleep(5)

    print("발행 완료 URL:", page.url)

    # 다시 방금 발행한 글 확인
    page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle")
    time.sleep(2)
    page.screenshot(path=str(BASE_DIR / "screenshots" / "test_keyboard_result.png"))

    # 첫번째 글 수정 링크 확인
    first_item = page.locator("li.item_post, ul.list_board li, .post_cont").first
    edit_url = page.evaluate("""() => {
        const a = document.querySelector('.tit_post a, .post_cont a');
        return a ? a.href : null;
    }""")
    print("최신 글 URL:", edit_url)

    ctx.close()
