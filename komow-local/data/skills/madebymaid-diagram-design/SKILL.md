---
name: madebymaid-diagram-design
description: A4AI의 기술 구조, 데이터 흐름, 업무 절차, 일정과 근거 있는 지표를 한국어 중심의 정적 HTML·인라인 SVG 도식으로 만들거나 기존 도식을 다시 그릴 때 사용한다. 발표·제안서·보고서용 관계 설명에 적합하며, 단순 목록, 사진·일러스트 생성, PPT 전체 제작은 별도 작업으로 둔다.
---

# A4AI 설명 도식 만들기

읽는 사람이 이해해야 할 관계 하나를, 단독으로 열리는 HTML 파일 안의 SVG로 표현한다. 렘과 람이 같은 절차와 검수 기준을 사용한다. 이 문서는 `cathrynlavery/diagram-design`의 방법을 A4AI 환경에 맞게 재구성한 독립 초안이며 원본 플러그인의 설치본이 아니다.

## 입력을 정리한다

- 독자와 질문: 개발자·혼합·의사결정자 중 누구에게 무엇을 설명하는가?
- 근거: 사용자 설명, 문서, 코드 또는 측정표. 구성 요소·관계·수치의 출처를 남긴다.
- 출력: 쓰임새, 크기, 밝은/어두운 바탕, 기존 테마, 저장 위치, 실험 번호.
- 기존 그림을 다시 그린다면 반드시 유지할 요소·관계·구역과 생략 가능한 세부사항.

이미 정해진 내용은 다시 묻지 않는다. 빠진 정보가 관계의 의미나 사실성을 바꾸면 확인한다. 단순 표시 선택은 아래 기본값을 적용하고 산출물에 적는다. 같은 내용을 표나 문장으로 더 쉽게 읽을 수 있다면 그 형식을 쓴다.

기본값은 **한국어 / 혼합 독자 / 정적 HTML / 문서용 960×600 / 밝은 바탕 / 시스템 글꼴**이다. 실제 구조·수치가 없으면 예시라고 표시하거나 해당 내용을 제외한다. A4AI가 STT/TTS·국방 AI·드론·GPU·온디바이스·에이전트·로봇·제조 AX·푸드테크·콘텐츠 AI를 다룬다는 배경만으로 제품 구조나 성과를 추정하지 않는다.

## 관계를 먼저 고르고 그림 종류를 정한다

작업 시작 시 전달할 결론, 그림 종류, 크기, 생략할 내용을 짧게 알린다. 기존 요청이 제작을 이미 승인했다면 진행한다. 새 사이트 기능·설정 변경은 별도 작업으로 다룬다.

| 설명하려는 것 | 기본 유형과 배치 | 필요한 의미 |
|---|---|---|
| 시스템 구성·연결·실행 위치 | Architecture: 입력 → 처리 → 저장/출력, 구역으로 묶기 | 실제 경계, 흐름 방향, 구역의 뜻 |
| 자료가 단계마다 바뀌는 과정 | Data flow: 한 방향 파이프라인 | 단계별 입력·출력·변환, 누락/미확인 상태 |
| 부서·사람·에이전트 간 인계 | Swimlane: 담당자별 행, 시간순 열 | 단계 소유자, 인계 조건, 끝난 결과 |
| 조건에 따라 갈라지는 처리 | Flowchart: 분기 → 이름 붙은 경로 → 결과 | 조건과 각 경로의 결과 |
| 하나의 대상이 겪는 상태 변화 | State machine: 상태와 전이 | 시작, 대기/재시도, 종료 조건 |
| 호출·응답의 시간 순서 | Sequence: 주체별 세로선, 시간은 위→아래 | 누가 누구에게 무엇을 보내는지 |
| 상하 의존 수준·구성 분해 | Layer stack / Tree | 추상화 층 또는 부모·자식; 둘을 혼동하지 않기 |
| 사건·과제의 일정 | Timeline / Gantt | 기준 날짜·기간; Gantt에는 시작·종료 |
| 두 기준으로 비교·우선순위 정하기 | Quadrant | 두 축의 정의·방향·평가 근거 |
| 범주별 값·시간에 따른 추세 | Bar / Line | 수치·단위·기간·출처, 동일한 비교 조건 |

