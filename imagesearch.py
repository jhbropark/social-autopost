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
