"""
캐러셀(여러 장) IG 포스터 렌더러. make_image의 NEWSROOM 톤을 그대로 계승.
구조: 표지(cover) → 포인트 슬라이드 N장 → 아웃트로(outro).

render_carousel(data, out_dir) → 슬라이드 jpg 경로 리스트 반환
data = {
  "badge": "SPACE NOTE",
  "cover_bold": "관람객을 30분",
  "cover_rest": ["머물게 하는"],
  "cover_keyword": "4가지 레버",
  "caption": "Creative Director's Notebook · parkjunhyuk.xyz",
  "points": [{"title": "...", "body": "..."}, ...],   # 3~5개 권장
  "outro_line": "경험을 길게 만드는 건 설계다.",
}
"""
import os
from PIL import Image, ImageDraw
import make_image as M

W = M.W  # 1080 (가로)
H = M.H  # 1350 (세로, 4:5)
ACCENT = (65, 105, 225)   # #4169E1 — 유일한 액센트(번호·구분선·힌트·워드마크)
PAD = 88
LI_SIGNATURE = "Junhyuk Park · parkjunhyuk.xyz   (SEOUL)"   # 링크드인 뉴스카드 서명


def _base():
    img = M._vertical_gradient(M.BG_TOP, M.BG_BOT)
    return img


def _footer(d, caption, right_text):
    fy = H - PAD + 2
    f_cap = M._font(M.F_CJK_REG, 24)
    f_idx = M._font(M.F_CJK_BOLD, 26)
    d.line([(PAD, fy - 18), (W - PAD, fy - 18)], fill=M.DIVIDER, width=1)
    d.text((PAD, fy), caption, font=f_cap, fill=M.CAPTION)
    iw = d.textlength(right_text, font=f_idx)
    d.text((W - PAD - iw, fy - 1), right_text, font=f_idx, fill=M.CAPTION)


def _wordmark(d):
    f = M._font(M.F_SERIF, 38)
    mark = "parkjunhyuk.xyz"
    w = d.textlength(mark, font=f)
    d.text((W - PAD - w, 60), mark, font=f, fill=M.FG)


def render_cover(data, path):
    # 표지 상단: 검색된 주제 사진(top_image). 없으면 단색 글로우 패널로 폴백.
    img = M._top_panel(_base(), top_image=data.get("top_image"))
    d = ImageDraw.Draw(img)
    _wordmark(d)

    badge = data["badge"].upper()
    bold, rest, keyword = data["cover_bold"], data.get("cover_rest", []), data["cover_keyword"]
    maxw = W - PAD * 2
    y_start, y_limit = 600, H - PAD - 130     # 본문 영역(힌트/푸터 위 여백)

    # 텍스트가 길면 폰트를 단계적으로 축소해 세로 영역을 넘지 않게 맞춘다(fit-to-box)
    for scale in (1.0, 0.92, 0.85, 0.78, 0.72, 0.66):
        f_badge = M._font(M.F_CJK_BOLD, 32)
        f_bold = M._font(M.F_CJK_BOLD, int(78 * scale))
        f_soft = M._font(M.F_CJK_REG, int(60 * scale))
        f_key = M._font(M.F_CJK_XBOLD, int(124 * scale))
        lh_bold, lh_soft, lh_key = int(94 * scale), int(74 * scale), int(136 * scale)
        bold_lines = M._wrap(d, bold, f_bold, maxw)
        rest_lines = [ln for raw in rest for ln in M._wrap(d, raw, f_soft, maxw)]
        key_lines = M._wrap(d, keyword, f_key, maxw)
        asc, dsc = f_badge.getmetrics()
        total = (asc + dsc + 28) + 34 + len(bold_lines) * lh_bold \
            + len(rest_lines) * lh_soft + 16 + len(key_lines) * lh_key
        if total <= y_limit - y_start:
            break

    y = M._pill(d, PAD, y_start, badge, f_badge) + 34
    for line in bold_lines:
        d.text((PAD, y), line, font=f_bold, fill=M.FG); y += lh_bold
    for line in rest_lines:
        d.text((PAD, y), line, font=f_soft, fill=M.HEAD_SOFT); y += lh_soft
    y += 16
    for line in key_lines:
        d.text((PAD, y), line, font=f_key, fill=M.FG); y += lh_key
    # 스와이프 힌트
    f_hint = M._font(M.F_CJK_BOLD, 30)
    hint = "밀어서 보기  →"
    hw = d.textlength(hint, font=f_hint)
    d.text((W - PAD - hw, H - PAD - 70), hint, font=f_hint, fill=ACCENT)
    _footer(d, data["caption"], "01")
    img.save(path, "JPEG", quality=92)
    return path


