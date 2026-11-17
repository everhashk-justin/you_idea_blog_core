import sys
import os
import json
import time
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent

def check_and_cleanup():
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(BASE_DIR / "browser_profile"),
            headless=True,
            viewport={"width": 1280, "height": 900}
        )
        page = context.pages[0] if context.pages else context.new_page()

        print("1. 글 관리 페이지로 이동...")
        page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle", timeout=30000)
        time.sleep(2)

        if "login" in page.url or "auth" in page.url:
            print("로그인 진행...")
            login_btn = page.locator(".btn_login, a:has-text('카카오계정으로 로그인')").first
            if login_btn.is_visible(timeout=3000):
                login_btn.click()
                time.sleep(2)
            profile_card = page.locator(".wrap_profile, .list_account li").first
            if profile_card.is_visible(timeout=5000):
                profile_card.click()
                page.wait_for_url(lambda u: "login" not in u and "auth" not in u, timeout=20000)
            page.goto("https://softwin.tistory.com/manage/posts", wait_until="networkidle")
            time.sleep(2)

        page.screenshot(path=str(BASE_DIR / "screenshots" / "manage_posts_list.png"))

        # 글 목록 파싱
        posts_data = page.evaluate("""() => {
            const list = [];
            const rows = document.querySelectorAll('.tbl_board tbody tr, ul.list_board li');
            rows.forEach(r => {
                const titleEl = r.querySelector('.tit_post, .txt_title, a[href*="/manage/newpost"]');
                const linkEl = r.querySelector('a[href*="/manage/newpost"]');
                const viewEl = r.querySelector('a[href*="softwin.tistory.com/"]');
                const dateEl = r.querySelector('.txt_date, .date');
                const categoryEl = r.querySelector('.txt_cate, .cate');
                list.push({
                    title: titleEl ? titleEl.innerText.trim() : "",
                    editUrl: linkEl ? linkEl.getAttribute('href') : "",
                    viewUrl: viewEl ? viewEl.getAttribute('href') : "",
                    date: dateEl ? dateEl.innerText.trim() : "",
                    category: categoryEl ? categoryEl.innerText.trim() : "",
                    raw: r.innerText.replace(/\\s+/g, ' ').trim()
                });
            });
            return list;
        }""")

        print(f"\n총 {len(posts_data)}개의 글을 확인했습니다.")
        for idx, p in enumerate(posts_data[:5]):
            print(f"[{idx+1}] {p['title']} | 카테고리: {p['category']} | 날짜: {p['date']} | 수정링크: {p['editUrl']}")

        # 만약 '내용 없는 글'(02:04경 발행된 글)과 '새로 발행된 글'(02:07 발행된 글)이 둘 다 있다면 확인
        # 첫 번째 글(최신 글)의 상세 뷰 또는 수정 페이지 확인
        if posts_data:
            latest = posts_data[0]
            print(f"\n최신 글 '{latest['title']}' 내용 검증 중...")
            if latest['editUrl']:
                target_url = "https://softwin.tistory.com" + latest['editUrl'] if not latest['editUrl'].startswith("http") else latest['editUrl']
                page.goto(target_url, wait_until="networkidle", timeout=30000)
                time.sleep(3)
                page.screenshot(path=str(BASE_DIR / "screenshots" / "latest_post_editor.png"))

                # TinyMCE 내용 가져오기
                content_info = page.evaluate("""() => {
                    let text = "";
                    let html = "";
                    if (window.tinymce && window.tinymce.activeEditor) {
                        text = window.tinymce.activeEditor.getContent({format: 'text'});
                        html = window.tinymce.activeEditor.getContent();
                    }
                    return { textLength: text.length, htmlLength: html.length, snippet: text.substring(0, 150) };
                }""")
                print(f"✅ 최신 글 본문 텍스트 길이: {content_info['textLength']}자, HTML 길이: {content_info['htmlLength']}자")
                print(f"미리보기: {content_info['snippet']}...")

        context.close()

if __name__ == "__main__":
    check_and_cleanup()
