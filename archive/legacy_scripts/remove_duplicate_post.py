"""
remove_duplicate_post.py - 중복 발행된 글 중 14:33:32에 발행된 글(이미지 중복본) 삭제
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
    page.goto(posts_url, wait_until="networkidle", timeout=30000)
    time.sleep(2)

    # 자동 로그인
    if "login" in page.url or "auth" in page.url:
        print("🔄 자동 로그인 진행 중...")
        login_btn = page.locator(".btn_login, a:has-text('카카오계정으로 로그인')").first
        if login_btn.is_visible(timeout=3000):
            login_btn.click()
            page.wait_for_load_state("networkidle", timeout=15000)
            time.sleep(1)
        profile_item = page.locator(".wrap_profile, .item_account").first
        if profile_item.is_visible(timeout=3000):
            profile_item.click()
            page.wait_for_load_state("networkidle", timeout=15000)
            time.sleep(3)
        page.goto(posts_url, wait_until="networkidle", timeout=30000)
        time.sleep(2)

    # 현재 글 목록 파싱
    print("📋 글 목록 분석 중...")
    page.screenshot(path=str(SCREENSHOT_DIR / "before_remove_duplicate.png"))

    rows_info = page.evaluate("""() => {
        const rows = document.querySelectorAll('.tbl_board tbody tr, ul.list_board li, ul.list_post > li');
        const results = [];
        rows.forEach((r, idx) => {
            const titleEl = r.querySelector('.tit_post, .txt_title, a[href*="/manage/newpost"], .link_title');
            const dateEl = r.querySelector('.txt_date, .date, .time_post');
            const chkEl = r.querySelector('input[type="checkbox"]');
            results.push({
                index: idx,
                title: titleEl ? titleEl.innerText.trim() : "",
                date: dateEl ? dateEl.innerText.trim() : "",
                fullText: r.innerText.replace(/\\s+/g, ' ').trim()
            });
        });
        return results;
    }""")

    print(f"총 {len(rows_info)}개 글 감지됨:")
    matching_rows = []
    for r in rows_info:
        if "쿠키와 세션" in r["title"]:
            print(f"  👉 [매칭] 인덱스 {r['index']} | 일시: {r['date']} | 제목: {r['title']}")
            matching_rows.append(r)
        else:
            print(f"     [기타] 인덱스 {r['index']} | 일시: {r['date']} | 제목: {r['title'][:30]}")

    deleted = False
    if len(matching_rows) >= 2:
        # 14:33 시간대가 포함되거나 더 최신인 항목 찾기
        target_item = None
        for m in matching_rows:
            if "14:33" in m["date"] or "14:33" in m["fullText"]:
                target_item = m
                break
        
        # 14:33 특정 문자열이 없다면 더 늦게 발행된(인덱스가 앞선) 항목 선택
        if not target_item:
            target_item = matching_rows[0]

        print(f"\n🎯 삭제 대상 선택: 인덱스 {target_item['index']}, 시간: {target_item['date']}, 텍스트: {target_item['title']}")

        # 해당 행 가져오기
        dom_rows = page.locator(".tbl_board tbody tr, ul.list_board li, ul.list_post > li")
        target_row = dom_rows.nth(target_item["index"])

        # 행에 호버
        target_row.hover()
        time.sleep(1)

        # 삭제 버튼 시도
        del_btn = target_row.locator("button:has-text('삭제'), a:has-text('삭제')").first
        if del_btn.is_visible(timeout=2000):
            print("🗑️ 행 내부 삭제 버튼 클릭!")
            del_btn.click()
            time.sleep(3)
            deleted = True
        else:
            print("체크박스 선택 후 상단 일괄 메뉴로 삭제 진행...")
            chk = target_row.locator("input[type='checkbox']").first
            chk.check()
            time.sleep(1)

            change_btn = page.locator("button:has-text('변경'), .btn_change").first
            change_btn.click()
            time.sleep(1)

            del_menu = page.locator("button:has-text('삭제'), a:has-text('삭제')").first
            del_menu.click()
            time.sleep(3)
            deleted = True

    elif len(matching_rows) == 1:
        print("⚠️ 쿠키와 세션 글이 1개만 발견되었습니다. 이미 중복이 해소되었을 수 있습니다.")
    else:
        print("⚠️ 대상 글을 찾지 못했습니다.")

    page.wait_for_load_state("networkidle", timeout=10000)
    time.sleep(2)
    page.screenshot(path=str(SCREENSHOT_DIR / "after_remove_duplicate.png"))

    if deleted:
        print("✅ 중복 글이 성공적으로 삭제되었습니다!")
    else:
        print("❌ 삭제 작업을 완료하지 못했습니다.")

    ctx.close()