def render_point(data, point, n, total, path):
    img = _base()
    d = ImageDraw.Draw(img)
    f_num = M._font(M.F_CJK_BOLD, 150)
    f_title = M._font(M.F_CJK_BOLD, 58)
    f_body = M._font(M.F_CJK_REG, 40)
    # 큰 번호
    d.text((PAD, 250), f"{n:02d}", font=f_num, fill=ACCENT)
    # 얇은 구분선
    d.line([(PAD, 460), (PAD + 120, 460)], fill=ACCENT, width=4)
    y = 540
    for line in M._wrap(d, point["title"], f_title, W - PAD * 2):
        d.text((PAD, y), line, font=f_title, fill=M.FG); y += 72
    y += 16
    for line in M._wrap_sentences(d, point["body"], f_body, W - PAD * 2):
        d.text((PAD, y), line, font=f_body, fill=M.HEAD_SOFT); y += 56
    _footer(d, data["caption"], f"{n} / {total}")
    img.save(path, "JPEG", quality=92)
    return path


def render_outro(data, path):
    img = M._top_panel(_base(), top_image=data.get("top_image"), panel_h=420)
    d = ImageDraw.Draw(img)
    f_line = M._font(M.F_CJK_BOLD, 56)
    f_mark = M._font(M.F_SERIF, 64)
    f_cta = M._font(M.F_CJK_REG, 34)
    # 결론 문장 (세로 중앙부)
    y = 500
    for line in M._wrap_sentences(d, data["outro_line"], f_line, W - PAD * 2):
        d.text((PAD, y), line, font=f_line, fill=M.FG); y += 72
    # 워드마크 (크게)
    y += 60
    d.text((PAD, y), "parkjunhyuk.xyz", font=f_mark, fill=ACCENT)
    y += 100
    d.text((PAD, y), "저장 · 공유하고, 팔로우하세요", font=f_cta, fill=M.HEAD_SOFT)
    _footer(d, data["caption"], "FIN")
    img.save(path, "JPEG", quality=92)
    return path


