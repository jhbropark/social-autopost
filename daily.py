"""
매일 게시: Instagram N개(기본 3) + LinkedIn M개(기본 1) + Facebook(토큰 있을 때만).

같은 요일 테마 아래에서 variant마다 다른 콘텐츠 기둥으로 서로 다른 글을 생성한다.
  python daily.py generate   # 오늘치 N개 생성 + 캐러셀 렌더 → out/daily/<i>/, out/daily/plan.json
  python daily.py publish    # plan.json 읽어 IG 전체 + LinkedIn 앞 M개 게시

개수 조정: 환경변수 IG_POSTS_PER_DAY(기본 3), LINKEDIN_POSTS_PER_DAY(기본 1).
"""
import os
import sys
import json
import time
import datetime

import generate
import carousel
import platforms
import imagesearch

OUT_DIR = "out/daily"
PLAN_JSON = os.path.join(OUT_DIR, "plan.json")
IG_POSTS = int(os.environ.get("IG_POSTS_PER_DAY", "3"))
LINKEDIN_POSTS = int(os.environ.get("LINKEDIN_POSTS_PER_DAY", "1"))


def _today_kst():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=9)


def _attach_hero(data, day_dir, fetch):
    cz = data["carousel"]
    hp = os.path.join(day_dir, "_hero.jpg")
    if fetch:
        img = imagesearch.search_image(data.get("image_query") or data.get("topic"))
        if img is not None:
            img.save(hp, "JPEG", quality=88)
    if os.path.exists(hp):
        cz["top_image"] = hp
    else:
        cz.pop("top_image", None)


def _render(i, data, fetch=True):
    day_dir = os.path.join(OUT_DIR, str(i))
    os.makedirs(day_dir, exist_ok=True)
    for f in os.listdir(day_dir):                # 슬라이드만 정리(_hero 보존)
        if f.endswith(".jpg") and not f.startswith("_"):
            os.remove(os.path.join(day_dir, f))
    _attach_hero(data, day_dir, fetch)
    slides = carousel.render_carousel(data["carousel"], out_dir=day_dir)
    data["_slides"] = [os.path.basename(p) for p in slides]
    data["_dir"] = str(i)
    return len(slides)


def do_generate():
    os.makedirs(OUT_DIR, exist_ok=True)
    today = _today_kst()
    plan = []
    for i in range(IG_POSTS):
        data = generate.generate_posts(target=today, variant=i)
        n = _render(i, data)
        plan.append(data)
        print(f"✅ #{i + 1}: {data.get('topic')}  [{n} slides] 🖼 {data.get('image_query')}")
    with open(PLAN_JSON, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print(f"\n오늘치 계획 저장: {PLAN_JSON} (IG {len(plan)}개)")
    return plan


def _slide_urls(data):
    base = os.environ["IMAGE_BASE_URL"].rstrip("/")
    bust = os.environ.get("CACHE_BUST", "1")
    return [f"{base}/{data['_dir']}/{name}?v={bust}" for name in data["_slides"]]


def do_publish():
    with open(PLAN_JSON, encoding="utf-8") as f:
        plan = json.load(f)

    failed = False
    # Instagram: 전체(IG_POSTS개)
    for i, data in enumerate(plan):
        print(f"\n=== IG #{i + 1}: {data.get('topic')} ===")
        try:
            print("✅ instagram:", platforms.post_instagram(data["instagram"]["caption"], _slide_urls(data)))
        except Exception as e:
            print("❌ instagram:", e); failed = True
        if i < len(plan) - 1:
            time.sleep(8)

    # LinkedIn: 앞에서 LINKEDIN_POSTS개만
    for data in plan[:LINKEDIN_POSTS]:
        print(f"\n=== LinkedIn: {data.get('topic')} ===")
        try:
            print("✅ linkedin:", platforms.post_linkedin(data["linkedin"]["text"]))
        except Exception as e:
            print("❌ linkedin:", e); failed = True

    # Facebook: 토큰 있을 때만(현재 미설정 → 건너뜀)
    if os.environ.get("FB_PAGE_ACCESS_TOKEN"):
        for data in plan[:LINKEDIN_POSTS]:
            try:
                print("✅ facebook:", platforms.post_facebook(data["facebook"]["text"]))
            except Exception as e:
                print("❌ facebook:", e); failed = True
    else:
        print("\n⏭️ facebook: FB_PAGE_ACCESS_TOKEN 미설정 — 건너뜀")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "generate"
    if cmd == "generate":
        do_generate()
    elif cmd == "publish":
        do_publish()
    else:
        print("usage: python daily.py [generate|publish]")
        sys.exit(2)
