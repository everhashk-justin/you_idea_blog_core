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
p_dir = BASE_DIR / "browser_profile"
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(user_data_dir=str(p_dir), headless=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    
    # 알림창 자동 승인 (삭제 확인 팝업)
    page.on("dialog", lambda dialog: dialog.accept())
    
    posts_url = "https://softwin.tistory.com/manage/posts/"
    print(f"🌐 글 관리 페이지 접속 중: {posts_url}")
    page.goto(posts_url, wait_until="networkidle", timeout=30000)
    time.sleep(2)

    # 자동 로그인 필요 여부 확인
    if "login" in page.url or "auth" in page.url:
        print("🔄 자동 로그인 진행 중...")
        login_btn = page.locator(".btn_login").first
        if login_btn.is_visible(timeout=3000):
            login_btn.click()
            page.wait_for_load_state("networkidle")
            time.sleep(1)
        profile_item = page.locator(".wrap_profile").first
        if profile_item.is_visible(timeout=3000):
            profile_item.click()
            page.wait_for_load_state("networkidle")
            time.sleep(2)
        page.goto(posts_url, wait_until="networkidle", timeout=30000)
        time.sleep(2)

    print(f"현재 페이지: {page.url}")

    # 최상단 글 찾기
    target_text = "[웹 기술의 본질] 쿠키와 세션의 모든 것"
    
    # 1. 대상 글의 체크박스를 선택하거나 행의 삭제 버튼 찾기
    rows = page.locator("ul.list_post > li, tr, div.item_post, li").all()
    deleted = False

    # 방법 A: 최상단 글 링크 주변의 삭제 버튼
    # 글 제목 요소 찾기
    title_el = page.locator(f"text={target_text}").first
    if title_el.is_visible(timeout=5000):
        print("🎯 대상 글 확인 완료!")
        # 해당 글이 속한 컨테이너(li 또는 tr) 찾기
        container = title_el.locator("xpath=./ancestor::li | ./ancestor::tr").first
        
        # 행에 마우스 호버하여 버튼 노출
        container.hover()
        time.sleep(1)
        
        # 삭제 버튼 클릭 시도
        del_btn = container.locator("button:has-text('삭제'), a:has-text('삭제')").first
        if del_btn.is_visible(timeout=2000):
            print("🗑️  삭제 버튼 클릭...")
            del_btn.click()
            time.sleep(3)
            deleted = True
        else:
            # 방법 B: 체크박스 체크 후 상단 일괄 삭제
            print("체크박스 선택 후 상단 메뉴로 삭제 시도...")
            chk = container.locator("input[type='checkbox']").first
            chk.check()
            time.sleep(1)
            
            # 상단 변경 드롭다운 클릭
            change_btn = page.locator("button:has-text('변경'), .btn_change").first
            change_btn.click()
            time.sleep(1)
            
            # 삭제 메뉴 클릭
            del_menu = page.locator("button:has-text('삭제'), a:has-text('삭제')").first
            del_menu.click()
            time.sleep(3)
            deleted = True

    page.screenshot(path=str(BASE_DIR / "screenshots" / "after_delete.png"))
    
    if deleted:
        print("✅ 글이 성공적으로 삭제되었습니다!")
    else:
        print("⚠️ 대상 글을 찾지 못했거나 삭제에 실패했습니다.")

    ctx.close()
