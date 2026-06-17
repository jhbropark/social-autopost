"""
LinkedIn refresh_token 일회용 발급 스크립트 (로컬에서 한 번만 실행).

준비:
  1) LinkedIn 앱 → Auth 탭 → "Authorized redirect URLs" 에
     http://localhost:8000/callback  추가
  2) 같은 화면의 Client ID / Client Secret 확인

실행:
  LINKEDIN_CLIENT_ID=xxx LINKEDIN_CLIENT_SECRET=yyy python linkedin_auth.py
  (Windows PowerShell)
  $env:LINKEDIN_CLIENT_ID="xxx"; $env:LINKEDIN_CLIENT_SECRET="yyy"; python linkedin_auth.py

브라우저가 열리면 로그인/동의 → 콘솔에 access_token / refresh_token 이 출력됩니다.
출력된 refresh_token 을 GitHub Secret  LINKEDIN_REFRESH_TOKEN  으로 등록하세요.
(refresh_token 은 365일 유효 — 만료되면 이 스크립트를 다시 한 번 실행)
"""
import os
import sys
import secrets
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

REDIRECT = "http://localhost:8000/callback"
SCOPE = "openid profile w_member_social"
PORT = 8000

CLIENT_ID = os.environ.get("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET")
STATE = secrets.token_urlsafe(12)
_code_holder = {}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.urlparse(self.path)
        if q.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        params = urllib.parse.parse_qs(q.query)
        _code_holder["code"] = params.get("code", [None])[0]
        _code_holder["state"] = params.get("state", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("<h2>완료. 이 창을 닫고 콘솔로 돌아가세요.</h2>".encode("utf-8"))

    def log_message(self, *a):
        pass


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        sys.exit("LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET 환경변수를 설정하세요.")

    auth_url = "https://www.linkedin.com/oauth/v2/authorization?" + urllib.parse.urlencode({
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT,
        "scope": SCOPE,
        "state": STATE,
    })
    print("브라우저에서 동의를 진행하세요. 안 열리면 아래 URL을 직접 여세요:\n", auth_url)
    webbrowser.open(auth_url)

    httpd = HTTPServer(("localhost", PORT), Handler)
    httpd.handle_request()  # 콜백 1회만 처리

    if _code_holder.get("state") != STATE:
        sys.exit("state 불일치 — 보안상 중단.")
    code = _code_holder.get("code")
    if not code:
        sys.exit("authorization code 를 받지 못했습니다.")

    tok = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        timeout=30,
    )
    tok.raise_for_status()
    data = tok.json()

    print("\n================ 결과 ================")
    rt = data.get("refresh_token")
    if rt:
        print("access_token (60일):", data.get("access_token", "")[:24], "...")
        print("\n✅ refresh_token (365일) — 이걸 Secret LINKEDIN_REFRESH_TOKEN 에 등록:\n")
        print(rt)
        print("\nrefresh_token_expires_in:", data.get("refresh_token_expires_in"))
    else:
        print("⚠️ 이 앱은 refresh_token 미발급(자동 갱신 불가). 아래 60일 access_token 을")
        print("   Secret  LINKEDIN_ACCESS_TOKEN  에 등록하세요. (약 60일 후 재실행 필요)")
        print(f"\n   expires_in(초): {data.get('expires_in')}  (~{int(data.get('expires_in', 0))//86400}일)\n")
        print("LINKEDIN_ACCESS_TOKEN:\n")
        print(data.get("access_token", ""))
    print("======================================")


if __name__ == "__main__":
    main()
