# 📘 타 블로그 에이전트용 코어 확장 및 사용 가이드 (AGENT_EXTENSION_GUIDE.md)

> **수신 대상**: 전 생태계 블로그 전담 에이전트 (`stock`, `gear`, `markets`, `dev`, `softwin`, `naver` 및 향후 신설될 모든 블로그 에이전트)  
> **핵심 원칙**: **"기존 코어 엔진을 한 줄도 수정하지 않고, 자신의 블로그에 필요한 규칙과 기능을 플러그인 형태로 안전하게 독립 추가한다."**

---

## 🏛️ 1. 코어 시스템 개요 및 에이전트 행동 지침

`01_you_idea_blog_core`는 모든 블로그가 공통으로 사용하는 **중앙 관제 및 공통 인프라 패키지**입니다.

과거에는 각 블로그마다 검증 스크립트나 라이트박스 JS를 제각각 복사하여 사용하여 다음과 같은 문제가 있었습니다:
* 특정 블로그의 코드를 고치다가 다른 블로그 기능이 망가짐 (회귀 버그)
* 동일한 버그를 여러 블로그 레포지토리를 찾아다니며 N번 수정해야 함
* 룰셋 버전이 제각각 달라져 품질 기준이 무너짐

본 코어 시스템을 사용하면:
1. **타 블로그 영향도 0%**: 여러분이 담당 블로그의 전용 룰을 추가하거나 수정해도, 다른 블로그에는 절대 영향을 주지 않습니다.
2. **원클릭 동기화**: 프론트엔드 자산을 코어에서 수정하고 스크립트 한 번만 실행하면 모든 블로그 웹사이트로 1초 만에 배포됩니다.
3. **단일 임포트**: `from blog_core import IroncladGatekeeper` 단 한 줄로 표준화된 기능을 어디서든 호출합니다.

---

## 🧩 2. 내 블로그 전용 규칙(Rule) 추가하는 방법 (플러그인 튜토리얼)

새로운 검증 규칙이나 법적 규제 방벽이 필요할 때, **코어 엔진(`engine/`) 코드는 절대 손댈 필요가 없습니다.**  
오직 `blog_core/rules/platforms/<내블로그>.py` 파일에 규칙 클래스를 추가하기만 하면 됩니다.

### Step 1: BaseRule 클래스 상속 및 메타데이터 정의
모든 규칙은 `blog_core.engine.base_rule.BaseRule`을 상속받습니다.

```python
# blog_core/rules/platforms/stock.py 예시

from blog_core.engine.base_rule import BaseRule
from blog_core.engine.models import Violation, Severity

class StockSpecificRiskWarningRule(BaseRule):
    """증시 블로그 전용: 파생상품/커버드콜 최대 손실 위험 고지 강제 규칙"""
    
    rule_id = "G8_STOCK_MAX_LOSS_WARNING"      # 규칙 고유 ID
    gate_name = "자본시장법 및 금소법 위험 고지 방벽" # 소속 게이트 명칭
    severity = Severity.REJECT                  # 심각도 (REJECT: 발행 차단, WARNING: 감점 및 경고)
    target_platforms = ["stock"]                # ★ 매우 중요: 오직 'stock' 블로그에만 적용!
    
    def evaluate(self, doc):
        """
        문서 검증 로직 구현
        :param doc: RuleContext 객체 (doc.raw_content, doc.body, doc.frontmatter, doc.platform 등 제공)
        :return: 위반 사항이 있을 경우 Violation 객체 리스트 반환, 없으면 빈 리스트 [] 반환
        """
        violations = []
        
        # 커버드콜 또는 파생상품을 다루는 글인지 확인
        if "커버드콜" in doc.raw_content or "옵션" in doc.raw_content:
            # 필수 리스크 문구 검사
            required_phrase = "원금 손실이 발생할 수 있으며"
            if required_phrase not in doc.raw_content:
                violations.append(Violation(
                    gate_id="GATE_8",
                    gate_name=self.gate_name,
                    rule_id=self.rule_id,
                    severity=self.severity,
                    line_number=doc.line_count,
                    snippet="No loss warning found in covered call article",
                    message="커버드콜/옵션 분석글에는 금융소비자보호법에 따른 '원금 손실 가능성 경고'가 필수입니다.",
                    fix_hint="본문 하단 면책 조항에 '금융투자상품은 시장 변동성에 따라 원금 손실이 발생할 수 있으며...' 문구를 추가하십시오."
                ))
                
        return violations
```

### Step 2: Auto-Discovery에 의한 자동 등록
* 클래스를 파일에 작성하고 저장하면 끝입니다!
* `RuleRegistry`가 부팅 시 `blog_core/rules/` 하위의 모든 모듈을 자동으로 스캔하여 새 규칙을 즉시 등록합니다.
* `target_platforms = ["stock"]`로 지정되어 있으므로, 개발 블로그(`dev`)나 네이버 블로그(`naver`)를 검증할 때는 **이 룰이 완벽히 무시(Filtering Out)**되어 오탐이 발생하지 않습니다.

---

## 🌐 3. 전 블로그 공통 규칙 추가하는 방법

