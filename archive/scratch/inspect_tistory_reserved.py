"""
inspect_tistory_reserved.py - 티스토리 관리자 페이지에서 실제 예약 글 목록 및 수정 링크 추출
"""
import sys
import os
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

    manage_url = f"https://{blog_name}.tistory.com/manage/posts"
    print(f"🌐 접속 중: {manage_url}")
    page.goto(manage_url, wait_until="networkidle", timeout=30000)
    time.sleep(2)

    # 카카오 원클릭 로그인 자동 통과
    if "login" in page.url or "auth" in page.url:
        print("🔄 저장된 카카오 계정으로 원클릭 로그인 진행 중...")
        try:
            login_btn = page.locator(".btn_login, a:has-text('카카오계정으로 로그인')").first
            if login_btn.is_visible(timeout=3000):
                login_btn.click()
                page.wait_for_load_state("networkidle", timeout=15000)
                time.sleep(1)

            profile_item = page.locator(".wrap_profile, .item_account").first
            if profile_item.is_visible(timeout=3000):
                print("👤 저장된 프로필 계정 클릭...")
                profile_item.click()
                page.wait_for_load_state("networkidle", timeout=15000)
                time.sleep(3)
        except Exception as auto_login_err:
            print(f"(자동 로그인 처리 안내: {auto_login_err})")

    # 관리자 URL로 다시 이동
    if "manage/posts" not in page.url:
        page.goto(manage_url, wait_until="networkidle", timeout=20000)
        time.sleep(2)

    print(f"현재 페이지 URL: {page.url}")
    print(f"현재 페이지 제목: {page.title()}")

    # 예약 탭 클릭
    # 티스토리 글 목록의 탭 구조 파악
    tabs = page.locator(".tab_manage a, .list_tab a, .wrap_tab a").all()
    print("발견된 탭 목록:")
    for t in tabs:
        print(f"  - 탭: {t.inner_text()} (href: {t.get_attribute('href')})")
        if "예약" in t.inner_text():
            print(f"👉 예약 탭 클릭: {t.inner_text()}")
            t.click()
            time.sleep(2)
            break

    # 글 목록 아이템 수집
    items = page.locator("a.link_tit, .title a, td.title a, .item_post a.link_post").all()
    print(f"\n발견된 글 제목 링크 수: {len(items)}")
    for idx, item in enumerate(items[:20]):
        print(f"  [{idx+1}] {item.inner_text().strip()} | href: {item.get_attribute('href')}")

    # 스크린샷 캡처
    shot_path = BASE_DIR / "screenshots" / "manage_posts_reserved.png"
    page.screenshot(path=str(shot_path))
    print(f"\n📸 스크린샷 저장 완료: {shot_path}")

    context.close()
