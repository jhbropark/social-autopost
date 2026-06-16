"""
세 플랫폼 게시 함수. 모든 자격증명은 환경변수(또는 .env)에서 읽는다.

필요 환경변수
  ANTHROPIC_API_KEY        : 콘텐츠 생성 (generate.py)
  LINKEDIN_ACCESS_TOKEN    : LinkedIn w_member_social 토큰 (openid profile 포함 권장)
  FB_PAGE_ID               : Facebook 페이지 ID
  FB_PAGE_ACCESS_TOKEN     : 페이지 액세스 토큰 (pages_manage_posts)
  IG_USER_ID               : Instagram 비즈니스 계정 ID (없으면 페이지에서 자동 조회)
  IMAGE_PUBLIC_URL         : 게시할 이미지의 공개 URL (Instagram 필수)
"""
import os
import requests

GRAPH = "https://graph.facebook.com/v21.0"


# ---------------------------------------------------------------- LinkedIn
def post_linkedin(text: str) -> dict:
    token = os.environ["LINKEDIN_ACCESS_TOKEN"]
    h = {"Authorization": f"Bearer {token}"}
    # 사용자 URN(sub) 조회 — openid/profile 스코프 필요
    me = requests.get("https://api.linkedin.com/v2/userinfo", headers=h, timeout=30)
    me.raise_for_status()
    sub = me.json()["sub"]

    body = {
        "author": f"urn:li:person:{sub}",
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    headers = {
        **h,
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202401",
    }
    r = requests.post("https://api.linkedin.com/rest/posts", headers=headers, json=body, timeout=30)
    if r.status_code >= 300:
        raise RuntimeError(f"LinkedIn {r.status_code}: {r.text}")
    return {"id": r.headers.get("x-restli-id", "ok")}


# ---------------------------------------------------------------- Facebook
def post_facebook(text: str) -> dict:
    page_id = os.environ["FB_PAGE_ID"]
    token = os.environ["FB_PAGE_ACCESS_TOKEN"]
    r = requests.post(
        f"{GRAPH}/{page_id}/feed",
        data={"message": text, "access_token": token},
        timeout=30,
    )
    if r.status_code >= 300:
        raise RuntimeError(f"Facebook {r.status_code}: {r.text}")
    return r.json()


# ---------------------------------------------------------------- Instagram
def _ig_user_id(token: str) -> str:
    if os.environ.get("IG_USER_ID"):
        return os.environ["IG_USER_ID"]
    page_id = os.environ["FB_PAGE_ID"]
    r = requests.get(
        f"{GRAPH}/{page_id}",
        params={"fields": "instagram_business_account", "access_token": token},
        timeout=30,
    )
    r.raise_for_status()
    acc = r.json().get("instagram_business_account")
    if not acc:
        raise RuntimeError("페이지에 연결된 Instagram 비즈니스 계정이 없습니다.")
    return acc["id"]


def post_instagram(caption: str, image_url: str) -> dict:
    token = os.environ["FB_PAGE_ACCESS_TOKEN"]
    ig_id = _ig_user_id(token)

    # 1) 미디어 컨테이너 생성
    c = requests.post(
        f"{GRAPH}/{ig_id}/media",
        data={"image_url": image_url, "caption": caption, "access_token": token},
        timeout=60,
    )
    if c.status_code >= 300:
        raise RuntimeError(f"IG media create {c.status_code}: {c.text}")
    creation_id = c.json()["id"]

    # 2) 게시
    p = requests.post(
        f"{GRAPH}/{ig_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=60,
    )
    if p.status_code >= 300:
        raise RuntimeError(f"IG publish {p.status_code}: {p.text}")
    return p.json()
