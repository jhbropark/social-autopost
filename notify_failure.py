"""
매일 발행 실패 시 원인을 한국어로 요약해 Telegram으로 보낸다.
daily.yml 의 `if: failure()` 스텝에서 실행한다.

필요 환경변수:
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID  : 알림 전송(둘 다 없으면 조용히 종료)
  ANTHROPIC_API_KEY                      : 원인 요약(없으면 원문 일부 사용)
  RUN_URL, RUN_DATE                      : 메시지에 첨부(선택)
"""
import os
import requests

ERR_FILE = "_error.txt"


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
                "비전문가가 이해하도록, 어느 채널에서 무엇이 왜 실패했는지 한국어 2~3줄로 요약하고 "
                "맨 끝에 '조치: ...' 한 줄로 해결 제안을 붙여라. 군더더기 없이.\n\n로그:\n" + errors[:4000]
            )}],
        )
        return r.content[0].text.strip()
    except Exception:
        return errors[:600]


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat):
        print("Telegram 미설정 — 알림 건너뜀")
        return
    errors = _read_errors()
    summary = _summarize(errors) if errors else (
        "원인 로그가 남지 않았습니다 — 생성/발행 이전(의존성 설치·인증 등) 단계에서 실패했을 수 있습니다."
    )
    date = os.environ.get("RUN_DATE", "")
    run_url = os.environ.get("RUN_URL", "")
    text = f"🔴 parkjunhyuk 자동 발행 실패 {date}\n\n{summary}"
    if run_url:
        text += f"\n\n자세한 로그: {run_url}"
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat, "text": text, "disable_web_page_preview": "true"},
        timeout=30,
    )
    print("telegram:", r.status_code, r.text[:200])


if __name__ == "__main__":
    main()
