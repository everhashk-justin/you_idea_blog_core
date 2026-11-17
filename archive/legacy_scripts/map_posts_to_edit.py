"""
map_posts_to_edit.py - 티스토리 글 관리자 1~2페이지에서 1탄 글(02~12번)의 POST ID 1:1 매핑
"""
import sys
import json
import re
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

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=str(profile_dir),
        headless=True,
        viewport={"width": 1280, "height": 1000}
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    all_posts = []

    for page_num in [1, 2]:
        url = f"https://softwin.tistory.com/manage/posts?page={page_num}"
        print(f"🌐 접속 중: {url}")
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        # 자동 로그인 체크
        if "login" in page.url or "auth" in page.url:
            login_btn = page.locator(".btn_login, a:has-text('카카오계정으로 로그인')").first
            if login_btn.is_visible(timeout=3000):
                login_btn.click()
                page.wait_for_timeout(2000)
            prof = page.locator(".wrap_profile, .item_account").first
            if prof.is_visible(timeout=3000):
                prof.click()
                page.wait_for_timeout(3000)
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

        page_posts = page.evaluate("""() => {
            const rows = document.querySelectorAll('.tbl_board tbody tr, ul.list_board li, ul.list_post > li');
            const list = [];
            rows.forEach(r => {
                const titleEl = r.querySelector('.tit_post, .txt_title, .link_title');
                const editA = r.querySelector('a[href*="/manage/post/"]');
                const title = titleEl ? titleEl.innerText.trim() : "";
                const editHref = editA ? editA.href : "";
                list.push({ title, editHref });
            });
            return list;
        }""")
        all_posts.extend(page_posts)

    print(f"\n📊 총 수집된 글: {len(all_posts)}편")
    
    # 02~12번 대상 목록
    targets = [
        {"key": "02", "query": "컴퓨터는 어떻게 작동하는가", "file": "posts/02_cs_cpu_and_memory.md"},
        {"key": "03", "query": "프로그래밍 언어란 무엇인가", "file": "posts/03_pl_what_is_language.md"},
        {"key": "04", "query": "인터넷은 어떻게 작동하는가", "file": "posts/04_net_osi_and_http.md"},
        {"key": "05", "query": "서버란 무엇인가", "file": "posts/05_be_what_is_server.md"},
        {"key": "06", "query": "브라우저는 어떻게 웹페이지를 그리는가", "file": "posts/06_fe_browser_rendering.md"},
        {"key": "07", "query": "데이터베이스란 무엇인가", "file": "posts/07_db_what_is_database.md"},
        {"key": "08", "query": "클라우드란 무엇인가", "file": "posts/08_cloud_what_is_cloud.md"},
        {"key": "09", "query": "비밀번호는 어떻게 저장되는가", "file": "posts/09_sec_password_and_hash.md"},
        {"key": "10", "query": "AI는 어떻게 학습하는가", "file": "posts/10_ai_how_ml_learns.md"},
        {"key": "11", "query": "좋은 코드란 무엇인가", "file": "posts/11_se_clean_code.md"},
        {"key": "12", "query": "임베디드 시스템이란 무엇인가", "file": "posts/12_emb_what_is_embedded.md"},
    ]

    matched_targets = []
    for t in targets:
        matched = None
        for p_item in all_posts:
            if t["query"] in p_item["title"]:
                matched = p_item
                break
        if matched:
            # post_id 추출
            m = re.search(r'/manage/post/(\d+)', matched["editHref"])
            post_id = m.group(1) if m else None
            t["post_id"] = post_id
            t["edit_url"] = f"https://softwin.tistory.com/manage/post/{post_id}" if post_id else None
            t["matched_title"] = matched["title"]
            matched_targets.append(t)
            print(f"✅ [{t['key']}] ID {post_id} 매칭: {matched['title'][:35]}...")
        else:
            print(f"❌ [{t['key']}] 매칭 실패: {t['query']}")

    # JSON 저장
    with open(BASE_DIR / "update_targets.json", "w", encoding="utf-8") as f:
        json.dump(matched_targets, f, ensure_ascii=False, indent=2)

    ctx.close()
