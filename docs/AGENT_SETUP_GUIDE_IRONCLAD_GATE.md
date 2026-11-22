# 🏛️ 타 블로그 에이전트를 위한 철벽 게이트 검증 시스템(Ironclad Gatekeeper) 세팅 및 연동 완벽 가이드

> **문서 대상**: 멀티 블로그 생태계 전담 에이전트 (`stock.ideaspot360.com`, `gear.ideaspot360.com`, `markets.ideaspot360.com`, 네이버 3대 블로그 등)  
> **핵심 파일**: [`ironclad_gatekeeper.py`](file:///d:/00_antigravity/01_you_idea_blog/ironclad_gatekeeper.py) (외부 라이브러리 설치 필요 없음 / Python Standard Library 100%)  
> **시스템 목적**: 에이전트의 주관적 의지나 다짐에 기대지 않고, **소프트웨어적 차단 게이트(`sys.exit(1)`)를 통해 저품질·AI 클리셰·소설화 글의 발행을 물리적으로 원천 차단**함.

---

## 📌 목차
1. [시스템 핵심 철학 및 도입 당위성](#1-시스템-핵심-철학-및-도입-당위성)
2. [5분 퀵스타트: 파일 복제 및 자가 검증 (Self-Test)](#2-5분-퀵스타트-파일-복제-및-자가-검증-self-test)
3. [도메인별 룰셋 커스터마이징 가이드 (증시, 기어, 매크로, 건강)](#3-도메인별-룰셋-커스터마이징-가이드-증시-기어-매크로-건강)
4. [글 발행 시스템 및 파이프라인 연동 방법 (Hard Block 구현)](#4-글-발행-시스템-및-파이프라인-연동-방법-hard-block-구현)
5. [글 작성 직후 자동 실행 워크플로우 & Pre-commit Hook](#5-글-작성-직후-자동-실행-워크플로우--pre-commit-hook)
6. [검증 실패(REJECT) 시 디버깅 및 품질 복구 SOP](#6-검증-실패reject-시-디버깅-및-품질-복구-sop)
7. [에이전트 행동 헌법 필수 명문화 조항](#7-에이전트-행동-헌법-필수-명문화-조항)

---

## 1. 시스템 핵심 철학 및 도입 당위성

### 1.1 왜 에이전트의 "다짐"은 실패하는가?
에이전트가 프롬프트나 지침에서 "인간다운 글쓰기를 하겠다"고 맹세하더라도, 대규모 언어 모델(LLM)은 구조적으로 다음과 같은 결함을 반복해서 배출합니다:
* **상투적 미사여구(AI Clichés)**: `delve`, `seamlessly`, `in modern cloud landscape`, `현대 사회에서는`, `결론적으로 말씀드리면` 등의 무의미한 서두.
* **작위적 소설화(Forced Drama)**: "새벽 3시 20분 비상 알람이 울렸고, 등줄기에 식은땀이 흘렀다..." 식의 유치한 스토리 조작.
* **정답 직행 편향 (Direct Solution Bias)**: 실제 엔지니어링이나 투자의 오판, 시행착오(Wrong Fix)가 거세된 비현실적 교과서 서술.
* **문법 및 조판 파손**: 백틱(```) 닫힘 누락으로 인한 렌더링 붕괴, 의료법/자본시장법 위반 단어 노출.

### 1.2 "철벽 게이트(Hard Block)"의 원칙
* **물리적 차단 (Exit Code 1)**: 검증 통과(Pass) 판정을 받지 못한 글은 발행 스크립트나 브라우저 자동화가 **실행조차 되지 않고 즉시 강제 종료**됩니다.
* **무의존성 (Zero External Dependency)**: `pip install` 없이 파이썬 표준 라이브러리(`re`, `sys`, `os`, `pathlib`, `argparse`, `json`)만으로 동작하므로, 어떤 가상환경에서도 즉시 실행 가능합니다.
* **단일 파일 완결성 (All-in-One)**: `ironclad_gatekeeper.py` 단 1개의 파일 안에 파서, 7대 검증 게이트, 컬러 리포터, 내장 셀프 테스트가 모두 포함되어 있습니다.

---

## 2. 5분 퀵스타트: 파일 복제 및 자가 검증 (Self-Test)

### Step 1: 모듈 파일 복사
원천 저장소([`01_you_idea_blog`](file:///d:/00_antigravity/01_you_idea_blog))의 [`ironclad_gatekeeper.py`](file:///d:/00_antigravity/01_you_idea_blog/ironclad_gatekeeper.py) 파일을 귀하의 블로그 프로젝트 루트 디렉터리에 그대로 복사합니다:

```powershell
# PowerShell 복사 예시 (예: stock_blog 워크스페이스로 복사 시)
Copy-Item -Path "D:\00_antigravity\01_you_idea_blog\ironclad_gatekeeper.py" -Destination "D:\00_antigravity\stock_blog\ironclad_gatekeeper.py"
```

### Step 2: 자가 무결성 단위 테스트 (Self-Test) 실행
터미널에서 복사한 스크립트의 내장 테스트를 실행하여 모든 차단 룰이 정상 동작하는지 즉시 검증합니다:

```powershell
python ironclad_gatekeeper.py --self-test
```

**[정상 실행 기대 출력]**:
```text
🧪 [철벽 게이트 검증 시스템 내장 Self-Test 시작]
  ✅ Test 1 Passed: Bad English AI Clichés caught successfully.
  ✅ Test 2 Passed: Forced Drama Story caught successfully.
  ✅ Test 3 Passed: Naver Medical Law violation caught successfully.
  ✅ Test 4 Passed: Unclosed Code Block caught successfully.

🎉 ALL SELF-TESTS PASSED: 철벽 게이트 검증 엔진의 모든 차단 룰이 정상 동작합니다!
```

---

## 3. 도메인별 룰셋 커스터마이징 가이드

`ironclad_gatekeeper.py`의 상단 룰셋 사전(`EN_AI_CLICHE_PATTERNS`, `KO_AI_CLICHE_PATTERNS` 등)에 각 블로그의 도메인 특화 금지 규칙을 손쉽게 추가할 수 있습니다.

### 3.1 증시/주식 블로그 (`stock.ideaspot360.com` / 맥락트레이딩)
자본시장법 위반 소지가 있거나 사기성 리딩방 어투를 원천 차단해야 합니다:

```python
# ironclad_gatekeeper.py 내 도메인 특화 룰 추가 예시
STOCK_FORBIDDEN_PATTERNS = [
    (r"원금\s*보장", "REJECT", "[자본시장법 위반] 주식/투자 글에 '원금 보장' 표방은 법적으로 금지됩니다."),
    (r"무조건\s*(급등|상승|폭등)", "REJECT", "비이성적 확증 편향 및 과장 어휘 감지. 객관적 데이터와 시나리오로 서술하십시오."),
    (r"확정\s*수익(률)?", "REJECT", "투자 글에 '확정 수익' 표현은 100% 금지됩니다."),
    (r"목표가\s*찍(는다|을\s*것)", "REJECT", "사기성 리딩방 어투 감지. '상방 저항선 레벨', '밸류에이션 밴드'로 서술하십시오."),
    (r"풀매수|영끌|몰빵", "REJECT", "비전문적 투기 조장 어휘 감지. 리스크 관리 및 분할 매매 원칙을 기술하십시오."),
]
```
* **필수 포함 요소 (Gate 4 연동)**:
  - 거시 지표(미 국채금리, 달러 인덱스, 연준 유동성 등) 및 차트/재무 데이터.
  - 최하단 **투자 유의사항 및 법적 면책 고지(Disclaimer)** 의무 삽입.

### 3.2 기어/테크 하드웨어 블로그 (`gear.ideaspot360.com`)
과장 마케팅 문구와 스펙 사기를 방지해야 합니다:

```python
GEAR_FORBIDDEN_PATTERNS = [
    (r"세계\s*(최초|최고)", "WARNING", "공인된 기관의 인증이 없는 '세계 최초/최고' 표현은 과장 광고입니다."),
    (r"종결자|끝판왕", "REJECT", "상투적 마케팅 은어 감지. 실제 벤치마크 수치(dB, W, RPM, 프레임 등)를 명시하십시오."),
    (r"압도적(인)?\s*성능", "REJECT", "모호한 감성 수식어 감지. 이전 세대 대비 전력 효율/처리 속도 비교표를 제시하십시오."),
]
```

### 3.3 글로벌 매크로·퀀트 블로그 (`markets.ideaspot360.com`)
영문 전문 퀀트/매크로 리포트의 신뢰성을 위해 저급 금융 클리셰를 차단합니다:

```python
MACRO_FORBIDDEN_PATTERNS_EN = [
    (r"\bguaranteed returns?\b", "REJECT", "Prohibited regulatory phrase detected."),
    (r"\bto the moon\b", "REJECT", "Unprofessional speculative slang detected."),
    (r"\beasy money\b", "REJECT", "Sensationalist financial phrase detected."),
]
```

---

## 4. 글 발행 시스템 및 파이프라인 연동 방법 (Hard Block 구현)

귀하의 블로그 워크스페이스에 있는 발행 스크립트(예: `publish.py`, `create_post.py`, `deploy.py` 등)의 **실행 시작점 최상단**에 아래 4줄의 연동 코드를 주입하십시오.

### 4.1 파이썬 발행 스크립트 연동 (표준 코드)

```python
# ==============================================================================
# 🛡️ 철벽 게이트 검증 시스템 연동 (Ironclad Gatekeeper Hard Block)
# ==============================================================================
try:
    from ironclad_gatekeeper import verify_or_abort
    
    print("\n🛡️ [Ironclad Gatekeeper] 발행 전 자동 품질 검증을 수행합니다...")
    # platform: "auto", "dev", "tistory", "naver" 중 선택 (기본값: "auto")
    verify_or_abort(file_path=target_markdown_path, platform="auto", strict=False)
    
except ImportError:
    print("❌ [Fatal Error] ironclad_gatekeeper.py 모듈이 워크스페이스 루트에 없습니다!")
    sys.exit(1)
except SystemExit as se:
    # 검증 실패 시 브라우저 실행이나 API 전송, 깃 푸시를 100% 물리적으로 차단
    print("🚫 [Execution Blocked] 품질 기준 미달로 인해 후속 발행 절차가 완전히 차단되었습니다.")
    raise se
# ==============================================================================
```

### 4.2 GitHub Pages 배포 스크립트 연동 (`publish_to_dev.py` 형태)
파일 복사(`shutil.copy2`) 및 `git push`를 수행하기 바로 전 단계에서 `verify_or_abort()`를 호출하여, **품질이 통과된 원고만 Git에 커밋**되도록 강제합니다.

---

## 5. 글 작성 직후 자동 실행 워크플로우 & Pre-commit Hook

에이전트가 글을 작성한 직후 발행 단계로 넘어가기 전에, 자가 진단을 수행하도록 워크플로우를 구성합니다.

### 5.1 CLI 수동/단독 검증 명령어
글 집필이 끝나면 터미널에서 즉시 검증을 실행합니다:

```powershell
# 단건 마크다운 글 정밀 검증 (상세 교정 팁 포함)
python ironclad_gatekeeper.py --file posts/my_new_article.md

# 디렉터리 내 전체 글 일괄 점검
python ironclad_gatekeeper.py --dir posts/

# 기계 판독용 JSON 출력 (CI/CD 파이프라인 연동 시)
python ironclad_gatekeeper.py --file posts/my_new_article.md --json
```

### 5.2 Git Pre-commit Hook 연동 (완전 무인 차단)
에이전트가 `git commit`을 시도할 때 검증을 통과하지 못한 마크다운 파일이 있으면 커밋 자체가 거부되도록 설정할 수 있습니다.

`.git/hooks/pre-commit` (또는 Windows의 경우 `.git/hooks/pre-commit.ps1`):
```bash
#!/bin/sh
echo "🛡️ Running Ironclad Gatekeeper Pre-commit Check..."
python ironclad_gatekeeper.py --dir posts/ --strict
if [ $? -ne 0 ]; then
    echo "❌ Git Commit Rejected: Unverified markdown posts detected!"
    exit 1
fi
```

---

## 6. 검증 실패(REJECT) 시 디버깅 및 품질 복구 SOP

게이트키퍼에서 `[REJECTED (발행 원천 차단)]`이 발생했을 때 에이전트가 조치해야 할 표준 절차(SOP)입니다.

```
[게이트키퍼 REJECT 발생]
       │
       ▼
[터미널 출력 리포트 확인] ──► (위반 행 번호, 문제 원문, 교정 팁 확인)
       │
       ▼
┌────────────────────────────────────────────────────────┐
│  Case 1: 백틱 홀수 (GATE_1) ──► 닫히지 않은 ``` 블록 닫기   │
│  Case 2: 분량 미달 (GATE_1) ──► 기술적 깊이/세부 분석 보강 │
│  Case 3: AI 클리셰 (GATE_2) ──► 담백한 엔지니어 실무어로 교체 │
│  Case 4: 새벽 알람 (GATE_3) ──► 객관적 모니터링 지표로 대체 │
│  Case 5: 아티팩트 결손(GATE_4)─► Raw Log, Diff, WrongFix 추가│
│  Case 6: 법적 금지어 (GATE_6) ──► 의학/금융 규제 어휘 완전 삭제│
└──────────────────────────┬─────────────────────────────┘
                           ▼
[python ironclad_gatekeeper.py --file <경로> 재검증]
       │
       ▼
[PASSED (Score >= 80) 확인 후 발행 파이프라인 재가동]
```

### 실제 교정 예시 (Before vs After)

#### 1) 억지 스토리 연출 (Gate 3)
* ❌ **Bad (REJECT)**:  
  `새벽 3시 40분, 비상 호출이 울렸다. 등줄기에 식은땀이 흘렀고 머릿속이 하얘졌다.`
* ✅ **Good (PASS)**:  
  `프로덕션 API 인그레스 게이트웨이에서 504 Gateway Timeout 에러율이 18%로 급증하며 알람이 발송되었다.`

#### 2) 정답 직행 편향 및 오진(Wrong Fix) 누락 (Gate 4)
* ❌ **Bad (REJECT)**:  
  `이 문제는 커널 파라미터 X를 1로 변경하면 즉시 해결됩니다.`
* ✅ **Good (PASS)**:  
  `처음에는 단순히 애플리케이션의 메모리 할당(Xmx)을 4GB에서 8GB로 늘려 대응했으나(Wrong Fix), 30분 만에 동일한 OOMKilled가 재발했다. 힙 덤프를 분석한 결과 실제 원인은 네이티브 다이렉트 버퍼 누수였으며...`

#### 3) Unified Diff 누락 (Gate 4)
* ❌ **Bad (REJECT)**:  
  `설정 파일에서 timeout 값을 60으로 수정하세요.`
* ✅ **Good (PASS)**:
  ````diff
  ```diff
  --- config/ingress.yaml.orig
  +++ config/ingress.yaml
  @@ -12,2 +12,2 @@
  - proxy-read-timeout: "10s"
  + proxy-read-timeout: "60s"
  ```
  ````

---

## 7. 에이전트 행동 헌법 필수 명문화 조항

타 블로그 워크스페이스의 마스터 지침서(`AGENTS.md` 또는 `GEMINI.md`) 최상단에 아래 조항을 반드시 명문화해야 합니다:

```markdown
## ⚖️ [철벽 게이트 검증 절대 헌법 (Ironclad Gate Law)]
1. 모든 블로그 글은 발행(Publish) 또는 커밋(Commit) 전, 반드시 `ironclad_gatekeeper.py`의 검증을 거쳐야 한다.
2. 게이트키퍼에서 `REJECT`가 단 1건이라도 발생하면 어떠한 예외나 변명 없이 발행 트랜잭션은 즉시 무효화 및 강제 중단된다.
3. 에이전트는 게이트키퍼 검증을 회피(Bypass)하기 위해 스크립트를 임의로 무력화하거나 예외 처리 코드를 삽입하는 행위를 영구히 금지한다.
4. 모든 완료 보고에는 게이트키퍼의 `[PASSED (발행 승인)]` 터미널 출력 로그(Proof of Work)를 필수로 첨부해야 한다.

## ⚖️ [최신 정보 실측 검증 및 과거 학습 데이터 의존 영구 금지 헌법 (Mandatory Real-Time Fact-Check Law)]
1. 모든 블로그 플랫폼에서 작성되는 모든 콘텐츠는 에이전트의 사전 학습 데이터(Pre-trained weights)나 과거 기억/기록에만 의존하여 작성하는 행위를 원천 영구 금지한다.
2. 집필 전 반드시 공식 레퍼런스, 공식 릴리스 노트, 식약처/국세청 등 정부 공인 최신 고시, 최신 커널 소스코드 등 공인된 실측 데이터와 최신 정보를 실시간으로 검색 및 교차 검증한 후 작성해야 한다.
3. 최신 실측 출처가 검증되지 않은 원고는 초안 단계에서 즉시 폐기하며 발행 파이프라인 진입을 원천 불허한다.
```

---
**문서 작성 완료**: 01_you_idea_blog 아키텍처 팀  
**원천 저장소**: `https://github.com/everhashk-justin/you_idea_blog`  
**배포 상태**: 프로덕션 마스터 표준 승인 완료 (v1.0.0)
