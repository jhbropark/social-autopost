"""
Notion '💡 Ideas Pipeline' DB에서 실제 아이디어/프로젝트를 읽어 콘텐츠 소재로 공급한다.
NOTION_TOKEN + NOTION_IDEAS_DB_ID 가 있고 통합이 그 DB와 공유돼 있을 때만 동작.
없으면 빈 결과 → generate 가 요일 테마만으로 생성(폴백).
"""
import os
import requests

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _txt(rich):
    return "".join(t.get("plain_text", "") for t in (rich or [])).strip()


def _ms(prop):
    return [o.get("name", "") for o in ((prop or {}).get("multi_select") or [])]


def _sel(prop):
    return ((prop or {}).get("select") or {}).get("name", "")


def fetch_ideas():
    token = os.environ.get("NOTION_TOKEN")
    db = os.environ.get("NOTION_IDEAS_DB_ID")
    if not (token and db):
        return []
    out = []
    try:
        r = requests.post(
            f"{NOTION_API}/databases/{db}/query",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
            json={"page_size": 100},
            timeout=30,
        )
        if r.status_code >= 300:
            print("⚠ Ideas fetch:", r.status_code, r.text[:200])
            return []
        for p in r.json().get("results", []):
            pr = p.get("properties", {})
            title = _txt((pr.get("Idea") or {}).get("title"))
            if not title:
                continue
            out.append({
                "idea": title,
                "notes": _txt((pr.get("Notes") or {}).get("rich_text")),
                "target": _txt((pr.get("Target") or {}).get("rich_text")),
                "hook": _txt((pr.get("Hook") or {}).get("rich_text")),
                "format": _ms(pr.get("Format")),
                "tech": _ms(pr.get("Tech")),
                "stage": _sel(pr.get("Stage")),
                "impact": _sel(pr.get("Impact")),
            })
    except Exception as e:
        print("⚠ Ideas fetch 예외:", e)
    return out


def pick_idea(seq=0):
    """비-Archive 아이디어를 제목순으로 안정 정렬하고 seq 인덱스로 회전 선택. 없으면 None."""
    ideas = [i for i in fetch_ideas() if i.get("stage") != "Archive"]
    if not ideas:
        return None
    ideas.sort(key=lambda i: i["idea"])
    return ideas[seq % len(ideas)]


def pick_ideas(n=5, seq=0):
    """위클리 큐레이션용 — 비-Archive 아이디어 중 seq부터 n개를 회전 선택."""
    pool = [i for i in fetch_ideas() if i.get("stage") != "Archive"]
    if not pool:
        return []
    pool.sort(key=lambda i: i["idea"])
    n = min(n, len(pool))
    start = seq % len(pool)
    return [pool[(start + k) % len(pool)] for k in range(n)]


def as_brief(idea):
    """프롬프트에 넣을 소재 브리프 텍스트."""
    if not idea:
        return ""
    parts = [f"아이디어: {idea['idea']}"]
    if idea.get("hook"):
        parts.append("후킹메시지(표지·릴스 후크의 출발점): " + idea["hook"])
    if idea.get("format"):
        parts.append("형식: " + ", ".join(idea["format"]))
    if idea.get("tech"):
        parts.append("기술: " + ", ".join(idea["tech"]))
    if idea.get("target"):
        parts.append("타깃: " + idea["target"])
    if idea.get("stage"):
        parts.append("단계: " + idea["stage"])
    if idea.get("notes"):
        parts.append("메모: " + idea["notes"])
    return "\n".join(parts)
