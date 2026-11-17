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
    page.goto("https://softwin.tistory.com/manage/newpost", wait_until="networkidle")
    if "login" in page.url:
        page.locator(".btn_login").first.click()
        time.sleep(2)
        page.locator(".wrap_profile").first.click()
        time.sleep(3)
        page.goto("https://softwin.tistory.com/manage/newpost", wait_until="networkidle")
    time.sleep(3)

    try:
        page.locator("button:has-text('취소')").first.click(timeout=1000)
    except Exception:
        pass

    matches = page.evaluate("""() => {
        const results = [];
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
        while (walker.nextNode()) {
            const node = walker.currentNode;
            if (node.innerText && node.innerText.includes('기본모드')) {
                results.push({
                    tag: node.tagName,
                    id: node.id,
                    className: node.className,
                    text: node.innerText,
                    outer: node.outerHTML.substring(0, 150)
                });
            }
        }
        return results;
    }""")

    print(f"Found {len(matches)} elements with '기본모드':")
    for m in matches:
        print(m)
    ctx.close()
