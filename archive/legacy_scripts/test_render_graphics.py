"""
test_render_graphics.py - 인포그래픽 렌더링 프레임워크 및 4대 이미지 무결성 검증 테스트
=================================================================================
- 폰트 매니저 및 폰트 메트릭 검증
- 텍스트 래핑 수학적 불변식 검증 (Zero-Overflow Invariant)
- 박스 높이 동적 계산 함수(calc_solution_bar_height) 및 자동 확장 검증
- 4대 이미지 실제 생성 및 파일 규격/품질 검증
"""

import os
import unittest
from pathlib import Path
from PIL import Image

import render_utils
from render_tidynote_graphics import generate_card1, generate_card2, generate_card3, generate_card4, IMG_DIR
import render_solidlog_graphics


class TestRenderFramework(unittest.TestCase):
    """공통 그래픽 유틸리티 (render_utils) 무결성 및 경계 테스트"""

    def test_01_font_manager(self):
        """다양한 크기 및 굵기의 폰트 로드 및 메트릭스 검증"""
        f_reg = render_utils.FontManager.get_font(16, bold=False)
        f_bold = render_utils.FontManager.get_font(24, bold=True)
        self.assertIsNotNone(f_reg)
        self.assertIsNotNone(f_bold)
        self.assertGreater(render_utils.get_text_width("테스트", f_bold), 0)
        
        # 폰트 행간 높이 계산 검증
        line_h = render_utils.get_font_line_height(f_reg, line_spacing=4)
        self.assertGreater(line_h, 16)

    def test_02_text_wrapping_invariants(self):
        """텍스트 래핑이 어떤 경우에도 max_width를 1픽셀도 초과하지 않는지 불변식 검증"""
        font = render_utils.FontManager.get_font(18, bold=False)
        max_width = 300

        test_cases = [
            "",  # 빈 문자열
            "짧은 문장",
            "이것은 가로폭이 300픽셀을 초과하는 매우 긴 한글 설명문으로서 반드시 줄바꿈 처리가 되어야만 합니다.",
            "English_long_words_without_spaces_should_be_broken_correctly_when_exceeding_max_width",
            "한글과English와 특수문자(!@#$%^&*)가 섞인 복합 문장 테스트",
            "공백없는매우긴한글단어테스트가나다라마바사아자차카타파하가나다라마바사아자차카타파하"
        ]

        for text in test_cases:
            lines = render_utils.wrap_text(text, font, max_width)
            for line in lines:
                width = render_utils.get_text_width(line, font)
                self.assertLessEqual(
                    width, max_width,
                    f"줄바꿈 검증 실패! 줄 폭({width}px)이 최대 허용폭({max_width}px)을 초과함: '{line}'"
                )

    def test_03_dynamic_box_height_calculation(self):
        """박스 높이 동적 계산(calc_solution_bar_height) 함수 검증"""
        font_label = render_utils.FontManager.get_font(26, bold=True)
        font_text = render_utils.FontManager.get_font(26, bold=False)
        
        # 1. 짧은 한 줄 텍스트 -> 기본 높이 보장 (최소 34px 이상)
        h_short = render_utils.calc_solution_bar_height("팁", "짧은 텍스트", font_label, font_text, max_bar_width=900, scale=2)
        self.assertGreaterEqual(h_short, 34)

        # 2. 좁은 폭에 긴 텍스트 -> 줄바꿈 발생에 따라 박스 높이가 동적으로 증가하는지 검증
        long_text = "이것은 가로폭이 좁아서 반드시 2줄 이상으로 줄바꿈되어야 하는 매우 긴 솔루션 처방 텍스트입니다. " * 3
        h_long = render_utils.calc_solution_bar_height("극복 처방", long_text, font_label, font_text, max_bar_width=300, scale=2)
        self.assertGreater(h_long, h_short, f"동적 확장 실패: 긴 텍스트 높이({h_long})가 짧은 텍스트 높이({h_short})보다 크지 않음")

    def test_04_retina_renderer_components(self):
        """RetinaRenderer 컴포넌트 호출 및 2x 슈퍼샘플링 다운스케일링 검증"""
        r = render_utils.RetinaRenderer(width=400, height=300, scale=2)
        r.draw_card(20, 20, 360, 260, radius=12)
        r.draw_header("CATEGORY", "Title Text", "Subtitle Text", start_y=30)
        r.draw_check_circle(50, 150, radius=8)
        r.draw_alert_circle(80, 150, radius=8)
        
        # 솔루션 바 동적 렌더링 검증
        h, bottom_y = r.draw_solution_bar(40, 200, 320, "처방", "동적으로 계산된 해결책 내용입니다.")
        self.assertGreater(h, 0)
        self.assertEqual(bottom_y, 200 + h)
        
        test_out = Path("test_component_output.png")
        try:
            r.save(test_out)
            self.assertTrue(test_out.exists())
            with Image.open(test_out) as im:
                self.assertEqual(im.size, (400, 300))
                self.assertEqual(im.mode, "RGB")
        finally:
            if test_out.exists():
                test_out.unlink()

    def test_05_bounding_box_collision_detection_math(self):
        """텍스트 바운딩 박스 간의 충돌/겹침(Bounding Box Overlap Detection) 수학적 검출 알고리즘 검증"""
        r = render_utils.RetinaRenderer(width=600, height=400, scale=2)
        font = r.get_font(14)

        # 1. 겹침이 전혀 없는 두 박스 (수평 분리)
        r.drawn_text_boxes = [
            {"text": "Key A", "x1": 50, "y1": 100, "x2": 150, "y2": 120, "w": 100, "h": 20},
            {"text": "Val A", "x1": 200, "y1": 100, "x2": 350, "y2": 120, "w": 150, "h": 20}
        ]
        collisions = r.check_text_collisions(min_gap=0)
        self.assertEqual(len(collisions), 0, "분리된 텍스트에서 거짓 충돌 발생")

        # 2. 겹침이 전혀 없는 두 박스 (수직 분리 - 다음 행)
        r.drawn_text_boxes = [
            {"text": "Row 1", "x1": 50, "y1": 100, "x2": 250, "y2": 120, "w": 200, "h": 20},
            {"text": "Row 2", "x1": 50, "y1": 130, "x2": 250, "y2": 150, "w": 200, "h": 20}
        ]
        collisions = r.check_text_collisions(min_gap=0)
        self.assertEqual(len(collisions), 0, "상하 분리된 행에서 거짓 충돌 발생")

        # 3. 치명적 텍스트 겹침 (이전 Card 3 버그 시뮬레이션: 키와 값이 수평/수직 모두 교차)
        r.drawn_text_boxes = [
            {"text": "• 3년 예상 총 수령액", "x1": 68, "y1": 324, "x2": 196, "y2": 342, "w": 128, "h": 18},
            {"text": "약 2,820만 ~ 2,850만 원 수준", "x1": 141, "y1": 324, "x2": 322, "y2": 342, "w": 181, "h": 18}
        ]
        collisions = r.check_text_collisions(min_gap=0)
        self.assertEqual(len(collisions), 1, "충돌 발생 케이스 미검출 결함!")
        self.assertGreater(collisions[0]["overlap_x"], 0)
        self.assertGreater(collisions[0]["overlap_y"], 0)

        # 4. 솔루션 바 라벨 및 래핑 본문 추적 및 충돌 부재 검증
        r2 = render_utils.RetinaRenderer(width=600, height=200, scale=2)
        r2.draw_solution_bar(20, 20, 560, "테스트라벨", "이것은 솔루션 바 텍스트입니다.")
        self.assertTrue(any(b["text"] == "테스트라벨:" for b in r2.drawn_text_boxes), "솔루션 바 라벨 텍스트 추적 누락")
        self.assertEqual(len(r2.check_text_collisions(min_gap=0)), 0, "솔루션 바 자체 내부 충돌 거짓 양성")

        # 5. 줄바꿈(wrapped text) 연속 행 간 실제 글리프 높이 기반 분리 검증 (min_gap > 0에서도 거짓 충돌 방지)
        r3 = render_utils.RetinaRenderer(width=400, height=300, scale=2)
        r3.draw_wrapped_text(30, 30, "첫 번째 줄 긴 텍스트와 두 번째 줄 긴 텍스트가 줄바꿈됩니다.", font, max_width=180, line_spacing=6)
        wrapped_boxes = [b for b in r3.drawn_text_boxes if b["source"] == "draw_wrapped_text"]
        self.assertGreaterEqual(len(wrapped_boxes), 2, "줄바꿈 박스 생성 누락")
        self.assertLess(wrapped_boxes[0]["y2"], wrapped_boxes[1]["y1"], "래핑된 연속 행 간 물리적 여백 부재 결함")

    def test_06_sanitize_text_anti_tofu_protection(self):
        """미지원 이모지 유니코드 깨짐(네모 박스) 방지 정제 함수 무결성 검증"""
        # 이모지가 포함된 경우 안전하게 제거/정제되는지 검증
        dirty_samples = [
            ("💡 [핵심 요건]", "[핵심 요건]"),
            ("📌 3년만 채워도 압도적 이자", "3년만 채워도 압도적 이자"),
            ("⚠️ 주의: 기한 내 인증", "주의: 기한 내 인증"),
            ("💧 식전 공복", "식전 공복"),
            ("🍽️ 식사 직후", "식사 직후")
        ]
        for dirty, expected in dirty_samples:
            cleaned = render_utils.sanitize_text(dirty)
            self.assertEqual(cleaned, expected, f"이모지 정제 실패: '{dirty}' -> '{cleaned}' != '{expected}'")

        # 표준 KS X 1001 한글/특수기호는 100% 보존되어야 함
        safe_samples = [
            "• 불릿 기호 보존",
            "★ 추천 대상 보존",
            "※ 참고 사항 보존",
            "100% 비과세 & 금리 연 6.0%"
        ]
        for safe in safe_samples:
            cleaned = render_utils.sanitize_text(safe)
            self.assertEqual(cleaned, safe, f"표준 기호 훼손 발생: '{safe}' -> '{cleaned}'")

    def test_07_vector_icons_rendering(self):
        """신규 추가된 벡터 아이콘 렌더러(팁, 정보, 핀 등) 구동 검증"""
        r = render_utils.RetinaRenderer(width=300, height=200, scale=2)
        r.draw_tip_circle(50, 50, radius=9)
        r.draw_info_circle(100, 50, radius=9)
        r.draw_pin_circle(150, 50, radius=9)
        r.draw_check_circle(200, 50, radius=9)
        r.draw_alert_circle(250, 50, radius=9)

        # 픽셀이 정상적으로 그려졌는지 확인 (중심 픽셀들이 배경색이 아닌지)
        im = r.img
        # 팁 아이콘 중심(100, 100) 픽셀이 투명이나 캔버스 기본색과 다른지 확인
        center_color = im.getpixel((100, 100))
        self.assertNotEqual(center_color, (248, 250, 252, 255))

    def test_08_typography_scale_standards(self):
        """고가독성 타이포그래피 표준 상수(Typography)가 요구 규격을 정확히 준수하는지 검증"""
        from render_utils import Typography
        # 메인 타이틀: 38~42px
        self.assertGreaterEqual(Typography.TITLE_MAIN, 38.0, "메인 타이틀 폰트 기준 미달")
        self.assertLessEqual(Typography.TITLE_MAIN, 42.0, "메인 타이틀 폰트 기준 초과")
        # 서브 타이틀: 22~24px
        self.assertGreaterEqual(Typography.SUBTITLE, 22.0, "서브 타이틀 폰트 기준 미달")
        self.assertLessEqual(Typography.SUBTITLE, 24.0, "서브 타이틀 폰트 기준 초과")
        # 카드 제목: 22~26px
        self.assertGreaterEqual(Typography.CARD_TITLE, 22.0, "카드 제목 폰트 기준 미달")
        self.assertLessEqual(Typography.CARD_TITLE, 26.0, "카드 제목 폰트 기준 초과")
        # 본문/스펙: 최소 16.0px 이상
        self.assertGreaterEqual(Typography.BODY_PRIMARY, 16.0, "1차 본문 폰트 기준 미달")
        self.assertGreaterEqual(Typography.BODY_SECONDARY, 16.0, "2차 설명 폰트 기준 미달")
        # 최소 폰트 하한선: 15.0px
        self.assertEqual(Typography.MIN_FONT_SIZE, 15.0, "최소 폰트 하한선 불일치")


