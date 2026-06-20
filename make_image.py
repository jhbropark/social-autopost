"""
오늘의 IG 포스터 카드(1080x1350, 4:5 세로 JPEG) 렌더.
참고 디자인: RIMAN 'NEWSROOM' 에디토리얼 템플릿.
  - 다크 차콜 배경 + 상단 그라데이션 패널(선택적 사진)
  - 우상단 세리프 워드마크
  - 세이지 그린 알약형 카테고리 배지
  - 혼합 굵기 헤드라인(강조 볼드 + 보조 라이트 + 거대 키워드)
  - 푸터: 좌측 캡션 + 우측 인덱스 + 구분선
브라우저/외부 폰트 없이 CI(Linux)에서 동작하도록 시스템 폰트를 자동 탐색한다.
"""
import os
import re
import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

# Instagram 피드는 세로 4:5(1080x1350)까지 크롭 없이 표시한다.
# 정사각형(1:1)으로 올리면 피드에서 좌우가 잘리므로 4:5로 렌더한다.
W, H = 1080, 1350

# 팔레트 — 3색 시스템 (#1A1D20 / #F8F9FA / #4169E1)
BG_TOP = (26, 29, 32)         # #1A1D20 (배경)
BG_BOT = (15, 17, 20)         # 같은 계열 더 어둡게(그라데이션 깊이용)
PILL = (65, 105, 225)         # #4169E1 (액센트) — 배지 배경
PILL_TX = (248, 249, 250)     # #F8F9FA
FG = (248, 249, 250)          # #F8F9FA (본문 텍스트)
HEAD_SOFT = (186, 190, 198)   # 흰색 계열 톤다운(보조 텍스트)
CAPTION = (118, 123, 130)     # 더 톤다운(푸터 캡션)
DIVIDER = (44, 48, 54)        # 어두운 계열 구분선

# ---- 폰트 후보 (1순위: 리포 번들 Pretendard / 폴백: Noto, malgun) ----
# Pretendard 를 fonts/ 에 번들 → 한+영 일관, 모던, apt 설치 의존 제거.
F_CJK_BOLD = [
    "fonts/Pretendard-Bold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "fonts/NotoSansKR-Bold.ttf",
    "C:/Windows/Fonts/malgunbd.ttf",
]
F_CJK_XBOLD = [  # 키워드/임팩트용 — 엑스트라볼드
    "fonts/Pretendard-ExtraBold.ttf",
    "fonts/Pretendard-Bold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "C:/Windows/Fonts/malgunbd.ttf",
]
F_CJK_REG = [
    "fonts/Pretendard-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "fonts/NotoSansKR-Regular.ttf",
    "C:/Windows/Fonts/malgun.ttf",
]
F_SERIF = [  # 우상단 워드마크용 세리프
    "C:/Windows/Fonts/georgiab.ttf",
    "C:/Windows/Fonts/georgia.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
]


def _font(cands, size):
    for p in cands:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _greedy_wrap(draw, text, font, max_w):
    """한 줄을 max_w까지 꽉 채우는 단순 그리디 줄바꿈."""
    out = []
    for para in text.split("\n"):
        cur = ""
        for w in para.split(" "):
            t = (cur + " " + w).strip()
            if not cur or draw.textlength(t, font=font) <= max_w:
                cur = t
            else:
                out.append(cur)
                cur = w
        out.append(cur)
    return out


def _wrap(draw, text, font, max_w):
    """줄을 균형 있게 나눈다. 그리디로 필요한 줄 수 n을 구한 뒤,
    n줄을 유지하는 한도에서 폭을 좁혀 줄 길이를 고르게 만든다.
    → 마지막 줄에 짧은 단어만 외톨이로 남거나 조사가 어색하게 끊기는 것을 줄인다.
    단, 명시적 줄바꿈(\\n)이 있으면 그 문단 구분은 보존한다."""
    if "\n" in text:
        out = []
        for para in text.split("\n"):
            out.extend(_wrap(draw, para, font, max_w) if para else [""])
        return out
    base = _greedy_wrap(draw, text, font, max_w)
    n = len(base)
    if n <= 1:
        return base
    lo, hi, best = 1, max_w, base
    while lo <= hi:
        mid = (lo + hi) // 2
        cand = _greedy_wrap(draw, text, font, mid)
        if len(cand) <= n:
            best, hi = cand, mid - 1
        else:
            lo = mid + 1
    return best


