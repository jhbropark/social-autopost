"""
매일 발행 직후 콘텐츠를 검수하고 결과를 Telegram(HTML)으로 보낸다.
daily.yml 의 publish 다음 스텝(if: success())에서 실행.

검수 항목:
  - 결정적 점검: 지어낸 통계 의심(N명/N%/N배), JSON 래퍼/리터럴 \n, '해시태그' 단어, 별표(**), 코너명 머리 누락
  - AI 점검: 사실성·표현·톤 (Claude)
필요 환경변수: TELEGRAM_BOT_TOKEN/CHAT_ID, ANTHROPIC_API_KEY(선택), RUN_DATE(선택)
"""
import os
import re
import json

import telegram_notify as tg

PLAN = "out/daily/plan.json"
DASH = "https://app.notion.com/p/37787cba93974a40a72ab0de6b39805e"


def _texts(item):
    return {
        "IG": item.get("instagram", {}).get("caption", "") or "",
        "FB": item.get("facebook", {}).get("text", "") or "",
        "LinkedIn": item.get("linkedin", {}).get("text", "") or "",
    }


def _checks(item, texts):
    flags = []
    facts = item.get("carousel", {}).get("facts", [])
    allt = " ".join(texts.values()) + " " + " ".join(facts)
    nums = re.findall(r"\d[\d,\.]*\s*(?:명|%|퍼센트|배|억|만\s*명|만원|원)", allt)
    if nums:
        flags.append("의심 수치 " + ", ".join(nums[:4]))
    for ch, t in texts.items():
        s = t.strip()
        if s.startswith("{") or '"text"' in s:
            flags.append(f"{ch} JSON래퍼")
        if "\\n" in t:
            flags.append(f"{ch} 리터럴\\n")
        if re.search(r"해시\s*태그\s*#", t):
            flags.append(f"{ch} '해시태그'단어")
        if "**" in t:
            flags.append(f"{ch} 별표")
        if t and not s.startswith("「"):
            flags.append(f"{ch} 코너명누락")
    return flags


def _ai_review(item, texts):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return ""
    try:
        import anthropic
        c = anthropic.Anthropic(api_key=key)
        body = (f"주제: {item.get('topic')}\n\nLinkedIn:\n{texts['LinkedIn'][:1400]}\n\n"
                f"Facebook:\n{texts['FB'][:900]}")
        r = c.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": (
                "다음은 오늘 발행된 소셜 콘텐츠다. 사실성(지어낸 통계·과장), 어색한 표현, 톤 일관성만 본다. "
                "문제가 있으면 1줄로 지적하고, 없으면 정확히 '이상 없음'이라고만 답하라. 군더더기 없이.\n\n" + body
            )}],
        )
        return r.content[0].text.strip()
    except Exception:
        return ""


def main():
    try:
        with open(PLAN, encoding="utf-8") as f:
            plan = json.load(f)
    except Exception:
        print("plan.json 없음 — 검수 건너뜀")
        return

    date = os.environ.get("RUN_DATE", "")
    parts = [f"🔍 <b>콘텐츠 검수</b> · {tg.esc(date)}"]
    total = 0
    for item in plan:
        label = "릴스" if item.get("_type") == "reel" else "캐러셀"
        texts = _texts(item)
        flags = _checks(item, texts)
        ai = _ai_review(item, texts)
        if ai and ai != "이상 없음":
            flags.append("AI: " + ai)
        total += len([x for x in flags if not x.startswith("AI:")])
        icon = "✅" if not flags else "⚠️"
        cz = item.get("carousel", {})
        parts.append(f"\n{icon} <b>{label}</b> · {tg.esc(str(item.get('topic'))[:48])}")
        parts.append(f"표지: {tg.esc(str(cz.get('cover_bold')))} — {tg.esc(str(cz.get('cover_keyword')))}")
        parts.append("검수: " + (tg.esc("; ".join(flags)) if flags else "이상 없음"))

    parts.append(f"\n종합: {'이상 없음 ✅' if total == 0 else f'⚠️ {total}건 확인 필요'}")

    # 게시 링크 버튼(있으면) + 대시보드
    links = {}
    for item in plan:
        lk = item.get("_links") or {}
        for k in ("instagram", "linkedin", "facebook"):
            if lk.get(k) and k not in links:
                links[k] = lk[k]
    buttons = [(n, links.get(k)) for n, k in (("IG", "instagram"), ("LinkedIn", "linkedin"), ("FB", "facebook"))]
    buttons.append(("📲 대시보드", DASH))
    tg.send("\n".join(parts), buttons=buttons)


if __name__ == "__main__":
    main()
