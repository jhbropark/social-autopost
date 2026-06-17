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

W = M.W  # 1080
AMBER = (231, 168, 90)
TEAL = (127, 208, 207)
PAD = 88


def _base():
    img = M._vertical_gradient(M.BG_TOP, M.BG_BOT)
    return img


def _footer(d, caption, right_text):
    fy = W - PAD + 2
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
    img = M._top_panel(_base(), top_image=data.get("top_image"))
    d = ImageDraw.Draw(img)
    _wordmark(d)
    f_badge = M._font(M.F_CJK_BOLD, 24)
    f_bold = M._font(M.F_CJK_BOLD, 60)
    f_soft = M._font(M.F_CJK_REG, 52)
    f_key = M._font(M.F_CJK_BOLD, 96)
    y = M._pill(d, PAD, 520, data["badge"].upper(), f_badge)
    y += 30
    for line in M._wrap(d, data["cover_bold"], f_bold, W - PAD * 2):
        d.text((PAD, y), line, font=f_bold, fill=M.FG); y += 74
    for raw in data.get("cover_rest", []):
        for line in M._wrap(d, raw, f_soft, W - PAD * 2):
            d.text((PAD, y), line, font=f_soft, fill=M.HEAD_SOFT); y += 64
    y += 10
    for line in M._wrap(d, data["cover_keyword"], f_key, W - PAD * 2):
        d.text((PAD, y), line, font=f_key, fill=M.FG); y += 104
    # 스와이프 힌트
    f_hint = M._font(M.F_CJK_BOLD, 30)
    hint = "밀어서 보기  →"
    hw = d.textlength(hint, font=f_hint)
    d.text((W - PAD - hw, W - PAD - 70), hint, font=f_hint, fill=TEAL)
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
    d.text((PAD, 150), f"{n:02d}", font=f_num, fill=AMBER)
    # 얇은 구분선
    d.line([(PAD, 360), (PAD + 120, 360)], fill=TEAL, width=4)
    y = 430
    for line in M._wrap(d, point["title"], f_title, W - PAD * 2):
        d.text((PAD, y), line, font=f_title, fill=M.FG); y += 72
    y += 16
    for line in M._wrap(d, point["body"], f_body, W - PAD * 2):
        d.text((PAD, y), line, font=f_body, fill=M.HEAD_SOFT); y += 56
    _footer(d, data["caption"], f"{n} / {total}")
    img.save(path, "JPEG", quality=92)
    return path


def render_outro(data, path):
    img = M._top_panel(_base(), panel_h=420)
    d = ImageDraw.Draw(img)
    f_line = M._font(M.F_CJK_BOLD, 56)
    f_mark = M._font(M.F_SERIF, 64)
    f_cta = M._font(M.F_CJK_REG, 34)
    # 결론 문장 (중앙 상단부)
    y = 300
    for line in M._wrap(d, data["outro_line"], f_line, W - PAD * 2):
        d.text((PAD, y), line, font=f_line, fill=M.FG); y += 72
    # 워드마크 (크게)
    y += 60
    d.text((PAD, y), "parkjunhyuk.xyz", font=f_mark, fill=AMBER)
    y += 100
    d.text((PAD, y), "저장 · 공유하고, 팔로우하세요", font=f_cta, fill=M.HEAD_SOFT)
    _footer(d, data["caption"], "↩")
    img.save(path, "JPEG", quality=92)
    return path


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
        "badge": "Space Note",
        "cover_bold": "관람객을 30분",
        "cover_rest": ["머물게 하는"],
        "cover_keyword": "4가지 레버",
        "caption": "Creative Director's Notebook · parkjunhyuk.xyz",
        "points": [
            {"title": "진입 동선의 첫 30초", "body": "입구에서 전체를 다 보여주면 호기심이 소진된다. 일부만 보여주고 나머지를 감춰라."},
            {"title": "질문의 연속성", "body": "각 장면은 다음 장면에 대한 궁금증을 남겨야 한다. '멋진 장면의 나열'이 아니라 '질문의 사슬'."},
            {"title": "멈춤의 지점", "body": "모든 구간이 강할 필요는 없다. 의도된 여백이 있어야 클라이맥스가 작동한다."},
            {"title": "떠날 명분 vs 머물 명분", "body": "출구가 너무 명확하면 효율적으로 떠난다. 마지막에 한 번 더 돌아보게 하라."},
        ],
        "outro_line": "경험을 강하게 만드는 건 기술,\n길게 만드는 건 설계다.",
    }
    for p in render_carousel(sample):
        print("rendered", p)
