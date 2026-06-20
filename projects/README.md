# projects/ — 작품 쇼케이스

실제 프로젝트(미디어아트·전시·공간·AI 크리에이티브)를 nendo식 포트폴리오 톤으로 발행합니다.
매일 자동 생성되는 '생각 콘텐츠'와 별개 트랙입니다.

## 새 작품 올리기
1. `projects/<slug>/` 폴더 생성 (slug는 영문·하이픈, 예: `void-pavilion`)
2. 작품 이미지를 **순서대로** `01.jpg`, `02.jpg` … 로 넣기 (가로/세로 무방, 표지는 자동 크롭)
3. (선택) 영상 `video.mp4` (세로 9:16 권장 — 릴스로도 게시)
4. `project.json` 작성 (아래 형식)
5. 커밋·푸시 → Actions의 **Showcase Publish** 워크플로우에서 `slug` 입력해 실행

## project.json
```json
{
  "name": "작품명",
  "badge": "MEDIA ART",
  "concept_ko": "작품을 한 줄로 설명하는 절제된 컨셉.",
  "concept_en": "One restrained line describing the work.",
  "credits": "Photography: 이름 · Space: 이름 · Tech: 이름",
  "hashtags": "#MediaArt #SpaceDesign #parkjunhyuk",
  "hero": "01.jpg",
  "video": "video.mp4"
}
```
- `hero`/`video`는 선택. `name`·`concept_ko`만 있어도 동작.

## 게시 채널
- **Instagram**: 뉴스카드 대신 **작품 표지 + 원본 이미지 캐러셀** (+ 영상 있으면 릴스)
- **LinkedIn**: 동일 캐러셀을 PDF 문서로
- **Facebook**: 컨셉/크레딧 글

## 톤 (nendo 참고)
- 팔지 말고 **작품이 말하게** — 컨셉은 1~2줄 시적으로.
- **협업자 크레딧**을 꼭 넣어 전문 네트워크·신뢰를 쌓는다.
- 한국어 + **영어 병기**로 글로벌 도달.
