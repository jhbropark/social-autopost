"""
매일 발행 실패 시 원인을 한국어로 요약해 Telegram(HTML)으로 보낸다.
daily.yml 의 `if: failure()` 스텝에서 실행.

메시지 구조:
  🔴 발행 실패 · 날짜
  실패: ❌ Instagram  ❌ Facebook         ← 칩(한눈에)
  원인  : <왜 실패했는지 1~2줄>
  조치  : <해결 제안 한 줄>
  [🔎 로그 보기]                          ← 인라인 버튼

필요 환경변수:
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID  : 전송(없으면 no-op)
  ANTHROPIC_API_KEY                      : 원인 요약(없으면 원문 일부)
  RUN_URL, RUN_DATE                      : 첨부(선택)
"""
import os
import re

import telegram_notify as tg

ERR_FILE = "_error.txt"
CHANNELS = [("Instagram", "instagram"), ("LinkedIn", "linkedin"), ("Facebook", "facebook")]


def _read_errors():
    try:
        with open(ERR_FILE, encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


def _fmt(s):
    """HTML 안전 처리 후, 모델이 쓴 마크다운 굵게(**x**)를 <b>로 변환하고 잔여 별표 제거."""
    s = tg.esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return s.replace("**", "").replace("*", "").strip()


def _summarize(errors):
    """원인 1~2줄 + '조치:' 한 줄. 채널명 반복/마크다운 금지(칩으로 이미 표시됨)."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not (key and errors):
        return errors[:500]
    try:
        import anthropic
        c = anthropic.Anthropic(api_key=key)
        r = c.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=350,
            messages=[{"role": "user", "content": (
                "다음은 소셜 자동 발행 파이프라인의 실패 로그다. 비전문가가 이해하도록 "
                "'왜' 실패했는지 핵심만 1~2줄로 쓰고, 줄을 바꿔 '조치: ...' 한 줄로 해결책을 제시해라.\n"
                "- 별표(*)·마크다운·이모지 쓰지 말 것(평문).\n"
                "- 어느 채널인지는 별도로 표시되니 채널명을 굵게 강조하거나 반복 나열하지 말 것.\n\n"
                "로그:\n" + errors[:4000]
            )}],
        )
        return r.content[0].text.strip()
    except Exception:
        return errors[:500]


def main():
    errors = _read_errors()
    summary = _summarize(errors) if errors else (
        "원인 로그가 남지 않았습니다. 생성/발행 이전(의존성 설치·인증) 단계에서 멈췄을 수 있습니다.\n조치: 로그를 확인하세요."
    )
    cause, action = summary, ""
    m = re.search(r"조치\s*[:：]\s*(.+)", summary, re.S)
    if m:
        action = m.group(1).strip()
        cause = summary[:m.start()].strip()

    failed_ch = [name for name, key in CHANNELS if ("❌ " + key) in errors]
    date = os.environ.get("RUN_DATE", "")
    run_url = os.environ.get("RUN_URL")

    parts = [f"🔴 <b>발행 실패</b> · {tg.esc(date)}"]
    if failed_ch:
        parts += ["", "실패  " + "  ".join("❌ " + c for c in failed_ch)]
    parts += ["", f"<b>원인</b>  {_fmt(cause)}"]
    if action:
        parts += ["", f"<b>조치</b>  {_fmt(action)}"]
    text = "\n".join(parts)

    tg.send(text, buttons=[("🔎 로그 보기", run_url)] if run_url else None)


if __name__ == "__main__":
    main()
