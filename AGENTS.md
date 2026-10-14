# 메이드 바이 메이드 — 먼저 읽기 (렘·람 공통)

> 이 문서는 **렘(GPT·Codex)과 람(Claude·Claude Code)이 이 폴더에서 일하기 전에 먼저 읽는 문서**입니다.
> Codex는 `AGENTS.md`, Claude Code는 `CLAUDE.md`(이 문서를 불러옴)로 읽습니다. 두 쪽이 같은 규칙으로 일합니다.
> 마지막 정리: 2026-10-15 (람). 규칙이나 결정이 바뀌면 이 문서부터 고칩니다.

## 1. 무엇을 만드나

**시드**: 나만의 메이드(렘·람)가 정보를 모아 오고, 스킬로 실험하고, 만든 결과를 정리해 주는 개인 통합 관리 홈.

| 축 | 메뉴 | 하는 일 |
|---|---|---|
| 받기 | 뉴스룸 · 지원사업 · 커뮤니티 | AI타임스·네이버·US News, 지원사업 기관 51곳, GitHub·Reddit 수집 + 추천 점수 |
| 만들기 | 작업 공방(도구·실험) · 스킬관리 | 도구 30개, 렘·람에게 실험 맡기기, 스킬 라이브러리·내 스킬 |
| 쌓기 | 산출물 정리 | 결과 파일 자동 보관, 펼쳐 보기 |

주소: 이 PC `http://127.0.0.1:8788` · 같은 네트워크 휴대폰 `komow-local/phone-address.txt` (비밀번호 필요)

## 2. 렘과 람의 합작 (가장 중요)

앞으로의 **스킬 활용, 페이지 수정, 실험 등 모든 작업은 Codex(렘)와 Claude(람)의 합작**으로 이루어집니다.

- **같은 규칙·같은 스킬·같은 파일**을 씁니다. 한쪽만 아는 약속을 만들지 않습니다. 새 약속은 이 문서나 스킬 문서에 적습니다.
- **기본 분담** (사용자가 따로 지시하면 그 지시가 우선)
  - 그림 생성: 렘 (`madebymaid-image-gen`)
  - 태그 미분류 분류(하루 한 번): 렘 (`madebymaid-tagging`)
  - 실험·PPT 분석: 사용자가 고른 쪽, "둘 다"면 같은 번호로 나란히 비교
  - 사이트 코드 수정: 사용자가 맡긴 쪽. 다른 쪽이 만든 코드를 고칠 때는 그 의도를 먼저 읽고, 바꾼 이유를 남김
- **넘겨주기**: 실험 번호(`EXP-MMDD-NN`)와 파일로 주고받습니다. 결과는 `outputs\렘`·`outputs\람`, 작업은 `실험실\EXP-번호`.
- **서로의 작업을 덮어쓰지 않습니다.** 같은 파일을 동시에 고치게 되면 먼저 사용자에게 알립니다.
- 사이트에서 "맡기기"를 누르면 서버가 렘(`codex exec`)·람(`claude -p`)을 화면 없이 직접 실행합니다 (`komow-local/runner.py`).

## 2-1. 작업 로그 — 상태를 묻지 말고 로그를 본다

모든 작업(렘·람 실행, 실험, PPT 게시, 그림, 태그, 수집, 파일 보관)이 `logs/work.jsonl`에 **start · step · error · done**을 남깁니다. 맡긴 일의 상태를 묻지 않습니다.

- 확인: `curl "http://127.0.0.1:8788/api/local/log?after=<마지막 n>&job=<EXP-번호>&wait=60"` → 새 사건이 생기면 바로, 없으면 60초 뒤 답. `done`이나 `error`가 나올 때까지 이것만 반복 (1~2초 간격으로 묻기 금지).
- 스킬 등록·수정, 설정 변경처럼 결과가 남는 일은 모두 로그에 남깁니다 (사이트 버튼으로 한 것은 자동, 직접 파일을 고친 것은 아래 명령으로).
- 직접 한 작업도 남김: `python komow-local/worklog.py <job> <rem|ram> <start|step|error|done> "<짧은 설명>" [ref]`
- 자세한 형식·작업별 사건: 스킬 `madebymaid-worklog`

## 3. 일하는 규칙

