"""
fix_visibility.py - 발행된 글의 공개 상태를 보호->공개로 전환
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
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=str(profile_dir),
        headless=False,
        viewport={"width": 1280, "height": 900},
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.on("dialog", lambda d: d.accept())

    print("글 관리 페이지 이동...")
    page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle", timeout=20000)
    time.sleep(2)

    if "login" in page.url or "auth" in page.url:
        print("로그인 필요 - 카카오 로그인 시도...")
        try:
            btn = page.locator(".btn_login, a:has-text('카카오계정으로 로그인')").first
            if btn.is_visible(timeout=3000):
                btn.click()
                page.wait_for_load_state("networkidle", timeout=15000)
            prof = page.locator(".wrap_profile, .item_account").first
            if prof.is_visible(timeout=3000):
                prof.click()
                page.wait_for_load_state("networkidle", timeout=15000)
            time.sleep(2)
        except Exception as e:
            print(f"로그인 처리: {e}")

    page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle", timeout=20000)
    time.sleep(2)

    page.screenshot(path=str(SCREENSHOT_DIR / "posts_list_before.png"))
    print(f"현재 URL: {page.url}")

    # 보호 버튼 찾아 공개로 변경
    try:
        protected_btn = page.locator("button:has-text('보호'), a:has-text('보호')").first
        if protected_btn.is_visible(timeout=3000):
            print("보호 버튼 발견 - 공개로 변경 중...")
            protected_btn.click()
            time.sleep(1)
            pub_opt = page.locator("button:has-text('공개'), a:has-text('공개'), [role='option']:has-text('공개')").first
            if pub_opt.is_visible(timeout=2000):
                pub_opt.click()
                time.sleep(2)
                print("공개 전환 완료!")
            else:
                # 드롭다운이 다른 형태일 수도 있음
                all_opts = page.locator("[role='option'], .option_item").all()
                for opt in all_opts:
                    if "공개" in opt.inner_text():
                        opt.click()
                        print("공개 옵션 클릭!")
                        time.sleep(2)
                        break
        else:
            print("보호 버튼 없음 - 상태 확인 중...")
            # 현재 글 목록 상태 출력
            first_item = page.locator("table tbody tr:first-child, .list_manage li:first-child").first
            if first_item.is_visible(timeout=2000):
                print(f"첫 번째 글: {first_item.inner_text()[:150]}")
    except Exception as e:
        print(f"공개 전환 중 오류: {e}")

    page.screenshot(path=str(SCREENSHOT_DIR / "posts_list_after.png"))
    ctx.close()
    print("완료!")
