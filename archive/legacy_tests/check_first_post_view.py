import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=str(BASE_DIR / "browser_profile"),
        headless=True
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle")
    if "login" in page.url:
        page.locator(".btn_login").first.click()
        time.sleep(2)
        page.locator(".wrap_profile").first.click()
        time.sleep(3)
        page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle")
    time.sleep(3)

    # 첫번째 글의 링크 클릭
    first_title = page.locator(".tit_post a").first
    print("첫 번째 글 제목:", first_title.inner_text())
    first_url = first_title.get_attribute("href")
    print("첫 번째 글 링크:", first_url)

    # 해당 링크로 이동하여 실제 화면 확인
    page.goto(first_url, wait_until="networkidle")
    time.sleep(3)
    page.screenshot(path=str(BASE_DIR / "screenshots" / "first_post_actual_view.png"), full_page=True)

    # 본문 텍스트 확인
    body_text = page.evaluate("""() => {
        const article = document.querySelector('.article_view, .entry-content, .tt_article_useless_p_margin, div[itemprop=\"articleBody\"]');
        return article ? article.innerText : document.body.innerText;
    }""")
    print("본문 내용:")
    print(body_text[:300].encode('cp949', errors='ignore').decode('cp949'))

    ctx.close()