def _wrap_sentences(draw, text, font, max_w):
    """본문용: 문장 종결부호(. ? !) 뒤에서 먼저 줄을 나눈 뒤 각 문장을 균형 래핑한다.
    → 한 줄 중간에서 문장이 끝나고 다음 문장이 시작되는 어색함을 없앤다.
    명시적 줄바꿈(\\n)도 문단 경계로 보존한다."""
    out = []
    for para in text.split("\n"):
        para = para.strip()
        if not para:
            out.append("")
            continue
        for sent in re.split(r"(?<=[.?!])\s+", para):
            if sent:
                out.extend(_wrap(draw, sent, font, max_w))
    return out


def _vertical_gradient(top, bottom):
    base = Image.new("RGB", (W, H), top)
    top_c = Image.new("RGB", (W, H), bottom)
    mask = Image.new("L", (1, H))
    for y in range(H):
        mask.putpixel((0, y), int(255 * (y / H)))
    mask = mask.resize((W, H))
    base.paste(top_c, (0, 0), mask)
    return base


def render_hero(w, h, seed=0):
    """주제별로 조금씩 다른 추상 비주얼을 생성한다(외부 의존 없음, CI에서도 동작).
    구성: 어두운 그라데이션 + 블루 라디얼 글로우 + 공간 원근 격자 + 노드 네트워크.
    3색 팔레트(#1A1D20/#F8F9FA/#4169E1) 계열로 통일."""
    rnd = random.Random(seed)

    # 베이스 세로 그라데이션
    base = Image.new("RGB", (w, h), BG_TOP)
    bd = ImageDraw.Draw(base)
    for y in range(h):
        t = y / max(1, h - 1)
        bd.line([(0, y), (w, y)], fill=tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3)))

    cx = int(w * rnd.uniform(0.30, 0.70))
    cy = int(h * rnd.uniform(0.18, 0.42))

    # 블루 라디얼 글로우 (screen 합성)
    glow = Image.new("RGB", (w, h), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([cx - w * 0.55, cy - h * 0.85, cx + w * 0.55, cy + h * 0.85], fill=(24, 38, 82))
    gd.ellipse([cx - w * 0.30, cy - h * 0.45, cx + w * 0.30, cy + h * 0.45], fill=(46, 70, 148))
    gd.ellipse([cx - w * 0.11, cy - h * 0.17, cx + w * 0.11, cy + h * 0.17], fill=(72, 102, 196))
    base = ImageChops.screen(base, glow.filter(ImageFilter.GaussianBlur(80)))

    # 공간 원근 격자(소실점으로 수렴) — 건축/공간 느낌
    grid = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    g2 = ImageDraw.Draw(grid)
    vp = (cx, int(h * 0.40))
    for i in range(-12, 13):
        g2.line([(w / 2 + i * (w / 10), h + 20), vp], fill=(82, 112, 200, 42), width=2)
    for j in range(1, 10):
        yy = vp[1] + (h - vp[1]) * (j / 10) ** 1.8
        g2.line([(0, yy), (w, yy)], fill=(82, 112, 200, int(42 * j / 10)), width=2)
    base = Image.alpha_composite(base.convert("RGBA"), grid)

    # 노드 네트워크(AI/연결) — 상단부
    net = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    n2 = ImageDraw.Draw(net)
    pts = [(rnd.uniform(w * 0.05, w * 0.95), rnd.uniform(h * 0.05, h * 0.60)) for _ in range(rnd.randint(10, 14))]
    for i, p in enumerate(pts):
        for q in pts[i + 1:]:
            dist = math.hypot(p[0] - q[0], p[1] - q[1])
            if dist < w * 0.24:
                n2.line([p, q], fill=(150, 175, 235, int(70 * (1 - dist / (w * 0.24)))), width=1)
    for p in pts:
        r = rnd.choice([2, 3, 3, 4])
        n2.ellipse([p[0] - r * 3, p[1] - r * 3, p[0] + r * 3, p[1] + r * 3], fill=(120, 150, 230, 38))
        n2.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=(226, 233, 248, 215))
    base = Image.alpha_composite(base, net)

    return base.convert("RGB")


