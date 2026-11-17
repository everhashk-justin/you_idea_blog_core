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

    # 다이얼로그 수락
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

    # 1. 마크다운 모드로 전환
    print("1. 마크다운 모드 전환 중...")
    page.locator("#editor-mode-layer-btn-open, #editor-mode-layer-btn button").first.click()
    time.sleep(1)
    page.locator("#editor-mode-markdown, div:has-text('마크다운')").last.click()
    time.sleep(2)

    # 2. 제목 입력
    title = "[검증 테스트] 마크다운 모드 실제 저장 테스트"
    print(f"2. 제목 입력: {title}")
    page.locator("#post-title-inp").first.fill(title)
    time.sleep(1)

    # 3. 본문 CodeMirror 주입
    print("3. 본문 CodeMirror 주입...")
    body_markdown = """# 웹 기술의 본질: 쿠키와 세션

웹 브라우저와 서버는 본래 **무상태(Stateless)** 프로토콜인 HTTP로 통신합니다.

## 핵심 정리
1. **쿠키**: 클라이언트 로컬에 저장되는 키-값 쌍의 텍스트 조각
2. **세션**: 서버 메모리 또는 저장소에 사용자 상태를 보관하고, 클라이언트에게는 난수 형태의 Session ID만 제공

| 구분 | 쿠키(Cookie) | 세션(Session) |
| :--- | :--- | :--- |
| 저장 위치 | 웹 브라우저 (클라이언트) | 웹 서버 (Server) |
| 보안성 | 탈취 및 변조 위험 | 상대적으로 훨씬 안전 |

이 글이 완벽하게 저장되었습니다!
"""
    injected = page.evaluate("""(text) => {
        const cmEl = document.querySelector('.CodeMirror');
        if (cmEl && cmEl.CodeMirror) {
            cmEl.CodeMirror.setValue(text);
            // change 이벤트 및 refresh 트리거
            cmEl.CodeMirror.refresh();
            return true;
        }
        return false;
    }""", body_markdown)
    print("CodeMirror 주입 여부:", injected)
    time.sleep(1)

    # 태그 입력
    tag_inp = page.locator("#tagText, input.inp_tag").first
    if tag_inp.is_visible():
        tag_inp.fill("마크다운테스트")
        tag_inp.press("Enter")
        time.sleep(0.5)

    page.screenshot(path=str(BASE_DIR / "screenshots" / "markdown_pre_publish.png"))

    # 4. 완료 버튼
    print("4. 완료 버튼 클릭...")
    page.locator("#publish-layer-btn, button:has-text('완료')").first.click()
    time.sleep(2)

    # 5. 비공개 설정
    try:
        page.locator("#open0, label[for='open0'], label:has-text('비공개')").first.click(timeout=2000)
    except Exception:
        pass
    time.sleep(1)

    # 6. 최종 발행
    print("6. 최종 발행 클릭...")
    page.locator("#publish-btn, button:has-text('비공개발행'), button:has-text('발행')").first.click()
    time.sleep(5)
    print("발행 후 URL:", page.url)

    # 7. 글 관리 페이지에서 최신 글 확인 및 검증
    page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle")
    time.sleep(3)
    page.screenshot(path=str(BASE_DIR / "screenshots" / "markdown_publish_done.png"))

    # 최신 글 entryId 파악
    entry_id = page.evaluate("""() => {
        const a = document.querySelector('.tit_post a, .post_cont a');
        if (a && a.href) {
            const m = a.href.match(/\\/(\\d+)$/);
            return m ? m[1] : null;
        }
        return null;
    }""")
    print("새로 생성된 글 Entry ID:", entry_id)

    if entry_id:
        # 수정 화면으로 들어가서 내용이 진짜 들어있는지 확인!
        edit_url = f"https://softwin.tistory.com/manage/newpost/{entry_id}"
        print(f"수정 화면 접속: {edit_url}")
        page.goto(edit_url, wait_until="networkidle")
        time.sleep(4)
        page.screenshot(path=str(BASE_DIR / "screenshots" / "verify_saved_markdown_content.png"))

        saved_info = page.evaluate("""() => {
            let cmVal = "";
            const cmEl = document.querySelector('.CodeMirror');
            if (cmEl && cmEl.CodeMirror) {
                cmVal = cmEl.CodeMirror.getValue();
            }
            let tmVal = "";
            if (window.tinymce && window.tinymce.activeEditor) {
                tmVal = window.tinymce.activeEditor.getContent();
            }
            return {
                cmLength: cmVal.length,
                cmSnippet: cmVal.substring(0, 150),
                tmLength: tmVal.length,
                tmSnippet: tmVal.substring(0, 150)
            };
        }""")
        print("🎉 검증 결과 (저장된 본문 데이터):")
        print(saved_info)

    ctx.close()
