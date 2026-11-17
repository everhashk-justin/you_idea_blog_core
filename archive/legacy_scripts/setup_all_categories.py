# -*- coding: utf-8 -*-
"""
setup_all_categories.py - 티스토리 블로그 11대 SW 기술 마스터 카테고리 일괄 자동 생성 도구
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
SCREENSHOT_DIR = BASE_DIR / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# 생성할 11대 마스터 카테고리 목록
CATEGORIES_TO_CREATE = [
    "프로그래밍 언어 & 패러다임",
    "컴퓨터 과학 핵심 기초",
    "네트워크 & 웹 통신 기술",
    "백엔드 & 서버 아키텍처",
    "프론트엔드 & 클라이언트",
    "데이터베이스 & 스토리지",
    "클라우드, DevOps & 인프라",
    "보안 & 인증 기술",
    "AI, 머신러닝 & 빅데이터",
    "소프트웨어 공학 & 아키텍처",
    "임베디드 & 차세대 기술"
]

def setup_categories():
    profile_dir = BASE_DIR / "browser_profile"
    
    print("\n" + "=" * 65)
    print("🏗️  [티스토리 11대 SW 마스터 카테고리 자동 구축 시작]")
    print(f"📁 총 생성 예정 카테고리 수: {len(CATEGORIES_TO_CREATE)}개")
    print("=" * 65)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        # 알림창 자동 수락
        page.on("dialog", lambda dialog: dialog.accept())

        # 카테고리 관리 페이지 접속
        cat_url = "https://softwin.tistory.com/manage/category"
        print(f"🌐 카테고리 관리 페이지 접속 중: {cat_url}")
        page.goto(cat_url)
        time.sleep(2)

        # 자동 로그인 처리
        if "login" in page.url or "auth" in page.url:
            print("🔄 자동 로그인 진행 중...")
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

        print("✅ 관리자 페이지 진입 완료!")

        # 기존 카테고리 이름 수집
        existing_names = []
        for el in page.locator(".list_order .txt_name").all():
            try:
                name = el.inner_text().strip()
                if name:
                    existing_names.append(name)
            except Exception:
                pass
        print(f"📋 현재 등록된 카테고리: {', '.join(existing_names)}\n")

        added_count = 0
        for idx, cat_name in enumerate(CATEGORIES_TO_CREATE, 1):
            if cat_name in existing_names:
                print(f"[{idx}/{len(CATEGORIES_TO_CREATE)}] ⏩ '{cat_name}' (이미 존재함)")
                continue

            print(f"[{idx}/{len(CATEGORIES_TO_CREATE)}] ➕ 카테고리 추가 중: '{cat_name}'")
            
            # '카테고리 추가' 버튼 클릭
            add_btn = page.locator("label.lab_add, .btn_add, a:has-text('카테고리 추가')").first
            if not add_btn.is_visible(timeout=3000):
                # 스크롤 내리기
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(0.5)

            add_btn.click()
            time.sleep(0.8)

            # 생성된 텍스트박스 찾기
            inp = page.locator("input.tf_blog.tf_on, input.tf_category, input[type=text]:focus").first
            if inp.is_visible(timeout=3000):
                inp.fill(cat_name)
                time.sleep(0.3)
                
                # 확인 버튼 클릭 (또는 Enter)
                confirm_btn = page.locator("button:has-text('확인'), input[value='확인'], a:has-text('확인')").first
                if confirm_btn.is_visible(timeout=1500):
                    confirm_btn.click()
                else:
                    inp.press("Enter")
                
                time.sleep(0.8)
                existing_names.append(cat_name)
                added_count += 1
                print(f"     ✅ '{cat_name}' 등록 완료")
            else:
                print(f"     ❌ '{cat_name}' 입력창을 찾지 못했습니다.")

        print(f"\n총 {added_count}개의 새로운 카테고리가 추가되었습니다.")

        if added_count > 0:
            print("💾 변경사항 저장 중...")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)

            save_btn = page.locator("button:has-text('변경사항 저장'), .btn_save").first
            if save_btn.is_visible(timeout=3000):
                save_btn.click()
                time.sleep(3)
                print("🎉 카테고리 변경사항이 티스토리에 성공적으로 저장되었습니다!")
            else:
                print("⚠️ 저장 버튼을 찾지 못했습니다.")

        time.sleep(2)
        final_shot = SCREENSHOT_DIR / "categories_setup_complete.png"
        page.screenshot(path=str(final_shot))
        print(f"📸 최종 카테고리 설정 캡처: {final_shot}\n")

        ctx.close()
        return True

if __name__ == "__main__":
    setup_categories()
