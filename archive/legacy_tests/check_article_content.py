import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(BASE_DIR / "browser_profile"),
        headless=True,
        viewport={"width": 1280, "height": 900}
    )
    page = context.pages[0] if context.pages else context.new_page()

    page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle")
    time.sleep(2)

    # 첫번째 글 제목 요소 클릭하여 보기 또는 링크 얻기
    # 첫번째 글의 수정 버튼 링크
    edit_link = page.locator(".tbl_board tbody tr:first-child a[href*='/manage/newpost']").first
    href = edit_link.get_attribute("href")
    print(f"Edit href: {href}")

    # entryId 찾기
    import re
    m = re.search(r"entryId=(\d+)", href if href else "")
    if m:
        entry_id = m.group(1)
        print(f"Found entryId: {entry_id}")
        
        # 블로그 상세 페이지 방문 (작성자 계정 로그인 상태이므로 비공개 글도 열람 가능)
        view_url = f"https://softwin.tistory.com/{entry_id}"
        print(f"Visiting article: {view_url}")
        page.goto(view_url, wait_until="networkidle")
        time.sleep(3)
        page.screenshot(path=str(BASE_DIR / "screenshots" / "verify_actual_blog_view.png"), full_page=False)

        # 본문 영역 텍스트 추출
        article_text = page.evaluate("""() => {
            const article = document.querySelector('.article_view, .entry-content, .tt_article_useless_p_margin, div[itemprop="articleBody"]');
            return article ? article.innerText : "본문 요소를 찾을 수 없음";
        }""")
        print(f"Article Text (first 200 chars):\n{article_text[:200]}")
    else:
        print("entryId not found!")

    context.close()
