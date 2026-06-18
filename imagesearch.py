"""
주제 키워드로 표지 배경 사진을 검색해 PIL.Image 로 반환한다.

우선순위:
  1) PEXELS_API_KEY 가 있으면 Pexels(고품질·관련성·상업사용 OK·출처표기 불필요)
  2) 없거나 실패하면 Openverse CC0/PDM(키 불필요, 공공도메인)
둘 다 실패하면 None → 호출측은 단색 패널로 폴백.
"""
import os
import io
import requests
from PIL import Image

PEXELS = "https://api.pexels.com/v1/search"
OPENVERSE = "https://api.openverse.org/v1/images/"
UA = "parkjunhyuk-autopost/1.0"


def _download(url):
    if not url:
        return None
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=40)
        if r.status_code < 300 and r.content:
            return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception:
        pass
    return None


def _pexels(query, key, pick=0):
    try:
        r = requests.get(
            PEXELS,
            headers={"Authorization": key, "User-Agent": UA},
            params={"query": query, "orientation": "landscape", "size": "large", "per_page": 15},
            timeout=40,
        )
        if r.status_code >= 300:
            return None
        photos = r.json().get("photos", [])
        if not photos:
            return None
        src = photos[pick % len(photos)].get("src", {})
        return _download(src.get("landscape") or src.get("large2x") or src.get("large") or src.get("original"))
    except Exception:
        return None


def _openverse(query, pick=0):
    try:
        r = requests.get(
            OPENVERSE,
            headers={"User-Agent": UA},
            params={"q": query, "license": "cc0,pdm", "page_size": 15},
            timeout=40,
        )
        if r.status_code >= 300:
            return None
        results = r.json().get("results", [])
        if not results:
            return None
        it = results[pick % len(results)]
        return _download(it.get("url") or it.get("thumbnail"))
    except Exception:
        return None


def search_image(query, pick=0):
    """가로형 사진 1장을 PIL.Image(RGB)로. 실패 시 None."""
    if not query:
        return None
    key = os.environ.get("PEXELS_API_KEY")
    img = _pexels(query, key, pick) if key else None
    if img is None:
        img = _openverse(query, pick)
    return img


PEXELS_VIDEO = "https://api.pexels.com/videos/search"


def _pexels_video_link(query, key, pick=0):
    """세로형 스톡 영상 mp4 링크 1개를 고른다(720~1920 높이 선호)."""
    try:
        r = requests.get(
            PEXELS_VIDEO,
            headers={"Authorization": key, "User-Agent": UA},
            params={"query": query, "orientation": "portrait", "size": "medium", "per_page": 12},
            timeout=40,
        )
        if r.status_code >= 300:
            return None
        vids = r.json().get("videos", [])
        if not vids:
            return None
        v = vids[pick % len(vids)]
        files = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("link")]
        if not files:
            return None
        files.sort(key=lambda f: (f.get("height") or 0))
        chosen = next((f for f in files if (f.get("height") or 0) >= 1200), files[-1])
        return chosen["link"]
    except Exception:
        return None


def search_video(query, out_path, pick=0):
    """주제 키워드로 세로 스톡 영상 mp4를 out_path에 내려받고 경로 반환. 실패 시 None.
    영상은 Pexels(키 필요)만 사용 — 키 없으면 None."""
    key = os.environ.get("PEXELS_API_KEY")
    if not key or not query:
        return None
    link = _pexels_video_link(query, key, pick)
    if not link:
        return None
    try:
        r = requests.get(link, headers={"User-Agent": UA}, timeout=180, stream=True)
        if r.status_code >= 300:
            return None
        with open(out_path, "wb") as fh:
            for chunk in r.iter_content(8192):
                if chunk:
                    fh.write(chunk)
        return out_path
    except Exception:
        return None
