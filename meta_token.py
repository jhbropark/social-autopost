"""
Meta(Facebook/Instagram) 장기 토큰 발급 헬퍼 (로컬에서 한 번 실행).

이 스크립트가 하는 일:
  1) 짧은 사용자 토큰 → 장기(60일) 사용자 토큰으로 교환
  2) me/accounts 로 페이지의 '무만료' 페이지 토큰 조회
  3) 각 페이지의 instagram_business_account(IG ID) 조회
  → GitHub Secret 에 넣을 FB_PAGE_ID / FB_PAGE_ACCESS_TOKEN / IG_USER_ID 를 출력

준비:
  - META_APP_ID, META_APP_SECRET : 앱 → 앱 설정 → 기본 설정
  - META_SHORT_TOKEN : Graph API Explorer에서 'Generate Access Token'으로 받은 사용자 토큰
    (parkjunhyuk-autopost 앱, 권한: instagram_basic, instagram_content_publish,
     pages_show_list, pages_read_engagement, business_management)

실행 (PowerShell):
  cd "C:\\Users\\im\\Downloads\\claude code\\social-autopost"
  $env:META_APP_ID="앱ID"; $env:META_APP_SECRET="앱시크릿"; $env:META_SHORT_TOKEN="Explorer토큰"; python meta_token.py
"""
import os
import sys
import requests

GRAPH = "https://graph.facebook.com/v21.0"

APP_ID = os.environ.get("META_APP_ID")
APP_SECRET = os.environ.get("META_APP_SECRET")
SHORT = os.environ.get("META_SHORT_TOKEN")


def main():
    if not (APP_ID and APP_SECRET and SHORT):
        sys.exit("META_APP_ID / META_APP_SECRET / META_SHORT_TOKEN 환경변수를 설정하세요.")

    # 1) 장기 사용자 토큰
    r = requests.get(f"{GRAPH}/oauth/access_token", params={
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "fb_exchange_token": SHORT,
    }, timeout=30)
    r.raise_for_status()
    long_user = r.json()["access_token"]
    print("✅ 장기 사용자 토큰 획득\n")

    # 2) 페이지 + 무만료 페이지 토큰
    pages = requests.get(f"{GRAPH}/me/accounts", params={"access_token": long_user}, timeout=30)
    pages.raise_for_status()
    data = pages.json().get("data", [])
    if not data:
        sys.exit("연결된 페이지가 없습니다. Explorer 동의에서 페이지를 선택했는지 확인하세요.")

    print("================ 등록할 Secret 값 ================")
    for p in data:
        pid, name, ptoken = p["id"], p.get("name", ""), p["access_token"]
        # 3) IG 비즈니스 계정 (페이지 토큰으로 조회)
        ig = requests.get(f"{GRAPH}/{pid}", params={
            "fields": "instagram_business_account,name",
            "access_token": ptoken,
        }, timeout=30).json()
        ig_id = (ig.get("instagram_business_account") or {}).get("id")

        print(f"\n[페이지] {name}")
        print(f"FB_PAGE_ID           = {pid}")
        print(f"FB_PAGE_ACCESS_TOKEN = {ptoken}")
        if ig_id:
            print(f"IG_USER_ID           = {ig_id}   ✅ Instagram 연결됨")
        else:
            print("IG_USER_ID           = (없음) ⚠️ 이 페이지에 IG 비즈니스 계정이 연결돼 있지 않습니다.")
    print("\n==================================================")
    print("위 값을 GitHub Secrets 에 등록하세요. (IG_USER_ID는 비워둬도 코드가 자동 조회)")


if __name__ == "__main__":
    main()
