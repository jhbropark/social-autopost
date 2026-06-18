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


def render_cover(data, path, seed=0):
    hero = data.get("top_image") or M.render_hero(W, 560, seed)
    img = M._top_panel(_base(), top_image=hero)
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


def render_outro(data, path, seed=0):
    img = M._top_panel(_base(), top_image=M.render_hero(W, 420, seed + 7), panel_h=420)
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


def render_carousel(data, out_dir="out/carousel"):
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    total = len(data["points"])
    # 주제별로 히어로 비주얼이 달라지도록 결정적 시드(badge+keyword 기반)
    seed = sum(ord(c) for c in (data.get("badge", "") + data.get("cover_keyword", ""))) or 1
    paths.append(render_cover(data, os.path.join(out_dir, "01_cover.jpg"), seed))
    for i, pt in enumerate(data["points"], 1):
        paths.append(render_point(data, pt, i, total, os.path.join(out_dir, f"{i+1:02d}_point.jpg")))
    paths.append(render_outro(data, os.path.join(out_dir, f"{total+2:02d}_outro.jpg"), seed))
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
