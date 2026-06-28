"""
인스타그램 릴스(9:16 영상) 생성 + 게시.

방식 B: Pexels 스톡 세로 영상 위에 에디토리얼 텍스트 오버레이를 합성한다.
  python reels.py make      # 주제 글 생성 → 스톡 영상 검색 → 오버레이 합성 → out/reels/reel.mp4
  python reels.py publish   # out/reels/reel.json 읽어 IG 릴스로 게시

영상 길이: REEL_SECONDS(기본 12). 배경음악: REEL_MUSIC(선택, CC0 mp3 경로) 있으면 입힘.
"""
import os
import sys
import json
import datetime

# moviepy 1.0.3 은 Pillow 10+ 에서 제거된 Image.ANTIALIAS 를 참조한다 → 호환 shim
from PIL import Image as _PILImage
if not hasattr(_PILImage, "ANTIALIAS"):
    _PILImage.ANTIALIAS = _PILImage.Resampling.LANCZOS

import generate
import carousel
import imagesearch
import platforms

OUT_DIR = "out/reels"
META = os.path.join(OUT_DIR, "reel.json")
DUR = int(os.environ.get("REEL_SECONDS", "12"))
MUSIC = os.environ.get("REEL_MUSIC")


def _today_kst():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=9)


TW, TH = 1080, 1920


def _fill_vertical(clip):
    """영상을 1080x1920로 채우고 중앙 크롭."""
    clip = clip.resize(max(TW / clip.w, TH / clip.h))
    return clip.crop(x1=(clip.w - TW) / 2, y1=(clip.h - TH) / 2, width=TW, height=TH)


def _make_video_v2(srcs, beats, out_path):
    """srcs: 스톡영상 경로 리스트, beats: [(overlay_png, seconds), ...].
    배경은 여러 클립을 ~5초씩 컷으로 이어 길이를 채우고 어둡게. 그 위에 비트별 텍스트를 페이드로 올린다."""
    import moviepy.editor as mpe

    total = sum(d for _, d in beats)
    parts, filled, i = [], 0.0, 0
    while filled < total and i < 12:
        src = srcs[i % len(srcs)]
        c = _fill_vertical(mpe.VideoFileClip(src).without_audio())
        seg = min(5.0, c.duration, total - filled)
        if seg <= 0.2:
            i += 1
            continue
        parts.append(c.subclip(0, seg))
        filled += seg
        i += 1
    bg = mpe.concatenate_videoclips(parts, method="compose").subclip(0, total)
    bg = bg.fx(mpe.vfx.colorx, 0.55)

    overlays, t = [], 0.0
    for png, dur in beats:
        overlays.append(mpe.ImageClip(png).set_start(t).set_duration(dur).crossfadein(0.4))
        t += dur

    final = mpe.CompositeVideoClip([bg] + overlays, size=(TW, TH)).set_duration(total)

    audio_codec = None
    if MUSIC and os.path.exists(MUSIC):
        a = mpe.AudioFileClip(MUSIC)
        a = mpe.afx.audio_loop(a, duration=total) if a.duration < total else a.subclip(0, total)
        final = final.set_audio(a.audio_fadeout(0.6))
        audio_codec = "aac"

    final.write_videofile(out_path, fps=30, codec="libx264", audio_codec=audio_codec,
                          preset="medium", bitrate="4500k", logger=None)
    final.close()


def build_reel(data, out_dir):
    """주어진 글(data)로 v2 릴스(0초 훅 + 멀티 비트 키네틱 + 컷)를 out_dir/reel.mp4 로 만든다.
    스톡영상 검색 실패 시 None. (daily.py 등에서 재사용)"""
    os.makedirs(out_dir, exist_ok=True)
    cz = data["carousel"]
    base_q = data.get("image_query") or data.get("topic")
    # 릴스 영상은 '작품 안에 사람 실루엣'이 위치성·저장을 높인다(표지 사진과 달리 인물 허용).
    # 인물 포함 footage 를 먼저 찾고, 부족하면 기본 쿼리로 폴백한다.
    queries = [f"{base_q} people silhouette", base_q]
    print("🔎 video query:", queries[0], "→ 폴백:", base_q)

    # 서로 다른 스톡 클립 최대 3개(컷 전환용)
    srcs = []
    for q in queries:
        for pick in range(4):
            p = imagesearch.search_video(q, os.path.join(out_dir, f"_src{len(srcs)}.mp4"), pick=pick)
            if p:
                srcs.append(p)
            if len(srcs) >= 3:
                break
        if len(srcs) >= 3:
            break
    if not srcs:
        return None

    # 비트 구성: 훅 → 포인트1 → 포인트2 → CTA
    pts = cz.get("points", [])
    beats_spec = [("hook", None, None, None, 4.0)]
    for i, pt in enumerate(pts[:2], 1):
        beats_spec.append(("point", i, pt.get("title"), pt.get("body"), 4.0))
    beats_spec.append(("cta", None, None, None, 3.0))

    beats = []
    for idx, (kind, n, title, body, dur) in enumerate(beats_spec):
        png = os.path.join(out_dir, f"_beat{idx}.png")
        carousel.render_reel_card(cz, kind, n=n, title=title, body=body).save(png)
        beats.append((png, dur))

    out = os.path.join(out_dir, "reel.mp4")
    _make_video_v2(srcs, beats, out)

    # 썸네일(커버): 훅 구간(텍스트 있는 시점) 프레임을 추출 → cover.jpg
    import moviepy.editor as mpe
    clip = mpe.VideoFileClip(out)
    clip.save_frame(os.path.join(out_dir, "cover.jpg"), t=min(1.8, clip.duration / 3))
    clip.close()

    for s in srcs:                       # 큰 원본 영상은 커밋하지 않음
        try:
            os.remove(s)
        except OSError:
            pass
    return out


def do_make():
    data = generate.generate_posts(target=_today_kst(), variant=0)
    out = build_reel(data, OUT_DIR)
    if not out:
        print("❌ 스톡 영상 검색 실패(Pexels). PEXELS_API_KEY 확인.")
        sys.exit(1)
    print(f"✅ reel.mp4 ({os.path.getsize(out) // 1024} KB) — {data.get('topic')}")
    with open(META, "w", encoding="utf-8") as f:
        json.dump({"caption": data["instagram"]["caption"], "topic": data.get("topic")},
                  f, ensure_ascii=False, indent=2)


def do_publish():
    with open(META, encoding="utf-8") as f:
        meta = json.load(f)
    base = os.environ["IMAGE_BASE_URL"].rstrip("/")
    bust = os.environ.get("CACHE_BUST", "1")
    url = f"{base}/reel.mp4?v={bust}"
    cover = f"{base}/cover.jpg?v={bust}"
    print("📤 publishing reel:", url)
    print("✅ instagram reel:", platforms.post_reel(url, meta["caption"], cover_url=cover))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "make"
    if cmd == "make":
        do_make()
    elif cmd == "publish":
        do_publish()
    else:
        print("usage: python reels.py [make|publish]")
        sys.exit(2)
