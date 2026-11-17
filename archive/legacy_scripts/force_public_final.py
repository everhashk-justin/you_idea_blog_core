"""
force_public_final.py - 에디터 발행 레이어에서 공개 라디오 버튼을 정확히 선택
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

    print(f"수정 에디터 진입: post/{POST_ID}")
    page.goto(f"https://softwin.tistory.com/manage/newpost/{POST_ID}", wait_until="networkidle", timeout=25000)
    time.sleep(3)

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
            page.goto(f"https://softwin.tistory.com/manage/newpost/{POST_ID}", wait_until="networkidle", timeout=20000)
            time.sleep(3)
        except Exception as e:
            print(f"로그인: {e}")

    print(f"현재 URL: {page.url}")
    page.screenshot(path=str(SCREENSHOT_DIR / "editor_loaded.png"))

    # 완료 버튼 클릭
    print("완료 버튼 클릭...")
    complete_btn = page.locator("#publish-layer-btn, button:has-text('완료')").first
    if complete_btn.is_visible(timeout=8000):
        complete_btn.click()
        time.sleep(2)
        print("  완료 버튼 클릭 성공")
    else:
        print("  완료 버튼 없음")

    page.screenshot(path=str(SCREENSHOT_DIR / "publish_layer2.png"))

    # 발행 레이어의 모든 라디오 버튼 확인
    print("\n발행 레이어 라디오 버튼 전체 확인:")
    try:
        radios = page.locator("input[type='radio']").all()
        for radio in radios:
            val = radio.get_attribute("value") or ""
            id_attr = radio.get_attribute("id") or ""
            checked = radio.is_checked()
            print(f"  radio: id={id_attr}, value={val}, checked={checked}")
    except Exception as e:
        print(f"  라디오 확인 오류: {e}")

    # 레이블 전체 확인
    print("\n발행 레이어 레이블 전체 확인:")
    try:
        labels = page.locator("label").all()
        for lbl in labels[:20]:
            txt = lbl.inner_text().strip()
            for_attr = lbl.get_attribute("for") or ""
            if txt and ("공개" in txt or "비공개" in txt or "보호" in txt):
                print(f"  label: for={for_attr}, text={txt}")
    except Exception as e:
        print(f"  레이블 확인 오류: {e}")

    # 공개 라디오 클릭 시도 - 여러 방법
    print("\n공개 라디오 클릭 시도...")
    clicked = False
    
    # 방법 1: value=20인 라디오
    try:
        r = page.locator("input[type='radio'][value='20']").first
        if r.is_visible(timeout=2000):
            r.click()
            print("  ✅ 방법1 성공: input[value='20'] 클릭")
            clicked = True
    except:
        pass

    # 방법 2: id=open20
    if not clicked:
        try:
            r = page.locator("#open20").first
            if r.is_visible(timeout=2000):
                r.click()
                print("  ✅ 방법2 성공: #open20 클릭")
                clicked = True
        except:
            pass

    # 방법 3: label for=open20 클릭
    if not clicked:
        try:
            lbl = page.locator("label[for='open20']").first
            if lbl.is_visible(timeout=2000):
                lbl.click()
                print("  ✅ 방법3 성공: label[for='open20'] 클릭")
                clicked = True
        except:
            pass

    # 방법 4: 텍스트가 '공개'인 label (비공개 제외)
    if not clicked:
        try:
            labels = page.locator("label").all()
            for lbl in labels:
                txt = lbl.inner_text().strip()
                if txt == "공개":
                    lbl.click()
                    print(f"  ✅ 방법4 성공: label text='공개' 클릭")
                    clicked = True
                    break
        except:
            pass

    # 방법 5: JS로 강제 선택
    if not clicked:
        try:
            result = page.evaluate("""() => {
                const radios = document.querySelectorAll('input[type="radio"]');
                for (const r of radios) {
                    if (r.value === '20' || r.id === 'open20') {
                        r.checked = true;
                        r.dispatchEvent(new Event('change', {bubbles: true}));
                        return 'clicked: ' + r.id + '=' + r.value;
                    }
                }
                // 모든 라디오 나열
                return Array.from(radios).map(r => r.id + ':' + r.value + ':' + r.checked).join(', ');
            }""")
            print(f"  JS 실행 결과: {result}")
            clicked = True
        except Exception as e:
            print(f"  JS 오류: {e}")

    time.sleep(0.5)
    page.screenshot(path=str(SCREENSHOT_DIR / "after_radio_click.png"))

    # 발행 버튼 클릭
    print("\n발행 버튼 클릭...")
    try:
        publish_btn = page.locator("#publish-btn, button.btn_publish, button:has-text('공개발행'), button:has-text('발행')").first
        if publish_btn.is_visible(timeout=3000):
            btn_text = publish_btn.inner_text()
            print(f"  발행 버튼 텍스트: '{btn_text}'")
            publish_btn.click()
            time.sleep(5)
            print(f"  최종 URL: {page.url}")
        else:
            print("  발행 버튼 없음")
            # 모든 버튼 나열
            btns = page.locator("button").all()
            for btn in btns[:15]:
                try:
                    print(f"    버튼: '{btn.inner_text()}'")
                except:
                    pass
    except Exception as e:
        print(f"  발행 오류: {e}")

    page.screenshot(path=str(SCREENSHOT_DIR / "force_public_final.png"))
    ctx.close()
    print("\n=== 완료 ===")
