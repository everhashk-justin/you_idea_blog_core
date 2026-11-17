"""
dump_all_links.py
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
    time.sleep(3)

    print("Current URL:", page.url)
    print("Page Title:", page.title())

    # 카카오 원클릭 로그인 자동 통과
    if "login" in page.url or "auth" in page.url:
        print("Logging in...")
        try:
            login_btn = page.locator(".btn_login, a:has-text('카카오계정으로 로그인')").first
            if login_btn.is_visible(timeout=3000):
                login_btn.click()
                time.sleep(2)
            profile_item = page.locator(".wrap_profile, .item_account").first
            if profile_item.is_visible(timeout=3000):
                profile_item.click()
                time.sleep(4)
        except Exception as e:
            print("Login error:", e)

    page.goto(f"https://{blog_name}.tistory.com/manage/posts", wait_until="networkidle", timeout=20000)
    time.sleep(3)

    print("After URL:", page.url)
    print("After Title:", page.title())

    links = page.evaluate("""() => Array.from(document.querySelectorAll('a')).map(a => ({ text: a.innerText, href: a.href }))""")
    print(f"Total links found: {len(links)}")
    for l in links[:30]:
        print(f"  {l['text'].strip()} -> {l['href']}")

    context.close()
