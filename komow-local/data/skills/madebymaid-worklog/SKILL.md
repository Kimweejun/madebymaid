---
name: madebymaid-worklog
description: 메이드 바이 메이드 작업 로그 스킬. 렘·람에게 맡긴 일이나 서버 작업(수집·게시·그림·태그·파일)의 진행·오류·완료를 확인하거나, 직접 한 작업을 기록할 때 사용한다. 상태를 묻는 대신 로그를 기다린다.
---

# 작업 로그 (madebymaid-worklog)

**상태를 묻지 않는다. 로그를 본다.** 모든 작업이 시작·진행·오류·완료를 한 파일에 남긴다 (사용자 결정 2026-10-15).

- 파일: `통합서버/logs/work.jsonl` (한 줄 = 한 사건, 5MB마다 `work-날짜.jsonl`로 넘어가고 번호는 이어짐)
- 코드: `komow-local/worklog.py` · 렘·람 실행 단계: `komow-local/runner.py`

## 한 줄 형식

```json
{"n": 42, "t": "2026-10-15T01:02:03", "job": "EXP-1015-01", "by": "ram", "ev": "step", "msg": "web: https://…", "ref": "…"}
```

| 칸 | 값 |
|---|---|
| `n` | 순번. 이것보다 큰 것만 받아 오면 새 사건 |
| `job` | `EXP-MMDD-NN`, `TAGS-…`, `collect:aitimes` 등 수집, `outputs`, `preview`, `tags`, `server`, `deck` |
| `by` | `rem` · `ram` · `server` · `user` |
| `ev` | `start` 시작 · `step` 진행 · `error` 오류 · `done` 완료 · `info` 기타 |
| `msg` | 짧게. 진행은 `web: 주소` · `read: 파일` · `write: 파일` · `run: 명령` 꼴 |
| `ref` | 관련 파일 경로나 웹 주소 (있을 때만) |

## 기다리는 법 (렘·람·사용자 공통)

```bash
curl "http://127.0.0.1:8788/api/local/log?after=0&job=EXP-1015-01"
curl "http://127.0.0.1:8788/api/local/log?after=<last>&job=EXP-1015-01&wait=60"
```

- 답은 `{"events": [...], "last": n}`. 다음 요청은 `after=last`.
- `wait=60`이면 새 사건이 생기는 즉시 답하고, 없으면 60초 뒤 빈 목록으로 답한다(최대 120).
- **같은 작업에 `done` 또는 `error`가 나오면 끝**. 그 전까지 `wait=60`으로 반복한다. 1~2초 간격으로 묻지 않는다.
- 서버가 꺼져 있으면 `logs/work.jsonl`의 끝부분을 읽는다.

## 직접 한 작업도 남긴다

사이트 밖에서(Codex·Claude Code 창에서 직접) 일할 때도 시작·완료·오류를 남긴다.

```bash
python komow-local/worklog.py <job> <rem|ram> <start|step|error|done|info> "<짧은 설명>" [ref]
```

예: `python komow-local/worklog.py fix-home ram done "home: top news dedupe" komow-local/workspace.py`

## 무엇이 자동으로 남나

| 작업 | 사건 |
|---|---|
| 맡기기(렘·람 실행) | start → step(웹·파일·명령) → done(마지막 답 요약) 또는 error(오류·로그인 필요·시간 초과) |
| 실험 | 만들기(info), 결과 파일 도착(done, ref=파일·웹 주소), 그림 필요(info), 평가(info) |
| PPT | build(step), 게시 완료(done, ref=웹 주소), deck.json·git 오류(error) |
| 태그 | 미분류 → 렘(info), 분류 완료(done), 직접 고침(info) |
| 수집 | 뉴스·커뮤니티·지원사업 작업마다 start / done(개수) / error |
| 파일 | outputs 자동 보관(info), Office→PDF 미리보기(done/error) |
| 서버 | 켜짐(start) |
