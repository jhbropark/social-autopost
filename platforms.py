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
    """게시 작성자 URN. LINKEDIN_ORG_ID 가 있으면 조직 페이지(urn:li:organization:{id})로 게시
    — w_organization_social 권한 필요. 없으면 개인 프로필(urn:li:person:{sub})로 게시."""
    org = os.environ.get("LINKEDIN_ORG_ID")
    if org:
        return f"urn:li:organization:{org.split(':')[-1]}"
    me = requests.get("https://api.linkedin.com/v2/userinfo",
                      headers={"Authorization": f"Bearer {token}"}, timeout=30)
    me.raise_for_status()
    return f"urn:li:person:{me.json()['sub']}"


# LinkedIn /rest/posts 의 commentary 는 little-text 포맷이라 예약문자를 백슬래시로
# 이스케이프해야 한다. 안 하면 그 지점에서 본문이 잘린다(예: 괄호 '('에서 끊김).
# 해시태그는 살리려 '#' 만 제외한다(맨 끝에 위치).
_LI_RESERVED = set("\\(){}[]<>|*~_@")


def _li_escape(text: str) -> str:
    if not text:
        return text
    return "".join("\\" + c if c in _LI_RESERVED else c for c in text)


def _li_post(token, author, commentary, content=None):
    """공통 게시 호출. content 가 있으면 미디어 포함 게시."""
    body = {
        "author": author,
        "commentary": _li_escape(commentary),
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
def _fb_page_token(page_id: str, token: str) -> str:
    """FB_PAGE_ACCESS_TOKEN 이 시스템 사용자 토큰이면 페이지 토큰을 받아온다.
    이미 페이지 토큰이어도 같은 호출로 페이지 토큰을 반환하므로 안전하다."""
    try:
        r = requests.get(
            f"{GRAPH}/{page_id}",
            params={"fields": "access_token", "access_token": token},
            timeout=30,
        )
        if r.status_code < 300:
            return r.json().get("access_token", token)
    except Exception:
        pass
    return token


def post_facebook(text: str, image_url: str = None, link: str = None) -> dict:
    """페이지 글 게시.
    image_url 있으면 사진 게시(/photos)로 — 텍스트 전용보다 도달이 크게 높다.
    link 있으면 게시 후 첫 댓글로 링크를 단다(본문 외부링크는 도달 페널티라 댓글로)."""
    page_id = os.environ["FB_PAGE_ID"]
    page_token = _fb_page_token(page_id, os.environ["FB_PAGE_ACCESS_TOKEN"])
    if image_url:
        r = requests.post(
            f"{GRAPH}/{page_id}/photos",
            data={"url": image_url, "message": text, "access_token": page_token},
            timeout=60,
        )
    else:
        r = requests.post(
            f"{GRAPH}/{page_id}/feed",
            data={"message": text, "access_token": page_token},
            timeout=30,
        )
    if r.status_code >= 300:
        raise RuntimeError(f"Facebook {r.status_code}: {r.text}")
    res = r.json()
    # 사진 게시는 story id가 post_id, 일반 글은 id
    target = res.get("post_id") or res.get("id")
    if link and target:
        try:
            requests.post(
                f"{GRAPH}/{target}/comments",
                data={"message": link, "access_token": page_token},
                timeout=30,
            )
        except Exception:
            pass  # 댓글 실패는 게시 성공을 막지 않는다
    return res


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
    # .strip(): gh secret set 시 섞일 수 있는 공백·줄바꿈을 제거(없으면 "Cannot parse access token" 400)
    ig_token = (os.environ.get("INSTAGRAM_ACCESS_TOKEN") or "").strip()
    if ig_token:
        return IG_GRAPH, ig_token, os.environ["IG_USER_ID"].strip()
    fb_token = os.environ["FB_PAGE_ACCESS_TOKEN"].strip()
    return GRAPH, fb_token, _ig_user_id(fb_token)


def ig_permalink(media_id: str):
    """게시된 IG 미디어의 공개 영구링크(permalink) 조회. 실패하면 None."""
    try:
        base, token, _ = _ig_endpoint()
        r = requests.get(f"{base}/{media_id}", params={"fields": "permalink", "access_token": token}, timeout=20)
        if r.status_code < 300:
            return r.json().get("permalink")
    except Exception:
        pass
    return None


# IG 일시 오류 코드 — 재시도로 대부분 복구된다.
#   9007/2207027 컨테이너가 아직 준비 안 됨(비동기 처리 지연)
#   9004/2207052 미디어 URL 다운로드 실패(raw.githubusercontent 일시 지연)
#   1·2 서버 일시 오류, 4·17·32·613 레이트리밋
_IG_TRANSIENT = {1, 2, 4, 17, 32, 613, 9004, 9007}


def _ig_call(url, data, what, attempts=4, delay=8):
    """IG API POST — 일시 오류(미디어 미준비·다운로드 실패·레이트리밋·5xx)면
    지수 백오프(8·16·32초)로 재시도. 영구 오류는 즉시 중단."""
    last = ""
    for i in range(attempts):
        r = requests.post(url, data=data, timeout=60)
        if r.status_code < 300:
            return r.json()
        last = f"{r.status_code}: {r.text}"
        try:
            err = r.json().get("error", {}) or {}
        except Exception:
            err = {}
        transient = bool(err.get("is_transient")) or err.get("code") in _IG_TRANSIENT or r.status_code >= 500
        if not transient or i == attempts - 1:
            break
        wait = delay * (2 ** i)
        msg = str(err.get("error_user_msg") or err.get("message") or "")[:90]
        print(f"⏳ IG {what} 일시 오류 — {wait}s 후 재시도 ({i + 1}/{attempts - 1}): {msg}")
        time.sleep(wait)
    raise RuntimeError(f"IG {what} {last}")


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
        creation_id = _ig_call(
            f"{base}/{ig_id}/media",
            {"image_url": image_urls[0], "caption": caption, "access_token": token},
            "media create",
        )["id"]
    else:
        # 캐러셀: 1) 각 슬라이드를 carousel_item 으로 생성
        child_ids = []
        for url in image_urls:
            ch = _ig_call(
                f"{base}/{ig_id}/media",
                {"image_url": url, "is_carousel_item": "true", "access_token": token},
                "carousel item",
            )
            child_ids.append(ch["id"])
        # 2) 캐러셀 컨테이너 생성
        creation_id = _ig_call(
            f"{base}/{ig_id}/media",
            {
                "media_type": "CAROUSEL",
                "children": ",".join(child_ids),
                "caption": caption,
                "access_token": token,
            },
            "carousel container",
        )["id"]

    # 컨테이너가 게시 가능 상태가 될 때까지 대기 (비동기 처리 완료 보장)
    _wait_until_ready(base, creation_id, token)

    # 게시 — 아직 준비 전이면(9007) 백오프 재시도
    return _ig_call(
        f"{base}/{ig_id}/media_publish",
        {"creation_id": creation_id, "access_token": token},
        "publish",
    )


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
    creation_id = _ig_call(f"{base}/{ig_id}/media", data, "reel create")["id"]

    # 영상 처리 대기(최대 ~6분)
    _wait_until_ready(base, creation_id, token, attempts=60, delay=6)

    # 게시 — 아직 준비 전이면(9007) 백오프 재시도
    return _ig_call(
        f"{base}/{ig_id}/media_publish",
        {"creation_id": creation_id, "access_token": token},
        "reel publish",
    )
