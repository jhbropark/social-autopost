"""
Krea AI 이미지 생성. KREA_API_KEY 가 있으면 표지 배경을 Pexels 대신 AI로 생성한다.
  POST https://api.krea.ai/generate/image/{KREA_MODEL}  (Bearer 토큰, {prompt,width,height})
  → {job_id} → GET https://api.krea.ai/jobs/{job_id} 폴링 → result.urls[0]

환경변수:
  KREA_API_KEY : 필수(없으면 None 반환 → 호출측이 Pexels 로 폴백)
  KREA_MODEL   : 모델 경로(기본 "bfl/flux-1-dev"; 예: "krea/krea-2-large")
"""
import os
import io
import time
import requests
from PIL import Image

BASE = "https://api.krea.ai"
UA = "parkjunhyuk-autopost/1.0"


def _prompt(query):
    return (
        f"{query}. cinematic media art installation, immersive exhibition space, "
        "volumetric light, dramatic moody lighting, dark atmosphere, architectural, "
        "high detail, photographic, no text, no watermark, no human faces"
    )


def generate(query, width=1024, height=1280):
    token = os.environ.get("KREA_API_KEY")
    if not (token and query):
        return None
    model = (os.environ.get("KREA_MODEL") or "bfl/flux-1-dev").strip("/")
    headers = {"Authorization": f"Bearer {token}", "User-Agent": UA, "Content-Type": "application/json"}
    try:
        r = requests.post(
            f"{BASE}/generate/image/{model}",
            headers=headers,
            json={"prompt": _prompt(query), "width": width, "height": height},
            timeout=60,
        )
        if r.status_code >= 300:
            print("⚠ Krea 생성 요청 실패:", r.status_code, r.text[:300])
            return None
        job_id = r.json().get("job_id") or r.json().get("id")
        if not job_id:
            print("⚠ Krea: job_id 없음:", r.text[:300])
            return None
        for _ in range(60):
            time.sleep(2)
            s = requests.get(f"{BASE}/jobs/{job_id}", headers=headers, timeout=30)
            if s.status_code >= 300:
                print("⚠ Krea 폴링 실패:", s.status_code, s.text[:200])
                return None
            js = s.json()
            st = js.get("status")
            if st in ("completed", "succeeded", "success"):
                urls = ((js.get("result") or {}).get("urls")) or js.get("urls") or []
                if urls:
                    return _download(urls[0])
                print("⚠ Krea: 결과 URL 없음:", str(js)[:300])
                return None
            if st in ("failed", "error", "cancelled"):
                print("⚠ Krea 생성 실패:", str(js)[:300])
                return None
    except Exception as e:
        print("⚠ Krea 예외:", e)
    return None


def _download(url):
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=60)
        if r.status_code < 300 and r.content:
            return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception:
        pass
    return None
