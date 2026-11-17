"""
fix_post60_public.py - dialog 없이 post/60을 공개로 변경
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
POST_ID = "60"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=str(profile_dir),
        headless=False,
        viewport={"width": 1280, "height": 900},
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    # dialog 핸들러 제거 - 티스토리 자체 다이얼로그 처리에 맡김

    # 1. 로그인 확인
    page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle", timeout=20000)
    time.sleep(2)
    if "login" in page.url or "auth" in page.url:
        print("로그인 필요...")
        prof = page.locator(".wrap_profile, .item_account").first
        if prof.is_visible(timeout=5000):
            prof.click()
            page.wait_for_load_state("networkidle", timeout=20000)
        time.sleep(2)
        page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle", timeout=20000)
        time.sleep(2)
    print(f"로그인 상태 URL: {page.url}")

    # 2. 수정 에디터 진입
    page.goto(f"https://softwin.tistory.com/manage/newpost/{POST_ID}", wait_until="networkidle", timeout=20000)
    time.sleep(4)
    page.screenshot(path=str(SCREENSHOT_DIR / "editor_no_dialog.png"))
    print(f"에디터 URL: {page.url}")

    # 3. 완료 버튼 클릭
    complete_btn = page.locator("button:has-text('완료'), #publish-layer-btn").first
    if not complete_btn.is_visible(timeout=8000):
        print("에디터 로딩 실패")
        ctx.close()
        sys.exit(1)
    complete_btn.click()
    time.sleep(3)
    page.screenshot(path=str(SCREENSHOT_DIR / "layer_nodialog.png"))

    # 4. 공개 라디오 선택 확인
    try:
        r20 = page.locator("#open20").first
        r0  = page.locator("#open0").first
        r15 = page.locator("#open15").first
        print(f"  open20(공개): {r20.is_checked()}")
        print(f"  open15(보호): {r15.is_checked()}")
        print(f"  open0(비공개): {r0.is_checked()}")
    except Exception as e:
        print(f"  라디오 확인 오류: {e}")

    # open20 클릭 (label 클릭이 더 신뢰성 높음)
    try:
        lbl20 = page.locator("label[for='open20']").first
        lbl20.click()
        time.sleep(0.5)
        print(f"  label[for=open20] 클릭 후 open20 checked: {page.locator('#open20').is_checked()}")
    except Exception as e:
        print(f"  label 클릭 오류: {e}")

    page.screenshot(path=str(SCREENSHOT_DIR / "before_publish_nodialog.png"))

    # 5. 발행 버튼 클릭 - dialog 없이 기다림
    print("발행 버튼 클릭 (dialog 없음)...")
    publish_btn = page.locator("button:has-text('발행'), #publish-btn").first
    if publish_btn.is_visible(timeout=3000):
        btn_txt = publish_btn.inner_text().strip()
        print(f"  버튼 텍스트: '{btn_txt}'")
        publish_btn.click()
        # URL 변경 또는 10초 대기
        for i in range(10):
            time.sleep(1)
            current_url = page.url
            if f"newpost/{POST_ID}" not in current_url:
                print(f"  URL 변경 감지: {current_url}")
                break
        else:
            print(f"  URL 변경 없음: {page.url}")
    else:
        print("  발행 버튼 없음")

    page.screenshot(path=str(SCREENSHOT_DIR / "after_publish_nodialog.png"))
    print(f"  최종 URL: {page.url}")
    ctx.close()

    # 6. 비로그인 접근 확인
    print("\n비로그인 접근 테스트...")
    browser2 = p.chromium.launch(headless=True)
    p2 = browser2.new_page()
    p2.goto(f"https://softwin.tistory.com/{POST_ID}", wait_until="networkidle", timeout=20000)
    time.sleep(2)
    title2 = p2.title()
    has_pwd = p2.locator("input[type='password']").count() > 0
    p2.screenshot(path=str(SCREENSHOT_DIR / "final_public_nodialog.png"))
    browser2.close()

    print(f"  제목: {title2}")
    print(f"  비밀번호창: {has_pwd}")
    if has_pwd:
        print("  ❌ 여전히 보호 — 티스토리 에디터에서 직접 수동 변경 필요")
    elif "권한" in title2:
        print("  ❌ 비공개")
    else:
        print("  ✅ 공개 접근 성공!")

print("\n=== 완료 ===")
