"""
오케스트레이터.

사용법:
  python main.py generate   # Claude로 글 생성 + 캐러셀 슬라이드 렌더 → out/posts.json, out/carousel/*.jpg
  python main.py publish    # out/posts.json 읽어 LinkedIn/Facebook/Instagram(캐러셀) 게시
  python main.py all        # 생성→게시 한 번에 (로컬 테스트용; IG는 IMAGE_BASE_URL 필요)

GitHub Actions에서는 generate → (슬라이드 커밋/푸시) → publish 순으로 분리 실행한다.
실패한 플랫폼이 있어도 나머지는 계속 진행하고, 마지막에 종합 결과를 출력한다.
"""
import os
import sys
import json

import generate
import carousel
import platforms
import imagesearch

OUT_DIR = "out"
CAROUSEL_DIR = os.path.join(OUT_DIR, "carousel")
POSTS_JSON = os.path.join(OUT_DIR, "posts.json")


def do_generate():
    os.makedirs(OUT_DIR, exist_ok=True)
    # 이전 슬라이드 정리 (장수 변동 대비)
    if os.path.isdir(CAROUSEL_DIR):
        for f in os.listdir(CAROUSEL_DIR):
            if f.endswith(".jpg") and not f.startswith("_"):
                os.remove(os.path.join(CAROUSEL_DIR, f))

    data = generate.generate_posts()
    # 표지 배경 사진 검색(주제 키워드) → top_image 연결
    os.makedirs(CAROUSEL_DIR, exist_ok=True)
    hero = imagesearch.search_image(data.get("image_query") or data.get("topic"))
    if hero is not None:
        hp = os.path.join(CAROUSEL_DIR, "_hero.jpg")
        hero.save(hp, "JPEG", quality=88)
        data["carousel"]["top_image"] = hp
        print("🖼  hero:", data.get("image_query"))
    slides = carousel.render_carousel(data["carousel"], out_dir=CAROUSEL_DIR)
    data["_slides"] = [os.path.basename(p) for p in slides]   # 게시 순서 보존

    with open(POSTS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("✅ generated:", data.get("topic"))
    print(f"   carousel → {len(slides)} slides in {CAROUSEL_DIR}")
    return data


def _slide_urls(data):
    """커밋된 슬라이드의 공개 raw URL 목록 (게시 순서대로)."""
    base = os.environ["IMAGE_BASE_URL"].rstrip("/")
    bust = os.environ.get("CACHE_BUST", "1")
    return [f"{base}/{name}?v={bust}" for name in data["_slides"]]


def do_publish(data=None):
    if data is None:
        with open(POSTS_JSON, encoding="utf-8") as f:
            data = json.load(f)

    results = {}

    # LinkedIn
    try:
        results["linkedin"] = ("ok", platforms.post_linkedin(data["linkedin"]["text"]))
    except Exception as e:
        results["linkedin"] = ("FAIL", str(e))

    # Facebook — 페이지 토큰이 있을 때만 게시(없으면 건너뜀. Meta 페이지 토큰 발급 전까지)
    if os.environ.get("FB_PAGE_ACCESS_TOKEN"):
        try:
            results["facebook"] = ("ok", platforms.post_facebook(data["facebook"]["text"]))
        except Exception as e:
            results["facebook"] = ("FAIL", str(e))
    else:
        results["facebook"] = ("skip", "FB_PAGE_ACCESS_TOKEN 미설정 — 건너뜀")

    # Instagram (캐러셀: 공개 슬라이드 URL 목록 필요)
    try:
        urls = _slide_urls(data)
        results["instagram"] = ("ok", platforms.post_instagram(data["instagram"]["caption"], urls))
    except Exception as e:
        results["instagram"] = ("FAIL", str(e))

    print("\n=== 게시 결과 ===")
    failed = False
    marks = {"ok": "✅", "skip": "⏭️", "FAIL": "❌"}
    for k, (status, info) in results.items():
        print(f"{marks.get(status, '❌')} {k}: {info}")
        if status == "FAIL":   # skip은 실패로 보지 않음
            failed = True
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "generate":
        do_generate()
    elif cmd == "publish":
        do_publish()
    elif cmd == "all":
        do_publish(do_generate())
    else:
        print("usage: python main.py [generate|publish|all]")
        sys.exit(2)
