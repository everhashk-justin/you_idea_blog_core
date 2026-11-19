# -*- coding: utf-8 -*-
"""
blog_core.rules.common.reservation_guard - Gate 9: Reservation Integrity & Anti-Bot Jitter Gate
선별적 예약 일시 및 안티봇 지터 검증 (미래 일시 10분 버퍼 검증, 00분/00초 정각 안티봇 금지, 일반글 선별 스킵)
"""

import re
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation
from blog_core.engine.context import RuleContext


def _parse_datetime_flexible(raw_date: str, raw_time: str, now_dt: Optional[datetime] = None) -> Tuple[Optional[datetime], bool]:
    """
    date와 time 문자열을 유연하게 파싱.
    반환: (parsed_datetime, has_explicit_seconds)
    """
    if now_dt is None:
        now_dt = datetime.now()

    raw_date = (raw_date or "").strip()
    raw_time = (raw_time or "").strip()

    # 날짜 정규화
    norm_date = ""
    if raw_date:
        if "-" in raw_date:
            parts = raw_date.split("-")
            if len(parts) == 3:
                try:
                    y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
                    datetime(y, m, d)
                    norm_date = f"{y:04d}-{m:02d}-{d:02d}"
                except ValueError:
                    return None, False
            else:
                return None, False
        elif raw_date.isdigit():
            day_val = int(raw_date)
            if not (1 <= day_val <= 31):
                return None, False
            try:
                datetime(now_dt.year, now_dt.month, day_val)
                norm_date = f"{now_dt.year:04d}-{now_dt.month:02d}-{day_val:02d}"
            except ValueError:
                return None, False
        else:
            return None, False
    else:
        norm_date = now_dt.strftime("%Y-%m-%d")

    # 시간 정규화
    has_sec = False
    norm_time = ""
    if raw_time:
        if ":" in raw_time:
            t_parts = raw_time.split(":")
            if len(t_parts) == 3:
                try:
                    h, m, s = int(t_parts[0]), int(t_parts[1]), int(t_parts[2])
                    if not (0 <= h <= 23 and 0 <= m <= 59 and 0 <= s <= 59):
                        return None, False
                    norm_time = f"{h:02d}:{m:02d}:{s:02d}"
                    has_sec = True
                except ValueError:
                    return None, False
            elif len(t_parts) == 2:
                try:
                    h, m = int(t_parts[0]), int(t_parts[1])
                    if not (0 <= h <= 23 and 0 <= m <= 59):
                        return None, False
                    norm_time = f"{h:02d}:{m:02d}:00"
                    has_sec = False
                except ValueError:
                    return None, False
            else:
                return None, False
        elif raw_time.isdigit():
            try:
                h = int(raw_time)
                if not (0 <= h <= 23):
                    return None, False
                norm_time = f"{h:02d}:00:00"
                has_sec = False
            except ValueError:
                return None, False
        else:
            return None, False
    else:
        norm_time = "18:00:00"
        has_sec = False

    try:
        dt = datetime.strptime(f"{norm_date} {norm_time}", "%Y-%m-%d %H:%M:%S")
        return dt, has_sec
    except ValueError:
        return None, False


def _parse_datetime_string(dt_str: str, now_dt: Optional[datetime] = None) -> Tuple[Optional[datetime], bool]:
    """단일 일시 문자열 파싱 (예: '2026-12-04 18:24:37 +0900', '2026-12-04 18:24')"""
    if not dt_str or not dt_str.strip():
        return None, False

    clean_str = dt_str.strip()
    # 타임존 오프셋 제거 (예: +0900, +09:00, Z)
    clean_str = re.sub(r"\s*([+-]\d{2}:?\d{2}|Z)$", "", clean_str).strip()

    # YYYY-MM-DD HH:MM:SS
    m3 = re.match(r"^(\d{4}-\d{2}-\d{2})[T\s](\d{1,2}):(\d{1,2}):(\d{1,2})$", clean_str)
    if m3:
        try:
            dt = datetime.strptime(f"{m3.group(1)} {int(m3.group(2)):02d}:{int(m3.group(3)):02d}:{int(m3.group(4)):02d}", "%Y-%m-%d %H:%M:%S")
            return dt, True
        except ValueError:
            return None, False

    # YYYY-MM-DD HH:MM
    m2 = re.match(r"^(\d{4}-\d{2}-\d{2})[T\s](\d{1,2}):(\d{1,2})$", clean_str)
    if m2:
        try:
            dt = datetime.strptime(f"{m2.group(1)} {int(m2.group(2)):02d}:{int(m2.group(3)):02d}:00", "%Y-%m-%d %H:%M:%S")
            return dt, False
        except ValueError:
            return None, False

    # composite 파싱 시도
    if " " in clean_str:
        d_part, t_part = clean_str.split(" ", 1)
        return _parse_datetime_flexible(d_part, t_part, now_dt)

    return _parse_datetime_flexible(clean_str, "", now_dt)


