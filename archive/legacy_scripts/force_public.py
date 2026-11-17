"""
force_public.py - 발행 글 직접 수정하여 공개로 변경
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

    # 글 관리 페이지
    page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle", timeout=20000)
    time.sleep(2)

    # 로그인 처리
    if "login" in page.url or "auth" in page.url:
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
            print(f"로그인: {e}")

    page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle", timeout=20000)
    time.sleep(2)

    # 첫 번째 글의 '수정' 버튼 클릭
    print("첫 번째 글 수정 버튼 클릭...")
    try:
        # 첫 번째 글 hover
        first_row = page.locator("table tbody tr:first-child, .list_manage li:first-child, article:first-child").first
        first_row.hover()
        time.sleep(0.5)

        edit_btn = page.locator("a:has-text('수정'), button:has-text('수정')").first
        if edit_btn.is_visible(timeout=3000):
            edit_btn.click()
            page.wait_for_load_state("networkidle", timeout=20000)
            time.sleep(2)
            print(f"수정 페이지: {page.url}")
        else:
            # 직접 '수정' 링크 찾기
            print("수정 버튼 찾는 중...")
            all_links = page.locator("a").all()
            for link in all_links[:20]:
                try:
                    txt = link.inner_text()
                    if "수정" in txt:
                        print(f"수정 링크 발견: {txt}")
                        link.click()
                        page.wait_for_load_state("networkidle", timeout=15000)
                        time.sleep(2)
                        break
                except:
                    pass
    except Exception as e:
        print(f"수정 버튼: {e}")

    page.screenshot(path=str(SCREENSHOT_DIR / "edit_page.png"))
    print(f"현재 URL: {page.url}")

    # 에디터에서 완료 버튼 클릭 → 발행 레이어에서 공개 선택
    if "newpost" in page.url or "edit" in page.url or "/manage/" in page.url:
        print("에디터에서 완료 버튼 클릭...")
        try:
            complete_btn = page.locator("#publish-layer-btn, button:has-text('완료')").first
            if complete_btn.is_visible(timeout=3000):
                complete_btn.click()
                time.sleep(2)

            # 공개 라디오 선택
            pub_opt = page.locator("label:has-text('공개'), label[for='open20'], #open20, input[value='20']").first
            if pub_opt.is_visible(timeout=3000):
                pub_opt.click()
                print("공개 라디오 선택!")
                time.sleep(0.5)

            # 발행 버튼
            publish_btn = page.locator("#publish-btn, button:has-text('공개발행'), button:has-text('발행')").first
            if publish_btn.is_visible(timeout=3000):
                publish_btn.click()
                print("발행 버튼 클릭!")
                time.sleep(5)

            page.screenshot(path=str(SCREENSHOT_DIR / "after_edit_publish.png"))
            print(f"발행 후 URL: {page.url}")
        except Exception as e:
            print(f"공개 발행 처리: {e}")

    ctx.close()
    print("완료!")