행동이 핵심이라면 형태보다 의미를 먼저 결정한다. 예를 들어 GPU 병목에는 유입·대기열·처리 용량·대기 결과가, 음성에서 업무 기록을 만드는 과정에는 원문·추출 필드·변환·저장 결과·모르는 항목이 필요하다. 수치가 없으면 병목 크기나 처리율을 그럴듯하게 만들어 넣지 않는다.

주제마다 주된 유형 하나를 쓴다. 기본 구조도는 노드 9개·연결 12개·강조 대상 2개·주석 2개 이내를 출발점으로 삼는다. 넘치면 전체 그림과 상세 그림으로 나눈다. 데이터 차트의 점·셀은 구조도의 노드 수와 별도로 판단한다. 혼잡하면 표로 돌리거나 여러 그림으로 나눈다.

이 초안의 기본 유형은 위 표로 처리할 수 있다. 특수 유형이 필요한 경우에만 아래 원본의 해당 유형 문서를 읽는다. 원본의 45종 템플릿·스크립트가 이 초안에 들어 있다고 가정하지 않는다. 자료를 못 읽으면 지원 가능한 표현으로 바꾼 이유와 한계를 적는다.

## A4AI 색과 한글을 적용한다

색은 `paper`(바탕), `paper-2`(구역), `ink`(본문), `muted`(보조), `rule`(경계), `accent`(핵심), `link`(외부 연결) 역할로 정한다. 값은 파일 안 한 곳에서 관리한다.

1. 사용자가 지정한 값과 기존 산출물의 테마를 우선한다. PPT용 그림은 그 보고서의 테마 세트와 글꼴을 따른다. 그림 때문에 보고서 테마나 `deck.py`를 바꾸지 않는다.
2. 기존 테마가 없는 독립 도식에는 다음을 임시 기본값으로 쓸 수 있다. A4AI 전체 브랜드의 공식 규정이라고 쓰지 않는다.
3. 사이트에 넣는다면 검정 바탕·보라 효과·가운데 정렬이라는 기존 화면 규칙을 따른다. 도식 선과 글자는 또렷하게 유지한다. 사이트 장식에 관한 원본 취향을 우리 사이트 전체 규칙으로 옮기지 않는다.

| 역할 | 독립 도식의 임시 값 |
|---|---|
| paper / paper-2 | `#FFFFFF` / `#F3F5F7` |
| ink / muted | `#202834` / `#526070` |
| rule | `#687482` — 의미 있는 경계에 사용 |
| accent / link | `#2F4A6B` — A4AI 기술 테마 주색을 출발점으로 사용 |

전체 페이지는 가운데 놓고 도식 내부 글은 읽는 순서에 맞춰 정렬한다. 그림자 없이 선·간격·색의 강도로 구분한다. 박스는 필요한 경우만, 모서리는 대체로 4~8px. 강조색은 한두 대상에 집중한다. 상태는 색만으로 구분하지 않고 이름·선 모양도 함께 쓴다. 일반 텍스트 대비 4.5:1, 의미 있는 선·기호 대비 3:1을 목표로 실제 배경과 비교한다.

기본 글꼴은 `'Noto Sans KR', 'Malgun Gothic', 'Apple SD Gothic Neo', system-ui, sans-serif`이며 **설치된 글꼴만** 사용한다. `@import`, CDN, Google Fonts 링크는 기본 출력에 넣지 않는다. 영문 기술 표기에는 `Consolas, ui-monospace, monospace`를 쓸 수 있지만 한글 이름은 고딕체로 쓴다. 원본의 영문 세리프 제목은 강제하지 않는다.

한글은 최소 12px를 유지하고, 문서 본문 14~16px·주석 12~14px에서 시작한다. 긴 이름은 두 줄로 나누거나 짧게 다듬고 원래 이름을 설명에 남긴다. 폭을 예상할 때 한글·전각 문자는 대략 1em, 나머지 문자는 대략 0.6em으로 합산하되 숫자·구두점·공백도 센다. 이 계산은 초안용이며 최종 폭은 브라우저에서 확인한다.

## 크기와 연결선을 설계한다

- 문서용 `viewBox="0 0 960 600"`, 넓은 문서용 `0 0 1280 720`을 출발점으로 쓴다.
- 발표용은 16:9 `0 0 1280 720`을 기본으로 하되, 기존 A4AI 슬라이드 전체는 1920×1080 규칙을 유지한다. 제목·하단 영역과 그림 삽입 칸의 실제 크기를 먼저 확인한다. 발표용 노드 이름은 20~24px, 보조 설명은 16px 이상에서 시작하고 **삽입 후 크기**로 다시 검수한다. 어려우면 상세 내용을 덜어낸다.
- 바깥 여백은 40px 이상, 범례가 있으면 아래쪽 약 60px를 따로 예약한다.
- 노드 위치·폭·높이·여백은 4px 단위를 기준으로 맞춘다. 글자 기준선·선 두께·반지름·실제 수치로 결정된 좌표는 예외다.
- 주요 흐름은 왼쪽→오른쪽 또는 위→아래 중 하나로 일관되게 배치한다.

