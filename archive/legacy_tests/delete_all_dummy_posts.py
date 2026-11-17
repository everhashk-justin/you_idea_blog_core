import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=str(BASE_DIR / "browser_profile"),
        headless=True
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    # 삭제 확인 팝업 자동 수락
    page.on("dialog", lambda d: d.accept())

    page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle")
    if "login" in page.url or "auth" in page.url:
        page.locator(".btn_login").first.click()
        time.sleep(2)
        page.locator(".wrap_profile").first.click()
        time.sleep(3)
        page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle")
    time.sleep(2)

    while True:
        # 현재 화면의 글 행 목록 가져오기
        rows = page.locator("li:has(.tit_post)").all()
        print(f"현재 글 개수: {len(rows)}")

        target_found = False
        for idx, row in enumerate(rows):
            if idx == 0:
                # 최신 0번 글은 정식 글이므로 절대 삭제하지 않음
                continue

            title_el = row.locator(".tit_post a").first
            title = title_el.inner_text().strip()

            # 삭제 조건: 제목에 테스트, 분석, 추적이 있거나, 0번 글과 중복된 쿠키와 세션 글인 경우
            if any(k in title for k in ["테스트", "분석", "추적", "쿠키와 세션"]):
                print(f"[{idx}] 삭제 대상 발견: '{title}' 삭제 시도...")
                row.hover()
                time.sleep(0.5)

                # a.btn_post의 2번째 항목(삭제 버튼) 클릭
                del_btn = row.locator("a.btn_post").nth(1)
                del_btn.click()
                print("삭제 버튼 클릭 완료, 대기 중...")
                time.sleep(2)
                target_found = True
                break # DOM이 변경되었으므로 루프 탈출 후 다시 검사

        if not target_found:
            print("더 이상 삭제할 대상 글이 없습니다.")
            break

        # 페이지 새로고침 후 다음 삭제 진행
        page.reload(wait_until="networkidle")
        time.sleep(1.5)

    # 정리 후 스크린샷 캡처
    page.screenshot(path=str(BASE_DIR / "screenshots" / "cleanup_complete_list.png"))

    remaining = page.evaluate("""() => {
        const res = [];
        document.querySelectorAll('li:has(.tit_post) .tit_post a').forEach(a => {
            res.push(a.innerText.trim());
        });
        return res;
    }""")
    print("\n=== 최종 정리 완료 후 남은 글 목록 ===")
    for idx, t in enumerate(remaining[:6]):
        print(f"{idx+1}. {t}")

    ctx.close()