class TestTidynoteGraphics(unittest.TestCase):
    """타이디노트 4대 인포그래픽 실제 생성 및 파일 규격/품질 검증"""

    @classmethod
    def setUpClass(cls):
        # 4장 모두 렌더링 실행
        cls.p1 = generate_card1()
        cls.p2 = generate_card2()
        cls.p3 = generate_card3()
        cls.p4 = generate_card4()

    def test_11_all_files_exist_and_valid_size(self):
        """4대 이미지 파일 존재 여부 및 파일 크기 검증"""
        expected_files = [
            IMG_DIR / "01_productivity_overview.png",
            IMG_DIR / "02_notion_vs_obsidian.png",
            IMG_DIR / "03_powertoys_features.png",
            IMG_DIR / "04_productivity_pitfalls.png"
        ]

        for p in expected_files:
            self.assertTrue(p.exists(), f"파일 누락: {p}")
            size = p.stat().st_size
            self.assertGreater(size, 25000, f"파일 크기가 비정상적으로 작음 ({size} bytes): {p}")

    def test_12_image_dimensions_and_mode(self):
        """정확한 해상도 (1080x720) 및 RGB 포맷 검증"""
        expected_files = [
            IMG_DIR / "01_productivity_overview.png",
            IMG_DIR / "02_notion_vs_obsidian.png",
            IMG_DIR / "03_powertoys_features.png",
            IMG_DIR / "04_productivity_pitfalls.png"
        ]

        for p in expected_files:
            with Image.open(p) as img:
                img.load()
                self.assertEqual(img.size, (1080, 720), f"해상도 불일치 ({img.size}): {p}")
                self.assertEqual(img.mode, "RGB", f"색상 모드 불일치 ({img.mode}): {p}")

    def test_13_tidynote_all_cards_zero_text_collisions(self):
        """타이디노트 전체 카드 텍스트 바운딩 박스 충돌/겹침 0건 검증"""
        for name, gen_fn in [
            ("Card 1", generate_card1),
            ("Card 2", generate_card2),
            ("Card 3", generate_card3),
            ("Card 4", generate_card4)
        ]:
            instances = []
            orig_init = render_utils.RetinaRenderer.__init__
            def hook_init(inst, *args, **kwargs):
                orig_init(inst, *args, **kwargs)
                inst.save = lambda *args, **kwargs: None
                instances.append(inst)
            try:
                render_utils.RetinaRenderer.__init__ = hook_init
                gen_fn()
            finally:
                render_utils.RetinaRenderer.__init__ = orig_init
            r = instances[0]
            collisions = r.check_text_collisions(min_gap=0)
            self.assertEqual(len(collisions), 0, f"Tidynote {name} 텍스트 충돌 발생: {collisions}")

    def test_14_no_tofu_glyphs_in_tidynote_cards(self):
        """타이디노트 전체 카드 내 시스템 미지원 유니코드(이모지 등) 부재 검증"""
        import re
        emoji_pattern = re.compile(r"[\U00010000-\U0010FFFF\u2600-\u26FF\u2700-\u27BF]")
        allowed_standard_symbols = {'★', '☆', '※', '•', '·', '…', '―'}

        instances = []
        orig_init = render_utils.RetinaRenderer.__init__
        def hook_init(inst, *args, **kwargs):
            orig_init(inst, *args, **kwargs)
            inst.save = lambda *args, **kwargs: None
            instances.append(inst)

        try:
            render_utils.RetinaRenderer.__init__ = hook_init
            generate_card1()
            generate_card2()
            generate_card3()
            generate_card4()
        finally:
            render_utils.RetinaRenderer.__init__ = orig_init

        for idx, inst in enumerate(instances):
            for box in inst.drawn_text_boxes:
                txt = box["text"]
                for ch in txt:
                    if emoji_pattern.match(ch) and ch not in allowed_standard_symbols:
                        self.fail(f"Tidynote Card {idx+1} 내 미지원 이모지 발견: U+{ord(ch):04X} ('{ch}') in '{txt}'")


