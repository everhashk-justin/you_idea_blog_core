# -*- coding: utf-8 -*-
"""
add_category.py - 티스토리 신규 카테고리 자동 추가 도구
"""

import sys
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
NEW_CATEGORY = "실무 장애 트러블슈팅 (Post-Mortem)"

def add_new_category():
    profile_dir = BASE_DIR / "browser_profile"
    print(f"🏗️  [티스토리 신규 카테고리 추가] '{NEW_CATEGORY}'")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=True,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.on("dialog", lambda dialog: dialog.accept())

        cat_url = "https://softwin.tistory.com/manage/category"
        page.goto(cat_url)
        time.sleep(2)

        # 자동 로그인 확인
        if "login" in page.url or "auth" in page.url:
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

            if "category" not in page.url:
                page.goto(cat_url)
                time.sleep(2)

        # 기존 카테고리 검사
        existing_names = [el.inner_text().strip() for el in page.locator(".list_order .txt_name").all()]
        if NEW_CATEGORY in existing_names:
            print(f"⏩ 이미 '{NEW_CATEGORY}' 카테고리가 존재합니다.")
            ctx.close()
            return True

        # 카테고리 추가 버튼 클릭
        add_btn = page.locator("label.lab_add, .btn_add, a:has-text('카테고리 추가')").first
        if not add_btn.is_visible(timeout=3000):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(0.5)

        add_btn.click()
        time.sleep(1)

        # 마지막 인풋에 카테고리명 입력
        inputs = page.locator(".list_order input[type='text'], input.tf_modify").all()
        if inputs:
            last_input = inputs[-1]
            last_input.click()
            last_input.fill(NEW_CATEGORY)
            last_input.press("Enter")
            time.sleep(1)

        # 변경사항 저장 클릭
        save_btn = page.locator("button:has-text('변경사항 저장'), .btn_apply").first
        if save_btn.is_visible(timeout=3000):
            save_btn.click()
            time.sleep(2)

        print(f"🎉 '{NEW_CATEGORY}' 카테고리 추가 완료!")
        ctx.close()
        return True

if __name__ == "__main__":
    add_new_category()

