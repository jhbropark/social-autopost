"""
링크드인 포맷별 게시 테스트/도구.
  python li_formats.py doc     # out/week/0_mon 슬라이드 → PDF 캐러셀(문서) 게시
  python li_formats.py image   # 표지 1장 + 글 게시
  python li_formats.py video   # out/reels/reel.mp4 동영상 게시

환경변수: LI_TARGET(슬라이드 폴더, 기본 out/week/0_mon), LI_FILE(이미지/영상 경로), LI_TEXT(폴백 본문).
가능하면 out/week/plan.json 에서 해당 요일의 실제 LinkedIn 글·주제를 commentary로 사용.
"""
import os
import sys
import glob
import json

import carousel
import platforms


def _commentary(target, fallback):
    plan_path = "out/week/plan.json"
    if os.path.exists(plan_path):
        with open(plan_path, encoding="utf-8") as f:
            plan = json.load(f)
        name = os.path.basename(target.rstrip("/"))
        for p in plan:
            if p.get("_dir") == name:
                return p.get("linkedin", {}).get("text", fallback), p.get("topic", "parkjunhyuk.xyz")
    return fallback, "parkjunhyuk.xyz"


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "doc"
    target = os.environ.get("LI_TARGET", "out/week/0_mon")
    fallback = os.environ.get("LI_TEXT", "공간을 설계하듯, 콘텐츠도 설계합니다. — parkjunhyuk.xyz")
    text, topic = _commentary(target, fallback)

    if cmd == "doc":
        slides = sorted(glob.glob(os.path.join(target, "[0-9]*.jpg")))
        if not slides:
            print("슬라이드 없음:", target); sys.exit(1)
        pdf = carousel.slides_to_pdf(slides, os.path.join(target, "carousel.pdf"))
        print(f"📄 {len(slides)}장 → PDF 캐러셀 게시")
        print("✅ doc:", platforms.post_linkedin_document(pdf, text, title=topic))
    elif cmd == "image":
        img = os.environ.get("LI_FILE", os.path.join(target, "01_cover.jpg"))
        print("✅ image:", platforms.post_linkedin_image(img, text))
    elif cmd == "video":
        vid = os.environ.get("LI_FILE", "out/reels/reel.mp4")
        print("✅ video:", platforms.post_linkedin_video(vid, text))
    else:
        print("usage: python li_formats.py [doc|image|video]"); sys.exit(2)


if __name__ == "__main__":
    main()
