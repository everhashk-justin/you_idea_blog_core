"""
login_and_fix_public.py - 카카오 로그인 완전 처리 후 post/60 공개 전환
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

    # 1. 티스토리 홈으로 이동하여 로그인 상태 체크
    print("티스토리 홈 이동...")
    page.goto("https://softwin.tistory.com", wait_until="networkidle", timeout=20000)
    time.sleep(2)
    page.screenshot(path=str(SCREENSHOT_DIR / "home_state.png"))
    print(f"홈 URL: {page.url}")

    # 2. 로그인 필요 시 수동 로그인 대기 또는 자동화
    if "login" in page.url or "auth" in page.url:
        print("로그인 페이지 감지...")
        page.goto("https://www.tistory.com/auth/login", wait_until="networkidle", timeout=20000)
        time.sleep(2)

        # 카카오로 로그인 버튼
        try:
            kakao_btn = page.locator("a.btn_login.btn_kakao, a:has-text('카카오계정으로 로그인')").first
            if kakao_btn.is_visible(timeout=5000):
                kakao_btn.click()
                time.sleep(3)
                page.screenshot(path=str(SCREENSHOT_DIR / "kakao_login.png"))
                print("카카오 로그인 버튼 클릭됨")

                # 저장된 계정 선택 (이전에 로그인한 계정)
                profile_item = page.locator(".item_profile, .wrap_profile, [class*='profile']").first
                if profile_item.is_visible(timeout=5000):
                    profile_item.click()
                    page.wait_for_load_state("networkidle", timeout=20000)
                    time.sleep(3)
                    print(f"계정 선택 후 URL: {page.url}")
                else:
                    print("계정 선택 화면 없음 — 이미 로그인됨 또는 수동 로그인 필요")
        except Exception as e:
            print(f"카카오 로그인 처리: {e}")
    
    # 3. 관리 페이지 접근 확인
    page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle", timeout=20000)
    time.sleep(3)
    page.screenshot(path=str(SCREENSHOT_DIR / "manage_posts2.png"))
    print(f"관리 URL: {page.url}")
    
    if "login" in page.url or "auth" in page.url:
        print("❌ 여전히 로그인 필요 — 수동 로그인을 위해 30초 대기...")
        time.sleep(30)  # 수동 로그인 대기
        page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle", timeout=20000)
        time.sleep(3)
        print(f"대기 후 URL: {page.url}")

    # 4. 수정 에디터 진입
    print(f"\n에디터 진입: newpost/{POST_ID}")
    page.goto(f"https://softwin.tistory.com/manage/newpost/{POST_ID}", wait_until="networkidle", timeout=25000)
    time.sleep(5)
    page.screenshot(path=str(SCREENSHOT_DIR / "editor_final.png"))
    print(f"에디터 URL: {page.url}")

    if "login" in page.url:
        print("❌ 에디터도 로그인 페이지 — 종료")
        ctx.close()
        sys.exit(1)

    # 5. 완료 버튼 클릭
    print("완료 버튼 클릭...")
    complete_btn = page.locator("button:has-text('완료'), #publish-layer-btn").first
    if complete_btn.is_visible(timeout=10000):
        complete_btn.click()
        time.sleep(3)
        print("완료 버튼 클릭 성공")
        page.screenshot(path=str(SCREENSHOT_DIR / "layer_final.png"))
    else:
        print("완료 버튼 없음 — 에디터 진입 실패")
        ctx.close()
        sys.exit(1)

    # 6. 라디오 상태 확인
    print("현재 공개 설정:")
    for rid in ["open20", "open15", "open0"]:
        try:
            r = page.locator(f"#{rid}").first
            if r.count() > 0:
                print(f"  #{rid}: checked={r.is_checked()}")
        except:
            pass

    # 7. label[for='open20'] 클릭
    print("공개 선택 (label 클릭)...")
    try:
        lbl = page.locator("label[for='open20']").first
        lbl.click()
        time.sleep(0.5)
        print(f"  label 클릭 후 open20 checked: {page.locator('#open20').is_checked()}")
    except Exception as e:
        print(f"  label 클릭 오류: {e}")

    page.screenshot(path=str(SCREENSHOT_DIR / "radio_open20.png"))

    # 8. 발행 버튼 클릭
    print("발행 버튼 클릭...")
    pub_btn = page.locator("button:has-text('발행'), #publish-btn").first
    if pub_btn.is_visible(timeout=3000):
        txt = pub_btn.inner_text().strip()
        print(f"  버튼 텍스트: '{txt}'")
        before_url = page.url
        pub_btn.click()
        for _ in range(15):
            time.sleep(1)
            if page.url != before_url:
                print(f"  URL 변경: {page.url}")
                break
        print(f"  최종 URL: {page.url}")
    else:
        print("  발행 버튼 없음")

    page.screenshot(path=str(SCREENSHOT_DIR / "published_final.png"))
    ctx.close()

    # 9. 비로그인 접근 최종 확인
    print("\n비로그인 최종 확인...")
    browser2 = p.chromium.launch(headless=True)
    p2 = browser2.new_page()
    p2.goto(f"https://softwin.tistory.com/{POST_ID}", wait_until="networkidle", timeout=20000)
    time.sleep(2)
    title2 = p2.title()
    has_pwd = p2.locator("input[type='password']").count() > 0
    p2.screenshot(path=str(SCREENSHOT_DIR / "access_final2.png"))
    browser2.close()

    print(f"  제목: {title2}")
    if has_pwd:
        print("  ❌ 보호(비밀번호) 게시물")
    elif "권한" in title2 or "TISTORY" == title2.strip():
        print("  ❌ 비공개/권한없음")
    else:
        print("  ✅ 공개 성공!")

print("\n=== 완료 ===")
