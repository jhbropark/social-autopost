"""다음 7일치 IG 포스터 미리 렌더 + 콘택트 시트(montage) 생성."""
import os
from PIL import Image, ImageDraw
import make_image as M

DAYS = [
    ("06/18 목", "AI FOR CREATORS",   "AI가 만든 공간이",   ["차갑게 느껴지는 건"], "동선이 없어서",   "AI for Creators · parkjunhyuk.xyz",            "02"),
    ("06/19 금", "BRAND EXPERIENCE",  "브랜드가 기억되는 건", ["로고가 아니라"],     "첫 3초의 감각",   "1 Minute Media Art · parkjunhyuk.xyz",         "03"),
    ("06/20 토", "CREATIVE LEADERSHIP","디렉터가 답을 줄수록", ["팀은 자라지 않는다"], "질문을 설계하라", "Before → After · parkjunhyuk.xyz",             "04"),
    ("06/21 일", "FUTURE CITY",       "사람이 머무는 광장은", ["채운 곳이 아니라"],   "비운 곳이다",     "Creative Director's Notebook · parkjunhyuk.xyz","05"),
    ("06/22 월", "CONTENT BUSINESS",  "미디어아트는 왜",     ["한 번 쓰고 버려질까"], "IP로 만들어라",  "Space Inspiration · parkjunhyuk.xyz",          "06"),
    ("06/23 화", "CREATOR OS",        "좋은 작업은",        ["영감이 아니라"],     "시스템에서 나온다","AI for Creators · parkjunhyuk.xyz",            "07"),
    ("06/24 수", "MEDIA ART",         "AI는 손을",          ["대체하지 않았다"],   "잡일을 가져갔다", "1 Minute Media Art · parkjunhyuk.xyz",         "08"),
]

os.makedirs("out/preview", exist_ok=True)
paths = []
for i, (date, badge, hb, hr, kw, cap, idx) in enumerate(DAYS, 1):
    p = f"out/preview/day{i}.jpg"
    M.render(badge=badge, head_bold=hb, head_rest=hr, keyword=kw, caption=cap, index=idx, out_path=p)
    paths.append((date, p))
    print("rendered", date, p)

# ---- 콘택트 시트 (4열) ----
TILE = 460
LABEL = 44
PAD = 22
COLS = 4
rows = (len(paths) + COLS - 1) // COLS
W = COLS * (TILE + PAD) + PAD
H = rows * (TILE + LABEL + PAD) + PAD
sheet = Image.new("RGB", (W, H), (18, 20, 22))
d = ImageDraw.Draw(sheet)
f = M._font(M.F_CJK_BOLD, 26)

for i, (date, p) in enumerate(paths):
    r, c = divmod(i, COLS)
    x = PAD + c * (TILE + PAD)
    y = PAD + r * (TILE + LABEL + PAD)
    d.text((x + 4, y), date, font=f, fill=(231, 168, 90))
    img = Image.open(p).resize((TILE, TILE))
    sheet.paste(img, (x, y + LABEL))

sheet.save("out/preview/contact_sheet.jpg", "JPEG", quality=90)
print("contact sheet -> out/preview/contact_sheet.jpg", sheet.size)
