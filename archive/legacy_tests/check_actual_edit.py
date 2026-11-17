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

    # 글 목록에서 첫 번째 글(최신 글)의 모든 정보 추출
    row_info = page.evaluate("""() => {
        const firstLi = document.querySelector('ul.list_board li, li:has(.tit_post), .post_cont');
        if (!firstLi) return null;
        
        const links = [];
        firstLi.querySelectorAll('a').forEach(a => {
            links.push({ text: a.innerText.trim(), href: a.href });
        });
        
        return {
            text: firstLi.innerText.replace(/\\s+/g, ' ').trim(),
            links: links
        };
    }""")
    print("Row Info:", row_info)

    # 첫번째 글에 마우스를 올렸을 때 나타나는 [수정] 버튼 찾기
    item = page.locator(".tit_post").first
    item.hover()
    time.sleep(1)

    # 수정 링크 확인
    edit_btn = page.locator("a:has-text('수정'), button:has-text('수정')").first
    if edit_btn.is_visible():
        print("수정 버튼 href:", edit_btn.get_attribute("href"))
        edit_btn.click()
        time.sleep(4)
        print("수정 클릭 후 이동된 URL:", page.url)
        page.screenshot(path=str(BASE_DIR / "screenshots" / "actual_edit_screen.png"))
        
        # 여기서 본문 텍스트 추출!
        content_data = page.evaluate("""() => {
            let tm = window.tinymce && window.tinymce.activeEditor ? window.tinymce.activeEditor.getContent() : "";
            let cm = "";
            const cmEl = document.querySelector('.CodeMirror');
            if (cmEl && cmEl.CodeMirror) cm = cmEl.CodeMirror.getValue();
            return {
                title: document.querySelector('#post-title-inp') ? document.querySelector('#post-title-inp').value : "",
                tmLength: tm.length,
                tmSnippet: tm.substring(0, 200),
                cmLength: cm.length,
                cmSnippet: cm.substring(0, 200)
            };
        }""")
        print("수정 화면 내 본문 데이터:", content_data)

    ctx.close()
