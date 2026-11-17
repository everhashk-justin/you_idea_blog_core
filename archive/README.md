# 🏛️ Centralized Archive Repository (중앙 코어 아카이브)

본 디렉터리는 **[글 발행용 저장소 순수성 보존 헌법 (Publishing-Only Repository Purity Law)]**에 의거하여, 메인 발행 저장소(`01_you_idea_blog`)에서 분리된 과거 개발 흔적, 1회성 핫픽스/수정 스크립트, 전략 리포트 및 디버깅 테스트 코드들을 중앙에서 영구 보존하고 통합 관리하는 단일 아카이브입니다.

---

## 📁 디렉터리 구조 및 아카이빙 내역

1. **`legacy_scripts/` (26개 파일)**
   - 초기 플랫폼 설정, 1회성 배치 발행, 일회성 DB/포스트 핫픽스 스크립트 및 이전 JSON 큐:
     - `add_category.py`, `setup_all_categories.py`: 초기 카테고리 설정 스크립트
     - `audit_posts_all.py`, `check_posts.py`, `check_post_public.py`: 초기 포스트 수동 검증 스크립트
     - `batch_update_all_posts.py`, `test_update_single_post.py`, `map_posts_to_edit.py`, `inspect_posts_for_edit.py`: 과거 포스트 일괄 업데이트 스크립트
     - `fix_*.py` (`fix_post60_public.py`, `fix_public_v2.py`, `fix_to_public_definitive.py`, `fix_visibility.py`): 공개 상태 긴급 패치 스크립트
     - `force_public.py`, `force_public_final.py`, `set_post_public.py`, `login_and_fix_public.py`: 공개 속성 강제 변경 스크립트
     - `clean_docker_duplicate.py`, `remove_duplicate_post.py`: 중복 포스트 정리 스크립트
     - `publish_queue.json`, `scheduler.py`: SQLite 도입 이전 사용된 초기 JSON 큐 스케줄러
     - `publish_remaining_batch.py`, `publish_series4.py`: 과거 배치 발행 스크립트
     - `test_render_graphics.py`: 그래픽 렌더링 수동 테스트 도구
     - `update_targets.json`: 과거 수정 대상 목록 JSON

2. **`legacy_tests/` (28개 파일)**
   - Playwright 기반의 초기 에디터 DOM 분석, 클립보드 주입 검증, 마크다운 모드 전환 디버깅 등 과거 1회성 테스트 스크립트들:
     - `check_actual_edit.py`, `check_article_content.py`, `check_first_post_view.py`, `check_mode.py`, `check_publish_endpoint.py`, `check_publish_handler.py`, `check_status.py`, `clean_posts_via_ui.py`, `cleanup_dummy_posts.py`, `delete_all_dummy_posts.py`, `find_delete_button.py`, `find_mode_elements.py`, `find_mode_selector.py`, `find_post_models.py`, `inspect_bulk_button.py`, `inspect_editor_form.py`, `inspect_textarea_1.py`, `test_clipboard_flow.py`, `test_codemirror.py`, `test_db_multiplatform.py`, `test_insert_content.py`, `test_keyboard_input.py`, `test_live_status.py`, `test_markdown_mode.py`, `test_markdown_publish.py`, `trace_publish.py`, `verify_post.py`, `capture_payload.py`

3. **`scratch/` (14개 파일)**
   - 티스토리 수정 링크 추출, DOM 덤프, 일시적 매핑 및 임시 계획 파일들:
     - `audit_all_blogs_complete.py`, `dump_all_links.py`, `dump_manage_posts_dom.py`, `final_update_plan.json`, `find_tistory_edit_links.py`, `get_all_reserved_edit_urls.py`, `inspect_tistory_reserved.py`, `map_posts_to_files.py`, `test_publish_layer_on_edit.py`, `test_single_post_edit.py`, `test_update_post_145.py`, `tistory_reserved_mapping.json`, `update_all_reserved_posts.py`, `update_db_record.py`

4. **`reports/` (5개 파일)**
   - 프로젝트 초기 전략 분석 및 플랫폼 기획 보고서:
     - `dev_blog_anti_ai_audit_report.md`: 글로벌 개발 블로그 안티 AI 감사 보고서
     - `tech_blog_architecture_monetization_strategy.md`: 기술 블로그 아키텍처 및 수익화 전략
     - `naver_blog_analysis/infopiece_strategy_report.md`: 건강 블로그 기획 보고서
     - `naver_blog_analysis/naver_blog_hybrid_strategy_report.md`: 네이버 하이브리드 워크플로우 전략 보고서
     - `naver_blog_analysis/naver_blog_minimal_intervention_pipeline_report.md`: 네이버 최소 개입 파이프라인 보고서

5. **`legacy_posts/` (6개 파일)**
   - 초기 테스트용 및 임시 파편 파일:
     - `posts/sample_post.md`: 최초 셋업 테스트용 샘플 포스트
     - `posts/table_copy.html`: 에디터 표 복사 테스트용 HTML
     - `posts/naver_solidlog_01.txt`, `posts/naver_infopiece_01.txt`: 네이버 포스트 초기 텍스트 초안
     - `posts_dev/02_postgres_deadlock_troubleshooting.md`, `posts_dev/03_kubernetes_pod_eviction_ephemeral_storage.md`: 개발 블로그 레포 분리 이전 초기 드래프트 원고

6. **`screenshots/` (127개 파일)**
   - 과거 티스토리 에디터 자동화, 로그인, 마크다운 주입 및 발행 과정에서 발생한 디버깅 및 실행 상태 캡처 이미지 전량.

---

## 🔒 격리 및 보존 원칙
- 본 디렉터리의 코드는 과거 기록 및 참조용(Historical Archive)으로 영구 보존됩니다.
- 코어 시스템의 단위/통합 테스트 스위트(`pytest`)는 `pyproject.toml`의 `testpaths = ["tests"]` 설정에 따라 오직 `tests/` 디렉터리만을 대상으로 수행되므로, 아카이브 내 과거 테스트 코드가 코어 빌드 및 테스트를 간섭하지 않습니다.
