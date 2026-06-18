"""
주단위(월~일 7일) 콘텐츠 계획 생성 + 게시.

사용법:
  python weekly.py generate   # 이번 주 7일치 글 생성 + 캐러셀 렌더 → out/week/<i_en>/, out/week/plan.json
  python weekly.py rerender   # plan.json 의 저장된 내용으로 슬라이드만 다시 렌더(재생성 X)
  python weekly.py publish    # plan.json 읽어 7일치 게시. 환경변수 WEEKLY_PLATFORMS 로 플랫폼 제한 가능
                              #   예) WEEKLY_PLATFORMS=instagram → IG만 게시

요일별 테마/기둥은 config.py 의 전략을 그대로 따른다(날짜 기반 순환).
폴더명은 ASCII(0_mon ...)로 둔다 — IG 미디어 페처가 비ASCII URL을 거부하기 때문.
GitHub Actions(weekly.yml)에서 generate → 슬라이드 커밋/푸시 → publish 순으로 실행.
"""
import os
import sys
import json
import time
import datetime

import generate
import carousel
import platforms

OUT_DIR = "out/week"
PLAN_JSON = os.path.join(OUT_DIR, "plan.json")
WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]
WEEKDAY_EN = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]  # 폴더명용(ASCII)


def _week_dates(base=None):
    """이번 주 월요일~일요일 7개 날짜(KST 기준)."""
    base = base or (datetime.datetime.utcnow() + datetime.timedelta(hours=9))
    monday = base - datetime.timedelta(days=base.weekday())
    return [monday + datetime.timedelta(days=i) for i in range(7)]


def _render_day(i, data):
    """i번째 요일의 캐러셀을 ASCII 폴더에 렌더하고 메타를 채운다."""
    day_name = f"{i}_{WEEKDAY_EN[i]}"
    day_dir = os.path.join(OUT_DIR, day_name)
    os.makedirs(day_dir, exist_ok=True)
    for f in os.listdir(day_dir):           # 이전 슬라이드 정리
        if f.endswith(".jpg"):
            os.remove(os.path.join(day_dir, f))
    slides = carousel.render_carousel(data["carousel"], out_dir=day_dir)
    data["_slides"] = [os.path.basename(p) for p in slides]
    data["_dir"] = day_name
    data["_weekday"] = WEEKDAY_KR[i]
    return len(slides)


def do_generate():
    os.makedirs(OUT_DIR, exist_ok=True)
    plan = []
    for i, d in enumerate(_week_dates()):
        data = generate.generate_posts(target=d)
        n = _render_day(i, data)
        data["_date"] = d.strftime("%Y-%m-%d")
        plan.append(data)
        print(f"✅ {WEEKDAY_KR[i]} ({d.strftime('%m-%d')}): {data.get('topic')}  [{n} slides]")
    with open(PLAN_JSON, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print(f"\n주간 계획 저장: {PLAN_JSON} ({len(plan)}일)")
    return plan


def do_rerender():
    """저장된 plan.json 내용으로 슬라이드만 다시 렌더(콘텐츠 재생성 없음)."""
    with open(PLAN_JSON, encoding="utf-8") as f:
        plan = json.load(f)
    for i, data in enumerate(plan):
        n = _render_day(i, data)
        print(f"re-rendered {data['_dir']} ({data.get('_date')}): {n} slides")
    with open(PLAN_JSON, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)


def _slide_urls(data):
    base = os.environ["IMAGE_BASE_URL"].rstrip("/")
    bust = os.environ.get("CACHE_BUST", "1")
    d = data["_dir"]
    return [f"{base}/{d}/{name}?v={bust}" for name in data["_slides"]]


def do_publish():
    only = os.environ.get("WEEKLY_PLATFORMS")
    allow = {p.strip() for p in only.split(",")} if only else {"linkedin", "facebook", "instagram"}
    print(f"게시 대상 플랫폼: {sorted(allow)}")

    with open(PLAN_JSON, encoding="utf-8") as f:
        plan = json.load(f)

    failed = False
    for idx, data in enumerate(plan):
        print(f"\n=== {data['_weekday']} ({data['_date']}) — {data.get('topic')} ===")

        if "linkedin" in allow:
            try:
                print("✅ linkedin:", platforms.post_linkedin(data["linkedin"]["text"]))
            except Exception as e:
                print("❌ linkedin:", e); failed = True

        if "facebook" in allow:
            if os.environ.get("FB_PAGE_ACCESS_TOKEN"):
                try:
                    print("✅ facebook:", platforms.post_facebook(data["facebook"]["text"]))
                except Exception as e:
                    print("❌ facebook:", e); failed = True
            else:
                print("⏭️ facebook: FB_PAGE_ACCESS_TOKEN 미설정 — 건너뜀")

        if "instagram" in allow:
            try:
                print("✅ instagram:", platforms.post_instagram(data["instagram"]["caption"], _slide_urls(data)))
            except Exception as e:
                print("❌ instagram:", e); failed = True

        if idx < len(plan) - 1:
            time.sleep(8)   # 연속 게시 사이 간격(API 안정성)

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "generate"
    if cmd == "generate":
        do_generate()
    elif cmd == "rerender":
        do_rerender()
    elif cmd == "publish":
        do_publish()
    else:
        print("usage: python weekly.py [generate|rerender|publish]")
        sys.exit(2)
