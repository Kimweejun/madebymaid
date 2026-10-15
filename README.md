# 메이드 바이 메이드 (madebymaid)

나만의 메이드 **렘(GPT·Codex)** 과 **람(Claude·Claude Code)** 이 정보를 모아 오고, 스킬로 실험하고, 만든 결과를 정리해 주는 **개인 통합 관리 홈페이지**입니다. 이 PC에서 도는 로컬 서버(Python 표준 라이브러리, 포트 8788)입니다.

> 이 저장소를 처음 보는 팀원은 이 문서 → [`AGENTS.md`](AGENTS.md)(렘·람 공통 규칙) → [`komow-local/README.md`](komow-local/README.md)(메뉴·데이터 구조) 순서로 읽으면 됩니다.

## 1. 개요

| 축 | 메뉴 | 하는 일 |
|---|---|---|
| 받기 | 뉴스룸 · 지원사업 · 커뮤니티 | AI타임스·네이버·US News, 지원사업 기관 51곳, GitHub·Reddit 수집 + 추천 점수 |
| 만들기 | 작업 공방(도구·실험) · 스킬관리 | 도구 30개, 렘·람에게 실험 맡기기, 스킬 라이브러리·내 스킬 |
| 쌓기 | 산출물 정리 | 결과 파일 자동 보관, 펼쳐 보기 |

- **실험하기**: 실험 번호(`EXP-MMDD-NN`) → 지시문 → 사이트에서 "맡기기"를 누르면 서버가 렘(`codex exec`)·람(`claude -p`)을 직접 실행 → 결과 파일이 `outputs/렘|람`에 생기면 산출물 정리로 자동 보관.
- **실험 종류**: 써보기 · 스킬로 만들기 · 적용 검토 · PPT로 분석하기.
- **PPT로 분석하기**: `komow-local/ppt/deck.py`가 PPT와 웹 슬라이드(슬라이드 옆 핵심 요약)를 만들어 공개 저장소에 게시합니다. 예: https://kimweejun.github.io/madebymaid-reports/
- **작업 로그**: 모든 작업이 `logs/work.jsonl`에 start·step·error·done을 남기고, `/api/local/log`로 기다립니다(상태를 계속 묻지 않음).
- **스킬**: 렘·람이 함께 쓰는 내 스킬 11개가 `komow-local/data/skills/`에 있습니다(목록은 `AGENTS.md` 4절).

## 2. 진행 상황 (2026-10-15 기준)

**완료**
- 홈: 오늘 숫자, 추천 뉴스·지원사업 상위 3개, 마감 임박, 렘·람 작업, 최근 보고서·파일.
- 뉴스룸·커뮤니티 30분, 지원사업 3시간마다 자동 수집 + 추천 점수(지원사업 분야30·지역25·자격15·형태10·기간20).
- 지원사업 ★ 관심 공고, 마감 임박(7일) 모아 보기.
- 실험하기 흐름과 자동 실행(맡기기), 작업 공방 > 실험 탭, 결과 펼쳐 보기(HTML·PDF·Office·한글·마크다운·그림).
- PPT로 분석하기: A4AI 발표 디자인 시스템, 보고서마다 테마 세트, 그래프 4종·사진·도식, GitHub Pages 게시.
- AI 기술 11·분야 8 태그(낱말 규칙 + 직접 고치기 + 미분류는 하루 한 번 렘).
- 같은 와이파이 휴대폰 접속(비밀번호), 다크 테마, 모든 페이지 가운데 정렬, 사이드바 하위 메뉴.
- 렘·람 공통 규칙 문서(`AGENTS.md`), 작업 로그, 로컬 git 기록(`[렘]`·`[람]` 커밋).

**보류**: Threads 수집, 클라우드(GCP) 배포·도메인.

**결정 근거**: 단계별 정리안 `메이드바이메이드_*_정리안.md`.

## 3. 직접 실행하려면 설정해야 하는 것

Windows 10/11 기준입니다.

| 필요한 것 | 왜 | 없으면 |
|---|---|---|
| Python 3.11+ | 서버 전체 | 실행 불가 |
| `pip install python-pptx` | PPT로 분석하기 | PPT 만들기만 안 됨 |
| Microsoft Office (Word·Excel·PowerPoint) | Office 파일 미리보기, PPT 슬라이드 그림 | 해당 미리보기만 안 됨 |
| Microsoft Edge | 도식(SVG)을 그림으로 | 도식만 안 됨 |
| Codex CLI (로그인) | 렘 맡기기 | 렘 자동 실행 안 됨 |
| Claude Code CLI (`/login` 한 번) | 람 맡기기 | 람 자동 실행 안 됨 |
| Git + GitHub 로그인 | PPT 보고서 게시 | 게시만 안 됨 |

**비밀 정보** — 저장소에 없습니다. `komow-local/data/secrets.example.json`을 `secrets.json`으로 복사해 직접 채웁니다.
- `naver_search`: 네이버 검색 API 키(뉴스 수집)
- `deepl`: DeepL API 키(US News 번역)
- `lan_password`: 휴대폰 접속 비밀번호(비우면 이 PC에서만 열림)

**저장소에 없는 것** (용량·저작권·개인 데이터라 `.gitignore`로 뺌): 수집 데이터(`komow-local/data/*.json` 대부분), 작업 공방 도구 실행 파일(`komow-local/site`), 스킬 라이브러리 원본(`a4ai-import`), `outputs`·`실험실`·`logs`. 서버를 켜면 수집 데이터는 다시 모이지만, 도구 실행과 스킬 라이브러리는 원본 자료를 따로 받아야 합니다.

**실행**
1. `메이드바이메이드-시작.cmd` → http://127.0.0.1:8788
2. 끄기: `메이드바이메이드-종료.cmd`
3. 휴대폰 접속: `lan_password`를 넣고, 관리자 PowerShell에서 방화벽 규칙 "MadeByMaid 8788"(같은 네트워크만 허용)을 추가합니다.
4. 검사: `cd komow-local && python test_local.py`

## 4. 함께 고칠 때

- 렘·람(그리고 사람)이 같은 규칙으로 일합니다: [`AGENTS.md`](AGENTS.md).
- 커밋 메시지 앞에 누가 했는지 적습니다: `[렘] …`, `[람] …`.
- `secrets.json`은 절대 커밋하지 않습니다(`git add -f` 금지).
