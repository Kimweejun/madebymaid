---
name: madebymaid-viewer
description: 메이드 바이 메이드의 결과물 뷰어 스킬. 실험 결과 파일(html, md, PPT·워드·엑셀, 한글, PDF, 이미지, 영상, 텍스트)을 사이트 안에서 펼쳐 보게 하거나, 새 형식을 추가하거나, 산출물 정리로 정확히 이동시키는 기능을 고칠 때 사용한다.
---

# 결과물 뷰어 (madebymaid-viewer)

실험 카드(작업 공방 > 실험)의 결과 파일마다 **펼치기**가 있고, 누르면 카드 안에서 바로 보인다. **산출물에서 보기**는 산출물 정리의 그 파일 줄로 이동해 두 번 반짝인다.

- 화면: `komow-local/app/app.js` (`KINDS`, `fileKind`, `openPreview`, `renderPdf`, `renderHwp`, 산출물 `flash`)
- 서버: `komow-local/server.py` 의 `/api/local/files/<id>?as=view|pdf`
- Office → PDF 변환: `komow-local/preview.py` (캐시 `data/previews/<id>.pdf`, 파일 삭제 시 같이 삭제)

## 형식별 방법

| 형식 | 확장자 | 보여 주는 방법 |
|---|---|---|
| 웹 페이지 | html, htm | 내용을 받아 `sandbox="allow-scripts"` iframe의 `srcdoc`으로. 사이트와 분리된 출처로 실행됨 |
| 마크다운 | md | marked 12.0.2 + DOMPurify 3.1.6(cdnjs)로 HTML로 바꿔 정화 후 표시. 링크는 새 창 |
| PPT·워드·엑셀 | pptx, ppt, docx, doc, rtf, odt, xlsx, xls, ods | `?as=pdf` → 이 PC의 PowerPoint·Word·Excel(COM)로 PDF 변환(읽기 전용, 창 없이, 120초 제한) → pdf.js |
| PDF | pdf | pdf.js 3.11.174(cdnjs)로 쪽마다 canvas (최대 30쪽) |
| 한글 | hwp, hwpx | 작업 공방 한글 뷰어 엔진 `/komow_app/rhwp/package/rhwp.js`(WASM)로 쪽마다 SVG (최대 30쪽) |
| 이미지 | png, jpg, gif, webp, svg, bmp | `<img src="?as=view">` |
| 영상·소리 | mp4, webm, mov, mp3, wav, ogg, m4a | `<video>` / `<audio>` |
| 텍스트 | txt, json, csv, log, yaml, py, js, ts, css | `<pre>` |
| 그 밖 | — | "미리 볼 수 없는 형식" + 받기 |

같은 이름으로 여러 번 올라온 결과는 **가장 최근 파일만** 카드에 보인다. 펼친 미리보기가 있으면 실험 탭의 10초 자동 새로고침은 멈춘다.

## 안전 규칙 (바꾸지 말 것)

- 실행될 수 있는 형식(html, svg, xml)은 `?as=view`라도 **iframe·이미지로 불렸을 때만**(`Sec-Fetch-Dest`) 화면에 보이고, 주소로 직접 열면 내려받기가 된다. 렘·람이 만든 페이지가 이 사이트 권한으로 실행되지 않게 하려는 것.
- 미리보기 응답에는 `Content-Disposition`을 붙이지 않는다 (샌드박스 iframe이 내려받기로 보고 막음).
- 사이트 전체가 `Cross-Origin-Embedder-Policy: require-corp`라서, 미리보기 응답만 `Cross-Origin-Resource-Policy: cross-origin`.
- 변환에 실패한 파일은 서버를 다시 켜기 전까지 다시 시도하지 않는다.

## 새 형식을 더할 때

1. `app.js`의 `KINDS`에 `[정규식, 종류, 표시 이름]` 추가
2. `openPreview`에 그 종류의 표시 방법 추가 (외부 라이브러리는 cdnjs의 **정확한 버전**으로, `loadScript`로 필요할 때만 불러오기)
3. 서버 변환이 필요하면 `preview.py`의 `OFFICE`·`SCRIPT`처럼 추가하고 `?as=pdf`로 받기
4. `python test_local.py`의 `test_file_preview`에 확인 한 줄 추가