def render_reel_overlay(data, w=1080, h=1920):
    """릴스(9:16) 텍스트 오버레이(투명 PNG). 영상 위에 합성된다.
    상/하단 어두운 스크림 + 워드마크 + 본문 블록 + 팔로우 CTA."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(img)
    # 가독성 스크림: 상단 약하게(워드마크), 하단(텍스트 영역) 강하게
    for y in range(h):
        if y < h * 0.16:
            a = int(150 * (1 - y / (h * 0.16)))
        elif y > h * 0.46:
            a = int(205 * ((y - h * 0.46) / (h * 0.54)))
        else:
            a = 0
        sd.line([(0, y), (w, y)], fill=(8, 10, 13, min(210, a)))

    d = ImageDraw.Draw(img)
    PADr = 90
    maxw = w - PADr * 2

    f_mark = M._font(M.F_SERIF, 46)
    mark = "parkjunhyuk.xyz"
    d.text(((w - d.textlength(mark, font=f_mark)) / 2, 96), mark, font=f_mark, fill=M.FG)

    badge = data.get("badge", "").upper()
    bold, rest, keyword = data.get("cover_bold", ""), data.get("cover_rest", []), data.get("cover_keyword", "")
    y_start, y_limit = 1010, 1640
    for scale in (1.0, 0.92, 0.85, 0.78, 0.72):
        f_badge = M._font(M.F_CJK_BOLD, 34)
        f_bold = M._font(M.F_CJK_BOLD, int(84 * scale))
        f_soft = M._font(M.F_CJK_REG, int(60 * scale))
        f_key = M._font(M.F_CJK_XBOLD, int(132 * scale))
        lh_bold, lh_soft, lh_key = int(100 * scale), int(74 * scale), int(146 * scale)
        bold_lines = M._wrap(d, bold, f_bold, maxw)
        rest_lines = [ln for raw in rest for ln in M._wrap(d, raw, f_soft, maxw)]
        key_lines = M._wrap(d, keyword, f_key, maxw)
        asc, dsc = f_badge.getmetrics()
        total = (asc + dsc + 28) + 32 + len(bold_lines) * lh_bold \
            + len(rest_lines) * lh_soft + 16 + len(key_lines) * lh_key
        if total <= y_limit - y_start:
            break

    y = M._pill(d, PADr, y_start, badge, f_badge) + 32
    for line in bold_lines:
        d.text((PADr, y), line, font=f_bold, fill=M.FG); y += lh_bold
    for line in rest_lines:
        d.text((PADr, y), line, font=f_soft, fill=M.HEAD_SOFT); y += lh_soft
    y += 16
    for line in key_lines:
        d.text((PADr, y), line, font=f_key, fill=M.FG); y += lh_key

    f_cta = M._font(M.F_CJK_BOLD, 40)
    cta = "팔로우하고 더 보기  →  @parkjunhyukxyz"
    d.text(((w - d.textlength(cta, font=f_cta)) / 2, 1740), cta, font=f_cta, fill=ACCENT)
    return img


def render_fb_card(data, path, w=1080, h=1080):
    """페이스북 글에 붙일 정사각 카드. 본문과 무관한 일반 사진 대신,
    주제 헤드라인(cover_bold + 키워드 액센트)을 사진 위에 얹어 글과 연결한다."""
    img = M._vertical_gradient(M.BG_TOP, M.BG_BOT).resize((w, h))
    top = data.get("top_image")
    if isinstance(top, str) and os.path.exists(top):
        photo = Image.open(top).convert("RGB")
        ratio = max(w / photo.width, h / photo.height)
        photo = photo.resize((int(photo.width * ratio), int(photo.height * ratio)))
        left, t = (photo.width - w) // 2, (photo.height - h) // 2
        photo = photo.crop((left, t, left + w, t + h))
        img = Image.blend(img, photo, 0.34)
        img = Image.blend(img, Image.new("RGB", (w, h), (8, 10, 13)), 0.50)
    d = ImageDraw.Draw(img)
    P = 76
    M._pill(d, P, 72, data.get("badge", "NOTE").upper(), M._font(M.F_CJK_BOLD, 28))
    mk = "parkjunhyuk.xyz"
    f_mark = M._font(M.F_SERIF, 34)
    d.text((w - P - d.textlength(mk, font=f_mark), 76), mk, font=f_mark, fill=M.FG)

    bold, rest, key = data.get("cover_bold", ""), data.get("cover_rest", []), data.get("cover_keyword", "")
    accent = data.get("cover_accent", "")
    f_bold = M._font(M.F_CJK_BOLD, 64)
    f_soft = M._font(M.F_CJK_REG, 46)
    f_key = M._font(M.F_CJK_XBOLD, 92)
    maxw = w - P * 2
    bl = M._wrap(d, bold, f_bold, maxw)
    rl = [ln for r in rest for ln in M._wrap(d, r, f_soft, maxw)]
    kl = M._wrap(d, key, f_key, maxw)
    total = len(bl) * 78 + len(rl) * 56 + 16 + len(kl) * 104
    y = h - 96 - total

    def _accent(ln, font, yy):
        if accent and accent in ln:
            before, after = ln.split(accent, 1)
            cx = P
            for seg, col in ((before, M.FG), (accent, ACCENT), (after, M.FG)):
                if seg:
                    d.text((cx, yy), seg, font=font, fill=col)
                    cx += d.textlength(seg, font=font)
        else:
            d.text((P, yy), ln, font=font, fill=M.FG)

    for ln in bl:
        _accent(ln, f_bold, y); y += 78
    for ln in rl:
        d.text((P, y), ln, font=f_soft, fill=M.HEAD_SOFT); y += 56
    y += 16
    for ln in kl:
        d.text((P, y), ln, font=f_key, fill=ACCENT); y += 104

    img.save(path, "JPEG", quality=92)
    return path


def render_li_cover(data, path, w=1080, h=1350):
    """링크드인 뉴스카드형 표지: NEWS 배지 + 좌측 큰 제목(키워드 액센트) + 우측 팩트 패널 + 서명.
    (차우진 엔터문화연구소 피드 포맷 참고)"""
    img = M._vertical_gradient(M.BG_TOP, M.BG_BOT)
    top = data.get("top_image")
    if isinstance(top, str) and os.path.exists(top):
        photo = Image.open(top).convert("RGB")
        ratio = max(w / photo.width, h / photo.height)
        photo = photo.resize((int(photo.width * ratio), int(photo.height * ratio))).crop((0, 0, w, h))
        img = Image.blend(img, photo, 0.30)                                   # 사진 은은하게
        img = Image.blend(img, Image.new("RGB", (w, h), (8, 10, 13)), 0.48)   # 전체 어둡게
    d = ImageDraw.Draw(img)
    P = 72

    # NEWS 배지(좌상단)
    M._pill(d, P, 84, "NEWS", M._font(M.F_CJK_BOLD, 30))

    # 우측 팩트 패널: facts(숫자·핵심) 3개. 없으면 포인트 제목으로 폴백.
    px = 616
    pw = w - P - px
    py = 168
    facts = data.get("facts") or [p.get("title", "") for p in data.get("points", [])[:3]]
    f_fact = M._font(M.F_CJK_BOLD, 33)
    for ft in facts[:3]:
        lines = M._wrap(d, ft, f_fact, pw - 48)[:3]
        ph = 30 + len(lines) * 44 + 30
        d.rounded_rectangle([px, py, px + pw, py + ph], radius=18, fill=(19, 22, 26))
        yy = py + 30
        for ln in lines:
            d.text((px + 24, yy), ln, font=f_fact, fill=M.FG); yy += 44
        py += ph + 22

    # 좌측 제목(하단 정렬): 볼드(어절 액센트) + 키워드(액센트)
    f_bold = M._font(M.F_CJK_BOLD, 64)
    f_key = M._font(M.F_CJK_XBOLD, 86)
    lw = px - P - 28
    accent = data.get("cover_accent", "")
    bold_lines = M._wrap(d, data.get("cover_bold", ""), f_bold, lw)
    key_lines = M._wrap(d, data.get("cover_keyword", ""), f_key, lw)
    total = len(bold_lines) * 78 + 16 + len(key_lines) * 98
    y = h - 156 - total

    def _line_accent(ln, font, yy):
        # accent 어절이 이 줄에 있으면 그 부분만 컬러로
        if accent and accent in ln:
            before, after = ln.split(accent, 1)
            cx = P
            for seg, col in ((before, M.FG), (accent, ACCENT), (after, M.FG)):
                if seg:
                    d.text((cx, yy), seg, font=font, fill=col)
                    cx += d.textlength(seg, font=font)
        else:
            d.text((P, yy), ln, font=font, fill=M.FG)

    for ln in bold_lines:
        _line_accent(ln, f_bold, y); y += 78
    y += 16
    for ln in key_lines:
        d.text((P, y), ln, font=f_key, fill=ACCENT); y += 98

    # 서명 푸터
    d.line([(P, h - 100), (w - P, h - 100)], fill=M.DIVIDER, width=1)
    d.text((P, h - 82), LI_SIGNATURE, font=M._font(M.F_CJK_REG, 24), fill=M.CAPTION)

    img.save(path, "JPEG", quality=92)
    return path


def render_li_outro(data, path, w=1080, h=1350):
    """링크드인 문서 마지막 페이지: 결론 한 줄 + 댓글 유도 CTA + 서명(IG '저장·팔로우' 대신)."""
    img = M._vertical_gradient(M.BG_TOP, M.BG_BOT)
    d = ImageDraw.Draw(img)
    P = 88
    maxw = w - P * 2

    f_line = M._font(M.F_CJK_BOLD, 60)
    lines = M._wrap_sentences(d, data.get("outro_line", ""), f_line, maxw)
    y = int(h * 0.34)
    for ln in lines:
        d.text((P, y), ln, font=f_line, fill=M.FG); y += 76

    y += 60
    f_cta = M._font(M.F_CJK_BOLD, 44)
    d.text((P, y), "이 주제, 어떻게 보시나요?", font=f_cta, fill=ACCENT); y += 60
    f_sub = M._font(M.F_CJK_REG, 38)
    d.text((P, y), "댓글로 의견을 남겨주세요.", font=f_sub, fill=M.HEAD_SOFT)

    d.line([(P, h - 100), (w - P, h - 100)], fill=M.DIVIDER, width=1)
    d.text((P, h - 82), LI_SIGNATURE, font=M._font(M.F_CJK_REG, 24), fill=M.CAPTION)
    img.save(path, "JPEG", quality=92)
    return path


def render_li_carousel(data, out_dir):
    """링크드인용 캐러셀: 뉴스카드 표지 + 포인트 슬라이드 + 아웃트로."""
    os.makedirs(out_dir, exist_ok=True)
    total = len(data["points"])
    paths = [render_li_cover(data, os.path.join(out_dir, "01_cover.jpg"))]
    for i, pt in enumerate(data["points"], 1):
        paths.append(render_point(data, pt, i, total, os.path.join(out_dir, f"{i+1:02d}_point.jpg")))
    paths.append(render_outro(data, os.path.join(out_dir, f"{total+2:02d}_outro.jpg")))
    return paths


def render_showcase_cover(meta, hero_path, path, w=1080, h=1350):
    """작품 쇼케이스 표지(nendo식 미니멀): 히어로 이미지 풀블리드 + 하단 그라데이션 +
    작품명 + 한 줄 컨셉 + 절제된 태그/워드마크. 작품이 주인공이 되도록 최소 개입."""
    img = Image.open(hero_path).convert("RGB")
    ratio = max(w / img.width, h / img.height)
    img = img.resize((int(img.width * ratio), int(img.height * ratio)))
    left = (img.width - w) // 2
    img = img.crop((left, 0, left + w, h))

    # 하단 그라데이션 스크림(텍스트 가독성)
    scrim = Image.new("L", (1, h), 0)
    for y in range(h):
        a = 0 if y < h * 0.50 else int(205 * ((y - h * 0.50) / (h * 0.50)))
        scrim.putpixel((0, y), min(215, a))
    img.paste(Image.new("RGB", (w, h), (8, 10, 13)), (0, 0), scrim.resize((w, h)))

    d = ImageDraw.Draw(img)
    P = 80
    M._pill(d, P, 82, (meta.get("badge", "PROJECT")).upper(), M._font(M.F_CJK_BOLD, 28))
    mk = "parkjunhyuk.xyz"
    f_mark = M._font(M.F_SERIF, 38)
    d.text((w - P - d.textlength(mk, font=f_mark), 86), mk, font=f_mark, fill=M.FG)

    f_name = M._font(M.F_CJK_BOLD, 82)
    f_con = M._font(M.F_CJK_REG, 38)
    name_lines = M._wrap(d, meta.get("name", ""), f_name, w - P * 2)
    con_lines = M._wrap(d, meta.get("concept_ko", ""), f_con, w - P * 2)
    total = len(name_lines) * 92 + 20 + len(con_lines) * 50
    y = h - 120 - total
    for ln in name_lines:
        d.text((P, y), ln, font=f_name, fill=M.FG); y += 92
    y += 20
    for ln in con_lines:
        d.text((P, y), ln, font=f_con, fill=M.HEAD_SOFT); y += 50

    img.save(path, "JPEG", quality=92)
    return path


def slides_to_pdf(slide_paths, out_pdf):
    """캐러셀 슬라이드(JPG)들을 하나의 PDF로 합친다 — 링크드인 문서(캐러셀) 게시용."""
    imgs = [Image.open(p).convert("RGB") for p in slide_paths]
    imgs[0].save(out_pdf, "PDF", save_all=True, append_images=imgs[1:], resolution=150.0)
    return out_pdf


def render_reel_card(data, kind, n=None, title=None, body=None, w=1080, h=1920):
    """릴스 비트(장면)별 텍스트 카드(투명 PNG). 중앙 정렬 + 안전영역(상15%/하20%) 준수.
    kind: 'hook' | 'point' | 'cta'."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(img)
    for y in range(h):                       # 가독성 스크림(중앙 강조 + 상단 워드마크)
        a = 60
        if 560 < y < 1400:
            a = 125
        if y < 280:
            a = max(a, int(155 * (1 - y / 280)))
        sd.line([(0, y), (w, y)], fill=(8, 10, 13, a))
    d = ImageDraw.Draw(img)
    PADc = 80
    maxw = w - PADc * 2

    def center(txt, font, y, fill):
        d.text(((w - d.textlength(txt, font=font)) / 2, y), txt, font=font, fill=fill)

    def center_block(lines, font, y, fill, lh):
        for ln in lines:
            center(ln, font, y, fill); y += lh
        return y

    center("parkjunhyuk.xyz", M._font(M.F_SERIF, 42), 150, M.FG)

    if kind == "hook":
        f_badge = M._font(M.F_CJK_BOLD, 34)
        f_bold = M._font(M.F_CJK_BOLD, 80)
        f_key = M._font(M.F_CJK_XBOLD, 148)
        bold_lines = M._wrap(d, data.get("cover_bold", ""), f_bold, maxw)
        key_lines = M._wrap(d, data.get("cover_keyword", ""), f_key, maxw)
        asc, dsc = f_badge.getmetrics(); bh = asc + dsc + 28
        total = bh + 30 + len(bold_lines) * 96 + 24 + len(key_lines) * 158
        y = int(h * 0.52 - total / 2)
        badge = data.get("badge", "").upper()
        bw = d.textlength(badge, font=f_badge) + 56
        M._pill(d, (w - bw) / 2, y, badge, f_badge); y += bh + 30
        y = center_block(bold_lines, f_bold, y, M.HEAD_SOFT, 96) + 24
        center_block(key_lines, f_key, y, M.FG, 158)

    elif kind == "point":
        f_num = M._font(M.F_CJK_BOLD, 110)
        f_title = M._font(M.F_CJK_BOLD, 78)
        f_body = M._font(M.F_CJK_REG, 50)
        title_lines = M._wrap(d, title or "", f_title, maxw)
        body_lines = M._wrap_sentences(d, body or "", f_body, maxw)
        total = 130 + 30 + len(title_lines) * 92 + 18 + len(body_lines) * 66
        y = int(h * 0.52 - total / 2)
        center(f"{n:02d}", f_num, y, ACCENT); y += 130 + 30
        y = center_block(title_lines, f_title, y, M.FG, 92) + 18
        center_block(body_lines, f_body, y, M.HEAD_SOFT, 66)

    else:  # cta
        f_key = M._font(M.F_CJK_XBOLD, 132)
        f_cta = M._font(M.F_CJK_BOLD, 46)
        key_lines = M._wrap(d, data.get("cover_keyword", ""), f_key, maxw)
        total = len(key_lines) * 146 + 60 + 60
        y = int(h * 0.50 - total / 2)
        y = center_block(key_lines, f_key, y, M.FG, 146) + 60
        center("팔로우하고 더 보기", f_cta, y, M.HEAD_SOFT); y += 64
        center("@parkjunhyukxyz", f_cta, y, ACCENT)

    return img


