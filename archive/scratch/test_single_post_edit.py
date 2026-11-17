"""
test_single_post_edit.py - 단건 수정 화면 진입 및 DOM 구조 확인
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
        print("Logging in...")
        try:
            page.locator(".btn_login, a:has-text('카카오계정으로 로그인')").first.click()
            time.sleep(2)
            page.locator(".wrap_profile, .item_account").first.click()
            time.sleep(4)
        except Exception:
            pass
        page.goto(edit_url, wait_until="networkidle", timeout=20000)
        time.sleep(3)

    print(f"현재 URL: {page.url}")
    print(f"현재 Title: {page.title()}")

    # 제목 확인
    title_inp = page.locator("#post-title-inp, textarea.textarea_tit").first
    if title_inp.is_visible(timeout=3000):
        print(f"글 제목: {title_inp.input_value()}")

    # 본문 iframe 확인
    iframe_el = page.wait_for_selector("#editor-tistory_ifr, iframe[id*='tinymce']", timeout=10000)
    iframe = iframe_el.content_frame() if iframe_el else None
    if iframe:
        body = iframe.locator("body#tinymce").first
        content_preview = body.inner_text()[:150].replace("\n", " ")
        print(f"기존 본문 미리보기: {content_preview}")

    # 완료 버튼 확인
    complete_btn = page.locator("#publish-layer-btn, button:has-text('완료')").first
    print(f"완료 버튼 가시성: {complete_btn.is_visible()}")

    page.screenshot(path=str(BASE_DIR / "screenshots" / "edit_post_145_check.png"))
    print(f"📸 캡처 완료: {BASE_DIR / 'screenshots' / 'edit_post_145_check.png'}")

    context.close()
