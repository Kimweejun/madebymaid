---
name: madebymaid-ppt-analysis
description: 메이드 바이 메이드의 "PPT로 분석하기" 묶음 스킬. 실험 대상(커뮤니티·뉴스 항목)을 분석해 8~12장 PPT와 웹 슬라이드로 만들고, GitHub Pages 주소를 받아 산출물 정리로 넘길 때 사용한다. 디자인·요약·게시 스킬을 순서대로 부른다.
---

# PPT로 분석하기 (madebymaid-ppt-analysis)

실험하기에서 종류를 **PPT로 분석하기**로 고르면 렘·람이 이 스킬을 따른다. 아래 세 스킬을 **순서대로** 읽고 지킨다.

| 순서 | 스킬 | 하는 일 |
|---|---|---|
| 1 | `madebymaid-ppt-summary` | 대상을 조사하고, 슬라이드 구성·핵심 요약·결론을 `deck.json`으로 쓴다 |
| 2 | `madebymaid-ppt-design` | A4AI 발표 디자인 시스템 틀 확인, 보고서에 맞는 테마 세트(`theme`) 고르기 (모양은 `deck.py`가 맞춰 줌, 로고 없음) |
| 3 | `madebymaid-ppt-publish` | `deck.py publish`로 PPT·웹 슬라이드를 만들고 git에 올려 주소를 받는다 |

스킬 위치: `komow-local/data/skills/<이름>/SKILL.md` · 도구: `komow-local/ppt/deck.py`

## 순서

1. 작업 폴더 `통합서버\실험실\EXP-번호`를 만든다 (없으면).
2. 대상 링크를 읽고 조사한다. 필요하면 작업 폴더 안에서만 내려받거나 실행한다 (설치 전에는 사용자 확인).
3. `madebymaid-ppt-summary` 규칙대로 작업 폴더에 `deck.json`을 쓴다. 기사·자료 사진은 작업 폴더에 내려받아 `visual.file`로 넣고, 숫자 비교는 그래프로, 구조·흐름·인과는 `madebymaid-diagram-design`으로 도식을 그려 `visual.type: diagram`으로 넣는다 (본문 3장마다 1개 이상).
4. `python "C:\Users\user\Desktop\통합서버\komow-local\ppt\deck.py" build deck.json` 으로 먼저 만들어 보고, 오류 문구가 나오면 고친다.
5. `python "...\deck.py" publish deck.json` — git에 바로 올린다 (사용자가 자동 게시를 허락함, 2026-10-14).
6. 출력된 웹 주소를 사용자에게 알려 준다.

## 결과가 가는 곳

- 웹 슬라이드: `https://kimweejun.github.io/madebymaid-reports/EXP-번호/` (공개 저장소 `Kimweejun/madebymaid-reports`)
- `통합서버\outputs\렘|람\`: `EXP-번호_제목.pptx`, `EXP-번호_제목.html`, `EXP-번호_웹주소.txt`
- 산출물 정리에 자동 보관되고, 작업 공방 > 실험 카드에 **웹으로 보기** 링크가 붙는다.

## 지킬 것

- 분석 대상은 **실험 대상(공개된 커뮤니티·뉴스 자료)** 만. 회사 내부 자료·개인정보·키는 넣지 않는다 (공개 저장소에 올라감).
- 분량은 표지·목차·결론 포함 **8~12장** (본문 5~9장).
