"""
test_live_status.py - 블로그 생태계 실시간 라이브 발행 상태 실측 및 동기화 도구 검증 테스트
"""

import sys
import unittest
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import db
import check_live_status


class TestLiveStatusParsers(unittest.TestCase):
    """라이브 피드 파서 단위 테스트"""

    def test_parse_rfc822_date(self):
        # 표준 RFC 822 날짜 포맷 변환
        raw = "Sun, 15 Nov 2026 01:38:36 +0900"
        formatted = check_live_status.parse_rfc822_date(raw)
        self.assertEqual(formatted, "2026-11-15 01:38:36")

        # 빈 문자열 처리
        self.assertEqual(check_live_status.parse_rfc822_date(""), "")

        # 비정상 포맷 fallback
        self.assertEqual(check_live_status.parse_rfc822_date("invalid-date-string"), "invalid-date-string")

    def test_parse_sitemap_xml(self):
        sample_sitemap = b"""<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://dev.ideaspot360.com/devops/nginx/2026/11/15/nginx-502-bad-gateway.html</loc>
                <lastmod>2026-11-15T10:00:00+09:00</lastmod>
            </url>
            <url>
                <loc>https://dev.ideaspot360.com/about.html</loc>
            </url>
        </urlset>
        """
        urls = check_live_status.parse_sitemap_xml(sample_sitemap)
        self.assertEqual(len(urls), 2)
        self.assertEqual(urls[0]["url"], "https://dev.ideaspot360.com/devops/nginx/2026/11/15/nginx-502-bad-gateway.html")
        self.assertEqual(urls[0]["lastmod"], "2026-11-15T10:00:00+09:00")
        self.assertEqual(urls[1]["url"], "https://dev.ideaspot360.com/about.html")
        self.assertIsNone(urls[1]["lastmod"])

        # 파싱 오류 및 빈 바이트 안전 처리
        self.assertEqual(check_live_status.parse_sitemap_xml(b""), [])
        self.assertEqual(check_live_status.parse_sitemap_xml(b"<invalid xml"), [])

    def test_parse_rss_xml(self):
        sample_rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>인포피스</title>
                <item>
                    <title><![CDATA[영양제 식전 식후 복용 시간표]]></title>
                    <link>https://blog.naver.com/infopiece/224477408706?fromRss=true&amp;trackingCode=rss</link>
                    <pubDate>Sun, 15 Nov 2026 01:38:36 +0900</pubDate>
                </item>
            </channel>
        </rss>
        """.encode("utf-8")
        items = check_live_status.parse_rss_xml(sample_rss)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "영양제 식전 식후 복용 시간표")
        # ?fromRss=true 파라미터가 정리된 순수 URL 검증
        self.assertEqual(items[0]["link"], "https://blog.naver.com/infopiece/224477408706")
        self.assertEqual(items[0]["pub_date"], "2026-11-15 01:38:36")

        # 빈 바이트 및 에러 안전 처리
        self.assertEqual(check_live_status.parse_rss_xml(b""), [])
        self.assertEqual(check_live_status.parse_rss_xml(b"<broken"), [])


class TestLiveStatusIntegration(unittest.TestCase):
    """라이브 실측 및 DB 동기화 통합 테스트"""

    def test_live_network_endpoints_reachability(self):
        """실제 외부 8대 엔드포인트의 200 OK 응답 및 초고속성 검증"""
        results = check_live_status.fetch_all_live_data(timeout=10)
        self.assertEqual(len(results), 8, "8개 라이브 엔드포인트 전수 호출 실패")
        for key, res in results.items():
            self.assertEqual(
                res["status_code"], 200,
                f"엔드포인트 '{key}' ({res['config']['url']}) 응답 실패: code={res['status_code']}, err={res['error']}"
            )
            self.assertIsNotNone(res["content"], f"엔드포인트 '{key}' 본문 부재")
            self.assertGreater(len(res["content"]), 0, f"엔드포인트 '{key}' 본문 비어있음")

    def test_infopiece_and_naver_published_in_db(self):
        """인포피스 및 네이버 전문 블로그 포스트의 DB PUBLISHED 상태 및 실측 URL 무결성 검증"""
        infopiece_post = db.get_post_by_uid("naver_infopiece_01")
        self.assertIsNotNone(infopiece_post, "인포피스 1호 포스트 DB 레코드 부재")
        self.assertEqual(infopiece_post["status"], "PUBLISHED", "인포피스 1호가 PUBLISHED 상태가 아님")
        self.assertEqual(infopiece_post["blog_id"], "infopiece", "인포피스 blog_id 불일치")
        self.assertTrue(
            infopiece_post["url"].startswith("https://blog.naver.com/infopiece/"),
            f"인포피스 실제 라이브 글 번호 URL 부재: {infopiece_post['url']}"
        )
        self.assertIsNotNone(infopiece_post["published_at"], "인포피스 발행일시 누락")

        # 솔리드로그 2호 청년도약계좌 검증
        solidlog_post = db.get_post_by_file("posts/naver_solidlog_02_youth_leap.md")
        self.assertIsNotNone(solidlog_post, "솔리드로그 2호 레코드 부재")
        self.assertEqual(solidlog_post["status"], "PUBLISHED", "솔리드로그 2호가 PUBLISHED 상태가 아님")
        self.assertTrue(
            solidlog_post["url"].startswith("https://blog.naver.com/solidlog/"),
            f"솔리드로그 실제 라이브 URL 부재: {solidlog_post['url']}"
        )

        # 타이디노트 1호 생산성툴 검증
        tidynote_post = db.get_post_by_file("posts/naver_tidynote_01_productivity_tools.md")
        self.assertIsNotNone(tidynote_post, "타이디노트 1호 레코드 부재")
        self.assertEqual(tidynote_post["status"], "PUBLISHED", "타이디노트 1호가 PUBLISHED 상태가 아님")

    def test_dev_blog_15_live_and_7_reserved(self):
        """글로벌 개발 블로그 실측 15편 PUBLISHED + 7편 RESERVED 분할 무결성 검증"""
        dev_posts = db.list_posts(platform="dev", track="TRACK_1")
        tech_posts = [p for p in dev_posts if str(p["file_path"]).startswith("blogs/dev/_posts/")]
        published = [p for p in tech_posts if p["status"] == "PUBLISHED"]
        reserved = [p for p in tech_posts if p["status"] == "RESERVED"]

        self.assertEqual(len(tech_posts), 22, f"개발 블로그 기술 백서 총 수 불일치: {len(tech_posts)}")
        self.assertEqual(len(published), 15, f"개발 블로그 라이브 실측 발행 수 불일치: {len(published)}")
        self.assertEqual(len(reserved), 7, f"개발 블로그 예약 수 불일치: {len(reserved)}")

    def test_tistory_81_published_and_14_reserved(self):
        """티스토리 81편 PUBLISHED + 14편 RESERVED 무결성 검증"""
        tistory_pub = db.list_posts(platform="tistory", status="PUBLISHED")
        tistory_res = db.list_posts(platform="tistory", status="RESERVED")
        self.assertEqual(len(tistory_pub), 81, f"티스토리 발행 수 불일치: {len(tistory_pub)}")
        self.assertEqual(len(tistory_res), 14, f"티스토리 예약 수 불일치: {len(tistory_res)}")

    def test_evaluate_sync_status(self):
        """동기화 상태 판정 로직 단위 테스트"""
        # 정상 100% 일치
        self.assertEqual(check_live_status.evaluate_sync_status(10, 10), "🟢 100% 일치")
        # 동기화 액션 완료 후 일치
        self.assertEqual(check_live_status.evaluate_sync_status(10, 10, has_sync_actions=True), "🟡 실측 동기화 완료")
        # 편수 불일치
        self.assertEqual(check_live_status.evaluate_sync_status(9, 10), "⚠️ 불일치 (9편 vs 10편)")
        # 미해결 차이 존재
        self.assertEqual(check_live_status.evaluate_sync_status(10, 10, has_unresolved_diff=True), "⚠️ 불일치 (10편 vs 10편)")
        # 에러 발생 시
        self.assertEqual(check_live_status.evaluate_sync_status(0, 10, is_error=True), "❌ 실측/연결 실패")

    def test_analyze_live_status_full_sync(self):
        """전체 실측 분석 결과 대시보드 데이터 구조 및 동기화 상태 검증"""
        results = check_live_status.fetch_all_live_data(timeout=10)
        report = check_live_status.analyze_live_status(results, apply_sync=True)

        self.assertIn("blogs", report)
        self.assertIn("softwin", report["blogs"])
        self.assertIn("dev", report["blogs"])
        self.assertIn("solidlog", report["blogs"])
        self.assertIn("tidynote", report["blogs"])
        self.assertIn("infopiece", report["blogs"])
        self.assertIn("gear", report["blogs"])
        self.assertIn("stock", report["blogs"])

        # 모든 블로그가 100% 일치 상태여야 하며, live_count == db_published_count 검증
        for b_id, b_data in report["blogs"].items():
            self.assertIn("일치", b_data["sync_status"], f"{b_id} 동기화 상태 비정상: {b_data['sync_status']}")
            self.assertEqual(
                b_data["live_count"], b_data["db_published_count"],
                f"{b_id} 라이브 수({b_data['live_count']})와 DB 발행 수({b_data['db_published_count']}) 불일치"
            )
            self.assertGreater(b_data["live_count"], 0, f"{b_id} 라이브 카운트 0")
            self.assertGreater(b_data["db_published_count"], 0, f"{b_id} DB 발행 카운트 0")

    def test_stock_and_gear_precise_counts(self):
        """증시 9편(창원개미 포함) 및 기어 10편 정밀 실측 매칭 검증"""
        stock_posts = [p for p in db.list_posts(platform="stock", status="PUBLISHED")
                       if p["post_uid"] != "stock_home" and p["post_uid"] != "stock_2026-11-10-welcome-to-stock-id"]
        self.assertEqual(len(stock_posts), 9, f"증시 실제 발행 포스트 수 불일치: {len(stock_posts)}")
        changwon = [p for p in stock_posts if "changwon" in p["slug"]]
        self.assertEqual(len(changwon), 1, "창원개미 10일선 포스트 DB 부재")

        gear_posts = db.list_posts(platform="gear", status="PUBLISHED")
        self.assertEqual(len(gear_posts), 10, f"기어 실제 발행 포스트 수 불일치: {len(gear_posts)}")

    def test_tistory_rss_real_urls_sync(self):
        """티스토리 최신 포스트의 실측 라이브 URL 매핑 검증"""
        latest_tistory = db.get_post_by_file("posts/81_cloud_linux_cgroups_namespaces_container.md")
        self.assertIsNotNone(latest_tistory)
        self.assertEqual(latest_tistory["url"], "https://softwin.tistory.com/140", f"티스토리 81호 실제 URL 불일치: {latest_tistory['url']}")


if __name__ == "__main__":
    unittest.main()