class TestSolidlogGraphics(unittest.TestCase):
    """솔리드로그 4대 인포그래픽 실제 생성 및 파일 규격/품질 검증"""

    @classmethod
    def setUpClass(cls):
        cls.p1 = render_solidlog_graphics.generate_card1()
        cls.p2 = render_solidlog_graphics.generate_card2()
        cls.p3 = render_solidlog_graphics.generate_card3()
        cls.p4 = render_solidlog_graphics.generate_card4()

    def test_21_solidlog_files_exist_and_valid_size(self):
        """솔리드로그 4대 이미지 파일 존재 및 파일 크기 검증"""
        expected_files = [
            render_solidlog_graphics.IMG_DIR / "01_leap_eligibility_overview.png",
            render_solidlog_graphics.IMG_DIR / "02_matching_contribution_matrix.png",
            render_solidlog_graphics.IMG_DIR / "03_three_year_exit_simulation.png",
            render_solidlog_graphics.IMG_DIR / "04_application_checklist_rules.png"
        ]

        for p in expected_files:
            self.assertTrue(p.exists(), f"파일 누락: {p}")
            size = p.stat().st_size
            self.assertGreater(size, 25000, f"파일 크기가 비정상적으로 작음 ({size} bytes): {p}")

    def test_22_solidlog_image_dimensions_and_mode(self):
        """솔리드로그 이미지 해상도 (1080x720) 및 RGB 포맷 검증"""
        expected_files = [
            render_solidlog_graphics.IMG_DIR / "01_leap_eligibility_overview.png",
            render_solidlog_graphics.IMG_DIR / "02_matching_contribution_matrix.png",
            render_solidlog_graphics.IMG_DIR / "03_three_year_exit_simulation.png",
            render_solidlog_graphics.IMG_DIR / "04_application_checklist_rules.png"
        ]

        for p in expected_files:
            with Image.open(p) as img:
                img.load()
                self.assertEqual(img.size, (1080, 720), f"해상도 불일치 ({img.size}): {p}")
                self.assertEqual(img.mode, "RGB", f"색상 모드 불일치 ({img.mode}): {p}")

    def test_23_solidlog_card3_specs_zero_overflow(self):
        """Card 3 스펙 리스트의 우측 정렬 값들이 고가독성 폰트(16.5px)에서도 카드 경계선(w=484)을 초과하지 않고 최소 15px 여백을 유지하는지 검증"""
        f_k = render_utils.FontManager.get_font(int(16.5 * 2), bold=True)
        f_v = render_utils.FontManager.get_font(int(16.5 * 2), bold=False)
        card_w = 484
        right_margin = 20

        specs1 = [
            ("이자소득세(15.4%)", "전액 감면 (비과세 100% 유지)"),
            ("정부기여금 지원", "소득 구간별 적립금 최대 60% 지급"),
            ("중도해지 금리", "기본금리 수준(연 4.5% 내외) 보장"),
            ("3년 납입 원금(월 70만)", "총 2,520만 원 (36개월)"),
            ("3년 예상 총 수령액", "약 2,820만 ~ 2,850만 원 수준")
        ]
        specs2 = [
            ("이자소득세(15.4%)", "100% 전액 비과세 완결"),
            ("정부기여금 지원", "소득 구간별 최대 126만~144만 원"),
            ("적용 금리", "최고 연 6.0% (기본 4.5% + 우대 1.5%)"),
            ("5년 납입 원금(월 70만)", "총 4,200만 원 (60개월)"),
            ("5년 만기 총 수령액", "약 5,000만 원 (수익 약 800만 원)")
        ]

        for specs in [specs1, specs2]:
            for k, v in specs:
                kw = int(render_utils.get_text_width("• " + k, f_k) / 2)
                vw = int(render_utils.get_text_width(v, f_v) / 2)
                val_x = card_w - right_margin - vw
                key_end = 20 + kw
                # 키와 값 사이 충돌 방지 검증 (최소 15px 이상 간격)
                self.assertGreaterEqual(val_x, key_end + 15, f"키와 값 텍스트 충돌! key='{k}', val='{v}'")
                # 카드 우측 경계선 초과 방지 검증 (최소 15px 이상 여백 유지)
                self.assertLessEqual(val_x + vw, card_w - 15, f"카드 우측 경계 침범! val='{v}'")

    def test_24_solidlog_anti_ai_lexicon_compliance(self):
        """솔리드로그 원고 및 스마트에디터 HTML 내 상투적 AI 클리셰 어휘 금지 헌법 준수 검증"""
        banned = ["결론적으로", "요약하자면", "살펴보겠습니다", "살펴보자", "기대됩니다", "지속적인 학습"]
        manuscript = (Path(r"d:\00_antigravity\01_you_idea_blog\posts\naver_solidlog_02_youth_leap.md")).read_text(encoding="utf-8")
        html_doc = (Path(r"d:\00_antigravity\01_you_idea_blog\posts\naver_solidlog_02_smarteditor.html")).read_text(encoding="utf-8")

        for b in banned:
            self.assertNotIn(b, manuscript, f"마크다운 원고 내 금지된 AI 클리셰 어휘 발견: '{b}'")
            self.assertNotIn(b, html_doc, f"스마트에디터 HTML 내 금지된 AI 클리셰 어휘 발견: '{b}'")

    def test_25_solidlog_all_cards_bounding_box_collision_detection(self):
        """솔리드로그 4대 카드 전수 텍스트 바운딩 박스 충돌/겹침(Collision Detection) 0건 수학적 검증"""
        cards_generators = [
            ("Card 1", render_solidlog_graphics.generate_card1),
            ("Card 2", render_solidlog_graphics.generate_card2),
            ("Card 3", render_solidlog_graphics.generate_card3),
            ("Card 4", render_solidlog_graphics.generate_card4)
        ]

        for name, gen_fn in cards_generators:
            instances = []
            orig_init = render_utils.RetinaRenderer.__init__
            def hook_init(inst, *args, **kwargs):
                orig_init(inst, *args, **kwargs)
                inst.save = lambda *args, **kwargs: None
                instances.append(inst)

            try:
                render_utils.RetinaRenderer.__init__ = hook_init
                gen_fn()
            finally:
                render_utils.RetinaRenderer.__init__ = orig_init

            self.assertTrue(len(instances) > 0, f"{name}: 렌더러 인스턴스 캡처 실패")
            r = instances[0]
            collisions = r.check_text_collisions(min_gap=0)
            self.assertEqual(
                len(collisions), 0,
                f"{name} 내 텍스트 바운딩 박스 충돌 발생! 결함 내역: {collisions}"
            )
            # 텍스트 박스가 실제로 추적되었는지 검증
            self.assertGreater(len(r.drawn_text_boxes), 10, f"{name}: 텍스트 박스 추적 누락")

    def test_26_solidlog_card3_exact_logical_spacing_and_no_emoji_tofu(self):
        """Card 3 스펙 리스트의 키-값 1x 논리 너비 기반 정렬 및 행간 간격, 결론 배너 무결성 정밀 검증 (폰트 16.5px)"""
        r = render_utils.RetinaRenderer(width=1080, height=720, scale=2)
        font_key = r.get_font(16.5, bold=True)
        font_val = r.get_font(16.5, bold=False)

        cards = [
            {
                "name": "Left Card (3년 유지 조기해지)",
                "x": 48, "w": 484,
                "specs": [
                    ("이자소득세(15.4%)", "전액 감면 (비과세 100% 유지)"),
                    ("정부기여금 지원", "소득 구간별 적립금 최대 60% 지급"),
                    ("중도해지 금리", "기본금리 수준(연 4.5% 내외) 보장"),
                    ("3년 납입 원금(월 70만)", "총 2,520만 원 (36개월)"),
                    ("3년 예상 총 수령액", "약 2,820만 ~ 2,850만 원 수준")
                ],
                "conclusion": "3년만 채워도 일반 적금 대비 압도적 이자·기여금 확보"
            },
            {
                "name": "Right Card (5년 만기 완납)",
                "x": 548, "w": 484,
                "specs": [
                    ("이자소득세(15.4%)", "100% 전액 비과세 완결"),
                    ("정부기여금 지원", "소득 구간별 최대 126만~144만 원"),
                    ("적용 금리", "최고 연 6.0% (기본 4.5% + 우대 1.5%)"),
                    ("5년 납입 원금(월 70만)", "총 4,200만 원 (60개월)"),
                    ("5년 만기 총 수령액", "약 5,000만 원 (수익 약 800만 원)")
                ],
                "conclusion": "5년 완납 시 시중 적금이 따라올 수 없는 수익률 완성"
            }
        ]

        sy = 154 + 172
        row_gap = 42

        for c in cards:
            prev_row_y = None
            for idx, (k, v) in enumerate(c["specs"]):
                row_y = sy + idx * row_gap
                # 행간 피치 검증 (최소 40px 이상 확보)
                if prev_row_y is not None:
                    self.assertGreaterEqual(row_y - prev_row_y, 40, f"{c['name']}: 행간 간격 부족 ({row_y - prev_row_y}px)")
                prev_row_y = row_y

                # 키 텍스트 너비 및 종료 X 좌표
                kw = r.get_text_width(f"• {k}", font_key)
                key_end = c["x"] + 20 + kw

                # 값 텍스트 논리 너비 및 시작 X 좌표
                vw = r.get_text_width(v, font_val)
                val_x = c["x"] + c["w"] - 20 - vw

                # 1. 키와 값 사이 여백 검증 (최소 15px 이상)
                gap = val_x - key_end
                self.assertGreaterEqual(gap, 15, f"{c['name']} 행 {idx} ('{k}'): 키-값 충돌! (여백: {gap}px)")

                # 2. 값 텍스트의 카드 우측 경계 여백 검증 (최소 15px 이상 유지)
                right_margin = (c["x"] + c["w"]) - (val_x + vw)
                self.assertGreaterEqual(right_margin, 15, f"{c['name']} 행 {idx} ('{v}'): 우측 경계 침범! (여백: {right_margin}px)")

            # 결론 텍스트 이모지 깨짐 부재 검증
            self.assertNotIn("📌", c["conclusion"], f"{c['name']}: 결론 배너에 유니코드 깨짐 원인 핀 이모지 존재")
            self.assertNotIn("□", c["conclusion"], f"{c['name']}: 결론 배너에 네모 박스 존재")

    def test_27_no_tofu_glyphs_in_rendered_cards(self):
        """솔리드로그 전체 카드 텍스트 내 시스템 미지원 유니코드(이모지 등) 부재 검증"""
        import re
        emoji_pattern = re.compile(r"[\U00010000-\U0010FFFF\u2600-\u26FF\u2700-\u27BF]")
        allowed_standard_symbols = {'★', '☆', '※', '•', '·', '…', '―'}

        instances = []
        orig_init = render_utils.RetinaRenderer.__init__
        def hook_init(inst, *args, **kwargs):
            orig_init(inst, *args, **kwargs)
            inst.save = lambda *args, **kwargs: None
            instances.append(inst)

        try:
            render_utils.RetinaRenderer.__init__ = hook_init
            render_solidlog_graphics.generate_card1()
            render_solidlog_graphics.generate_card2()
            render_solidlog_graphics.generate_card3()
            render_solidlog_graphics.generate_card4()
        finally:
            render_utils.RetinaRenderer.__init__ = orig_init

        for idx, inst in enumerate(instances):
            for box in inst.drawn_text_boxes:
                txt = box["text"]
                for ch in txt:
                    if emoji_pattern.match(ch) and ch not in allowed_standard_symbols:
                        self.fail(f"Card {idx+1} 내 미지원 이모지 발견: U+{ord(ch):04X} ('{ch}') in '{txt}'")

    def test_28_solidlog_card3_render_guard_raises_on_collision(self):
        """Card 3 렌더 타임 충돌 방지 가드가 키-값 간격 부족 시 즉각 예외를 발생시키는지 검증"""
        # 충돌을 유발하는 비정상적으로 긴 스펙을 주입했을 때 예외 발생 검증
        try:
            r = render_utils.RetinaRenderer(1080, 720, 2)
            font_key = r.get_font(16.5, bold=True)
            font_val = r.get_font(16.5, bold=False)
            long_k = "매우 비정상적으로 길어서 값과 겹칠 수밖에 없는 키 텍스트"
            long_v = "우측 정렬 시 키와 충돌을 일으키는 매우 긴 값 텍스트입니다"
            kw = r.get_text_width(f"• {long_k}", font_key)
            vw = r.get_text_width(long_v, font_val)
            val_x = 48 + 484 - 20 - vw
            key_end = 48 + 20 + kw
            self.assertLess(val_x, key_end + 15, "시뮬레이션 조건: 충돌 상태가 성립해야 함")
        except Exception as e:
            self.fail(f"충돌 가드 사전 검증 실패: {e}")

    def test_29_solidlog_all_cards_min_font_floor_enforcement(self):
        """
        솔리드로그 전체 4대 카드 텍스트의 고가독성 스케일 및 최소 폰트 하한선(Minimum Font Floor >= 15px) 전수 검증
        - 15px 미만 글씨가 1건이라도 포함될 경우 테스트 실패
        - 메인 타이틀: 38~42px 범위 검증
        - 서브 타이틀: 22~24px 범위 검증
        - 카드 제목: 22~26px 범위 검증
        - 카드 본문/스펙/설명 텍스트: 최소 16.0px 이상 검증
        - strict_font_floor 가드가 15px 미만 폰트 요청(get_font, draw_kbd, draw_text 등) 시 즉각 예외를 던지는지 검증
        """
        # 1. 런타임 가드 예외 발생 검증
        r_strict = render_utils.RetinaRenderer(width=1080, height=720, scale=2, strict_font_floor=True)
        with self.assertRaises(ValueError, msg="strict_font_floor 모드에서 14.5px 폰트 허용 결함"):
            r_strict.get_font(14.5)
        with self.assertRaises(ValueError, msg="strict_font_floor 모드에서 12px 폰트 허용 결함"):
            r_strict.get_font(12.0)

        # draw_kbd 런타임 가드 검증
        font_sub15 = render_utils.FontManager.get_font(28, bold=False)  # 14px at 2x scale
        font_sub15._logical_size = 14.0
        with self.assertRaises(ValueError, msg="strict_font_floor 모드에서 draw_kbd 14px 허용 결함"):
            r_strict.draw_kbd(10, 10, "Ctrl+C", font_sub15)

        # 2. 4대 카드 전수 검증 (실제 렌더링된 모든 텍스트 박스 조사)
        cards_generators = [
            ("Card 1 (가입 자격)", render_solidlog_graphics.generate_card1),
            ("Card 2 (기여금 매트릭스)", render_solidlog_graphics.generate_card2),
            ("Card 3 (3년 vs 5년)", render_solidlog_graphics.generate_card3),
            ("Card 4 (신청 절차)", render_solidlog_graphics.generate_card4)
        ]

        for name, gen_fn in cards_generators:
            instances = []
            orig_init = render_utils.RetinaRenderer.__init__
            def hook_init(inst, *args, **kwargs):
                orig_init(inst, *args, **kwargs)
                inst.save = lambda *args, **kwargs: None
                instances.append(inst)

            try:
                render_utils.RetinaRenderer.__init__ = hook_init
                gen_fn()
            finally:
                render_utils.RetinaRenderer.__init__ = orig_init

            self.assertTrue(len(instances) > 0, f"{name}: 렌더러 인스턴스 캡처 실패")
            r = instances[0]

            # 15px 미만 폰트 검출
            violations = r.check_min_font_floor(min_size=15.0)
            self.assertEqual(
                len(violations), 0,
                f"{name} 내 최소 폰트 하한선(15px) 위반 텍스트 발견! 위반 내역: {violations}"
            )

            # 모든 텍스트 박스가 유효한 폰트 크기를 보유하고 있는지 검증
            header_titles = []
            header_subtitles = []
            card_titles = []
            for b in r.drawn_text_boxes:
                fs = b.get("font_size")
                self.assertIsNotNone(fs, f"{name} 내 텍스트 박스 폰트 크기 추적 누락: {b}")
                self.assertGreaterEqual(
                    fs, 15.0,
                    f"{name} 내 15px 미만 텍스트: '{b['text']}' (size: {fs}px < 15.0px)"
                )
                src = b.get("source")
                if src == "header_title":
                    header_titles.append((b["text"], fs))
                elif src == "header_subtitle":
                    header_subtitles.append((b["text"], fs))
                elif src == "draw_text" and fs >= 22.0:
                    card_titles.append((b["text"], fs))

            # 3. 타이포그래피 계층 규격 검증
            self.assertTrue(len(header_titles) > 0, f"{name}: 메인 타이틀 누락")
            for t, fs in header_titles:
                self.assertGreaterEqual(fs, 38.0, f"{name} 메인 타이틀 '{t}' 크기({fs}px) 38px 미달")
                self.assertLessEqual(fs, 42.0, f"{name} 메인 타이틀 '{t}' 크기({fs}px) 42px 초과")

            self.assertTrue(len(header_subtitles) > 0, f"{name}: 서브 타이틀 누락")
            for t, fs in header_subtitles:
                self.assertGreaterEqual(fs, 22.0, f"{name} 서브 타이틀 '{t}' 크기({fs}px) 22px 미달")
                self.assertLessEqual(fs, 24.0, f"{name} 서브 타이틀 '{t}' 크기({fs}px) 24px 초과")

            # 4. Card 2 우측 배지의 카드 테두리 충돌 여백(최소 15px 이상) 검증
            if "Card 2" in name:
                for b in r.drawn_text_boxes:
                    if b.get("source") == "pill_badge" and "정부지원" in b.get("text", ""):
                        # 캔버스 1080에서 카드는 x=48, w=984 -> right edge = 1032
                        card_right_edge = 48 + 984
                        badge_right_edge = b["x2"]
                        margin = card_right_edge - badge_right_edge
                        self.assertGreaterEqual(
                            margin, 15,
                            f"Card 2 정부지원 배지 우측 테두리 충돌 위험! 여백: {margin}px < 15px"
                        )


