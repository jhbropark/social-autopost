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
import time
import requests

GRAPH = "https://graph.facebook.com/v21.0"


# ---------------------------------------------------------------- LinkedIn
def _linkedin_token() -> str:
    """refresh_token(+client_id/secret)이 있으면 매번 새 액세스 토큰을 발급.
    없으면 기존 LINKEDIN_ACCESS_TOKEN(수동 60일)을 그대로 사용."""
    rt = os.environ.get("LINKEDIN_REFRESH_TOKEN")
    cid = os.environ.get("LINKEDIN_CLIENT_ID")
    csec = os.environ.get("LINKEDIN_CLIENT_SECRET")
    if rt and cid and csec:
        r = requests.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "refresh_token",
                "refresh_token": rt,
                "client_id": cid,
                "client_secret": csec,
            },
            timeout=30,
        )
        if r.status_code >= 300:
            raise RuntimeError(f"LinkedIn refresh {r.status_code}: {r.text}")
        return r.json()["access_token"]
    return os.environ["LINKEDIN_ACCESS_TOKEN"]


def post_linkedin(text: str) -> dict:
    token = _linkedin_token()
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
        "LinkedIn-Version": "202601",
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


IG_GRAPH = "https://graph.instagram.com/v21.0"


def _ig_endpoint():
    """게시에 사용할 (base_url, token, ig_user_id) 결정.
    INSTAGRAM_ACCESS_TOKEN 이 있으면 Instagram 로그인 API(graph.instagram.com)를 쓴다
    — FB 페이지·비즈니스 불필요. 없으면 FB 페이지 토큰(graph.facebook.com)으로 폴백."""
    ig_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if ig_token:
        return IG_GRAPH, ig_token, os.environ["IG_USER_ID"]
    fb_token = os.environ["FB_PAGE_ACCESS_TOKEN"]
    return GRAPH, fb_token, _ig_user_id(fb_token)


def _wait_until_ready(base, container_id, token, attempts=15, delay=4):
    """미디어 컨테이너가 게시 가능(FINISHED) 상태가 될 때까지 폴링.
    IG는 컨테이너 생성이 비동기라, 생성 직후 media_publish 하면
    'media is not ready'(9007/2207027) 오류가 난다."""
    for _ in range(attempts):
        r = requests.get(
            f"{base}/{container_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=30,
        )
        if r.status_code < 300:
            status = r.json().get("status_code")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise RuntimeError(f"IG container 처리 실패: {r.text}")
        time.sleep(delay)
    # 폴링이 끝나도 FINISHED를 못 봤으면 일단 진행(아래 publish에서 최종 판정)


def post_instagram(caption: str, image_urls) -> dict:
    """image_urls: 단일 URL(str) 또는 캐러셀용 URL 리스트(2~10장)."""
    base, token, ig_id = _ig_endpoint()
    if isinstance(image_urls, str):
        image_urls = [image_urls]

    # 단일 이미지
    if len(image_urls) == 1:
        c = requests.post(
            f"{base}/{ig_id}/media",
            data={"image_url": image_urls[0], "caption": caption, "access_token": token},
            timeout=60,
        )
        if c.status_code >= 300:
            raise RuntimeError(f"IG media create {c.status_code}: {c.text}")
        creation_id = c.json()["id"]
    else:
        # 캐러셀: 1) 각 슬라이드를 carousel_item 으로 생성
        child_ids = []
        for url in image_urls:
            ch = requests.post(
                f"{base}/{ig_id}/media",
                data={"image_url": url, "is_carousel_item": "true", "access_token": token},
                timeout=60,
            )
            if ch.status_code >= 300:
                raise RuntimeError(f"IG carousel item {ch.status_code}: {ch.text}")
            child_ids.append(ch.json()["id"])
        # 2) 캐러셀 컨테이너 생성
        c = requests.post(
            f"{base}/{ig_id}/media",
            data={
                "media_type": "CAROUSEL",
                "children": ",".join(child_ids),
                "caption": caption,
                "access_token": token,
            },
            timeout=60,
        )
        if c.status_code >= 300:
            raise RuntimeError(f"IG carousel container {c.status_code}: {c.text}")
        creation_id = c.json()["id"]

    # 컨테이너가 게시 가능 상태가 될 때까지 대기 (비동기 처리 완료 보장)
    _wait_until_ready(base, creation_id, token)

    # 게시
    p = requests.post(
        f"{base}/{ig_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=60,
    )
    if p.status_code >= 300:
        raise RuntimeError(f"IG publish {p.status_code}: {p.text}")
    return p.json()
