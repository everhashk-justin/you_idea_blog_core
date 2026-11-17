"""
clean_docker_duplicate.py - 도커 중복 글 중 1개 안전 정리
"""
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
profile_dir = BASE_DIR / "browser_profile"
SCREENSHOT_DIR = BASE_DIR / "screenshots"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=str(profile_dir),
        headless=True,
        viewport={"width": 1280, "height": 900}
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.on("dialog", lambda dialog: dialog.accept())

    posts_url = "https://softwin.tistory.com/manage/posts"
    print(f"🌐 글 관리 페이지 접속: {posts_url}")
    page.goto(posts_url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)

    # 자동 로그인 확인
    if "login" in page.url or "auth" in page.url:
        login_btn = page.locator(".btn_login, a:has-text('카카오계정으로 로그인')").first
        if login_btn.is_visible(timeout=3000):
            login_btn.click()
            page.wait_for_timeout(2000)
        prof = page.locator(".wrap_profile, .item_account").first
        if prof.is_visible(timeout=3000):
            prof.click()
            page.wait_for_timeout(3000)
        page.goto(posts_url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

    # 글 목록 파싱
    rows_info = page.evaluate("""() => {
        const rows = document.querySelectorAll('.tbl_board tbody tr, ul.list_board li, ul.list_post > li');
        const results = [];
        rows.forEach((r, idx) => {
            const titleEl = r.querySelector('.tit_post, .txt_title, a[href*="/manage/newpost"], .link_title');
            const dateEl = r.querySelector('.txt_date, .date, .time_post');
            results.push({
                index: idx,
                title: titleEl ? titleEl.innerText.trim() : "",
                date: dateEl ? dateEl.innerText.trim() : "",
                fullText: r.innerText.replace(/\\s+/g, ' ').trim()
            });
        });
        return results;
    }""")

    docker_rows = [r for r in rows_info if "도커(Docker)" in r["title"]]
    print(f"🔍 감지된 도커 게시글 수: {len(docker_rows)}")
    for r in docker_rows:
        print(f"  - 인덱스 {r['index']}: {r['title']} ({r['date']})")

    if len(docker_rows) > 1:
        # 두 번째(더 먼저 등록된) 도커 글 선택
        target = docker_rows[1]
        print(f"🗑️ 중복 글 삭제 대상: 인덱스 {target['index']} ({target['title']})")

        dom_rows = page.locator(".tbl_board tbody tr, ul.list_board li, ul.list_post > li")
        target_row = dom_rows.nth(target["index"])
        chk = target_row.locator("input[type='checkbox']").first
        if chk.count() > 0:
            chk.evaluate("el => el.click()")
            page.wait_for_timeout(1000)
            
            # 변경 드롭다운 클릭
            change_btn = page.locator("button:has-text('변경'), .btn_change, .btn_action").first
            if change_btn.is_visible(timeout=2000):
                change_btn.click()
                page.wait_for_timeout(1000)
                del_opt = page.locator("button:has-text('삭제'), a:has-text('삭제'), .item_layer:has-text('삭제')").first
                if del_opt.is_visible(timeout=2000):
                    del_opt.click()
                    page.wait_for_timeout(3000)
                    print("✅ 중복 도커 글 삭제 완료!")
        else:
            # 개별 삭제 버튼 시도
            target_row.hover()
            page.wait_for_timeout(500)
            del_btn = target_row.locator("button:has-text('삭제'), a:has-text('삭제')").first
            if del_btn.is_visible(timeout=2000):
                del_btn.click()
                page.wait_for_timeout(3000)
                print("✅ 행 개별 삭제 버튼으로 완료!")
    else:
        print("ℹ️ 중복 없음 (도커 글이 1개만 있습니다).")

    page.wait_for_timeout(2000)
    page.screenshot(path=str(SCREENSHOT_DIR / "docker_cleaned.png"), full_page=True)
    ctx.close()
