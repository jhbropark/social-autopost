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


LI_VERSION = "202601"
LI_REST = "https://api.linkedin.com/rest"


def _li_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": LI_VERSION,
    }


def _li_author(token):
    """게시 작성자 URN(urn:li:person:{sub}). openid/profile 스코프 필요."""
    me = requests.get("https://api.linkedin.com/v2/userinfo",
                      headers={"Authorization": f"Bearer {token}"}, timeout=30)
    me.raise_for_status()
    return f"urn:li:person:{me.json()['sub']}"


def _li_post(token, author, commentary, content=None):
    """공통 게시 호출. content 가 있으면 미디어 포함 게시."""
    body = {
        "author": author,
        "commentary": commentary,
        "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    if content:
        body["content"] = content
    r = requests.post(f"{LI_REST}/posts",
                      headers={**_li_headers(token), "Content-Type": "application/json"}, json=body, timeout=30)
    if r.status_code >= 300:
        raise RuntimeError(f"LinkedIn post {r.status_code}: {r.text}")
    return {"id": r.headers.get("x-restli-id", "ok")}


def _li_upload(kind, token, author, file_path):
    """documents/images 단일 업로드: initializeUpload → uploadUrl 에 PUT → 미디어 URN 반환."""
    init = requests.post(f"{LI_REST}/{kind}?action=initializeUpload",
                         headers={**_li_headers(token), "Content-Type": "application/json"},
                         json={"initializeUploadRequest": {"owner": author}}, timeout=30)
    if init.status_code >= 300:
        raise RuntimeError(f"LinkedIn {kind} init {init.status_code}: {init.text}")
    val = init.json()["value"]
    urn = val[kind[:-1]]                    # documents→document, images→image
    with open(file_path, "rb") as fh:
        put = requests.put(val["uploadUrl"], data=fh.read(),
                           headers={"Authorization": f"Bearer {token}"}, timeout=180)
    if put.status_code >= 300:
        raise RuntimeError(f"LinkedIn {kind} upload {put.status_code}: {put.text}")
    return urn


def post_linkedin(text: str) -> dict:
    """텍스트 게시."""
    token = _linkedin_token()
    return _li_post(token, _li_author(token), text)


def post_linkedin_document(pdf_path: str, commentary: str, title: str = "parkjunhyuk.xyz") -> dict:
    """PDF 문서(캐러셀) 게시 — 링크드인에서 좌우로 넘기는 슬라이드로 표시."""
    token = _linkedin_token()
    author = _li_author(token)
    urn = _li_upload("documents", token, author, pdf_path)
    return _li_post(token, author, commentary, {"media": {"id": urn, "title": title[:100]}})


def post_linkedin_image(image_path: str, commentary: str, alt: str = "parkjunhyuk.xyz") -> dict:
    """단일 이미지 + 글 게시."""
    token = _linkedin_token()
    author = _li_author(token)
    urn = _li_upload("images", token, author, image_path)
    return _li_post(token, author, commentary, {"media": {"id": urn, "altText": alt[:300]}})


def post_linkedin_video(video_path: str, commentary: str, title: str = "parkjunhyuk.xyz") -> dict:
    """동영상 게시 — 멀티파트 업로드(initialize→PUT parts→finalize)."""
    token = _linkedin_token()
    author = _li_author(token)
    size = os.path.getsize(video_path)
    init = requests.post(f"{LI_REST}/videos?action=initializeUpload",
                         headers={**_li_headers(token), "Content-Type": "application/json"},
                         json={"initializeUploadRequest": {"owner": author, "fileSizeBytes": size,
                                                            "uploadCaptions": False, "uploadThumbnail": False}}, timeout=30)
    if init.status_code >= 300:
        raise RuntimeError(f"LinkedIn video init {init.status_code}: {init.text}")
    val = init.json()["value"]
    urn = val["video"]
    with open(video_path, "rb") as fh:
        data = fh.read()
    etags = []
    for ins in val["uploadInstructions"]:
        part = data[ins["firstByte"]:ins["lastByte"] + 1]
        put = requests.put(ins["uploadUrl"], data=part,
                           headers={"Authorization": f"Bearer {token}"}, timeout=300)
        if put.status_code >= 300:
            raise RuntimeError(f"LinkedIn video upload {put.status_code}: {put.text}")
        etags.append(put.headers.get("ETag"))
    fin = requests.post(f"{LI_REST}/videos?action=finalizeUpload",
                        headers={**_li_headers(token), "Content-Type": "application/json"},
                        json={"finalizeUploadRequest": {"video": urn, "uploadToken": "", "uploadedPartIds": etags}}, timeout=60)
    if fin.status_code >= 300:
        raise RuntimeError(f"LinkedIn video finalize {fin.status_code}: {fin.text}")
    return _li_post(token, author, commentary, {"media": {"id": urn, "title": title[:100]}})


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


def post_reel(video_url: str, caption: str, cover_url: str = None) -> dict:
    """릴스(세로 영상) 게시. video_url 은 공개 접근 가능한 MP4.
    cover_url 이 있으면 그 이미지를 썸네일(커버)로 지정한다.
    영상은 처리에 시간이 걸리므로 컨테이너 status_code 를 길게 폴링한다."""
    base, token, ig_id = _ig_endpoint()
    data = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
        "access_token": token,
    }
    if cover_url:
        data["cover_url"] = cover_url
    c = requests.post(f"{base}/{ig_id}/media", data=data, timeout=60)
    if c.status_code >= 300:
        raise RuntimeError(f"IG reel create {c.status_code}: {c.text}")
    creation_id = c.json()["id"]

    # 영상 처리 대기(최대 ~6분)
    _wait_until_ready(base, creation_id, token, attempts=60, delay=6)

    p = requests.post(
        f"{base}/{ig_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=60,
    )
    if p.status_code >= 300:
        raise RuntimeError(f"IG reel publish {p.status_code}: {p.text}")
    return p.json()
