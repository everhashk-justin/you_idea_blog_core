"""
fix_to_public_definitive.py - 비공개/보호 게시물을 완전히 공개로 전환
발행 레이어: open20(공개) 클릭 → '공개 발행' 버튼 클릭 → 페이지 이동 대기
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
    page.on("dialog", lambda d: d.accept())

    # 에디터 진입
    print(f"에디터 진입: /manage/newpost/{POST_ID}")
    page.goto(f"https://softwin.tistory.com/manage/newpost/{POST_ID}", wait_until="networkidle", timeout=25000)
    time.sleep(4)
    print(f"현재 URL: {page.url}")

    # 완료 버튼 클릭 (발행 레이어 열기)
    print("완료 버튼 클릭...")
    complete_btn = page.locator("#publish-layer-btn, button:has-text('완료')").first
    complete_btn.wait_for(state="visible", timeout=10000)
    complete_btn.click()
    time.sleep(2)
    page.screenshot(path=str(SCREENSHOT_DIR / "layer_open.png"))

    # 현재 라디오 상태 확인
    print("현재 공개 설정 확인:")
    for rid, label in [("open20", "공개"), ("open15", "보호"), ("open0", "비공개")]:
        try:
            radio = page.locator(f"#{rid}").first
            if radio.is_visible(timeout=1000):
                checked = radio.is_checked()
                print(f"  {rid}({label}): checked={checked}")
        except:
            pass

    # open20(공개) 라디오 클릭 - JS 직접 실행으로 확실하게
    print("open20(공개) 선택...")
    page.evaluate("""() => {
        const r = document.getElementById('open20');
        if (r) {
            r.checked = true;
            r.click();
            r.dispatchEvent(new Event('change', {bubbles: true}));
            r.dispatchEvent(new Event('click', {bubbles: true}));
        }
    }""")
    time.sleep(0.5)

    # 라디오 버튼 직접 클릭도 시도
    try:
        r = page.locator("#open20").first
        r.click(force=True)
        print("  직접 클릭 성공")
    except Exception as e:
        print(f"  직접 클릭: {e}")

    time.sleep(0.5)

    # 선택 확인
    try:
        checked = page.locator("#open20").is_checked()
        print(f"  open20 선택 상태: {checked}")
    except:
        pass

    page.screenshot(path=str(SCREENSHOT_DIR / "layer_public_selected.png"))

    # 발행 버튼 클릭 (URL 변경 대기)
    print("'공개 발행' 버튼 클릭...")
    publish_btn = page.locator("button:has-text('공개 발행'), button:has-text('공개발행'), #publish-btn").first
    if publish_btn.is_visible(timeout=3000):
        btn_txt = publish_btn.inner_text()
        print(f"  버튼 텍스트: '{btn_txt}'")
        with page.expect_navigation(timeout=15000, wait_until="networkidle"):
            publish_btn.click()
        print(f"  발행 후 URL: {page.url}")
    else:
        # 강제로 폼 submit
        print("  직접 버튼 텍스트로 재시도...")
        all_btns = page.locator("button").all()
        for btn in all_btns:
            try:
                txt = btn.inner_text().strip()
                print(f"    버튼: '{txt}'")
                if "발행" in txt or "저장" in txt:
                    btn.click()
                    time.sleep(5)
                    break
            except:
                pass

    page.screenshot(path=str(SCREENSHOT_DIR / "after_publish.png"))
    print(f"최종 URL: {page.url}")

    # 비로그인 확인
    print("\n비로그인 접근 테스트...")
    browser2 = p.chromium.launch(headless=True)
    p2 = browser2.new_page()
    p2.goto(f"https://softwin.tistory.com/{POST_ID}", wait_until="networkidle", timeout=20000)
    time.sleep(2)
    title2 = p2.title()
    has_pwd = p2.locator("input[type='password']").count() > 0
    p2.screenshot(path=str(SCREENSHOT_DIR / "public_final_check.png"))
    browser2.close()

    print(f"  페이지 제목: {title2}")
    print(f"  비밀번호 입력창: {has_pwd}")
    if has_pwd:
        print("  ❌ 여전히 보호 게시물")
    elif "login" in p2.url.lower():
        print("  ❌ 비공개 게시물")
    else:
        print("  ✅ 공개 접근 성공!")

    ctx.close()
    print("\n=== 완료 ===")