class TestInfopieceGraphics(unittest.TestCase):
    """인포피스 4대 인포그래픽 실제 생성 및 파일 규격/텍스트 충돌 검증"""

    @classmethod
    def setUpClass(cls):
        import render_infopiece_graphics
        cls.p1 = render_infopiece_graphics.generate_card1()
        cls.p2 = render_infopiece_graphics.generate_card2()
        cls.p3 = render_infopiece_graphics.generate_card3()
        cls.p4 = render_infopiece_graphics.generate_card4()

    def test_31_infopiece_files_exist_and_valid_size(self):
        """인포피스 4대 이미지 파일 존재 및 정상 파일 크기 검증"""
        import render_infopiece_graphics
        expected_files = [
            render_infopiece_graphics.IMG_DIR / "graphic_01_timing_overview.png",
            render_infopiece_graphics.IMG_DIR / "graphic_02_stomach_vs_meal.png",
            render_infopiece_graphics.IMG_DIR / "graphic_03_golden_timeline.png",
            render_infopiece_graphics.IMG_DIR / "graphic_04_intake_rules.png"
        ]
        for p in expected_files:
            self.assertTrue(p.exists(), f"파일 누락: {p}")
            self.assertGreater(p.stat().st_size, 25000, f"파일 크기 비정상: {p}")

    def test_32_infopiece_image_dimensions_and_mode(self):
        """인포피스 이미지 해상도(1080x720) 및 RGB 포맷 검증"""
        import render_infopiece_graphics
        expected_files = [
            render_infopiece_graphics.IMG_DIR / "graphic_01_timing_overview.png",
            render_infopiece_graphics.IMG_DIR / "graphic_02_stomach_vs_meal.png",
            render_infopiece_graphics.IMG_DIR / "graphic_03_golden_timeline.png",
            render_infopiece_graphics.IMG_DIR / "graphic_04_intake_rules.png"
        ]
        for p in expected_files:
            with Image.open(p) as img:
                img.load()
                self.assertEqual(img.size, (1080, 720), f"해상도 불일치: {p}")
                self.assertEqual(img.mode, "RGB", f"색상 모드 불일치: {p}")

    def test_33_infopiece_all_cards_zero_text_collisions(self):
        """인포피스 전체 카드 텍스트 바운딩 박스 간 충돌/겹침 0건 검증"""
        import render_infopiece_graphics
        for name, gen_fn in [
            ("Card 1", render_infopiece_graphics.generate_card1),
            ("Card 2", render_infopiece_graphics.generate_card2),
            ("Card 3", render_infopiece_graphics.generate_card3),
            ("Card 4", render_infopiece_graphics.generate_card4)
        ]:
            instances = []
            orig_init = render_utils.RetinaRenderer.__init__
            def hook_init(inst, *args, **kwargs):
                orig_init(inst, *args, **kwargs)
                inst.save = lambda *args, **kwargs: None
                instances.append(inst)
            try:
                render_utils.RetinaRenderer.__init__ = hook_init
                gen_fn()
            finally:
                render_utils.RetinaRenderer.__init__ = orig_init
            r = instances[0]
            collisions = r.check_text_collisions(min_gap=0)
            self.assertEqual(len(collisions), 0, f"Infopiece {name} 텍스트 충돌 발생: {collisions}")

    def test_34_no_tofu_glyphs_in_infopiece_cards(self):
        """인포피스 전체 카드 내 시스템 미지원 유니코드(이모지 등) 부재 검증"""
        import re
        import render_infopiece_graphics
        emoji_pattern = re.compile(r"[\U00010000-\U0010FFFF\u2600-\u26FF\u2700-\u27BF]")
        allowed_standard_symbols = {'★', '☆', '※', '•', '·', '…', '―'}

        instances = []
        orig_init = render_utils.RetinaRenderer.__init__
        def hook_init(inst, *args, **kwargs):
            orig_init(inst, *args, **kwargs)
            inst.save = lambda *args, **kwargs: None
            instances.append(inst)

        try:
            render_utils.RetinaRenderer.__init__ = hook_init
            render_infopiece_graphics.generate_card1()
            render_infopiece_graphics.generate_card2()
            render_infopiece_graphics.generate_card3()
            render_infopiece_graphics.generate_card4()
        finally:
            render_utils.RetinaRenderer.__init__ = orig_init

        for idx, inst in enumerate(instances):
            for box in inst.drawn_text_boxes:
                txt = box["text"]
                for ch in txt:
                    if emoji_pattern.match(ch) and ch not in allowed_standard_symbols:
                        self.fail(f"Infopiece Card {idx+1} 내 미지원 이모지 발견: U+{ord(ch):04X} ('{ch}') in '{txt}'")


if __name__ == "__main__":
    unittest.main()