def extract_reservation_info(ctx: RuleContext) -> Tuple[bool, Optional[datetime], bool, str]:
    """
    원고 메타데이터 또는 인자에서 예약 여부 및 목표 일시를 선별적으로 판별.
    반환: (is_reservation, target_dt, has_explicit_seconds, raw_string)
    """
    # 1. 인자 기반 명시적 예약 정보 전달 시
    if ctx.is_reserved or ctx.reserve_composite or ctx.reserve_date or ctx.reserve_time:
        raw_date = (ctx.reserve_date or "").strip()
        raw_time = (ctx.reserve_time or "").strip()
        comp = (ctx.reserve_composite or "").strip()

        if comp:
            if " " in comp:
                parts = comp.split(" ", 1)
                raw_date = raw_date or parts[0].strip()
                raw_time = raw_time or parts[1].strip()
            elif "-" in comp:
                raw_date = raw_date or comp
            elif ":" in comp:
                raw_time = raw_time or comp

        if not raw_date:
            raw_date = ctx.fm_data.get("reserve_date", "")
        if not raw_time:
            raw_time = ctx.fm_data.get("reserve_time", "")

        raw_str = f"{raw_date} {raw_time}".strip() or comp
        dt, has_sec = _parse_datetime_flexible(raw_date, raw_time, ctx.now_dt)
        return True, dt, has_sec, raw_str

    # 2. Frontmatter 메타데이터 기반 확인
    fm = ctx.fm_data
    pub_type = fm.get("publish_type", "").lower()
    is_res_fm = str(fm.get("is_reserved", "")).lower() in ["true", "yes", "1"]
    reserve_at = fm.get("reserve_at") or fm.get("scheduled_at") or fm.get("reserved_at")
    reserve_date_fm = fm.get("reserve_date")
    reserve_time_fm = fm.get("reserve_time")
    date_fm = fm.get("date")

    # 예약 모드 명시적 선언인 경우
    is_declared = (
        pub_type in ["scheduled", "reserved", "reservation"] or
        is_res_fm or
        bool(reserve_at) or
        bool(reserve_date_fm and reserve_time_fm)
    )

    if is_declared:
        raw_target = reserve_at or f"{reserve_date_fm or ''} {reserve_time_fm or ''}".strip() or date_fm or ""
        dt, has_sec = _parse_datetime_string(str(raw_target), ctx.now_dt)
        return True, dt, has_sec, str(raw_target)

    # 3. date 필드만 존재하는 경우 (미래 일시인지 확인하여 미래글만 선별 예약 검증)
    if date_fm:
        dt, has_sec = _parse_datetime_string(str(date_fm), ctx.now_dt)
        if dt:
            now = ctx.now_dt or datetime.now()
            # 미래 일시인 경우에만 예약 글로 간주하여 지터 및 버퍼 검증 수행
            # (과거 일시이고 publish_type이 scheduled가 아니면 이미 발행된 과거 글이므로 스킵)
            if dt > now:
                return True, dt, has_sec, str(date_fm)

    # 일반/즉시공개 글
    return False, None, False, ""