만약 모든 블로그에 예외 없이 적용되어야 하는 절대적 규칙(예: 새로운 API 시크릿 키 패턴, 신규 AI 클리셰 등)이라면:
* `blog_core/rules/common/` 폴더 내의 적절한 파일(`anti_ai.py`, `secret_leak.py`, `markdown_structure.py`)에 추가하거나,
* `blog_core/rules/common/my_new_common_rule.py` 파일을 새로 생성하고,
* `target_platforms = ["all"]`로 선언하십시오. 모든 블로그 검증 시 자동으로 적용됩니다.

---

## 🧪 4. 내가 추가한 규칙 테스트 및 검증하는 방법

작성한 규칙이 의도대로 잘 작동하는지 확인하려면 `tests/` 폴더에 테스트를 추가하거나 기존 테스트 러너를 실행합니다:

```powershell
# 1. 코어 루트 디렉터리로 이동
cd D:\00_antigravity\01_you_idea_blog_core

# 2. 전체 단위 테스트 실행 (200개 이상)
pytest

# 3. 내 블로그 관련 테스트만 집중 실행
pytest tests/test_platform_isolation.py
pytest tests/e2e/test_tier1_features.py -k "stock"
```

---

## 🎨 5. 웹 프론트엔드 자산(Pan & Zoom 라이트박스 등) 개선 및 동기화

블로그 도안 확대 뷰어(라이트박스)의 JS나 CSS를 수정해야 할 경우:
1. **각 블로그 레포지토리의 `assets/js/main.js`를 직접 고치지 마십시오.** (코드가 다시 파편화됩니다)
2. 오직 `D:\00_antigravity\01_you_idea_blog_core\web_assets\` 아래의 마스터 파일을 수정하십시오:
   * `web_assets/js/lightbox.js`
   * `web_assets/css/lightbox.css`
3. 수정 후 터미널에서 동기화 스크립트를 실행합니다:
   ```powershell
   python sync_to_blogs.py
   ```
   * 이 명령어 하나로 `blogs/dev`, `blogs/markets`, `blogs/gear`, `blogs/stock` 등 모든 블로그의 `assets/` 폴더로 최신 코드가 1초 만에 자동 복사 및 배포 준비가 완결됩니다.

---

## 🗄️ 6. 통합 데이터베이스 & 성과 분석 모듈 사용법

각 에이전트는 코어의 데이터베이스 및 분석 모듈을 표준 파이썬 임포트로 즉시 활용할 수 있습니다:

### 데이터베이스 활용 (`blog_core.database`)
```python
from blog_core.database import get_db_connection, get_post_by_id, list_posts

# 1. 특정 플랫폼의 글 목록 조회
stock_posts = list_posts(platform="stock", status="PUBLISHED")
for p in stock_posts:
    print(f"[{p['id']}] {p['title']} -> {p['file_path']}")

# 2. 새 글 등록 또는 상태 업데이트
# create_post(...), update_post_status(...) 제공
```

### 성과 분석 활용 (`blog_core.analytics`)
```python
from blog_core.analytics import GA4Client, SearchConsoleClient

# GA4 페이지뷰 및 방문자 데이터 조회
ga4 = GA4Client()
stats = ga4.get_daily_report(platform="dev", days=7)
print("최근 7일 페이지뷰:", stats.total_pageviews)
```

---

## 🚀 7. GitHub Actions (CI/CD) 연동 방법

블로그 레포지토리의 GitHub Actions 워크플로우(`.github/workflows/*.yml`)에서 `blog_core`를 사용하여 자동 검증을 수행할 경우, `Install dependencies` 단계에 아래 패키지 설치 명령을 반드시 추가하십시오:

```yaml
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pyyaml pytest
          pip install git+https://github.com/everhashk-justin/you_idea_blog_core.git
```

`you_idea_blog_core`는 공개(Public) 오픈소스 저장소이므로, 별도의 Secret 토큰이나 인증 설정 없이 클라우드 러너에서 즉시 100% 정상 설치됩니다.

---

## 💡 요약: 에이전트 5대 행동 수칙
1. **독립성 유지**: 내 블로그 룰은 `rules/platforms/<블로그명>.py`에서만 작성하고, 타 블로그 코드나 코어 엔진은 건드리지 않는다.
2. **단일 원천 원칙**: 프론트엔드 자산 수정은 오직 `web_assets/`에서만 수행하고 `sync_to_blogs.py`로 배포한다.
3. **CI/CD 연동 표준화**: GitHub Actions 워크플로우에 `pip install git+https://github.com/everhashk-justin/you_idea_blog_core.git`를 의무 적용한다.
4. **안전성 검증**: 규칙 추가 후 반드시 `pytest`를 실행하여 100% 통과를 확인한 후 완료 보고한다.
5. **최신 정보 실측 검증 (Mandatory Real-Time Fact-Check)**: 사전 학습 데이터(가중치)나 과거 기억/기록에만 의존한 작성을 100% 원천 영구 금지하고, 공식 레퍼런스·최신 릴리스 노트·정부 공인 고시·최신 소스코드 등 공인된 실측 데이터를 실시간으로 검색(`search_web`) 및 교차 검증한 후 집필한다.
