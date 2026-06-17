# 토큰 발급 가이드

이 작업들은 **본인 계정에서 직접** 하셔야 합니다(개발자 앱 생성·OAuth 승인은 대행 불가).
각 단계 끝의 **굵은 값**을 GitHub Secret으로 등록하면 됩니다.

발급할 시크릿 목록:
| Secret | 용도 |
|---|---|
| `ANTHROPIC_API_KEY` | 매일 글 생성 |
| `LINKEDIN_REFRESH_TOKEN` + `LINKEDIN_CLIENT_ID` + `LINKEDIN_CLIENT_SECRET` | LinkedIn 게시 (자동 갱신, 권장) |
| `LINKEDIN_ACCESS_TOKEN` | LinkedIn 게시 (수동 60일, 폴백) |
| `FB_PAGE_ID` | Facebook 페이지 식별 |
| `FB_PAGE_ACCESS_TOKEN` | Facebook·Instagram 게시 |
| `IG_USER_ID` | Instagram 계정(선택, 자동조회 가능) |

---

## 0. Anthropic (콘텐츠 생성)
1. https://console.anthropic.com → **API Keys** → Create Key
2. 값을 복사 → Secret **`ANTHROPIC_API_KEY`**
3. 결제수단 등록 필요(글 1건 생성 비용은 매우 적음, sonnet 기준 하루 1~2원 수준).

---

## 1. LinkedIn (가장 간단)
개인 프로필에 글을 올리는 데 필요한 건 `w_member_social` 스코프 토큰 하나입니다.

1. https://www.linkedin.com/developers/apps → **Create app**
   - 회사 페이지 연결을 요구하면, 본인 소유 LinkedIn 페이지를 하나 만들어 연결(없으면 임시 생성).
2. 앱 **Products** 탭 → 다음 2개 추가(즉시 승인됨):
   - **Sign In with LinkedIn using OpenID Connect**
   - **Share on LinkedIn**
### 방법 A — 자동 갱신 (권장, refresh_token)
한 번 인증해두면 365일 동안 매 실행마다 토큰이 자동 발급됩니다.
1. 앱 **Auth** 탭 → **Authorized redirect URLs** 에 추가:
   ```
   http://localhost:8000/callback
   ```
2. 같은 화면의 **Client ID / Client Secret** 확인 → Secret 등록:
   **`LINKEDIN_CLIENT_ID`**, **`LINKEDIN_CLIENT_SECRET`**
3. 로컬에서 일회용 스크립트 실행:
   ```powershell
   $env:LINKEDIN_CLIENT_ID="xxx"; $env:LINKEDIN_CLIENT_SECRET="yyy"; python linkedin_auth.py
   ```
   브라우저 동의 후 콘솔에 출력된 **refresh_token** 복사 → Secret **`LINKEDIN_REFRESH_TOKEN`**
4. ⚠️ 만약 출력에 refresh_token 이 **없으면**, 이 앱은 아직 refresh token 발급 대상이 아닙니다.
   → 방법 B(수동)로 진행하세요. (refresh_token 은 365일 후 재실행해 갱신)

### 방법 B — 수동 토큰 (폴백, 60일)
1. 앱 **Auth** 탭 → **OAuth 2.0 tools** → *Create token* (또는 https://www.linkedin.com/developers/tools/oauth )
   - 스코프 체크: `openid`, `profile`, `w_member_social`
   - **Request access token** → 토큰 복사 → Secret **`LINKEDIN_ACCESS_TOKEN`**
2. ⚠️ 약 **60일** 후 만료 → 만료 시 위를 다시 해서 Secret 갱신.

> 코드는 자동 갱신(A)을 우선 사용하고, 그 값이 없을 때만 수동 토큰(B)으로 폴백합니다.

---

## 2. Facebook 페이지 + Instagram (Meta 앱 하나로 둘 다)

### 준비
- **Instagram을 비즈니스/크리에이터 계정으로 전환** (IG 앱 → 설정 → 계정 유형 전환)
- 그 **Instagram을 Facebook 페이지(parkjunhyukxyz)에 연결** (페이지 설정 → 연결된 계정)

### 앱 만들기
1. https://developers.facebook.com/apps → **Create app** → 유형 **Business**
2. 좌측 **Add products**:
   - **Facebook Login** (또는 그냥 Graph API Explorer 사용)
   - **Instagram Graph API**
3. **App roles**에 본인 계정이 관리자/개발자인지 확인(본인 자산이라 앱 심사 없이 사용 가능).

### 토큰 받기 (Graph API Explorer)
4. https://developers.facebook.com/tools/explorer → 우측에서 본인 앱 선택
5. **Permissions**에 아래를 모두 추가하고 **Generate Access Token**:
   ```
   pages_show_list
   pages_read_engagement
   pages_manage_posts
   instagram_basic
   instagram_content_publish
   business_management
   ```
6. 받은 **User 토큰**으로 페이지 토큰 조회 — Explorer 주소창에 입력 후 전송:
   ```
   GET /me/accounts
   ```
   결과에서 parkjunhyukxyz 페이지의 `id` → Secret **`FB_PAGE_ID`**,
   그 페이지의 `access_token` → 이게 **페이지 토큰**입니다.
7. 페이지 토큰을 **장기 토큰(60일)** 으로 교환(만료 줄이기). 브라우저에서:
   ```
   https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id=<앱ID>&client_secret=<앱시크릿>&fb_exchange_token=<위 User 토큰>
   ```
   반환된 장기 User 토큰으로 다시 `GET /me/accounts` → **페이지 토큰**(이건 보통 만료 없음) 복사
   → Secret **`FB_PAGE_ACCESS_TOKEN`**
8. (선택) Instagram 계정 ID 미리 확인:
   ```
   GET /<FB_PAGE_ID>?fields=instagram_business_account
   ```
   나온 id → Secret **`IG_USER_ID`** (비워두면 스크립트가 자동 조회합니다)

> 핵심 제약: Instagram은 **공개 이미지 URL**로만 게시됩니다. 이 프로젝트는 생성한 이미지를
> 리포지토리에 커밋해 `raw.githubusercontent.com` 공개 URL로 자동 제공하므로 별도 호스팅이 필요 없습니다.
> (리포지토리는 **public** 이어야 raw URL이 외부에서 열립니다. private면 이미지 호스팅을 따로 붙여야 합니다.)

---

## 3. GitHub Secrets 등록
리포지토리 → **Settings → Secrets and variables → Actions → New repository secret**
위에서 모은 값들을 같은 이름으로 등록하면 끝입니다.
