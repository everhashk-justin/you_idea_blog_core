"""
fix_public_v2.py - 첫 번째 글 제목 클릭 → 수정 에디터에서 공개로 변경
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

POST_TITLE_KEYWORD = "컴퓨터는 어떻게 작동하는가"

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

    # 제목 링크 찾아서 href 수집 → post ID 파악
    print("첫 번째 글 링크 탐색...")
    try:
        # 제목으로 링크 찾기
        title_link = page.locator(f"a:has-text('{POST_TITLE_KEYWORD[:10]}')").first
        href = title_link.get_attribute("href")
        print(f"  제목 링크 href: {href}")
        
        # post ID 추출 (예: /manage/posts/123 또는 /42 같은 형태)
        # 수정 페이지는 /manage/newpost?id=XXX 또는 /manage/posts/XXX/edit
        if href:
            # 글 번호 추출 시도
            import re
            nums = re.findall(r'\d+', href)
            if nums:
                post_id = nums[-1]
                edit_url = f"https://softwin.tistory.com/manage/newpost/{post_id}"
                print(f"  수정 페이지 이동: {edit_url}")
                page.goto(edit_url, wait_until="networkidle", timeout=20000)
                time.sleep(3)
            else:
                # 제목 링크 클릭
                title_link.click()
                page.wait_for_load_state("networkidle", timeout=15000)
                time.sleep(2)
        
        page.screenshot(path=str(SCREENSHOT_DIR / "edit_attempt.png"))
        print(f"  현재 URL: {page.url}")

    except Exception as e:
        print(f"제목 링크 탐색 실패: {e}")
        # 대안: 수정 버튼을 마우스 hover 후 클릭
        try:
            print("대안: 마우스로 직접 hover 후 수정 버튼 클릭...")
            title_elem = page.locator(f"text={POST_TITLE_KEYWORD[:10]}").first
            title_elem.hover()
            time.sleep(1)
            page.screenshot(path=str(SCREENSHOT_DIR / "hover_state.png"))
            edit_btn = page.locator("a:has-text('수정')").first
            if edit_btn.is_visible(timeout=3000):
                edit_btn.click()
                page.wait_for_load_state("networkidle", timeout=15000)
                time.sleep(3)
                print(f"  수정 페이지: {page.url}")
        except Exception as e2:
            print(f"대안도 실패: {e2}")

    # 에디터에서 공개 발행 처리
    if "newpost" in page.url or "manage" in page.url:
        print("\n에디터에서 완료 버튼 클릭 중...")
        try:
            # 완료 버튼
            complete_btn = page.locator("#publish-layer-btn, button:has-text('완료')").first
            if complete_btn.is_visible(timeout=5000):
                complete_btn.click()
                time.sleep(2)
                print("  완료 버튼 클릭!")
                page.screenshot(path=str(SCREENSHOT_DIR / "publish_layer.png"))

                # 공개 라디오 버튼
                pub_opt = page.locator("label:has-text('공개'), label[for='open20'], input[value='20']").first
                if pub_opt.is_visible(timeout=3000):
                    pub_opt.click()
                    print("  공개 선택!")
                    time.sleep(0.5)
                else:
                    # 다른 방식으로 공개 선택
                    all_labels = page.locator("label").all()
                    for lbl in all_labels:
                        try:
                            if lbl.inner_text().strip() == "공개":
                                lbl.click()
                                print("  label 텍스트로 공개 선택!")
                                time.sleep(0.5)
                                break
                        except:
                            pass

                # 발행 버튼
                publish_btn = page.locator("#publish-btn, button:has-text('공개발행'), button:has-text('발행')").first
                if publish_btn.is_visible(timeout=3000):
                    publish_btn.click()
                    print("  발행 버튼 클릭!")
                    time.sleep(5)
                    
                page.screenshot(path=str(SCREENSHOT_DIR / "final_public.png"))
                print(f"  최종 URL: {page.url}")
            else:
                print("  완료 버튼이 없습니다 (에디터가 아닌 페이지?)")
                page.screenshot(path=str(SCREENSHOT_DIR / "no_complete_btn.png"))
        except Exception as e:
            print(f"공개 발행: {e}")

    ctx.close()
    print("\n=== 완료 ===")
