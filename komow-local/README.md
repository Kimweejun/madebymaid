# 메이드 바이 메이드 (madebymaid)

> 렘(Codex)·람(Claude)이 일하기 전에 읽는 공통 규칙은 상위 폴더의 `AGENTS.md`(Claude는 `CLAUDE.md`가 불러옴)에 있습니다.

렘(GPT)·람(Claude)이 정보를 모아 오고, 실험하고, 결과를 정리해 주는 개인 통합 관리 홈. 로컬 서버(Python 표준 라이브러리)로 돌아갑니다.

## 실행

상위 폴더의 **메이드바이메이드-시작.cmd** / **메이드바이메이드-종료.cmd**. 시작해도 브라우저는 열리지 않습니다.

- 이 PC: http://127.0.0.1:8788
- 같은 네트워크의 휴대폰: `phone-address.txt`의 주소 (아이디 아무거나 + `data/secrets.json`의 `lan_password`). 비밀번호가 없으면 이 PC에만 열립니다. 방화벽 규칙 "MadeByMaid 8788"(같은 네트워크만 허용)이 필요합니다.

## 메뉴와 데이터

| 메뉴 | 데이터 | 갱신 |
|---|---|---|
| 홈 | `/api/local/home` (오늘 숫자, 추천 상위, 마감, 렘·람 작업, 최근 보고서) | 열 때마다 |
| 뉴스룸 | `data/aitimes.json`, `naver.json`, `usnews.json`(DeepL 번역, 월 48만 자 상한), 구독 피드 `feeds.json` | 30분마다 (`collectors.py`) |
| 지원사업 | `data/support.json` (기관 51곳, `support.py` + `support_sources.json`), 관심 공고 `bookmarks.json` | 3시간마다 |
| 커뮤니티 | `data/community_github.json`, `community_reddit.json`, 설정 `community_sources.json` | 30분마다 |
| 작업 공방 | 도구 `app/tools.json`(실행 파일은 `site/komow_app/labs` 등), 실험 `data/experiments.json` | |
| 산출물 정리 | `data/files/` + `../outputs/` 자동 보관 (하위 폴더 = 산출물 폴더) | 30초마다 |
| 스킬관리 | 라이브러리 `../a4ai-import/sources`, 내 스킬 `data/skills/` | |

추천 점수: `scoring.json`(기준표) + `scoring.py`. 스킬 문서 `data/skills/madebymaid-scoring`.

AI 기술·분야 태그: `tags.json`(기준표·도구 태그) + `tagging.py`. 커뮤니티·도구·실험·스킬 박스에 표시, 태그를 누르면 모아 보기, ✎로 고치기(`data/tags_override.json`). 규칙으로 못 정한 미분류는 하루 한 번 렘이 분류(`data/tags_ai.json`).

## 렘·람

- 상태 표시 (`maids.py`): 람 = `~/.clawdex/events.log`, 렘 = `~/.codex/sessions` 를 읽기만 함.
- 맡기기 (`runner.py`): 서버가 렘(Codex CLI)·람(Claude Code CLI)을 직접 실행. 설치 금지, 쓰기는 `../실험실/EXP-번호`·`../outputs`·`../madebymaid-reports`만. 실행 기록은 `../실험실/EXP-번호/run-렘|람.log`.
- 실험하기 흐름: 스킬 `data/skills/madebymaid-experiment`. PPT로 분석하기: `ppt/deck.py` + 스킬 `madebymaid-ppt-*`, `madebymaid-image-gen`. 보고서는 https://kimweejun.github.io/madebymaid-reports/

## 검사

`python test_local.py` (테스트는 렘·람을 실제로 실행하지 않습니다)

이전 꼬물이 화면·도구 서재 포털·사이트 수집 도구는 `../backup/`에 보관했습니다.