1. **한국어**로 답합니다. 사용자에게 쉬운 말로, 결과부터.
2. **구현 전에 정리안**: 새 기능은 시드·축·가지로 정리해 보여 주고 **확인을 받은 뒤** 만듭니다. 이어서 하는 작업도 확인을 받습니다.
3. **스킬로 만들 거리가 생기면 먼저 물어봅니다**: "이걸 스킬로 만들까요?" — 사용자가 좋다고 하면 `komow-local/data/skills/<이름>/SKILL.md`로 만들고 이 문서의 스킬 표에 한 줄 추가합니다.
4. **자동 실행(맡기기)일 때**: 프로그램·패키지를 설치하지 않습니다(필요하면 결과에 "설치 필요: 무엇·왜"). 쓰기는 `실험실\EXP-번호`, `outputs`, `madebymaid-reports`에만. 비밀번호·API 키를 쓰거나 출력하지 않습니다.
5. **비밀 정보**: `komow-local/data/secrets.json`(DeepL·네이버 키, 휴대폰 비밀번호)은 내용을 화면·로그·커밋에 절대 내보내지 않습니다.
6. **공개 게시**: PPT 보고서는 공개 저장소 `Kimweejun/madebymaid-reports`(GitHub Pages)에 **확인 없이 올려도 됩니다**(사용자 허락). 기사 사진은 출처를 적으면 사용 가능. 그 밖의 외부 게시는 사용자에게 먼저 묻습니다.
7. **보류 중**: Threads 수집, GCP 배포·도메인. 사용자가 말하기 전에는 하지 않습니다.
8. **검사**: 코드를 고치면 `komow-local`에서 `python test_local.py`. 테스트가 렘·람을 실제로 실행하지 않게 유지합니다. 서버 반영은 `메이드바이메이드-종료.cmd` → `메이드바이메이드-시작.cmd`.
9. **변경 기록(git, 이 PC 전용·원격 없음)**: 고치기 전에 `git status`·`git log --oneline -5`로 다른 쪽이 바꾼 걸 먼저 봅니다. 고친 뒤에는 작은 단위로 커밋하고 메시지 앞에 누가 했는지 적습니다: `[렘] …` 또는 `[람] …`. 비밀 정보·수집 데이터는 `.gitignore`로 빠져 있으니 강제로 넣지 않습니다(`git add -f` 금지). 원격 저장소를 붙이거나 push하지 않습니다.

## 4. 스킬 (내 스킬 — `komow-local/data/skills/`)

| 스킬 | 언제 |
|---|---|
| `madebymaid-scoring` | 지원사업·뉴스·커뮤니티 추천 점수 (기준표 `scoring.json`) |
| `madebymaid-experiment` | 실험하기 흐름: 번호 → 지시문 → 결과 파일 → 기록 |
| `madebymaid-ppt-analysis` | PPT로 분석하기 묶음 (아래 셋을 순서대로) |
| `madebymaid-ppt-summary` | 슬라이드 구성·핵심 요약·결론·그래프/그림 분량 |
| `madebymaid-ppt-design` | A4AI 발표 디자인 시스템, 테마 세트, 그래프·그림 배치 |
| `madebymaid-ppt-publish` | `ppt/deck.py publish` → GitHub Pages 주소 → outputs |
| `madebymaid-image-gen` | "이미지 생성 대기" 그림 채우기 (기본 렘) |
| `madebymaid-tagging` | AI 기술·분야 태그 (기준표 `tags.json`) |
| `madebymaid-viewer` | 결과물 펼쳐 보기·산출물 위치 이동 |
| `madebymaid-worklog` | 작업 로그 읽기·기다리기·남기기 (상태 묻기 대신) |

스킬 라이브러리(남이 만든 297개)는 `a4ai-import/sources` — 읽기만 합니다.

## 5. 폴더

```
통합서버/
  AGENTS.md · CLAUDE.md          ← 이 문서
  메이드바이메이드-시작.cmd / -종료.cmd
  komow-local/                   사이트 (Python 표준 라이브러리 서버, 포트 8788)
    server.py · workspace.py      서버·API
    collectors.py · support.py    수집 (30분 / 지원사업 3시간)
    scoring.py · scoring.json     추천 점수
    tagging.py · tags.json        태그
    runner.py                     렘·람 자동 실행
    preview.py                    Office → PDF 미리보기
    worklog.py                    작업 로그
    ppt/deck.py                   PPT·웹 슬라이드 만들기·게시
    app/                          화면 (index.html, app.js, app.css)
    data/                         수집 데이터·실험 기록·스킬·비밀 정보
    site/                         작업 공방 도구 실행 파일 (건드리지 않음)
  logs/work.jsonl                작업 로그 (모든 작업의 시작·진행·오류·완료)
  outputs/렘 · outputs/람         결과 파일 → 산출물 정리로 자동 보관
  실험실/EXP-번호                  실험 작업 폴더 (실행 기록 run-렘.log / run-람.log)
  madebymaid-reports/             공개 보고서 저장소 (GitHub Pages)
  a4ai-import/                    스킬 라이브러리 원본·도구 자료
  backup/                         옛 꼬물이 화면·도구 서재 등 보관본
  *_정리안.md                     단계별 정리안 (결정 근거)
```

## 6. 사용자가 정한 것 (요약)

- 렘 = GPT(Codex), 람 = Claude. 메이드 상태는 로컬 기록만 읽음(API 키 없음).
- 추천 점수: 지원사업 분야30·지역25·자격15·형태10·기간20, 마감 임박 7일. 👍/👎는 기준 점검용.
- 실험 종류: 써보기·스킬로 만들기·적용 검토·PPT로 분석하기. 맡기기는 자동 실행, 설치 금지.
- PPT: A4AI 발표 디자인 시스템, 로고 없음, 보고서마다 테마 세트 하나, 핵심 요약은 웹 페이지에서 슬라이드 옆, 본문 3장마다 그래프·그림 1개 이상, 8~12장.
- 태그: AI 기술 11·분야 8, 기준마다 최대 2개, 낱말 규칙 + 직접 고치기 + 미분류는 렘.
- 화면: 다크 테마는 검정 바탕에 보라 효과, 모든 페이지 가운데 정렬.
