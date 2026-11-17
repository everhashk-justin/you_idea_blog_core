import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=str(BASE_DIR / "browser_profile"),
        headless=True
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    # 다이얼로그 수락
    page.on("dialog", lambda d: d.accept())

    page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle")
    if "login" in page.url or "auth" in page.url:
        page.locator(".btn_login").first.click()
        time.sleep(2)
        page.locator(".wrap_profile").first.click()
        time.sleep(3)
        page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle")
    time.sleep(3)

    # 1. 삭제할 대상 글들의 체크박스 클릭
    # 0번(최신 정식 글)은 체크하지 않고, 삭제 대상 글들만 체크
    checked_count = page.evaluate("""() => {
        let count = 0;
        const rows = document.querySelectorAll('li:has(.tit_post)');
        rows.forEach((row, idx) => {
            if (idx === 0) return; // 0번(최신 글)은 건너뜀
            const titleEl = row.querySelector('.tit_post a');
            if (!titleEl) return;
            const title = titleEl.innerText;
            if (title.includes('테스트') || title.includes('분석') || title.includes('추적') || title.includes('쿠키와 세션')) {
                const chk = row.querySelector('input[type=\"checkbox\"], .inp_check');
                if (chk && !chk.checked) {
                    chk.click();
                    count++;
                }
            }
        });
        return count;
    }""")

    print(f"체크된 삭제 대상 글 개수: {checked_count}")

    if checked_count > 0:
        time.sleep(1)
        page.screenshot(path=str(BASE_DIR / "screenshots" / "before_bulk_delete.png"))

        # 2. 일괄 변경 드롭다운 열기
        change_btn = page.locator("button:has-text('변경'), .btn_change, a:has-text('변경')").first
        if change_btn.is_visible():
            change_btn.click()
            time.sleep(1)
            page.screenshot(path=str(BASE_DIR / "screenshots" / "change_menu_open.png"))

            # '삭제' 메뉴 클릭
            delete_opt = page.locator("button:has-text('삭제'), a:has-text('삭제'), [role='menuitem']:has-text('삭제')").first
            if delete_opt.is_visible():
                delete_opt.click()
                time.sleep(3)
                print("일괄 삭제 완료!")
            else:
                print("삭제 메뉴 옵션을 찾지 못함")
        else:
            print("변경 버튼을 찾지 못함, 개별 호버 삭제 시도...")
            # 개별 호버 삭제 fallback
            pass

    time.sleep(2)
    page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle")
    time.sleep(2)
    page.screenshot(path=str(BASE_DIR / "screenshots" / "final_clean_result.png"))

    remaining_titles = page.evaluate("""() => {
        const list = [];
        document.querySelectorAll('li:has(.tit_post) .tit_post a').forEach(a => {
            list.push(a.innerText.trim());
        });
        return list;
    }""")
    print("=== 글 목록 (상위 5개) ===")
    for t in remaining_titles[:5]:
        print("-", t)

    ctx.close()
