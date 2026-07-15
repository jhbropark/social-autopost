"""
실제 아이디어 소재로 콘텐츠를 생성하고, 이미지(캐러셀·FB카드·LinkedIn카드)를 렌더해
out/imgpreview/ 에 저장한다(게시 없음). 이미지 생성 결과 확인용.
"""
import os
import datetime

import ideas
import generate
import carousel
import imagesearch

OUT = "out/imgpreview"


def main():
    os.makedirs(OUT, exist_ok=True)
    today = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    idea = ideas.pick_idea(today.timetuple().tm_yday)
    print("소재:", idea["idea"] if idea else "(없음)")
    d = generate.generate_posts(target=today, idea=idea)
    cz = d["carousel"]
    print("TOPIC:", d.get("topic"))
    print("표지:", cz.get("cover_bold"), "/", cz.get("cover_keyword"))

    # 표지 배경 사진(Pexels, 날짜로 회전)
    pick = today.timetuple().tm_yday % 15
    img = imagesearch.search_image(d.get("image_query") or d.get("topic"), pick=pick)
    if img is not None:
        hp = os.path.join(OUT, "_hero.jpg")
        img.save(hp, "JPEG", quality=88)
        cz["top_image"] = hp
        print("hero:", "OK")
    else:
        print("hero:", "없음(그라데이션 폴백)")

    # 포인트 슬라이드 배경 이미지(4컷 만화식 연속) — daily 와 동일 로직
    import daily
    daily._attach_point_images(d, OUT)
    print("포인트 이미지:", [os.path.basename(p.get("image", "-")) for p in cz.get("points", [])])

    slides = carousel.render_carousel(cz, out_dir=OUT)
    carousel.render_fb_card(cz, os.path.join(OUT, "fb_card.jpg"))
    carousel.render_li_cover(cz, os.path.join(OUT, "li_cover.jpg"))
    carousel.render_li_outro(cz, os.path.join(OUT, "li_outro.jpg"))

    # 릴스 0초 후크 카드(영상 첫 프레임 디자인) 미리보기 — 히어로 위에 합성
    try:
        from PIL import Image as _I
        print("릴스 후크:", cz.get("reel_hook"))
        hook = carousel.render_reel_card(cz, "hook")
        base = _I.new("RGB", (1080, 1920), (12, 14, 18))
        if cz.get("top_image") and os.path.exists(cz["top_image"]):
            ph = _I.open(cz["top_image"]).convert("RGB")
            rr = max(1080 / ph.width, 1920 / ph.height)
            ph = ph.resize((int(ph.width * rr), int(ph.height * rr)))
            base.paste(ph.crop((0, 0, 1080, 1920)))
        base.paste(hook, (0, 0), hook)
        base.save(os.path.join(OUT, "reel_hook.jpg"), quality=90)
    except Exception as e:
        print("reel_hook 실패:", e)
    print("렌더 완료:", len(slides), "슬라이드 + fb_card + li_cover + li_outro + reel_hook")


if __name__ == "__main__":
    main()