def _top_panel(img, top_image=None, panel_h=560):
    """상단 패널: 사진/생성이미지가 있으면 채우고 아래로 어둡게 페이드, 없으면 은은한 글로우.
    top_image 는 파일 경로(str) 또는 PIL.Image 모두 허용."""
    photo = None
    if isinstance(top_image, Image.Image):
        photo = top_image.convert("RGB")
    elif isinstance(top_image, str) and os.path.exists(top_image):
        photo = Image.open(top_image).convert("RGB")
    if photo is not None:
        # 가로 채움 크롭
        ratio = max(W / photo.width, panel_h / photo.height)
        photo = photo.resize((int(photo.width * ratio), int(photo.height * ratio)))
        photo = photo.crop((0, 0, W, panel_h))
        img.paste(photo, (0, 0))
        # 가독성: 사진을 전체적으로 어둡게(약 38%) — 상단 워드마크/대비 확보
        img.paste(Image.new("RGB", (W, panel_h), BG_TOP), (0, 0), Image.new("L", (W, panel_h), 96))
        # 하단 페이드 (패널 → 배경색)
        fade = Image.new("L", (1, panel_h), 0)
        for y in range(panel_h):
            a = max(0.0, (y - panel_h * 0.45) / (panel_h * 0.55))
            fade.putpixel((0, y), int(255 * min(1.0, a)))
        fade = fade.resize((W, panel_h))
        img.paste(Image.new("RGB", (W, panel_h), BG_TOP), (0, 0), fade)
    else:
        glow = Image.new("RGB", (W, H), BG_TOP)
        gd = ImageDraw.Draw(glow)
        gd.ellipse([W * 0.30, -H * 0.18, W * 1.05, panel_h * 0.95], fill=(32, 38, 52))
        gd.ellipse([W * 0.52, -H * 0.05, W * 1.15, panel_h * 0.7], fill=(44, 56, 92))
        glow = glow.filter(ImageFilter.GaussianBlur(110))
        img.paste(Image.composite(glow, img, Image.new("L", (W, H), 150)), (0, 0))
    return img


def _pill(draw, x, y, text, font):
    pad_x, pad_y = 28, 14
    tw = draw.textlength(text, font=font)
    asc, desc = font.getmetrics()
    th = asc + desc
    w, h = tw + pad_x * 2, th + pad_y * 2
    draw.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=PILL)
    draw.text((x + pad_x, y + pad_y - 2), text, font=font, fill=PILL_TX)
    return y + h


def render(badge, head_bold, head_rest, keyword, caption,
           index="01", out_path="out/today.jpg", top_image=None):
    """
    badge      : 알약 배지 텍스트 (영문 대문자 권장, 예 'MEDIA ART')
    head_bold  : 강조 헤드라인(볼드) 한 줄
    head_rest  : 보조 헤드라인(라이트) — str 또는 list[str]
    keyword    : 거대 키워드/결론 한 줄 (엑스트라볼드)
    caption    : 푸터 좌측 캡션
    index      : 푸터 우측 번호
    top_image  : 상단 패널에 넣을 사진 경로(선택)
    """
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    if isinstance(head_rest, str):
        head_rest = [head_rest]

    img = _vertical_gradient(BG_TOP, BG_BOT)
    img = _top_panel(img, top_image=top_image)
    d = ImageDraw.Draw(img)

    pad = 88
    f_mark = _font(F_SERIF, 40)
    f_badge = _font(F_CJK_BOLD, 24)
    f_bold = _font(F_CJK_BOLD, 58)
    f_soft = _font(F_CJK_REG, 50)
    f_key = _font(F_CJK_XBOLD, 92)
    f_cap = _font(F_CJK_REG, 24)
    f_idx = _font(F_CJK_BOLD, 26)

    # 우상단 워드마크
    mark = "parkjunhyuk.xyz"
    mw = d.textlength(mark, font=f_mark)
    d.text((W - pad - mw, 58), mark, font=f_mark, fill=FG)

    # 배지
    y = _pill(d, pad, 525, badge.upper(), f_badge)
    y += 30

    # 강조 헤드라인 (볼드)
    for line in _wrap(d, head_bold, f_bold, W - pad * 2):
        d.text((pad, y), line, font=f_bold, fill=FG)
        y += 72
    # 보조 헤드라인 (라이트)
    for raw in head_rest:
        for line in _wrap(d, raw, f_soft, W - pad * 2):
            d.text((pad, y), line, font=f_soft, fill=HEAD_SOFT)
            y += 62
    # 거대 키워드
    y += 12
    for line in _wrap(d, keyword, f_key, W - pad * 2):
        d.text((pad, y), line, font=f_key, fill=FG)
        y += 100

    # 푸터: 구분선 + 캡션 + 인덱스
    fy = H - pad + 2
    d.line([(pad, fy - 18), (W - pad, fy - 18)], fill=DIVIDER, width=1)
    d.text((pad, fy), caption, font=f_cap, fill=CAPTION)
    iw = d.textlength(index, font=f_idx)
    d.text((W - pad - iw, fy - 1), index, font=f_idx, fill=CAPTION)

    img.save(out_path, "JPEG", quality=92)
    return out_path


if __name__ == "__main__":
    p = render(
        badge="Space Note",
        head_bold="관람객을 머물게 하는 건",
        head_rest=["자극의 총량이 아니라", "다음 장면에 대한"],
        keyword="궁금증이다",
        caption="Creative Director's Notebook · parkjunhyuk.xyz",
        index="01",
    )
    print("saved:", p)
