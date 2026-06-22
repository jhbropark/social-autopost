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

# 요일별 '명명된 포맷'(월=0 ... 일=6).
# 인기 뉴스레터의 성공 공식(고정 요일 + 일관된 포맷 + 관점/큐레이션)을 따른다.
# 각 요일은 반복되는 '코너 이름'을 가지며, 글머리에 그 코너명을 노출한다.
WEEKLY_THEMES = {
    0: "「공간 한 문제」 — 이번 주 풀어야 할 공간·경험 설계 문제 하나를 제시하고 접근법을 보여준다. 글 첫 부분에 코너명 노출.",
    1: "「현장 노트」 — 전시·미디어아트 현장에서 직접 관찰한 것 하나와 거기서 얻은 인사이트. (Right Click Save식 현장 디스패치)",
    2: "「AI 실험실」 — 이번 주 시도한 AI 크리에이티브 실험이나 도구 하나와 그 결과·배운 점. (Designing with AI식)",
    3: "「공간 해부」 — 좋은 공간·전시 사례 하나를 골라 '왜 작동하는가'를 구조로 해부. (Dezeen·Frame식 케이스 분석)",
    4: "「메이킹」 — 진행 중 프로젝트의 제작 과정·스케치·결정의 비하인드. (Creative Lives식 과정 공개)",
    5: "「창작 노트」 — 일과 창작에 대한 1인칭 에세이·관점. (CRAFT TALK식 에세이)",
    6: "「위클리 큐레이션」 — 이번 주 공간·AI·미디어아트에서 주목할 것 3~5개를 각각 한 줄 코멘트와 함께 정리. (Dense Discovery·뉴닉식 다이제스트)",
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
