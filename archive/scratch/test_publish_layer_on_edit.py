"""
test_publish_layer_on_edit.py - 수정 화면에서 완료 버튼 클릭 시 발행 레이어 동작 확인
"""
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
PROFILE_DIR = BASE_DIR / "browser_profile"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

blog_name = config.get("blog_name", "softwin")

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=True,
        viewport={"width": 1280, "height": 900},
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
    )
    page = context.pages[0] if context.pages else context.new_page()

    edit_url = f"https://{blog_name}.tistory.com/manage/post/145"
    print(f"🌐 접속 중: {edit_url}")
    page.goto(edit_url, wait_until="networkidle", timeout=30000)
    time.sleep(3)

    if "login" in page.url or "auth" in page.url:
        try:
            page.locator(".btn_login, a:has-text('카카오계정으로 로그인')").first.click()
            time.sleep(2)
            page.locator(".wrap_profile, .item_account").first.click()
            time.sleep(4)
        except Exception:
            pass
        page.goto(edit_url, wait_until="networkidle", timeout=20000)
        time.sleep(3)

    # 완료 버튼 클릭
    complete_btn = page.locator("#publish-layer-btn, button:has-text('완료')").first
    print("완료 버튼 클릭 중...")
    complete_btn.click()
    time.sleep(3)

    # 발행 레이어 내 버튼들 탐색
    buttons = page.locator(".layer_post button, #publish-layer button, .wrap_publish button").all()
    print("발행 레이어 내 버튼 목록:")
    for b in buttons:
        try:
            print(f"  * 버튼: '{b.inner_text().strip()}' (id: {b.get_attribute('id')}, class: {b.get_attribute('class')})")
        except Exception:
            pass

    # 라디오 / 레이블 탐색
    labels = page.locator(".layer_post label, #publish-layer label").all()
    print("발행 레이어 내 레이블 목록:")
    for l in labels:
        try:
            print(f"  * 레이블: '{l.inner_text().strip()}' (for: {l.get_attribute('for')})")
        except Exception:
            pass

    page.screenshot(path=str(BASE_DIR / "screenshots" / "edit_post_145_layer.png"))
    print(f"📸 캡처 완료: {BASE_DIR / 'screenshots' / 'edit_post_145_layer.png'}")

    context.close()
