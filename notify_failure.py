"""
매일 발행 실패 시 원인을 한국어로 요약해 Telegram(HTML)으로 보낸다.
daily.yml 의 `if: failure()` 스텝에서 실행.

필요 환경변수:
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID  : 알림 전송(둘 다 없으면 no-op)
  ANTHROPIC_API_KEY                      : 원인 요약(없으면 원문 일부)
  RUN_URL, RUN_DATE                      : 메시지 첨부(선택)
"""
import os

import telegram_notify as tg

ERR_FILE = "_error.txt"
CHANNELS = [("Instagram", "instagram"), ("LinkedIn", "linkedin"), ("Facebook", "facebook")]


def _read_errors():
    try:
        with open(ERR_FILE, encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


def _summarize(errors):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not (key and errors):
        return errors[:600]
    try:
        import anthropic
        c = anthropic.Anthropic(api_key=key)
        r = c.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{"role": "user", "content": (
                "다음은 소셜 미디어 자동 발행 파이프라인의 실패 로그다. "
                "비전문가가 이해하도록, 어느 채널에서 무엇이 왜 실패했는지 한국어 1~2줄로 요약하고 "
                "맨 끝에 '조치: ...' 한 줄로 해결 제안을 붙여라. 군더더기 없이.\n\n로그:\n" + errors[:4000]
            )}],
        )
        return r.content[0].text.strip()
    except Exception:
        return errors[:600]


def main():
    errors = _read_errors()
    summary = _summarize(errors) if errors else (
        "원인 로그가 남지 않았습니다 — 생성/발행 이전(의존성 설치·인증 등) 단계에서 실패했을 수 있습니다."
    )
    # 원인 / 조치 분리
    cause, action = summary, ""
    if "조치:" in summary:
        a, b = summary.split("조치:", 1)
        cause, action = a.strip(), b.strip()

    failed_ch = [name for name, key in CHANNELS if ("❌ " + key) in errors]
    date = os.environ.get("RUN_DATE", "")
    run_url = os.environ.get("RUN_URL")

    parts = [f"🔴 <b>자동 발행 실패</b> · {tg.esc(date)}", "", "<b>원인</b>", tg.esc(cause)]
    if action:
        parts += ["", "<b>조치</b>", tg.esc(action)]
    if failed_ch:
        parts += ["", "실패 채널: <b>" + tg.esc(", ".join(failed_ch)) + "</b>"]
    text = "\n".join(parts)

    tg.send(text, buttons=[("🔎 로그 보기", run_url)] if run_url else None)


if __name__ == "__main__":
    main()