class ReservationIntegrityRule(BaseRule):
    """예약 일시 무결성 검증 규칙 (미래 일시 및 최소 10분 버퍼 검증, Gate 9)"""

    rule_id = "G9_RESERVATION_INTEGRITY"
    gate_id = "GATE_9"
    gate_name = "예약 발행 무결성 및 안티봇 지터 방벽"
    description = "예약 콘텐츠의 유효 날짜 형식, 과거 일시 차단 및 현재 시각 기준 최소 10분 미래 버퍼 검증"
    platforms = None  # 모든 플랫폼 공통 적용
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        is_res, target_dt, has_sec, raw_str = extract_reservation_info(ctx)
        # 일반/즉시공개 글은 예약 검사를 안전하게 건너뜀
        if not is_res:
            return []

        violations: List[Violation] = []
        now = ctx.now_dt or datetime.now()
        min_buffer = ctx.min_buffer_minutes if ctx.min_buffer_minutes is not None else 10

        # 포맷 파싱 실패 시
        if target_dt is None:
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id="G9_RESERVATION_INVALID_FORMAT",
                severity=self.default_severity,
                line_number=1,
                snippet=f"Invalid reservation format: '{raw_str}'",
                message=f"[예약 무결성 방벽] 예약 일시 형식이 올바르지 않거나 유효하지 않은 날짜/시간입니다: '{raw_str}'",
                fix_hint="예약 일시를 'YYYY-MM-DD HH:MM' 또는 'YYYY-MM-DD HH:MM:SS' 형식으로 정확히 지정하십시오."
            ))
            return violations

        target_str = target_dt.strftime("%Y-%m-%d %H:%M:%S" if has_sec else "%Y-%m-%d %H:%M")
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")

        # 과거 일시 검증
        if target_dt < now:
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id="G9_RESERVATION_PAST_TIME",
                severity=self.default_severity,
                line_number=1,
                snippet=f"Target: {target_str} < Current: {now_str}",
                message=f"[오발행 차단] 예약 일시({target_str})가 현재 시각({now_str})보다 과거입니다. 즉시 공개 오발행 방지를 위해 발행을 물리적으로 차단합니다.",
                fix_hint="현재 시각보다 미래의 예약 일시를 지정하십시오."
            ))
            return violations

        # 최소 10분 버퍼 검증
        min_allowed = now + timedelta(minutes=min_buffer)
        if target_dt < min_allowed:
            diff_mins = (target_dt - now).total_seconds() / 60.0
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id="G9_RESERVATION_BUFFER_UNDERFLOW",
                severity=self.default_severity,
                line_number=1,
                snippet=f"Buffer: {diff_mins:.1f} mins < Required: {min_buffer} mins",
                message=f"[오발행 차단] 예약 일시({target_str})는 현재 시각({now_str}) 기준 최소 {min_buffer}분 이후여야 합니다. (현재 버퍼: {diff_mins:.1f}분)",
                fix_hint=f"충분한 발행 버퍼(최소 {min_buffer}분 이상)를 확보하여 예약 일시를 재설정하십시오."
            ))

        return violations


class ReservationAntiBotJitterRule(BaseRule):
    """예약 일시 안티봇 랜덤 지터 검증 규칙 (00분 및 00초 정각 영구 금지, Gate 9)"""

    rule_id = "G9_RESERVATION_ANTIBOT_JITTER"
    gate_id = "GATE_9"
    gate_name = "예약 발행 무결성 및 안티봇 지터 방벽"
    description = "포털 어뷰징 매크로 봇 감지 레이더 회피 및 피드 충돌 방지를 위한 불규칙한 랜덤 분/초 적용 필수"
    platforms = None
    default_severity = "REJECT"

    def check(self, ctx: RuleContext) -> List[Violation]:
        is_res, target_dt, has_sec, raw_str = extract_reservation_info(ctx)
        if not is_res or target_dt is None:
            return []

        violations: List[Violation] = []

        # 1. 00분 정각 금지 검증 (티스토리 및 전 플랫폼 공통 헌법)
        if target_dt.minute == 0:
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id="G9_RESERVATION_BOT_COLLISION_MINUTE",
                severity=self.default_severity,
                line_number=1,
                snippet=f"Time minute: {target_dt.strftime('%H:%M')} (00m)",
                message=f"[안티봇 지터 헌법 위반] 예약 시각의 분이 '00분' 정각({target_dt.strftime('%H:%M')})입니다. 포털 자동화 봇 감지 레이더에 노출될 수 있으므로 정각 발행은 영구 금지됩니다.",
                fix_hint="05~52분 사이의 불규칙한 임의의 분(예: 08분, 14분, 23분, 37분, 46분 등)을 적용하여 인간의 자연스러운 발행 흔적을 보존하십시오."
            ))

        # 2. 00초 정각 금지 검증 (초 단위 타임스탬프 지원 시 또는 개발 블로그 초 생략 시)
        is_dev = ctx.platform in ["dev", "markets"]
        if (has_sec and target_dt.second == 0) or (is_dev and not has_sec):
            sec_display = target_dt.strftime('%H:%M:%S') if has_sec else f"{target_dt.strftime('%H:%M')}:00 (초 생략)"
            violations.append(Violation(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                rule_id="G9_RESERVATION_BOT_COLLISION_SECOND",
                severity=self.default_severity,
                line_number=1,
                snippet=f"Time seconds: '{sec_display}' (00s)",
                message=f"[안티봇 지터 헌법 위반] 예약 타임스탬프의 초가 '00초' 정각이거나 초 단위가 누락({sec_display})되었습니다. 개발 블로그 랜덤 초 지터 헌법을 위반했습니다.",
                fix_hint="Frontmatter의 date 속성에 정각(00초)을 배제하고 05~58초 사이의 불규칙한 랜덤 초(예: 10:52:43 +0900)를 적용하십시오."
            ))

        return violations
