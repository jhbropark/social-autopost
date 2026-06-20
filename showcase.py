"""
작품 쇼케이스(nendo식) 게시 — 실제 프로젝트를 포트폴리오 톤으로 발행.

준비: projects/<slug>/ 폴더에
  - 작품 이미지: 01.jpg, 02.jpg ... (ASCII 파일명, 순서대로)
  - (선택) 영상: video.mp4
  - project.json:
      {
        "name": "작품명",
        "badge": "MEDIA ART",                 // 표지 태그
        "concept_ko": "한 줄 컨셉(한국어)",
        "concept_en": "One-line concept (English)",
        "credits": "Photography: ... · Space: ...",
        "hashtags": "#MediaArt #SpaceDesign",
        "hero": "01.jpg",                       // 선택(표지 배경, 기본 첫 이미지)
        "video": "video.mp4"                    // 선택(있으면 릴스로도 게시)
      }

사용:
  python showcase.py render <slug>    # 표지 생성 + 슬라이드 구성
  python showcase.py publish <slug>   # IG 캐러셀(+영상 릴스) + LinkedIn 문서 + Facebook 글
"""
import os
import sys
import json
import glob

import carousel
import platforms

ROOT = "projects"


def _load(slug):
    base = os.path.join(ROOT, slug)
    with open(os.path.join(base, "project.json"), encoding="utf-8-sig") as f:
        meta = json.load(f)
    imgs = sorted(glob.glob(os.path.join(base, "[0-9]*.jpg")) + glob.glob(os.path.join(base, "[0-9]*.png")))
    return base, meta, imgs


def _caption(meta):
    parts = [meta.get("concept_ko", "").strip()]
    if meta.get("concept_en"):
        parts += ["", meta["concept_en"].strip()]
    if meta.get("credits"):
        parts += ["", "—", meta["credits"].strip()]
    if meta.get("hashtags"):
        parts += ["", meta["hashtags"].strip()]
    return "\n".join(parts).strip()


def render(slug):
    base, meta, imgs = _load(slug)
    if not imgs:
        print("작품 이미지 없음:", base); sys.exit(1)
    hero = os.path.join(base, meta.get("hero") or os.path.basename(imgs[0]))
    carousel.render_showcase_cover(meta, hero, os.path.join(base, "00_cover.jpg"))
    print(f"✅ 쇼케이스 '{meta.get('name')}' — 표지 + 작품 {len(imgs)}장")
    return base, meta, imgs


def publish(slug):
    base, meta, imgs = _load(slug)
    if not os.path.exists(os.path.join(base, "00_cover.jpg")):
        render(slug)
    names = ["00_cover.jpg"] + [os.path.basename(p) for p in imgs]
    base_url = os.environ["IMAGE_BASE_URL"].rstrip("/") + "/" + slug
    bust = os.environ.get("CACHE_BUST", "1")
    urls = [f"{base_url}/{n}?v={bust}" for n in names]
    cap = _caption(meta)
    failed = False

    print(f"\n=== 쇼케이스 게시: {meta.get('name')} ===")
    try:
        print("✅ instagram:", platforms.post_instagram(cap, urls))
    except Exception as e:
        print("❌ instagram:", e); failed = True

    if meta.get("video"):
        try:
            v = f"{base_url}/{meta['video']}?v={bust}"
            c = f"{base_url}/00_cover.jpg?v={bust}"
            print("✅ instagram reel:", platforms.post_reel(v, cap, cover_url=c))
        except Exception as e:
            print("❌ instagram reel:", e); failed = True

    try:
        pdf = carousel.slides_to_pdf([os.path.join(base, n) for n in names], os.path.join(base, "showcase.pdf"))
        print("✅ linkedin(doc):", platforms.post_linkedin_document(pdf, cap, title=meta.get("name", "parkjunhyuk.xyz")))
    except Exception as e:
        print("❌ linkedin:", e); failed = True

    if os.environ.get("FB_PAGE_ACCESS_TOKEN"):
        try:
            print("✅ facebook:", platforms.post_facebook(cap))
        except Exception as e:
            print("❌ facebook:", e); failed = True

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    slug = sys.argv[2] if len(sys.argv) > 2 else ""
    if cmd == "render" and slug:
        render(slug)
    elif cmd == "publish" and slug:
        publish(slug)
    else:
        print("usage: python showcase.py [render|publish] <slug>")
        sys.exit(2)
