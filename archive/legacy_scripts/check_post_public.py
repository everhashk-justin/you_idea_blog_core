"""
check_post_public.py - 실제 글 URL 접속하여 공개 여부 확인
"""
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
profile_dir = BASE_DIR / "browser_profile"
SCREENSHOT_DIR = BASE_DIR / "screenshots"

with sync_playwright() as p:
    # 로그인 없는 일반 브라우저로 접속 (공개 여부 확인)
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    print("공개 URL로 접속 시도 (비로그인 상태)...")
    page.goto("https://softwin.tistory.com/60", wait_until="networkidle", timeout=20000)
    time.sleep(2)

    current_url = page.url
    page_title = page.title()
    print(f"접속 URL: {current_url}")
    print(f"페이지 제목: {page_title}")

    page.screenshot(path=str(SCREENSHOT_DIR / "public_check.png"))

    # 비밀번호 입력창이 있으면 보호 게시물
    if page.locator("input[type='password']").is_visible(timeout=2000):
        print("⚠️  비밀번호 입력창 감지 → 보호 게시물입니다!")
    elif "로그인" in page_title or "login" in current_url.lower():
        print("⚠️  로그인 페이지로 리다이렉트 → 비공개 게시물입니다!")
    else:
        print("✅ 정상 접속 → 공개 게시물입니다!")

    browser.close()

    # 로그인 상태 브라우저로도 확인 (발행 레이어 공개 상태 확인)
    print("\n로그인 상태에서 수정 에디터 공개 상태 확인...")
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=str(profile_dir),
        headless=False,
        viewport={"width": 1280, "height": 900},
    )
    page2 = ctx.pages[0] if ctx.pages else ctx.new_page()
    page2.on("dialog", lambda d: d.accept())

    # 수정 에디터 진입
    page2.goto("https://softwin.tistory.com/manage/newpost/60", wait_until="networkidle", timeout=20000)
    time.sleep(3)

    # 완료 버튼 클릭
    complete_btn = page2.locator("#publish-layer-btn, button:has-text('완료')").first
    if complete_btn.is_visible(timeout=5000):
        complete_btn.click()
        time.sleep(2)

    page2.screenshot(path=str(SCREENSHOT_DIR / "publish_layer_state.png"))
    
    # 현재 선택된 공개 상태 확인
    try:
        # 선택된 라디오 버튼 찾기
        checked_input = page2.locator("input[type='radio']:checked").first
        if checked_input.is_visible(timeout=2000):
            val = checked_input.get_attribute("value") or ""
            id_attr = checked_input.get_attribute("id") or ""
            print(f"현재 선택된 공개 설정: value={val}, id={id_attr}")
            
            # value 20 = 공개, 0 = 비공개, 15 = 보호
            if val == "20" or "20" in id_attr:
                print("✅ 공개 상태!")
            elif val == "15" or "15" in id_attr:
                print("⚠️  보호(비밀번호) 상태! → 공개로 변경 필요")
                # 공개로 변경
                pub_lbl = page2.locator("label[for='open20'], label:has-text('공개')").first
                if pub_lbl.is_visible(timeout=2000):
                    pub_lbl.click()
                    time.sleep(0.5)
                    pub_btn = page2.locator("button:has-text('공개발행'), button:has-text('발행')").first
                    if pub_btn.is_visible(timeout=2000):
                        pub_btn.click()
                        time.sleep(4)
                        print("✅ 공개로 변경 완료!")
            else:
                print(f"기타 상태: {val}")
    except Exception as e:
        print(f"상태 확인 오류: {e}")

    page2.screenshot(path=str(SCREENSHOT_DIR / "after_state_check.png"))
    ctx.close()
    print("\n=== 완료 ===")
