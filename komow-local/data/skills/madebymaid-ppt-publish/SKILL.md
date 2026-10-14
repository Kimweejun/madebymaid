---
name: madebymaid-ppt-publish
description: PPT를 웹 슬라이드(HTML)로 만들어 GitHub 저장소에 올리고 GitHub Pages 주소를 돌려받은 뒤, PPT·HTML·주소를 산출물 정리(outputs\렘·람)로 옮기는 스킬. deck.json을 게시할 때 사용한다.
---

# 웹 게시·산출물 보관 (madebymaid-ppt-publish)

## 한 줄로

```
python "C:\Users\user\Desktop\통합서버\komow-local\ppt\deck.py" publish deck.json
```

마지막 줄에 웹 주소가 출력된다. 그 주소를 사용자에게 알려 준다.

## publish가 하는 일

1. `deck.json` 검사 → `EXP-번호_제목.pptx`를 만들고, PowerPoint로 슬라이드마다 그림을 뽑아 **슬라이드 그림 + 옆 핵심 요약** 웹 페이지 `EXP-번호_제목.html`(그림을 품은 한 파일)을 만든다.
2. 로컬 저장소 `통합서버\madebymaid-reports`에서 `git pull --rebase` 후
   - `EXP-번호/index.html`(웹 슬라이드), `EXP-번호/*.pptx`(내려받기용), `EXP-번호/meta.json`을 넣고
   - 맨 앞 `index.html`(보고서 목록)을 다시 만든다.
3. `git commit` → `git push` (저장된 GitHub 로그인 `Kimweejun` 사용). 확인 없이 바로 올린다 (사용자 허락, 2026-10-14).
4. 웹 주소 `https://kimweejun.github.io/madebymaid-reports/EXP-번호/` 를 정한다. 처음 올린 뒤 1~2분 지나야 열린다.
5. `통합서버\outputs\<렘|람>\`에 `.pptx`, `.html`, `EXP-번호_웹주소.txt`를 복사한다.
   → 30초 안에 산출물 정리로 자동 보관되고, 같은 번호의 실험 카드에 **웹으로 보기** 링크가 붙는다.

## 문제가 생기면

- `git push 실패`: 네트워크·로그인 문제. 오류 문구를 그대로 사용자에게 알리고, 만든 PPT·HTML은 outputs에 직접 복사해 둔다.
- `deck.json 확인 필요`: 적힌 항목을 고치고 다시 실행한다.
- 저장소: https://github.com/Kimweejun/madebymaid-reports (공개). 내부 자료·개인정보·키는 올리지 않는다.
