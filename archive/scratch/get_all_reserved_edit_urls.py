"""
get_all_reserved_edit_urls.py - 전체 예약 글의 post_id와 제목 및 수정 링크 매핑 (로그인 포함)
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

    page.goto(f"https://{blog_name}.tistory.com/manage/posts", wait_until="networkidle", timeout=30000)
    time.sleep(2)

    # 카카오 원클릭 로그인 자동 통과
    if "login" in page.url or "auth" in page.url:
        print("Logging in...")
        try:
            page.locator(".btn_login, a:has-text('카카오계정으로 로그인')").first.click()
            time.sleep(2)
            page.locator(".wrap_profile, .item_account").first.click()
            time.sleep(4)
        except Exception:
            pass

    all_reserved_posts = []

    for page_num in [1, 2, 3]:
        url = f"https://{blog_name}.tistory.com/manage/posts?page={page_num}"
        print(f"Fetching page {page_num}: {url}")
        page.goto(url, wait_until="networkidle", timeout=20000)
        time.sleep(3)

        posts = page.evaluate("""() => {
            const list = [];
            // 모든 글 행 탐색
            document.querySelectorAll('.tbl_post tbody tr, .list_post li').forEach(el => {
                const text = el.innerText.replace(/\\s+/g, ' ').trim();
                if (text.includes('[예약]') || text.includes('예약')) {
                    const editA = el.querySelector('a[href*=\"/manage/post/\"]');
                    const titA = el.querySelector('.tit_post, .link_tit, .title');
                    const idMatch = editA ? editA.href.match(/\\/manage\\/post\\/(\\d+)/) : null;
                    list.push({
                        title: titA ? titA.innerText.trim() : (editA ? editA.innerText.trim() : ''),
                        editUrl: editA ? editA.href : '',
                        postId: idMatch ? idMatch[1] : '',
                        fullText: text
                    });
                }
            });
            return list;
        }""")

        print(f"Page {page_num} reserved posts found: {len(posts)}")
        for p_item in posts:
            all_reserved_posts.append(p_item)
            print(f"  * Post ID {p_item['postId']}: {p_item['title']}")

        if len(posts) == 0:
            print("No more reserved posts on this page.")
            break

    print(f"\n총 수집된 티스토리 예약 글: {len(all_reserved_posts)}편")
    out_path = BASE_DIR / "scratch" / "tistory_reserved_mapping.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_reserved_posts, f, ensure_ascii=False, indent=2)
    print(f"저장 완료: {out_path}")

    context.close()
