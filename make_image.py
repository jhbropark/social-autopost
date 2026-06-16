"""
오늘의 IG 포스터 카드(1080x1080 JPEG)를 Pillow로 렌더링한다.
브라우저/폰트 설치 없이 CI에서 동작하도록 시스템 한글 폰트를 자동 탐색한다.
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W = H = 1080
BG = (10, 12, 13)
FG = (243, 241, 236)
TEAL = (127, 208, 207)
AMBER = (231, 168, 90)
SUB = (200, 196, 187)
MUTED = (140, 147, 143)

# 한글 폰트 후보 (CI Linux: fonts-noto-cjk / Windows: malgun)
FONT_CANDIDATES_BOLD = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "fonts/NotoSansKR-Bold.ttf",
    "C:/Windows/Fonts/malgunbd.ttf",
    "C:/Windows/Fonts/malgun.ttf",
]
FONT_CANDIDATES_REG = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "fonts/NotoSansKR-Regular.ttf",
    "C:/Windows/Fonts/malgun.ttf",
]


def _font(candidates, size):
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    """공백 단위 줄바꿈. \\n은 강제 줄바꿈."""
    lines = []
    for para in text.split("\n"):
        words = para.split(" ")
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if draw.textlength(test, font=font) <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def render(kicker: str, hook: str, sub: str, out_path: str = "out/today.jpg") -> str:
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # 하단 글로우 (앰버/틸) — 블러로 부드럽게
    glow = Image.new("RGB", (W, H), BG)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([W * 0.20, H * 0.74, W * 0.80, H * 1.26], fill=(58, 40, 18))
    gd.ellipse([W * 0.30, H * 0.84, W * 0.70, H * 1.30], fill=(16, 42, 42))
    glow = glow.filter(ImageFilter.GaussianBlur(90))
    img = Image.blend(img, glow, 0.7)
    d = ImageDraw.Draw(img)

    pad = 96
    f_kick = _font(FONT_CANDIDATES_BOLD, 26)
    f_hook = _font(FONT_CANDIDATES_BOLD, 70)
    f_sub = _font(FONT_CANDIDATES_REG, 32)
    f_foot = _font(FONT_CANDIDATES_BOLD, 27)
    f_foot_r = _font(FONT_CANDIDATES_REG, 25)

    y = pad
    # kicker
    d.text((pad, y), kicker.upper(), font=f_kick, fill=TEAL)
    y += 70

    # hook (강조 단어 색 처리는 단순화: 전체 FG, 줄바꿈 처리)
    y += 30
    for line in _wrap(d, hook, f_hook, W - pad * 2):
        d.text((pad, y), line, font=f_hook, fill=FG)
        y += 92

    # sub
    y += 30
    for line in _wrap(d, sub, f_sub, W - pad * 2):
        d.text((pad, y), line, font=f_sub, fill=SUB)
        y += 48

    # footer
    fy = H - pad - 20
    d.text((pad, fy), "parkjunhyuk.xyz", font=f_foot, fill=FG)
    tag = "Space · Media Art · Experience"
    tw = d.textlength(tag, font=f_foot_r)
    d.text((W - pad - tw, fy + 2), tag, font=f_foot_r, fill=MUTED)

    img.save(out_path, "JPEG", quality=92)
    return out_path


if __name__ == "__main__":
    p = render(
        "Creative Director's Notebook / 01",
        "왜 어떤 전시는 5분 만에 빠져나오고,\n어떤 전시는 30분을 머물게 할까?",
        "머무는 시간을 결정한 건 '다음 장면이 궁금한가'였다.",
    )
    print("saved:", p)
