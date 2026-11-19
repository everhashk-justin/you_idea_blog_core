# -*- coding: utf-8 -*-
"""
tests.test_reservation_guard - Unit tests for Gate 9 (Reservation Integrity & Anti-Bot Jitter)
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from blog_core.engine.gatekeeper import IroncladGatekeeper
from blog_core.engine.models import Severity


class TestReservationGuardGate9(unittest.TestCase):
    """코어 엔진 Gate 9 예약 무결성 및 안티봇 지터 규칙 단위 테스트 스위트"""

    def setUp(self):
        self.gatekeeper = IroncladGatekeeper()
        self.temp_dir = Path(tempfile.mkdtemp(prefix="gate9_test_"))
        self.fixed_now = datetime(2026, 11, 20, 10, 0, 0)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_temp(self, filename: str, content: str) -> Path:
        p = self.temp_dir / filename
        p.write_text(content, encoding="utf-8")
        return p

    def test_immediate_post_skips_gate_9(self):
        """일반 즉시공개 글은 예약 검사를 안전하게 건너뜀 (0건 위반)"""
        md = """---
title: "Immediate Publication Test Post"
category: "Cloud & DevOps"
tags: [devops, cloud]
---
# Content here
"""
        p = self._write_temp("immediate.md", md)
        rep = self.gatekeeper.verify(str(p), platform="dev", now_dt=self.fixed_now)
        g9_viols = [v for v in rep.violations if v.gate_id == "GATE_9"]
        self.assertEqual(len(g9_viols), 0)
        self.assertFalse(rep.is_reserved)

    def test_valid_jittered_scheduled_post_passes(self):
        """지터(예: 18:24)가 적용된 정상 미래 예약은 Gate 9 통과"""
        md = """---
title: "Valid Scheduled Post"
category: "백엔드 & 서버 아키텍처"
tags: [backend, java]
publish_type: scheduled
reserve_at: "2026-11-20 18:24"
---
# Content
"""
        p = self._write_temp("valid_res.md", md)
        rep = self.gatekeeper.verify(str(p), platform="tistory", now_dt=self.fixed_now)
        g9_viols = [v for v in rep.violations if v.gate_id == "GATE_9"]
        self.assertEqual(len(g9_viols), 0)
        self.assertTrue(rep.is_reserved)
        self.assertEqual(rep.reserve_date, "2026-11-20")
        self.assertEqual(rep.reserve_time, "18:24")

    def test_zero_minute_collision_rejected(self):
        """00분 정각 예약은 봇 피드 충돌 방지를 위해 차단"""
        md = """---
title: "Zero Minute Collision Post"
category: "백엔드 & 서버 아키텍처"
publish_type: scheduled
reserve_at: "2026-11-20 18:00"
---
# Content
"""
        p = self._write_temp("zero_min.md", md)
        rep = self.gatekeeper.verify(str(p), platform="tistory", now_dt=self.fixed_now)
        self.assertFalse(rep.is_passed)
        self.assertTrue(any(v.rule_id == "G9_RESERVATION_BOT_COLLISION_MINUTE" for v in rep.violations))

    def test_past_time_reservation_rejected(self):
        """과거 시점 예약은 즉각 차단"""
        md = """---
title: "Past Time Reservation Post"
category: "백엔드 & 서버 아키텍처"
publish_type: scheduled
reserve_at: "2026-11-19 18:24"
---
# Content
"""
        p = self._write_temp("past_res.md", md)
        rep = self.gatekeeper.verify(str(p), platform="tistory", now_dt=self.fixed_now)
        self.assertFalse(rep.is_passed)
        self.assertTrue(any(v.rule_id == "G9_RESERVATION_PAST_TIME" for v in rep.violations))

    def test_insufficient_buffer_rejected(self):
        """현재 시각 대비 10분 미만 임박 예약은 차단"""
        close_time = (self.fixed_now + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")
        md = f"""---
title: "Close Time Reservation Post"
category: "백엔드 & 서버 아키텍처"
publish_type: scheduled
reserve_at: "{close_time}"
---
# Content
"""
        p = self._write_temp("close_res.md", md)
        rep = self.gatekeeper.verify(str(p), platform="tistory", now_dt=self.fixed_now)
        self.assertFalse(rep.is_passed)
        self.assertTrue(any(v.rule_id == "G9_RESERVATION_BUFFER_UNDERFLOW" for v in rep.violations))

    def test_dev_blog_missing_seconds_rejected(self):
        """개발 블로그에서 초 단위 지터가 생략된 경우 안티봇 초 지터 헌법 위반 차단"""
        md = """---
title: "Dev Blog Missing Seconds"
category: "Cloud & DevOps"
tags: [k8s, devops]
date: 2026-11-20 18:24 +0900
publish_type: scheduled
---
# Content
"""
        p = self._write_temp("dev_missing_sec.md", md)
        rep = self.gatekeeper.verify(str(p), platform="dev", now_dt=self.fixed_now)
        self.assertFalse(rep.is_passed)
        self.assertTrue(any(v.rule_id == "G9_RESERVATION_BOT_COLLISION_SECOND" for v in rep.violations))

    def test_dev_blog_zero_seconds_rejected(self):
        """개발 블로그에서 00초 정각 예약 차단"""
        md = """---
title: "Dev Blog Zero Seconds"
category: "Cloud & DevOps"
tags: [k8s, devops]
date: 2026-11-20 18:24:00 +0900
publish_type: scheduled
---
# Content
"""
        p = self._write_temp("dev_zero_sec.md", md)
        rep = self.gatekeeper.verify(str(p), platform="dev", now_dt=self.fixed_now)
        self.assertFalse(rep.is_passed)
        self.assertTrue(any(v.rule_id == "G9_RESERVATION_BOT_COLLISION_SECOND" for v in rep.violations))

    def test_dev_blog_valid_random_seconds_passes(self):
        """개발 블로그에서 43초 랜덤 지터 적용 시 Gate 9 통과"""
        md = """---
title: "Dev Blog Valid Seconds"
category: "Cloud & DevOps"
tags: [k8s, devops]
date: 2026-11-20 18:24:43 +0900
publish_type: scheduled
---
# Content
"""
        p = self._write_temp("dev_valid_sec.md", md)
        rep = self.gatekeeper.verify(str(p), platform="dev", now_dt=self.fixed_now)
        g9_viols = [v for v in rep.violations if v.gate_id == "GATE_9"]
        self.assertEqual(len(g9_viols), 0)
        self.assertTrue(rep.is_reserved)

    def test_platform_keyword_argument_compatibility(self):
        """IroncladGatekeeper.verify() 및 evaluate_file()에 platform 키워드 인자 전달 시 예외 없이 정상 동작"""
        md = """---
title: "Platform Kwarg Test"
category: "컴퓨터 과학 핵심 기초"
tags: [cs, test]
visibility: public
---
# Content
"""
        p = self._write_temp("platform_kwarg.md", md)
        rep1 = self.gatekeeper.verify(str(p), platform="tistory")
        self.assertEqual(rep1.platform, "tistory")

        rep2 = self.gatekeeper.evaluate_file(str(p), platform="tistory")
        self.assertEqual(rep2.platform, "tistory")


if __name__ == "__main__":
    unittest.main()
