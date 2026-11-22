# -*- coding: utf-8 -*-
"""
blog_core.engine.context - Execution context for rules (RuleContext)
"""

import re
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any


def split_frontmatter_and_body(content: str) -> Tuple[Optional[str], str, int]:
    """
    Frontmatter(--- ... ---)와 Body 분리.
    반환: (frontmatter_text, body_text, body_start_line)
    """
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, content, 1

    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            fm_text = "\n".join(lines[1:i])
            body_text = "\n".join(lines[i + 1:])
            return fm_text, body_text, i + 2

    return None, content, 1


def parse_frontmatter(fm_text: Optional[str]) -> Dict[str, Any]:
    """정규식 기반 안전한 Frontmatter 파싱 (PyYAML 미설치 환경 대비, 멀티라인 및 인라인 리스트 지원)."""
    if not fm_text:
        return {}
    data: Dict[str, Any] = {}
    current_list_key: Optional[str] = None
    for raw_line in fm_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        # 멀티라인 리스트 아이템: - value
        if line.startswith("-") and current_list_key:
            val = line.lstrip("-").strip()
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            if isinstance(data.get(current_list_key), list):
                data[current_list_key].append(val)
            else:
                data[current_list_key] = [val]
            continue

        match = re.match(r"^([a-zA-Z0-9_\-]+)\s*:\s*(.*)$", line)
        if match:
            k, v = match.group(1).strip(), match.group(2).strip()
            if v == "" or v == "[]":
                data[k] = []
                current_list_key = k
            elif v.startswith("[") and v.endswith("]"):
                inner = v[1:-1].strip()
                items = []
                if inner:
                    for item in re.findall(r'(?:"([^"]*)"|\'([^\']*)\'|([^,]+))', inner):
                        extracted = item[0] or item[1] or item[2]
                        items.append(extracted.strip())
                data[k] = items
                current_list_key = None
            else:
                if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                    v = v[1:-1]
                data[k] = v
                current_list_key = None
        else:
            current_list_key = None
    return data


def extract_code_blocks(body: str) -> List[Tuple[str, str, int]]:
    """
    코드 블록 추출: (language, code_text, start_line)
    """
    blocks = []
    lines = body.splitlines()
    in_block = False
    lang = ""
    current_block = []
    block_start = 0

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```") and not stripped.startswith("+```") and not stripped.startswith("-```"):
            if in_block:
                blocks.append((lang, "\n".join(current_block), block_start))
                in_block = False
                current_block = []
                lang = ""
            else:
                in_block = True
                lang = stripped[3:].strip()
                block_start = idx
        elif in_block:
            current_block.append(line)

    return blocks


@dataclass
class RuleContext:
    file_path: str
    content: str
    lines: List[str]
    platform: str
    fm_data: Dict[str, str]
    body: str
    body_start_line: int
    code_blocks: List[Tuple[str, str, int]]
    strict_mode: bool = False
    is_reserved: Optional[bool] = None
    reserve_date: Optional[str] = None
    reserve_time: Optional[str] = None
    reserve_composite: Optional[str] = None
    now_dt: Optional[datetime] = None
    min_buffer_minutes: int = 10

    def is_english(self) -> bool:
        """영문 플랫폼이거나 본문 앞부분에 한글이 없는 경우 영문 콘텐츠로 판별."""
        return self.platform in ["dev", "markets"] or len(re.findall(r"[가-힣]", self.body[:500])) == 0


def create_context(
    file_path: str,
    content: str,
    platform: str,
    strict_mode: bool = False,
    is_reserved: Optional[bool] = None,
    reserve_date: Optional[str] = None,
    reserve_time: Optional[str] = None,
    reserve_composite: Optional[str] = None,
    now_dt: Optional[datetime] = None,
    min_buffer_minutes: int = 10
) -> RuleContext:
    """원시 텍스트와 파일 정보로부터 RuleContext를 1회 생성하는 팩토리 함수."""
    fm_text, body, body_start_line = split_frontmatter_and_body(content)
    fm_data = parse_frontmatter(fm_text)
    lines = content.splitlines()
    code_blocks = extract_code_blocks(body)

    return RuleContext(
        file_path=file_path,
        content=content,
        lines=lines,
        platform=platform,
        fm_data=fm_data,
        body=body,
        body_start_line=body_start_line,
        code_blocks=code_blocks,
        strict_mode=strict_mode,
        is_reserved=is_reserved,
        reserve_date=reserve_date,
        reserve_time=reserve_time,
        reserve_composite=reserve_composite,
        now_dt=now_dt,
        min_buffer_minutes=min_buffer_minutes,
    )
