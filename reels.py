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


def _make_video(src, overlay_png, out_path):
    import moviepy.editor as mpe

    tw, th = 1080, 1920
    clip = mpe.VideoFileClip(src).without_audio()
    clip = clip.resize(max(tw / clip.w, th / clip.h))            # 9:16 채움
    x1, y1 = (clip.w - tw) / 2, (clip.h - th) / 2
    clip = clip.crop(x1=x1, y1=y1, width=tw, height=th)          # 중앙 크롭
    if clip.duration < DUR:
        clip = clip.fx(mpe.vfx.loop, duration=DUR)
    else:
        clip = clip.subclip(0, DUR)
    clip = clip.fx(mpe.vfx.colorx, 0.6)                           # 어둡게(텍스트 가독성)

    overlay = mpe.ImageClip(overlay_png).set_duration(DUR)
    final = mpe.CompositeVideoClip([clip, overlay], size=(tw, th)).set_duration(DUR)

    audio_codec = None
    if MUSIC and os.path.exists(MUSIC):
        a = mpe.AudioFileClip(MUSIC)
        a = mpe.afx.audio_loop(a, duration=DUR) if a.duration < DUR else a.subclip(0, DUR)
        final = final.set_audio(a)
        audio_codec = "aac"

    final.write_videofile(out_path, fps=30, codec="libx264", audio_codec=audio_codec,
                          preset="medium", bitrate="4500k", logger=None)
    clip.close()
    final.close()


def do_make():
    os.makedirs(OUT_DIR, exist_ok=True)
    data = generate.generate_posts(target=_today_kst(), variant=0)
    vq = data.get("image_query") or data.get("topic")
    print("🔎 video query:", vq)
    src = imagesearch.search_video(vq, os.path.join(OUT_DIR, "_src.mp4"))
    if not src:
        print("❌ 스톡 영상 검색 실패(Pexels). PEXELS_API_KEY 확인.")
        sys.exit(1)
    overlay = os.path.join(OUT_DIR, "_overlay.png")
    carousel.render_reel_overlay(data["carousel"]).save(overlay)
    out = os.path.join(OUT_DIR, "reel.mp4")
    _make_video(src, overlay, out)
    print(f"✅ reel.mp4 ({os.path.getsize(out) // 1024} KB) — {data.get('topic')}")
    with open(META, "w", encoding="utf-8") as f:
        json.dump({"caption": data["instagram"]["caption"], "topic": data.get("topic"), "image_query": vq},
                  f, ensure_ascii=False, indent=2)


def do_publish():
    with open(META, encoding="utf-8") as f:
        meta = json.load(f)
    base = os.environ["IMAGE_BASE_URL"].rstrip("/")
    url = f"{base}/reel.mp4?v={os.environ.get('CACHE_BUST', '1')}"
    print("📤 publishing reel:", url)
    print("✅ instagram reel:", platforms.post_reel(url, meta["caption"]))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "make"
    if cmd == "make":
        do_make()
    elif cmd == "publish":
        do_publish()
    else:
        print("usage: python reels.py [make|publish]")
        sys.exit(2)