def render_carousel(data, out_dir="out/carousel"):
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    total = len(data["points"])
    paths.append(render_cover(data, os.path.join(out_dir, "01_cover.jpg")))
    for i, pt in enumerate(data["points"], 1):
        paths.append(render_point(data, pt, i, total, os.path.join(out_dir, f"{i+1:02d}_point.jpg")))
    paths.append(render_outro(data, os.path.join(out_dir, f"{total+2:02d}_outro.jpg")))
    return paths


if __name__ == "__main__":
    sample = {
        "badge": "AI Creative",
        "cover_bold": "공간에서 배운 AI 작업법",
        "cover_rest": ["흐름을 설계하는 사람이 결과도 다르다"],
        "cover_keyword": "흐름 설계",
        "caption": "Creative Director's Notebook · parkjunhyuk.xyz",
        "points": [
            {"title": "목적을 하나로 좁히기", "body": "의도가 여러 개면 결과가 흐릿해진다. 시작 전에 이 작업이 무엇을 위한 것인지 하나만 정한다."},
            {"title": "질문의 연속성", "body": "각 장면은 다음 장면에 대한 궁금증을 남겨야 한다. '멋진 장면의 나열'이 아니라 '질문의 사슬'."},
            {"title": "멈춤의 지점", "body": "모든 구간이 강할 필요는 없다. 의도된 여백이 있어야 클라이맥스가 작동한다."},
            {"title": "떠날 명분 vs 머물 명분", "body": "출구가 너무 명확하면 효율적으로 떠난다. 마지막에 한 번 더 돌아보게 하라."},
        ],
        "outro_line": "경험을 강하게 만드는 건 기술,\n길게 만드는 건 설계다.",
    }
    for p in render_carousel(sample):
        print("rendered", p)
