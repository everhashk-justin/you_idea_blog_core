"""
batch_update_all_posts.py - 티스토리 1탄 글(02~12번) 본문 이미지 및 내용 일괄 수정 업데이트
"""
import sys
import time
import base64
import re
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
profile_dir = BASE_DIR / "browser_profile"
SCREENSHOT_DIR = BASE_DIR / "screenshots"

def update_single_post_in_page(page, post_id, md_file_rel):
    md_path = BASE_DIR / md_file_rel
    with open(md_path, "r", encoding="utf-8") as f:
        full_content = f.read()

    content = full_content
    title = ""
    tags = []
    category = ""
    if full_content.startswith("---"):
        parts = full_content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            content = parts[2].strip()
            for line in fm_text.strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k == "title": title = v
                    elif k == "tags": tags = [t.strip() for t in v.split(",") if t.strip()]
                    elif k == "category": category = v

    print(f"\n============================================================")
    print(f"🔄 [글 수정 시작] POST ID: {post_id} | {title}")
    print(f"============================================================")

    edit_url = f"https://softwin.tistory.com/manage/post/{post_id}"
    page.goto(edit_url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3500)

    # 에디터 iframe 대기
    try:
        iframe_element = page.wait_for_selector("#editor-tistory_ifr, iframe[id*='tinymce']", timeout=15000)
    except Exception as e:
        print(f"❌ iframe 로드 실패: {e}")
        return False

    iframe = iframe_element.content_frame()
    if not iframe:
        print("❌ iframe 프레임 획득 실패")
        return False

    # 본문 전체 비우기 (Ctrl+A ➔ Delete)
    print("🧹 기존 본문 내용 초기화 중...")
    body = iframe.locator("body#tinymce").first
    body.click()
    page.wait_for_timeout(500)
    page.keyboard.press("Control+a")
    page.wait_for_timeout(400)
    page.keyboard.press("Backspace")
    page.wait_for_timeout(800)

    # 새 마크다운 및 고해상도 다이어그램 이미지 주입
    print("📄 새 마크다운 본문 및 최신 다이어그램 이미지 주입 중...")
    img_pattern = re.compile(r'!\[(.*?)\]\((.*?)\)')
    parts = []
    last_idx = 0
    for m in img_pattern.finditer(content):
        start, end = m.span()
        if start > last_idx:
            parts.append({"type": "text", "val": content[last_idx:start]})
        parts.append({"type": "image", "alt": m.group(1), "src": m.group(2)})
        last_idx = end
    if last_idx < len(content):
        parts.append({"type": "text", "val": content[last_idx:]})

    for part in parts:
        if part["type"] == "text":
            chunk = part["val"].strip("\r\n")
            if chunk:
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
                }""", chunk)
                page.wait_for_timeout(500)
                page.keyboard.press("Control+v")
                page.wait_for_timeout(1000)
                page.keyboard.press("Enter")
                page.wait_for_timeout(400)
        elif part["type"] == "image":
            img_rel = part["src"]
            img_path = Path(img_rel)
            if not img_path.is_absolute():
                if (BASE_DIR / "posts" / img_rel).exists():
                    img_path = BASE_DIR / "posts" / img_rel
                elif (BASE_DIR / img_rel).exists():
                    img_path = BASE_DIR / img_rel

            if img_path.exists():
                print(f"🖼️ 최신 다이어그램 이미지 본문 삽입: {img_path.name}")
                with open(img_path, "rb") as imf:
                    img_b64 = base64.b64encode(imf.read()).decode("utf-8")

                page.evaluate(f"""async () => {{
                    try {{
                        const res = await fetch('data:image/png;base64,{img_b64}');
                        const blob = await res.blob();
                        await navigator.clipboard.write([
                            new ClipboardItem({{ 'image/png': blob }})
                        ]);
                        return "SUCCESS";
                    }} catch(e) {{
                        return "ERR: " + e.toString();
                    }}
                }}""")
                page.wait_for_timeout(700)
                page.keyboard.press("Control+v")
                page.wait_for_timeout(5000)

                # 캡션 탈출 및 본문 새 문단 이동
                iframe.evaluate("""() => {
                    const body = document.body;
                    if (document.activeElement) document.activeElement.blur();
                    const newP = document.createElement('p');
                    newP.innerHTML = '<br>';
                    body.appendChild(newP);
                }""")
                body.click()
                page.keyboard.press("PageDown")
                page.wait_for_timeout(400)

    try:
        # 완료 버튼 클릭
        print("🎯 수정 완료(저장) 버튼 클릭 중...")
        complete_btn = page.locator("button.btn_complete, button:has-text('완료')").first
        complete_btn.click()
        page.wait_for_timeout(2000)

        # 공개 라디오 버튼 확인
        page.evaluate("""() => {
            const rad = document.querySelector('input[type="radio"][value="20"]');
            if (rad) {
                rad.checked = true;
                rad.dispatchEvent(new Event('change', { bubbles: true }));
                rad.click();
            }
        }""")
        page.wait_for_timeout(1000)

        # 최종 발행(수정 완료) 버튼 클릭
        publish_btn = page.locator(".btn_publish, button:has-text('수정 발행'), button:has-text('공개 발행'), button:has-text('발행')").first
        btn_text = publish_btn.inner_text().strip() if publish_btn.is_visible() else "발행"
        print(f"📤 최종 수정 발행 버튼 클릭 (버튼명: '{btn_text}')")
        publish_btn.click()
        page.wait_for_timeout(5000)

        screenshot_path = SCREENSHOT_DIR / f"edit_batch_{post_id}.png"
        page.screenshot(path=str(screenshot_path))
        print(f"✅ 수정 완료: POST ID {post_id} | 캡처 저장: {screenshot_path.name}")
        return True
    except Exception as e:
        print(f"❌ 수정 중 에러 발생 (POST ID {post_id}): {e}")
        try:
            page.screenshot(path=str(SCREENSHOT_DIR / f"err_batch_{post_id}.png"))
        except Exception:
            pass
        return False

def run_all_updates():
    with open(BASE_DIR / "update_targets.json", "r", encoding="utf-8") as f:
        targets = json.load(f)

    # 이미 수정한 03번(ID 62) 제외하거나 포함하여 순차 실행
    items_to_update = [t for t in targets if t["key"] != "03"]

    print(f"🚀 총 {len(items_to_update)}편의 기존 글 본문 이미지 일괄 수정 시작...")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=True,
            viewport={"width": 1280, "height": 900},
            permissions=["clipboard-read", "clipboard-write"],
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        def handle_dialog(dialog):
            try: dialog.accept()
            except Exception: pass
        page.on("dialog", handle_dialog)

        # 관리자 페이지 접속 및 로그인 확인
        page.goto("https://softwin.tistory.com/manage/posts", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        if "login" in page.url or "auth" in page.url:
            login_btn = page.locator(".btn_login, a:has-text('카카오계정으로 로그인')").first
            if login_btn.is_visible(timeout=3000):
                login_btn.click()
                page.wait_for_timeout(2000)
            prof = page.locator(".wrap_profile, .item_account").first
            if prof.is_visible(timeout=3000):
                prof.click()
                page.wait_for_timeout(3000)

        for idx, item in enumerate(items_to_update):
            print(f"\n[{idx+1}/{len(items_to_update)}] 대상: {item['matched_title']} (POST ID: {item['post_id']})")
            success = update_single_post_in_page(page, item["post_id"], item["file"])
            if success:
                print(f"🎉 성공: {item['key']}번 글 수정 완료!")
            else:
                print(f"⚠️ 실패: {item['key']}번 글 수정 실패")
            time.sleep(3)

        ctx.close()
        print("\n🏆 모든 대상 글의 본문 이미지 수정 업데이트가 완료되었습니다!")

if __name__ == "__main__":
    run_all_updates()