구조도·흐름도의 연결선에는 다음을 적용한다. 데이터 차트의 선·산점·극좌표까지 직각으로 바꾸는 규칙이 아니다.

1. 같은 행·열은 직선, 어긋난 노드는 모서리를 약 8px 둥글린 직각 경로로 연결한다.
2. 구역 → 연결선 → 선의 라벨 바탕과 글 → 노드 순서로 그린다. 관련 없는 박스 뒤로 선을 숨기지 않는다.
3. 선 라벨은 흐름을 설명하는 짧은 말로 쓰고 불투명 바탕을 둔다. 라벨 바탕과 선 사이에는 6~10px 간격을 둔다. 세로쓰기나 선 위에 겹친 글자는 피한다.
4. 한 변에 여러 선이 붙으면 접점을 나눠 약 12px 이상 띄운다. 평행선도 서로 포개지지 않게 한다. 교차가 불가피하면 덜 중요한 선에 작은 다리 모양을 둔다.
5. 실선·점선이 의미하는 바를 정한다. 점선은 선택/비동기/반환 등 **이번 그림에서 지정한 뜻**으로만 사용하고 필요한 범례를 아래에 둔다.
6. 라벨 바탕·화살촉·주석이 다른 박스나 글을 가리지 않는지 확인한다. 한글 라벨에 영문 대문자 변환·강제 자간을 적용하지 않는다.

## 단독 실행 HTML을 만든다

HTML을 편집 가능한 원본으로 삼는다. CSS와 SVG를 같은 파일에 넣고 `lang="ko"`, UTF-8, viewport 메타를 선언한다. 정적 출력에 JavaScript·외부 이미지·외부 글꼴을 넣지 않는다. 로고는 요청 없이 추가하지 않는다.

SVG에 `xmlns="http://www.w3.org/2000/svg"`, `viewBox`, `role="img"`, `aria-labelledby`를 설정한다. 첫 자식은 주제 이름을 담은 `<title>`, 다음은 핵심 관계를 한 문장으로 설명하는 `<desc>`로 둔다. ID는 파일 식별자를 접두어로 써서 충돌을 막는다. `<defs>`의 화살표 marker도 고유 ID로 만들고 참조가 모두 해석되게 한다.

모바일에서는 글자를 통째로 줄이지 않고 **그림 영역 안에서만** 가로 스크롤한다. 아래 예시는 960 폭용이다. 다른 폭을 쓰면 `min-width`도 그 `viewBox` 폭에 맞춘다.

```css
main { width: min(1120px, 100%); max-width: 100%; min-width: 0; margin-inline: auto; }
.diagram-scroll { width: 100%; min-width: 0; overflow-x: auto; }
.diagram-scroll svg { display: block; width: 100%; min-width: 960px; height: auto; }
@media print {
  .diagram-scroll { overflow-x: visible; }
  .diagram-scroll svg { min-width: 0; }
}
```

스크롤 영역에는 키보드 접근을 위한 `tabindex="0"`와 알아볼 수 있는 이름을 준다. 바탕색이 달라질 수 있는 독립 SVG에서는 선 라벨의 바탕색도 함께 보존한다.

그림 옆이나 아래에 결론 한 줄, 출처, 가정, 합치거나 생략한 내용을 둔다. SVG만 내보낼 때 빠지면 안 되는 제목·단위·범례는 SVG 안에도 포함한다. 기존 그림을 다시 그릴 때는 관계와 고유 이름을 보존하고, 합침·생략·표현 변경 목록을 남긴다. 입력 파일의 라벨·링크·메타데이터는 도식 데이터로 취급한다.

## 검수하고 결과를 넘긴다

