"""
update_all_reserved_posts.py - 티스토리 예약 글 전체(24편) 본문 일괄 수정 저장
"""
import sys
import os
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
PROFILE_DIR = BASE_DIR / "browser_profile"
PLAN_FILE = BASE_DIR / "scratch" / "final_update_plan.json"

sys.path.insert(0, str(BASE_DIR))
from post_publisher import parse_markdown_post

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

blog_name = config.get("blog_name", "softwin")

with open(PLAN_FILE, "r", encoding="utf-8") as f:
    plan = json.load(f)

# Post ID 145는 이미 테스트로 완료했으므로 제외 (146부터 169까지 총 24편)
targets = [p for p in plan if p["postId"] != "145"]
print(f"🚀 [티스토리 예약 글 일괄 본문 수정 저장 시작] 총 대상: {len(targets)}편\n")

success_list = []
failed_list = []

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

    # 1. 초기 로그인 확인
    page.goto(f"https://{blog_name}.tistory.com/manage/posts", wait_until="networkidle", timeout=30000)
    time.sleep(2)
    if "login" in page.url or "auth" in page.url:
        print("🔄 카카오 원클릭 로그인 진행 중...")
        try:
            page.locator(".btn_login, a:has-text('카카오계정으로 로그인')").first.click()
            time.sleep(2)
            page.locator(".wrap_profile, .item_account").first.click()
            time.sleep(4)
        except Exception as e:
            print("로그인 안내:", e)

    for idx, item in enumerate(targets):
        post_id = item["postId"]
        num = item["num"]
        file_path = item["matchedFile"]
        file_name = item["matchedFileName"]
        title = item["title"]

        print("=" * 60)
        print(f"[{idx+1}/{len(targets)}] Post ID {post_id} (No.{num}) 업데이트 진행 중...")
        print(f"  파일: {file_name}")
        print(f"  제목: {title}")

        if not file_path or not os.path.exists(file_path):
            print(f"  ❌ 로컬 파일을 찾을 수 없어 건너뜁니다: {file_path}")
            failed_list.append((post_id, "File Not Found"))
            continue

        meta, content = parse_markdown_post(file_path)

        edit_url = f"https://{blog_name}.tistory.com/manage/post/{post_id}"
        try:
            page.goto(edit_url, wait_until="networkidle", timeout=25000)
            time.sleep(2)

            # 임시저장 알림 팝업 닫기
            try:
                cancel_btn = page.locator("button:has-text('취소'), .btn_cancel").first
                if cancel_btn.is_visible(timeout=1500):
                    cancel_btn.click()
                    time.sleep(0.5)
            except Exception:
                pass

            # iframe 본문 로드
            iframe_el = page.wait_for_selector("#editor-tistory_ifr, iframe[id*='tinymce']", timeout=10000)
            iframe = iframe_el.content_frame()
            if not iframe:
                raise RuntimeError("iframe을 찾을 수 없습니다.")

            # 기존 본문 비우기
            body = iframe.locator("body#tinymce").first
            body.click()
            time.sleep(0.3)
            page.keyboard.press("Control+a")
            time.sleep(0.3)
            page.keyboard.press("Backspace")
            time.sleep(0.3)

            # 새 교정 본문 클립보드 주입
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
            time.sleep(0.5)
            page.keyboard.press("Control+v")
            time.sleep(2)

            # 완료 버튼 클릭
            complete_btn = page.locator("#publish-layer-btn, button:has-text('완료')").first
            complete_btn.click()
            time.sleep(2.5)

            # [공개 발행] 버튼 클릭
            publish_btn = page.locator("button:has-text('공개 발행')").first
            if publish_btn.is_visible(timeout=5000):
                publish_btn.click()
                print(f"  📤 [공개 발행] 클릭 완료! 서버 반영 대기...")
                # 페이지 이동 대기
                for _ in range(8):
                    time.sleep(1)
                    if "manage/posts" in page.url or "newpost" not in page.url:
                        break
                print(f"  ✅ [성공] Post ID {post_id} 티스토리 서버 저장 완결!")
                success_list.append((post_id, num, file_name))
            else:
                raise RuntimeError("공개 발행 버튼을 찾을 수 없습니다.")

            # 다음 글을 위한 안전 딜레이
            time.sleep(2)

        except Exception as e:
            print(f"  ❌ [실패] Post ID {post_id} 업데이트 중 오류: {e}")
            failed_list.append((post_id, str(e)))
            # 에러 스크린샷
            err_shot = BASE_DIR / "screenshots" / f"err_update_{post_id}.png"
            try:
                page.screenshot(path=str(err_shot))
            except Exception:
                pass
            time.sleep(2)

    context.close()

print("\n" + "=" * 60)
print(f"🎉 [티스토리 예약 글 전체 본문 수정 저장 완료 보고]")
print(f"  - 총 대상: {len(targets)}편")
print(f"  - 성공: {len(success_list)}편")
print(f"  - 실패: {len(failed_list)}편")
if failed_list:
    print("  ❌ 실패 내역:")
    for f_id, err in failed_list:
        print(f"    * Post ID {f_id}: {err}")
print("=" * 60)
