"""
매일 게시: Instagram 총 N개(기본 3) = 캐러셀 (N-R)개 + 릴스 R개, LinkedIn M개(기본 1).
Facebook 은 토큰 있을 때만.

같은 요일 테마 아래에서 variant마다 다른 콘텐츠 기둥으로 서로 다른 글을 생성한다.
  python daily.py generate   # 오늘치 생성(캐러셀 렌더 + 릴스 MP4) → out/daily/, plan.json
  python daily.py publish    # plan.json 읽어 IG(캐러셀+릴스) + LinkedIn 게시

개수 조정(환경변수):
  IG_POSTS_PER_DAY (기본 3), REELS_PER_DAY (기본 1), LINKEDIN_POSTS_PER_DAY (기본 1)
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
import reels
import notion_sync

OUT_DIR = "out/daily"
PLAN_JSON = os.path.join(OUT_DIR, "plan.json")
IG_POSTS = int(os.environ.get("IG_POSTS_PER_DAY", "1"))
REELS = int(os.environ.get("REELS_PER_DAY", "0"))
LINKEDIN_POSTS = int(os.environ.get("LINKEDIN_POSTS_PER_DAY", "1"))
FB_POSTS = int(os.environ.get("FB_POSTS_PER_DAY", "1"))


def _today_kst():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=9)


def _attach_hero(data, day_dir):
    cz = data["carousel"]
    hp = os.path.join(day_dir, "_hero.jpg")
    img = imagesearch.search_image(data.get("image_query") or data.get("topic"))
    if img is not None:
        img.save(hp, "JPEG", quality=88)
    if os.path.exists(hp):
        cz["top_image"] = hp
    else:
        cz.pop("top_image", None)


def _render_carousel(slot, data):
    day_dir = os.path.join(OUT_DIR, slot)
    os.makedirs(day_dir, exist_ok=True)
    for f in os.listdir(day_dir):
        if f.endswith(".jpg") and not f.startswith("_"):
            os.remove(os.path.join(day_dir, f))
    _attach_hero(data, day_dir)
    slides = carousel.render_carousel(data["carousel"], out_dir=day_dir)
    # 페이스북용 카드(주제 헤드라인을 사진 위에 얹어 글과 연결)
    carousel.render_fb_card(data["carousel"], os.path.join(day_dir, "fb_card.jpg"))
    data["_type"], data["_dir"] = "carousel", slot
    data["_slides"] = [os.path.basename(p) for p in slides]
    return len(slides)


def do_generate():
    os.makedirs(OUT_DIR, exist_ok=True)
    today = _today_kst()

    # 시드 우회: out/daily/_seed.json 이 있으면 Claude API 대신 그 콘텐츠로 렌더(크레딧 0).
    seed = None
    seed_path = os.path.join(OUT_DIR, "_seed.json")
    if os.path.exists(seed_path):
        with open(seed_path, encoding="utf-8-sig") as f:
            seed = json.load(f)
        print(f"🌱 시드 콘텐츠({len(seed)}개) 사용 — Claude API 호출 건너뜀")

    def _content(v):
        if seed is not None:
            return dict(seed[v] if v < len(seed) else seed[-1])
        return generate.generate_posts(target=today, variant=v)

    carousels = max(0, IG_POSTS - REELS)
    plan, variant = [], 0

    for i in range(carousels):
        v = variant; variant += 1
        try:   # 한 항목 생성·렌더 실패가 전체 발행을 막지 않게 격리
            data = _content(v)
            n = _render_carousel(str(i), data)
        except Exception as e:
            print(f"⚠ 캐러셀 #{i + 1} 실패 — 건너뜀: {e}")
            continue
        plan.append(data)
        print(f"✅ 캐러셀 #{i + 1}: {data.get('topic')} [{n} slides]")

    for r in range(REELS):
        v = variant; variant += 1
        slot = f"reel{r}"
        try:
            data = _content(v)
            mp4 = reels.build_reel(data, os.path.join(OUT_DIR, slot))
            if mp4:
                data["_type"], data["_dir"], data["_video"] = "reel", slot, "reel.mp4"
                print(f"✅ 릴스 #{r + 1}: {data.get('topic')} ({os.path.getsize(mp4) // 1024} KB)")
            else:   # 영상 실패 시 캐러셀로 폴백
                n = _render_carousel(slot, data)
                print(f"⚠ 릴스 영상 실패 → 캐러셀 폴백 #{r + 1}: {data.get('topic')} [{n} slides]")
            plan.append(data)
        except Exception as e:
            print(f"⚠ 릴스 #{r + 1} 실패 — 건너뜀: {e}")
            continue

    if not plan:
        print("❌ 생성된 게시물이 없음 — 발행할 것이 없습니다.")
        sys.exit(1)

    with open(PLAN_JSON, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    n_reel = sum(1 for p in plan if p.get("_type") == "reel")
    print(f"\n오늘치 저장: IG {len(plan)}개(캐러셀 {len(plan) - n_reel} + 릴스 {n_reel}), LinkedIn {LINKEDIN_POSTS}")
    return plan


def _slide_urls(data):
    base = os.environ["IMAGE_BASE_URL"].rstrip("/")
    bust = os.environ.get("CACHE_BUST", "1")
    return [f"{base}/{data['_dir']}/{name}?v={bust}" for name in data["_slides"]]


def _reel_url(data):
    base = os.environ["IMAGE_BASE_URL"].rstrip("/")
    bust = os.environ.get("CACHE_BUST", "1")
    return f"{base}/{data['_dir']}/{data['_video']}?v={bust}"


def _reel_cover_url(data):
    base = os.environ["IMAGE_BASE_URL"].rstrip("/")
    bust = os.environ.get("CACHE_BUST", "1")
    return f"{base}/{data['_dir']}/cover.jpg?v={bust}"


def _fb_image_url(data):
    """FB 사진 게시용 공개 URL. 주제 헤드라인을 얹은 fb_card 우선, 없으면 hero, 둘 다 없으면 None."""
    d = data.get("_dir", "")
    base = os.environ["IMAGE_BASE_URL"].rstrip("/")
    bust = os.environ.get("CACHE_BUST", "1")
    for name in ("fb_card.jpg", "_hero.jpg"):
        if os.path.exists(os.path.join(OUT_DIR, d, name)):
            return f"{base}/{d}/{name}?v={bust}"
    return None


def do_publish():
    with open(PLAN_JSON, encoding="utf-8") as f:
        plan = json.load(f)

    failed = False
    for i, data in enumerate(plan):
        data["_links"] = {}
        label = "릴스" if data.get("_type") == "reel" else "캐러셀"
        print(f"\n=== IG {label} #{i + 1}: {data.get('topic')} ===")
        try:
            if data.get("_type") == "reel":
                res = platforms.post_reel(_reel_url(data), data["instagram"]["caption"], cover_url=_reel_cover_url(data))
            else:
                res = platforms.post_instagram(data["instagram"]["caption"], _slide_urls(data))
            print("✅ instagram:", res)
            data["_links"]["instagram"] = platforms.ig_permalink(res.get("id"))
        except Exception as e:
            print("❌ instagram:", e); failed = True
        if i < len(plan) - 1:
            time.sleep(8)

    for data in plan[:LINKEDIN_POSTS]:
        print(f"\n=== LinkedIn: {data.get('topic')} ===")
        li_text = data.get("linkedin", {}).get("text", "")
        try:
            # 캐러셀이면 PDF 문서(뉴스카드 표지)로 게시(도달 최상), 아니면 텍스트
            if data.get("_type") == "carousel" and data.get("_slides"):
                day_dir = os.path.join(OUT_DIR, data["_dir"])
                li_cover = carousel.render_li_cover(data["carousel"], os.path.join(day_dir, "li_cover.jpg"))
                li_outro = carousel.render_li_outro(data["carousel"], os.path.join(day_dir, "li_outro.jpg"))
                # IG 표지/아웃트로는 빼고 LinkedIn 전용으로 교체(가운데 포인트 슬라이드는 재사용)
                pdf_slides = [li_cover] + [os.path.join(day_dir, s) for s in data["_slides"][1:-1]] + [li_outro]
                pdf = carousel.slides_to_pdf(pdf_slides, os.path.join(day_dir, "carousel.pdf"))
                res = platforms.post_linkedin_document(pdf, li_text, title=data.get("topic", "parkjunhyuk.xyz"))
                print("✅ linkedin(doc):", res)
            else:
                res = platforms.post_linkedin(li_text)
                print("✅ linkedin:", res)
            urn = res.get("id", "")
            if urn.startswith("urn:"):
                data.setdefault("_links", {})["linkedin"] = f"https://www.linkedin.com/feed/update/{urn}"
        except Exception as e:
            print("❌ linkedin:", e); failed = True

    if os.environ.get("FB_PAGE_ACCESS_TOKEN"):
        for data in plan[:FB_POSTS]:
            print(f"\n=== Facebook: {data.get('topic')} ===")
            fb_text = data.get("facebook", {}).get("text", "") or data.get("linkedin", {}).get("text", "")
            try:
                res = platforms.post_facebook(
                    fb_text, image_url=_fb_image_url(data), link="https://parkjunhyuk.xyz")
                print("✅ facebook:", res)
                pid = res.get("post_id") or res.get("id")
                if pid:
                    data.setdefault("_links", {})["facebook"] = f"https://www.facebook.com/{pid}"
            except Exception as e:
                print("❌ facebook:", e); failed = True
    else:
        print("\n⏭️ facebook: FB_PAGE_ACCESS_TOKEN 미설정 — 건너뜀")

    # Notion 콘텐츠 대시보드에 기록(토큰 있을 때만)
    today = _today_kst().strftime("%Y-%m-%d")
    for data in plan:
        lk = data.get("_links") or {}
        cover = _fb_image_url(data) or (_reel_cover_url(data) if data.get("_type") == "reel" else None)
        if notion_sync.upsert(data, links=lk, status="발행됨" if any(lk.values()) else "실패",
                              cover_url=cover, date=today):
            print(f"🗂  Notion 기록: {str(data.get('topic'))[:30]}")

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
