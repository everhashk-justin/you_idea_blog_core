"""
test_update_post_145.py - 85번 글(Post ID 145)의 본문을 로컬 교정본으로 실제 수정 저장 테스트
"""
import sys
import os
import json
import time
import base64
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
PROFILE_DIR = BASE_DIR / "browser_profile"

sys.path.insert(0, str(BASE_DIR))
from post_publisher import parse_markdown_post

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

blog_name = config.get("blog_name", "softwin")
target_file = BASE_DIR / "posts" / "85_se_clean_architecture_solid_dependency_rule.md"
meta, content = parse_markdown_post(str(target_file))

print(f"📑 대상 파일: {target_file.name}")
print(f"📌 제목: {meta.get('title')}")
print(f"📏 본문 길이: {len(content)} 글자")

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=True,
        viewport={"width": 1280, "height": 900},
        permissions=["clipboard-read", "clipboard-write"],
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
    )
    page = context.pages[0] if context.pages else context.new_page()

    def handle_dialog(dialog):
        try:
            dialog.accept()
        except Exception:
            pass
    page.on("dialog", handle_dialog)

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

    # 본문 iframe 진입
    iframe_el = page.wait_for_selector("#editor-tistory_ifr, iframe[id*='tinymce']", timeout=10000)
    iframe = iframe_el.content_frame()
    if not iframe:
        raise RuntimeError("iframe을 찾을 수 없습니다.")

    # 1. 기존 본문 비우기
    print("🧹 기존 본문 내용 비우는 중...")
    body = iframe.locator("body#tinymce").first
    body.click()
    time.sleep(0.5)
    page.keyboard.press("Control+a")
    time.sleep(0.5)
    page.keyboard.press("Backspace")
    time.sleep(0.5)

    # 2. 새로운 교정 본문 주입 (클립보드 방식)
    print("📄 교정된 최신 마크다운 본문 주입 중...")
    page.evaluate("""async (text) => {
        try {
            await navigator.clipboard.writeText(text);
        } catch(e) {
            const el = document.createElement('textarea');
            el.value = text;
            document.body.appendChild(el);
            el.select();
            document.execCommand('copy');
            document.body.removeChild(el);
        }
    }""", content)
    time.sleep(0.8)
    page.keyboard.press("Control+v")
    time.sleep(2.5)

    # 3. 완료 버튼 클릭
    print("🎯 완료 버튼 클릭...")
    complete_btn = page.locator("#publish-layer-btn, button:has-text('완료')").first
    complete_btn.click()
    time.sleep(3)

    # 4. 최종 [공개 발행] 버튼 클릭
    print("📤 최종 [공개 발행] 클릭하여 티스토리 서버에 저장...")
    publish_btn = page.locator("button:has-text('공개 발행')").first
    if publish_btn.is_visible(timeout=5000):
        publish_btn.click()
        print("✅ [공개 발행] 버튼 클릭 완료! 서버 저장 대기 중...")
        # 페이지 이동 또는 완료 대기
        for i in range(10):
            time.sleep(1)
            if "manage/posts" in page.url or "newpost" not in page.url:
                print(f"🎉 저장 완료 후 페이지 이동 확인: {page.url}")
                break
        else:
            print("⚠️ URL 변화 대기 시간 초과 (저장 완료 가능성 확인)")
    else:
        raise RuntimeError("❌ [공개 발행] 버튼을 찾을 수 없습니다.")

    time.sleep(2)
    # 스크린샷 캡처
    shot_path = BASE_DIR / "screenshots" / "updated_post_145_success.png"
    page.screenshot(path=str(shot_path))
    print(f"📸 최종 상태 캡처: {shot_path}")

    context.close()
