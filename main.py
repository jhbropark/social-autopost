"""
오케스트레이터.

사용법:
  python main.py generate   # Claude로 글 생성 + 이미지 렌더 → out/posts.json, out/today.jpg
  python main.py publish    # out/posts.json 읽어 LinkedIn/Facebook/Instagram 게시
  python main.py all        # 생성→게시 한 번에 (로컬 테스트용; IG는 IMAGE_PUBLIC_URL 필요)

GitHub Actions에서는 generate → (이미지 커밋/푸시) → publish 순으로 분리 실행한다.
실패한 플랫폼이 있어도 나머지는 계속 진행하고, 마지막에 종합 결과를 출력한다.
"""
import os
import sys
import json

import generate
import make_image
import platforms

OUT_DIR = "out"
POSTS_JSON = os.path.join(OUT_DIR, "posts.json")
IMAGE_JPG = os.path.join(OUT_DIR, "today.jpg")


def do_generate():
    os.makedirs(OUT_DIR, exist_ok=True)
    data = generate.generate_posts()
    img = data["image"]
    # 푸터 인덱스: 연중 일수 기반 2자리 번호
    import datetime
    index = f"{(datetime.datetime.utcnow().timetuple().tm_yday % 99) + 1:02d}"
    make_image.render(
        badge=img["badge"],
        head_bold=img["head_bold"],
        head_rest=img.get("head_rest", []),
        keyword=img["keyword"],
        caption=img.get("caption", "parkjunhyuk.xyz"),
        index=index,
        out_path=IMAGE_JPG,
    )
    with open(POSTS_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("✅ generated:", data.get("topic"))
    print("   image →", IMAGE_JPG)
    return data


def do_publish(data=None):
    if data is None:
        with open(POSTS_JSON, encoding="utf-8") as f:
            data = json.load(f)

    results = {}

    # LinkedIn
    try:
        results["linkedin"] = ("ok", platforms.post_linkedin(data["linkedin"]["text"]))
    except Exception as e:
        results["linkedin"] = ("FAIL", str(e))

    # Facebook
    try:
        results["facebook"] = ("ok", platforms.post_facebook(data["facebook"]["text"]))
    except Exception as e:
        results["facebook"] = ("FAIL", str(e))

    # Instagram (공개 이미지 URL 필요)
    try:
        image_url = os.environ["IMAGE_PUBLIC_URL"]
        results["instagram"] = ("ok", platforms.post_instagram(data["instagram"]["caption"], image_url))
    except Exception as e:
        results["instagram"] = ("FAIL", str(e))

    print("\n=== 게시 결과 ===")
    failed = False
    for k, (status, info) in results.items():
        mark = "✅" if status == "ok" else "❌"
        print(f"{mark} {k}: {info}")
        if status != "ok":
            failed = True
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "generate":
        do_generate()
    elif cmd == "publish":
        do_publish()
    elif cmd == "all":
        do_publish(do_generate())
    else:
        print("usage: python main.py [generate|publish|all]")
        sys.exit(2)
