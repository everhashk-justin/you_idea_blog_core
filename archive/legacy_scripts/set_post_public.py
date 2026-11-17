"""
set_post_public.py - 카카오 로그인 후 특정 글을 공개로 전환
"""
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from playwright.sync_api import sync_playwright, expect

BASE_DIR = Path(__file__).resolve().parent
profile_dir = BASE_DIR / "browser_profile"
SCREENSHOT_DIR = BASE_DIR / "screenshots"
POST_ID = "60"

def do_kakao_login(page):
    """카카오 로그인 처리"""
    print("카카오 로그인 처리 중...")
    try:
        # 저장된 프로필 버튼 클릭
        profile_btn = page.locator(".wrap_profile, .item_account, [data-id]").first
        if profile_btn.is_visible(timeout=3000):
            profile_btn.click()
            page.wait_for_load_state("networkidle", timeout=20000)
            time.sleep(2)
            print("  프로필 클릭으로 로그인 완료")
            return True
    except Exception as e:
        print(f"  프로필 로그인 실패: {e}")

    # 카카오 계정으로 로그인 버튼
    try:
        btn = page.locator("a:has-text('카카오계정으로 로그인'), .btn_login").first
        if btn.is_visible(timeout=3000):
            btn.click()
            page.wait_for_load_state("networkidle", timeout=15000)
            time.sleep(2)
            # 계정 선택 화면
            acct = page.locator(".wrap_profile, .item_account, .account_item").first
            if acct.is_visible(timeout=3000):
                acct.click()
                page.wait_for_load_state("networkidle", timeout=15000)
            time.sleep(2)
            return True
    except Exception as e:
        print(f"  카카오 버튼 로그인 실패: {e}")
    
    return False

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=str(profile_dir),
        headless=False,
        viewport={"width": 1280, "height": 900},
        args=["--disable-blink-features=AutomationControlled"]
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.on("dialog", lambda d: d.accept())

    # 1. 티스토리 메인 이동하여 로그인 상태 확인
    print("티스토리 이동 중...")
    page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle", timeout=25000)
    time.sleep(3)
    print(f"현재 URL: {page.url}")

    # 로그인 필요 시 처리
    if "login" in page.url or "auth" in page.url:
        do_kakao_login(page)
        time.sleep(2)
        page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle", timeout=20000)
        time.sleep(2)
        print(f"로그인 후 URL: {page.url}")

    # 2. 수정 에디터 진입
    print(f"\n수정 에디터 진입: post/{POST_ID}")
    page.goto(f"https://softwin.tistory.com/manage/newpost/{POST_ID}", wait_until="networkidle", timeout=25000)
    time.sleep(4)
    print(f"에디터 URL: {page.url}")

    if "login" in page.url or "auth" in page.url:
        print("세션 만료 → 재로그인")
        do_kakao_login(page)
        page.goto(f"https://softwin.tistory.com/manage/newpost/{POST_ID}", wait_until="networkidle", timeout=25000)
        time.sleep(4)

    page.screenshot(path=str(SCREENSHOT_DIR / "editor_state.png"))

    # 3. 완료 버튼 클릭 (발행 레이어 열기)
    print("완료 버튼 클릭...")
    complete_btn = page.locator("button:has-text('완료'), #publish-layer-btn").first
    if complete_btn.is_visible(timeout=8000):
        complete_btn.click()
        time.sleep(2)
        print("  완료 버튼 클릭 성공")
        page.screenshot(path=str(SCREENSHOT_DIR / "layer_open2.png"))
    else:
        print("  완료 버튼 없음! 현재 페이지 상태:")
        page.screenshot(path=str(SCREENSHOT_DIR / "no_complete_btn2.png"))
        ctx.close()
        sys.exit(1)

    # 4. 공개 라디오 선택
    print("공개(open20) 라디오 선택...")
    # JS로 강제 설정 후 직접 클릭도 시도
    page.evaluate("""() => {
        const r20 = document.getElementById('open20');
        if (r20) { r20.checked = true; r20.click(); }
    }""")
    time.sleep(0.3)

    try:
        r = page.locator("#open20").first
        r.click(force=True)
        time.sleep(0.3)
        print(f"  open20 checked: {r.is_checked()}")
    except Exception as e:
        print(f"  직접 클릭 실패: {e}")

    # label[for=open20] 클릭
    try:
        lbl = page.locator("label[for='open20']").first
        if lbl.is_visible(timeout=1000):
            lbl.click()
            time.sleep(0.3)
            print("  label[for=open20] 클릭")
    except:
        pass

    page.screenshot(path=str(SCREENSHOT_DIR / "radio_selected2.png"))

    # 5. 발행 버튼 클릭 (navigation 없이 단순 클릭 후 대기)
    print("발행 버튼 클릭...")
    publish_btn = page.locator("button:has-text('발행'), #publish-btn, button.btn_publish").first
    if publish_btn.is_visible(timeout=3000):
        btn_txt = publish_btn.inner_text().strip()
        print(f"  발행 버튼: '{btn_txt}'")
        publish_btn.click()
        time.sleep(8)  # 충분히 대기
        print(f"  발행 후 URL: {page.url}")
        page.screenshot(path=str(SCREENSHOT_DIR / "after_final_publish.png"))
    else:
        print("  발행 버튼 없음")
        # 버튼 전체 목록
        all_btns = page.locator("button").all()
        for b in all_btns[:20]:
            try: print(f"    {b.inner_text()}")
            except: pass

    ctx.close()

    # 6. 비로그인 접근 확인
    print("\n비로그인 접근 테스트...")
    browser_check = p.chromium.launch(headless=True)
    pc = browser_check.new_page()
    pc.goto(f"https://softwin.tistory.com/{POST_ID}", wait_until="networkidle", timeout=20000)
    time.sleep(2)
    title_check = pc.title()
    has_pwd = pc.locator("input[type='password']").count() > 0
    pc.screenshot(path=str(SCREENSHOT_DIR / "public_access_final.png"))
    browser_check.close()

    print(f"  제목: {title_check}")
    print(f"  비밀번호 입력창: {has_pwd}")
    if has_pwd:
        print("  ❌ 아직 보호 게시물 — 에디터에서 직접 공개 설정 필요")
    elif "권한" in title_check:
        print("  ❌ 비공개 게시물")
    else:
        print("  ✅ 공개 게시물!")

print("\n=== 완료 ===")
