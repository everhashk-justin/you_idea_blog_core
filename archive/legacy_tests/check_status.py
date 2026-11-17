import asyncio
from playwright.async_api import async_playwright

async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="browser_profile",
            headless=True
        )
        page = await browser.new_page()
        await page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle")
        await page.screenshot(path="screenshots/manage_current_posts.png")
        
        posts = await page.evaluate("""() => {
            const results = [];
            document.querySelectorAll("table.tbl_board tbody tr, ul.list_post li").forEach(row => {
                const text = row.innerText.replace(/\\s+/g, " ").trim();
                results.push(text);
            });
            return results;
        }""")
        print("글 목록:")
        for idx, p_text in enumerate(posts):
            print(f"{idx+1}. {p_text}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(check())
