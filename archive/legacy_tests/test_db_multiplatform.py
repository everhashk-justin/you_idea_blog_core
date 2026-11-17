"""
test_db_multiplatform.py - 멀티 플랫폼(dev, tistory, naver, gear, stock) DB 스키마 및 연동 통합 검증 테스트
"""

import sys
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import db
import check_analytics
import manage_db


def test_multiplatform_db():
    print("=== [1. DB 연결 및 스키마 검증] ===")
    with db.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_key_check;")
        fk_errors = cursor.fetchall()
        assert len(fk_errors) == 0, f"외래키 제약조건 위반 발견: {fk_errors}"
        print("  ✅ 외래키 무결성 100% 검증 완료 (위반 0건)")

        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='blog_posts'")
        schema_sql = cursor.fetchone()[0]
        assert "blog_id" in schema_sql, "blog_id 컬럼 부재"
        assert "'naver'" in schema_sql, "naver 플랫폼 CHECK 제약조건 부재"
        assert "'gear'" in schema_sql, "gear 플랫폼 CHECK 제약조건 부재"
        assert "'stock'" in schema_sql, "stock 플랫폼 CHECK 제약조건 부재"
        print("  ✅ blog_posts 테이블 스키마에 naver, gear, stock, blog_id 완벽 반영 확인")

    print("\n=== [2. 플랫폼 및 블로그별 콘텐츠 적재 카운트 검증] ===")
    summary = db.get_stats_summary()
    print(f"  • 총 관리 콘텐츠: {summary['total_posts']}편")
    print(f"  • 플랫폼별: {summary['by_platform']}")
    print(f"  • 블로그별: {summary['by_blog']}")
    
    # 96편 기존 포스트 보존 검증
    dev_posts = db.list_posts(platform="dev")
    tistory_posts = db.list_posts(platform="tistory")
    naver_posts = db.list_posts(platform="naver")
    gear_posts = db.list_posts(platform="gear")
    stock_posts = db.list_posts(platform="stock")

    assert len(tistory_posts) >= 81, f"티스토리 포스트 수 부족: {len(tistory_posts)}"
    assert len(db.list_posts(platform="tistory", status="PUBLISHED")) == 81, "티스토리 발행 포스트 수 불일치"
    assert len(dev_posts) >= 15, f"개발 블로그 포스트 수 부족: {len(dev_posts)}"
    assert len(naver_posts) >= 3, f"네이버 포스트 수 부족: {len(naver_posts)}"
    assert len(gear_posts) >= 7, f"기어 포스트 수 부족: {len(gear_posts)}"
    assert len(stock_posts) >= 2, f"증시 포스트 수 부족: {len(stock_posts)}"
    print("  ✅ 기존 96편(티스토리 81편 + dev 15편) 및 신규 플랫폼 포스트 전수 보존 확인")

    print("\n=== [3. 네이버 3대 블로그 등록 상태 검증] ===")
    for np in naver_posts:
        print(f"  • [{np['blog_id'].upper()}] ID={np['id']} | status={np['status']} | title={np['title']}")
        assert np["blog_id"] in ("solidlog", "tidynote", "infopiece", "mhsjkk"), f"비정상 블로그 ID: {np['blog_id']}"
    print("  ✅ 네이버 solidlog, tidynote, infopiece 식별자 검증 완료")

    print("\n=== [4. 키워드 검색 엔진 검증] ===")
    naver_search = db.search_posts("청년월세")
    assert len(naver_search) > 0, "청년월세 검색 실패"
    print(f"  • '청년월세' 검색 결과: {len(naver_search)}건 (성공: {naver_search[0]['title'][:30]}...)")

    gear_search = db.search_posts("공액")
    assert len(gear_search) > 0, "기어 공액 검색 실패"
    print(f"  • '공액' 검색 결과: {len(gear_search)}건 (성공: {gear_search[0]['title'][:30]}...)")

    stock_search = db.search_posts("커버드콜")
    assert len(stock_search) > 0, "증시 커버드콜 검색 실패"
    print(f"  • '커버드콜' 검색 결과: {len(stock_search)}건 (성공: {stock_search[0]['title'][:30]}...)")

    # 블로그 식별자 키워드 검색 검증
    blog_search = db.search_posts("solidlog")
    assert len(blog_search) > 0, "블로그 식별자 solidlog 검색 실패"
    print(f"  • 블로그 식별자 'solidlog' 검색 결과: {len(blog_search)}건")

    print("\n=== [5. GA4 성과 지표(post_analytics) 적재 검증] ===")
    with db.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT p.platform, p.blog_id, p.title, a.pageviews, a.users, a.record_date
        FROM post_analytics a
        JOIN blog_posts p ON a.post_id = p.id
        WHERE a.source = 'GA4' AND a.record_date = (SELECT MAX(record_date) FROM post_analytics WHERE source = 'GA4')
        ORDER BY a.pageviews DESC
        """)
        rows = cursor.fetchall()
        print(f"  • 최근 기록일 성과 적재 포스트 수: {len(rows)}건")
        platforms_with_analytics = set(r["platform"] for r in rows)
        print(f"  • 성과 데이터가 적재된 플랫폼 목록: {platforms_with_analytics}")
        assert "dev" in platforms_with_analytics, "dev 성과 부재"
        assert "gear" in platforms_with_analytics, "gear 성과 부재"
        assert "stock" in platforms_with_analytics, "stock 성과 부재"
        print("  ✅ Dev, Gear, Stock 멀티 플랫폼 GA4 성과 적재 무결성 확인 완료")

    print("\n=== [6. GA4 URL 해석기(resolve_post_id) 엣지 케이스 검증] ===")
    with db.get_db() as conn:
        cursor = conn.cursor()
        # 1. 쿼리 스트링 및 일반 사이트명 타이틀인 경우
        pid_query = check_analytics.resolve_post_id(
            cursor, "H-GEAR STUDIO", "/en/part1-kinematics/01-conjugate-action/?utm_source=twitter&utm_medium=social"
        )
        assert pid_query == 101, f"쿼리 스트링 URL 매칭 실패: {pid_query}"
        print(f"  • 쿼리 스트링 URL 매칭: 성공 (post_id={pid_query})")

        # 2. 티스토리 글 번호에 쿼리 스트링 및 카테고리가 붙은 경우 (/57?category=123)
        pid_tistory = check_analytics.resolve_post_id(cursor, "Softwin IT", "/57?category=123&fbclid=abc")
        assert pid_tistory is not None, "티스토리 파라미터 URL 매칭 실패"
        print(f"  • 티스토리 글 번호 파라미터 매칭: 성공 (post_id={pid_tistory})")

        # 3. 루트 /index.html 정규화
        pid_index = check_analytics.resolve_post_id(cursor, "IdeaSpot360 Dev - Practical Whitepapers", "/index.html")
        assert pid_index is not None, "/index.html 매칭 실패"
        print(f"  • /index.html 정규화 매칭: 성공 (post_id={pid_index})")

        # 4. 언어별 홈 /ko/index.html 정규화
        pid_ko_index = check_analytics.resolve_post_id(cursor, "H-GEAR STUDIO", "/ko/index.html")
        assert pid_ko_index == 104, f"/ko/index.html 매칭 실패: {pid_ko_index}"
        print(f"  • /ko/index.html 정규화 매칭: 성공 (post_id={pid_ko_index})")

        # 5. 퍼센트 인코딩 한글 URL 및 파라미터
        pid_pct = check_analytics.resolve_post_id(
            cursor, "증시 맥락 1분", "/%EA%B3%B5%EC%A7%80%EC%82%AC%ED%95%AD/2026/11/10/welcome-to-stock-ideaspot360.html?ref=1"
        )
        assert pid_pct == 107, f"퍼센트 인코딩 URL 매칭 실패: {pid_pct}"
        print(f"  • 퍼센트 인코딩 한글 URL 매칭: 성공 (post_id={pid_pct})")

    print("\n=== [7. 네이버 blog_id 자동 추론 및 upsert 검증] ===")
    test_uid = "test_naver_inference_01"
    pid_infer = db.upsert_post({
        "post_uid": test_uid,
        "platform": "naver",
        "file_path": "posts/naver_tidynote_test.txt",
        "title": "테스트 타이디노트 글",
        "status": "DRAFT"
    })
    post_fetched = db.get_post_by_id(pid_infer)
    assert post_fetched["blog_id"] == "tidynote", f"blog_id 추론 실패: {post_fetched['blog_id']}"
    print(f"  • naver_tidynote 경로 기반 blog_id='tidynote' 자동 산출: 성공 (post_id={pid_infer})")

    # 정리
    with db.get_db() as conn:
        conn.execute("DELETE FROM blog_posts WHERE post_uid = ?", (test_uid,))
    print("  • 테스트 레코드 정상 정리 완료")

    print("\n=== [8. manage_db CLI 필터링 연동 검증] ===")
    # --platform 단독 필터 동작 확인
    gear_list = db.list_posts(platform="gear")
    assert len(gear_list) >= 7, f"gear 플랫폼 필터 결과 불일치: {len(gear_list)}"
    stock_list = db.list_posts(platform="stock")
    assert len(stock_list) >= 2, f"stock 플랫폼 필터 결과 불일치: {len(stock_list)}"
    solidlog_list = db.list_posts(blog_id="solidlog")
    assert len(solidlog_list) >= 1, f"solidlog 블로그ID 필터 결과 불일치: {len(solidlog_list)}"
    print("  • manage_db 플랫폼 및 블로그ID 필터 데이터셋 검증 완료")

    print("\n=== [9. 동일 프로퍼티 내 다중 URL 지표 사전 합산 검증] ===")
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")
    mock_pages = [
        ("Chapter 1 Contact Kinematics", "/en/part1-kinematics/01-conjugate-action/", 5, 4),
        ("Chapter 1 Contact Kinematics", "/en/part1-kinematics/01-conjugate-action/?utm_source=test", 3, 2),
    ]
    check_analytics.save_analytics_to_db(mock_pages, "테스트 프로퍼티")
    with db.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT pageviews, users FROM post_analytics WHERE post_id = 101 AND record_date = ?", (today_str,))
        row = cursor.fetchone()
        assert row is not None, "mock 적재 실패"
        assert row["pageviews"] >= 8, f"합산 페이지뷰 불일치 (기대값>=8): {row['pageviews']}"
        print(f"  • 동일 포스트 다중 URL 합산 확인: pageviews={row['pageviews']} (최소 5+3=8 검증 성공)")

        # mock 적재 데이터 격리 정리
        conn.execute("DELETE FROM post_analytics WHERE source = '테스트 프로퍼티' OR (post_id = 101 AND record_date = ?)", (today_str,))
        print("  • mock 성과 데이터 정리 완료")

    print("\n🎉 모든 단위, 통합 및 엣지 케이스 검증 테스트 100% 통과!")


if __name__ == "__main__":
    test_multiplatform_db()