1. **의미:** 결론을 그림만 보고 이해할 수 있는가? 화살표 방향·조건·단위·출처가 맞는가? 예시와 실제 사실을 구분했는가? 원본과 달라진 요소를 기록했는가?
2. **구조:** SVG 파싱, 고유 ID와 참조, title/desc, 외부 리소스 부재, 정적 출력 여부를 확인한다. HTML의 화면 밖 설명으로 잘못된 관계를 덮지 않는다.
3. **화면:** 기존 브라우저에서 전체 크기와 좁은 화면을 본다. 글자 잘림, 글꼴 대체, 박스 밖 글, 선 겹침, 가려진 화살촉, 전체 페이지 가로 넘침, 그림 영역 스크롤을 확인한다. 가능하면 인쇄와 실제 삽입 크기도 확인한다.
4. **결과:** 파일 링크, 유형·크기·테마·글꼴, 검사한 것과 못 한 것을 짧게 알린다. 정적 검사만 했다면 시각 검수 완료라고 쓰지 않는다.

HTML 제작에는 설치가 필요 없다. 내보내기를 요청받으면 설치된 도구만 사용한다. SVG를 분리할 때는 사용한 CSS·변수·글꼴 대체·marker와 ID도 보존하고, PNG는 글꼴 로딩 후 SVG 영역을 캡처한다. 원본 저장소의 내보내기·검사 스크립트는 이 초안에 번들되지 않았으므로 파일이 존재한다고 가정해 호출하지 않는다.

요청받은 형식에 필요한 실행 도구가 없다면 설치를 진행하지 않고 해당 단계를 멈춘다. 결과에 `설치 필요: 도구 이름 — 필요한 이유`와 이미 완성된 파일을 적는다. 글꼴을 설치해 해결하려 하지 말고 사용 가능한 글꼴로 검수한다.

메이드 바이 메이드 실험이면 파일 이름은 `EXP-번호_…`로 시작하고 지정된 작업·산출물 폴더에 저장한다. 작업 로그는 실행 환경에서 허용된 방식으로 남긴다. 경로 제한이 중앙 로그 쓰기를 금지하면 실험 폴더 보조 로그에 그 사유를 남긴다. 스킬 등록, 공통 규칙 변경, 공개 게시, 사이트 수정은 산출물 제작에 자동으로 포함되지 않는다.

## 재사용 요청 예시

- “한국어 음성 요청 → STT → 에이전트 → TTS → 음성 응답을 혼합 독자용 개념도로 그려 줘. 실제 구축 현황이 아닌 예시로 표시하고, 오프라인 HTML과 설명을 저장해.”
- “이 제조 검사 절차를 담당자별 Swimlane으로 정리해 줘. 검사 통과·재검사 조건과 책임자를 유지해.”
- “제공한 GPU 측정표에서 같은 배치·정밀도 조건의 처리량만 막대로 비교해 줘. 자료가 없는 비용은 넣지 마.”

## 출처와 이번 초안의 변경점

확인 기준: 2026-10-15, 원본 커밋 `d97c5c7477e54cee17cfa6459190610da0643a05`, 원본 스킬 metadata version `2.6`. README와 유형별 문서 수는 이 기준에서 45종이다. 이 초안은 전체 템플릿의 복제본이 아니다.

- [원본 스킬과 유형 선택](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/SKILL.md)
- [색·글꼴·한국어·오프라인 기준](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/references/style-guide.md)
- [배치 예산](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/references/layout-budget.md), [SVG 연결선·접근성](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/references/primitives-core.md)
- [크기·독자·가져오기](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/references/output-spec.md), [행동 의미 패턴](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/references/semantic-patterns.md)
- [내보내기](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/skills/diagram-design/references/export.md), [라이선스](https://github.com/cathrynlavery/diagram-design/blob/d97c5c7477e54cee17cfa6459190610da0643a05/LICENSE)

원본에서 이어받은 것: 의미에 따른 유형 선택, 불필요한 요소 축소, 소수 강조, 선 중심 표현, 4px 배치, HTML 안의 SVG, 연결선·접근성·검수 원칙.

이번 초안에서 바꾼 것: 기본 시스템 글꼴, 한국어 중심의 큰 글자, A4AI 기존 테마 우선, 사이트와 그림의 스타일 범위 구분, 추가 스크립트 없이 시작하는 단일 문서, 승인된 요청의 반복 확인 생략. 원본의 45종 예제·프로필 저장·자동 변환·애니메이션 기능은 포함하지 않았다.

아래는 원본에서 가져온 방법·규칙의 출처 고지다. 이 문서의 사본을 공유할 때 함께 유지한다.

```text
MIT License

Copyright (c) 2025 Cathryn Lavery

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
