# 🏛️ 01_you_idea_blog_core 중앙 코어 에이전트 행동 지침 (AGENTS.md)

본 저장소는 전체 블로그 생태계(`dev`, `tistory`, `gear`, `stock`, `markets`, `naver`)가 공유하는 단일 진실 공급원(Single Source of Truth)입니다.

## ⚖️ [필수] 독립 감사용 제3자 서브에이전트(Red Team Critic) 의무 호출 원칙

1. **오케스트레이터의 독립 제3자 감사 서브에이전트 직접 호출 의무**:
   - 파이썬 스크립트(`ironclad_gatekeeper.py`) 단독으로는 Antigravity AI 서브에이전트(`invoke_subagent`)를 직접 호출할 수 없습니다.
   - 따라서 글 발행/배포 직전, 오케스트레이터(집필 AI 에이전트)는 반드시 스스로 독립 감사용 제3자 서브에이전트(`invoke_subagent(TypeName='research', Role='Independent Red Team Post Auditor')`)를 호출하여 원고의 컴파일/문법 오류, 커널·라이브러리 버전 모순, 산술 수식·단위·procfs 정합성, Before/After 대칭 및 허위 메트릭 유무를 정밀 감사해야 합니다.
2. **Gate 14 승인 토큰 기반 통과**:
   - 독립 감사 서브에이전트가 `[PASSED]`를 판정한 경우에만 일회성 감사 토큰(`.subagent_audit_token` 또는 `SUBAGENT_AUDIT_PASSED=1`)을 발급하여 `ironclad_gatekeeper.py` Gate 14를 통과시키고, 배포 완료 즉시 토큰 파일을 삭제하십시오.
3. **최신 단일 파일 게이트키퍼 사용**:
   - 본 저장소 루트의 `ironclad_gatekeeper.py`는 Gate 1~14(Gate 13 동적 Diff·PromQL·허위 메트릭 검증 및 Gate 14 서브에이전트 감사 검증 포함)가 통합된 최신 마스터 버전입니다.
