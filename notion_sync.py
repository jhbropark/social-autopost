"""
발행 결과를 Notion 콘텐츠 대시보드(📲 Social Autopost DB)에 기록한다.
NOTION_TOKEN / NOTION_DATABASE_ID 가 있을 때만 동작(없으면 조용히 건너뜀).

DB 속성: 주제(title) · 날짜(date) · 상태(select) · 채널(multi_select) ·
         IG 캡션 · Facebook · LinkedIn(rich_text) · IG/LinkedIn/Facebook 링크(url)
"""
import os
import requests

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _rt(text, limit=2000):
    return [{"text": {"content": (text or "")[:limit]}}]


def upsert(item, links=None, status="발행됨", cover_url=None, date=None):
    """하루치 콘텐츠 1건을 Notion DB에 새 페이지로 추가. 페이지 id 반환(또는 None)."""
    token = os.environ.get("NOTION_TOKEN")
    db = os.environ.get("NOTION_DATABASE_ID")
    if not (token and db):
        return None

    links = links or {}
    chan_map = (("Instagram", "instagram"), ("LinkedIn", "linkedin"), ("Facebook", "facebook"))
    channels = [name for name, key in chan_map if links.get(key)]

    props = {
        "주제": {"title": _rt(item.get("topic", ""), 200)},
        "상태": {"select": {"name": status}},
        "IG 캡션": {"rich_text": _rt(item.get("instagram", {}).get("caption", ""))},
        "Facebook": {"rich_text": _rt(item.get("facebook", {}).get("text", ""))},
        "LinkedIn": {"rich_text": _rt(item.get("linkedin", {}).get("text", ""))},
    }
    if date:
        props["날짜"] = {"date": {"start": date}}
    if channels:
        props["채널"] = {"multi_select": [{"name": c} for c in channels]}
    for label, key in (("IG 링크", "instagram"), ("LinkedIn 링크", "linkedin"), ("Facebook 링크", "facebook")):
        if links.get(key):
            props[label] = {"url": links[key]}

    body = {"parent": {"database_id": db}, "properties": props}
    if cover_url:
        body["cover"] = {"type": "external", "external": {"url": cover_url}}

    try:
        r = requests.post(
            f"{NOTION_API}/pages",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
            json=body,
            timeout=30,
        )
        if r.status_code >= 300:
            print("⚠ Notion sync 실패:", r.status_code, r.text[:300])
            return None
        return r.json().get("id")
    except Exception as e:
        print("⚠ Notion sync 예외:", e)
        return None
