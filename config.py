"""
브랜드 전략 설정.
parkjunhyuk.xyz — 기술·공간·브랜드를 연결해 새로운 경험을 만드는 사람.

요일별 테마와 7개 콘텐츠 기둥, 플랫폼별 역할을 정의합니다.
generate.py 가 이 값을 Claude 프롬프트에 주입해 매일 글을 생성합니다.
"""

# 콘텐츠 생성에 사용할 Claude 모델 (속도·비용 균형: sonnet 권장. 더 높은 품질은 claude-opus-4-8)
CLAUDE_MODEL = "claude-sonnet-4-6"

# 플랫폼별 브랜드 포지션 / 역할 ("같은 소재 하나 → 3개 게시물")
PLATFORM_ROLES = {
    "instagram": {
        "position": "Visual Thinker",
        "question": "나는 무엇을 만들고 있는가",
        "style": "짧고 강한 훅 + 줄바꿈이 많은 가독성. 마지막에 시리즈 태그와 해시태그 6~8개.",
        "length": "120~220자 본문 + 해시태그",
    },
    "facebook": {
        "position": "Thought Leader",
        "question": "나는 왜 그렇게 생각하는가",
        "style": ("1인칭 에세이. 첫 줄은 일반론 금지 — 구체적·개인적·역설적 한 문장으로 "
                  "스크롤을 멈추게(예: '나는 ...한 적이 있다'). 주장 → 근거 → 내 사례 → 닫기. "
                  "짧은 문단마다 빈 줄(\\n\\n)로 끊어 스캔 가능하게. "
                  "마지막은 그 글의 소재에 딱 맞는 '구체적 질문' 한 줄로 닫는다('어떻게 생각하세요'같은 "
                  "일반 질문 금지). 본문에 외부 링크(URL)를 넣지 말 것(도달 페널티). 해시태그 없음."),
        "length": "350~600자",
    },
    "linkedin": {
        "position": "Experience Innovation Director",
        "question": "나는 어떻게 비즈니스 문제를 해결하는가",
        "style": ("뉴스/분석 톤(엔터·테크 업계 애널리스트 피드 느낌). "
                  "첫 줄은 본인의 경험·관찰에 근거한 구체적·역설적 훅으로 스크롤을 멈추게. "
                  "1~2문장 짧은 문단마다 빈 줄(\\n\\n)로 끊어 스캔 가능하게. "
                  "★통계·퍼센트·인원수·배수 같은 수치를 지어내지 말 것 — 검증 불가한 숫자를 사실처럼 쓰면 거짓이 된다. "
                  "수치 대신 본인 경험 기반의 정성적 표현을 쓰고, 꼭 예를 들 땐 '가령'으로 가정임을 밝힌다. "
                  "끝에서 두 번째 문단에 한 줄 통찰(인용형도 좋다 — 곧은 따옴표 대신 “ ” 사용). "
                  "맨 끝 줄에 해시태그 4~6개(영문+한글 혼합)."),
        "length": "500~800자",
    },
}

# 요일별 테마 (월=0 ... 일=6) — Instagram 운영 기준, 3개 플랫폼 공통 소재로 변주
WEEKLY_THEMES = {
    0: "이번 주 풀어야 할 공간 경험 설계 문제",
    1: "전시/미디어아트 현장 인사이트",
    2: "AI 크리에이티브 실험",
    3: "좋은 공간 디자인 사례 분석",
    4: "프로젝트 스케치 / 제작 비하인드",
    5: "창작 노트 / 개인 철학",
    6: "한 주의 인사이트 정리",
}

# 7개 콘텐츠 기둥
CONTENT_PILLARS = [
    "Media Art (공간·전시·인터랙션·공공미디어)",
    "AI Creative (AI 영상·디자인·워크플로우)",
    "Brand Experience (브랜딩·고객 경험·공간 브랜딩)",
    "Creative Leadership (팀 운영·PM·디렉팅)",
    "Future City (스마트시티·디지털 공공예술·도시 경험)",
    "Content Business (콘텐츠 수익화·IP·문화콘텐츠 산업)",
    "Creator OS (CRM·자동화·생산성)",
]

# 반복 가능한 IG 시리즈
IG_SERIES = [
    "1 Minute Media Art",
    "Before → After",
    "Creative Director's Notebook",
    "Space Inspiration",
    "AI for Creators",
]

BRAND_TAGLINE = "기술·공간·브랜드를 연결해 새로운 경험을 만드는 사람"
BRAND_HANDLE = "parkjunhyuk.xyz"
# SILO→SILOLab 으로 정정. SILOLab·STUDIO GALE 는 중복되는 공간·경험 작업이라 하나로 합쳐 표기.
CAREER = "CJ → SILOLab → SM"
