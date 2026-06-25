"""
Telegram 전송 공용 모듈 (HTML 포맷 + 인라인 버튼).
TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 없으면 조용히 no-op.

HTML 모드 사용 이유: MarkdownV2는 특수문자 17개를 모두 이스케이프해야 깨지지 않음 →
HTML은 & < > 3개만 처리하면 되고 링크에 커스텀 텍스트도 가능.
동적 텍스트는 반드시 esc()로 감싼다.
"""
import os
import json
import html
import requests

API = "https://api.telegram.org"


def esc(s):
    """HTML 모드에서 안전하도록 & < > 만 이스케이프."""
    return html.escape(str(s if s is not None else ""), quote=False)


def send(html_text, buttons=None):
    """html_text: <b> 등 허용 태그가 든 본문. buttons: [(텍스트, url), ...] (url None이면 제외).
    발신자 제목(봇 이름)은 setMyName 으로 'sns.parkjunhyukxyz' 설정됨."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat):
        print("Telegram 미설정 — 전송 건너뜀")
        return None
    data = {
        "chat_id": chat,
        "text": html_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }
    if buttons:
        row = [{"text": t, "url": u} for t, u in buttons if u]
        if row:
            data["reply_markup"] = json.dumps({"inline_keyboard": [row]})
    try:
        r = requests.post(f"{API}/bot{token}/sendMessage", data=data, timeout=30)
        print("telegram:", r.status_code, r.text[:160])
        return r.status_code < 300
    except Exception as e:
        print("telegram 예외:", e)
        return None
