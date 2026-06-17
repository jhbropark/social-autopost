# parkjunhyuk.xyz — 소셜 자동 게시

매일 정해진 시각에 **Claude가 오늘의 글을 생성** → **IG 포스터 이미지 렌더** →
**LinkedIn · Facebook · Instagram 동시 게시**하는 GitHub Actions 파이프라인.

브랜드 전략(요일 테마 · 7개 콘텐츠 기둥 · 플랫폼별 역할)은 [`config.py`](config.py)에 들어 있고,
"같은 소재 하나 → 3개 게시물" 원칙대로 한 주제를 IG(무엇을)/FB(왜)/LinkedIn(어떻게)로 변주합니다.

## 구성
| 파일 | 역할 |
|---|---|
| `config.py` | 브랜드 전략 · 요일 테마 · 모델 설정 |
| `generate.py` | Claude API로 오늘의 3종 글 + 이미지 문구 생성 |
| `make_image.py` | Pillow로 1080×1080 포스터(JPEG) 렌더 |
| `platforms.py` | LinkedIn / Facebook / Instagram 게시 함수 |
| `main.py` | generate → publish 오케스트레이션 |
| `.github/workflows/daily.yml` | 매일 cron 실행 |

## 빠른 시작
1. **[TOKENS.md](TOKENS.md)** 따라 토큰 발급 → GitHub Secrets 등록
2. 이 폴더를 **public** GitHub 리포지토리로 push
3. Actions 탭 → **Daily Social Post** → *Run workflow* 로 수동 테스트
4. 잘 되면 매일 **KST 09:00**(UTC 00:00) 자동 게시. 시간은 `daily.yml`의 cron에서 변경.

## 로컬 테스트
```bash
pip install -r requirements.txt
cp .env.example .env   # 값 채우기
python main.py generate          # out/today.jpg, out/posts.json 확인
python make_image.py             # 이미지 렌더만 단독 확인
# Instagram은 공개 URL이 필요하므로 게시 테스트는 Actions에서 권장
python main.py publish           # LinkedIn/Facebook은 로컬에서도 게시됨
```

## 자주 바꾸는 것
- **게시 시각**: `daily.yml` → `cron` (UTC 기준)
- **글 톤/길이/테마**: `config.py`
- **생성 모델**: `config.py`의 `CLAUDE_MODEL` (품질↑ `claude-opus-4-8`, 비용↓ `claude-haiku-4-5-20251001`)
- **이미지 디자인**: `make_image.py`

## 알아둘 제약
- LinkedIn은 refresh_token 방식(자동 갱신, `python linkedin_auth.py`로 1회 발급)을 쓰면 365일에 한 번만 재인증. refresh_token 미발급 앱이면 수동 60일 토큰으로 폴백.
- Instagram은 공개 이미지 URL 필수 → 리포지토리가 **public**이어야 함.
- 게시 실패한 플랫폼이 있어도 나머지는 진행되며, Actions 로그에 실패 사유가 남습니다.
