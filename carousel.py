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
        f_key = M._font(M.F_CJK_BOLD, int(124 * scale))
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
        f_key = M._font(M.F_CJK_BOLD, int(132 * scale))
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
        f_key = M._font(M.F_CJK_BOLD, 148)
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
        f_key = M._font(M.F_CJK_BOLD, 132)
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
