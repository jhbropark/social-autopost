"""
Claude API로 '오늘의 게시물 3종'을 생성한다.
요일 테마 + 7개 기둥 중 하나를 골라 같은 소재를 IG/FB/LinkedIn 역할에 맞게 변주.

반환(JSON):
{
  "topic": "...",
  "pillar": "...",
  "instagram": {"caption": "...", "series": "Creative Director's Notebook"},
  "facebook": {"text": "..."},
  "linkedin": {"text": "..."},
  "image": {"kicker": "...", "hook": "...", "sub": "..."}
}
"""
import os
import re
import json
import datetime
import anthropic

import config


def _parse_json(text: str) -> dict:
    """모델 응답에서 JSON을 견고하게 추출. 코드펜스/바깥 텍스트/후행 콤마를 정리."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.lower().startswith("json"):
            text = text[4:]
    # 첫 '{' ~ 마지막 '}' 만 취해 본문 바깥 잡텍스트 제거
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e != -1:
        text = text[s:e + 1]
    # 흔한 모델 실수: } 또는 ] 앞 후행 콤마 제거
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    return json.loads(text)


def _today_kst():
    # GitHub Actions는 UTC이므로 KST(+9)로 보정해 요일을 맞춘다.
    return datetime.datetime.utcnow() + datetime.timedelta(hours=9)


# tool-use 스키마: 모델이 이 구조를 채워 반환 → 항상 유효한 객체(파싱 오류 불가)
_S = {"type": "string"}
_CONTENT_TOOL = {
    "name": "post_content",
    "description": "오늘의 소셜 콘텐츠를 IG/Facebook/LinkedIn 역할에 맞게 작성해 제출한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "topic": _S,
            "image_query": _S,
            "instagram": {
                "type": "object",
                "properties": {"caption": _S, "series": _S},
                "required": ["caption"],
            },
            "facebook": {"type": "object", "properties": {"text": _S}, "required": ["text"]},
            "linkedin": {"type": "object", "properties": {"text": _S}, "required": ["text"]},
            "carousel": {
                "type": "object",
                "properties": {
                    "badge": _S,
                    "cover_bold": _S,
                    "cover_accent": _S,
                    "cover_rest": {"type": "array", "items": _S},
                    "cover_keyword": _S,
                    "facts": {"type": "array", "items": _S},
                    "caption": _S,
                    "points": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"title": _S, "body": _S},
                            "required": ["title", "body"],
                        },
                    },
                    "outro_line": _S,
                },
                "required": ["badge", "cover_bold", "cover_keyword", "facts", "points", "outro_line"],
            },
        },
        "required": ["topic", "image_query", "instagram", "facebook", "linkedin", "carousel"],
    },
}


def generate_posts(target=None, variant=0) -> dict:
    today = target or _today_kst()
    weekday = today.weekday()
    theme = config.WEEKLY_THEMES[weekday]
    # 날짜 기반 순환 + variant 오프셋 (같은 날 여러 개 만들 때 기둥/시리즈를 다르게)
    base = today.timetuple().tm_yday + variant
    pillar = config.CONTENT_PILLARS[base % len(config.CONTENT_PILLARS)]
    series = config.IG_SERIES[base % len(config.IG_SERIES)]

    roles = config.PLATFORM_ROLES
    system = (
        f"너는 '{config.BRAND_TAGLINE}'인 {config.BRAND_HANDLE}의 소셜 콘텐츠 작가다. "
        f"경력: {config.CAREER}. 미디어아트·전시·공간·AI 크리에이티브 전문가의 1인칭 목소리로 쓴다. "
        "과장된 마케팅 어투, 이모지 남발, 클리셰를 피하고 통찰이 또렷한 문장을 쓴다. 한국어로 쓴다. "
        "전문용어·영어 약어·번역투를 피하고, 비전문가도 한 번에 이해하는 쉬운 우리말로 쓴다. "
        "각 문장은 짧고 또렷하게. 한 문장에 한 가지 생각만 담는다."
    )

    user = f"""오늘 날짜: {today.strftime('%Y-%m-%d (%A)')}
요일 테마: {theme}
오늘의 콘텐츠 기둥: {pillar}

이 하나의 소재를 세 플랫폼의 역할에 맞게 변주해서 작성해줘. 같은 핵심 메시지, 다른 형식.

[Instagram] 포지션: {roles['instagram']['position']} — "{roles['instagram']['question']}"
  스타일: {roles['instagram']['style']}
  분량: {roles['instagram']['length']}
  IG 시리즈 라벨: "{series}" 를 본문 끝부분에 넣을 것.
  줄바꿈: 한 문단은 1~3줄로 짧게, 문단 사이는 빈 줄(\\n\\n)로 나눠 읽기 쉽게. 문장 중간에서 어색하게 끊지 말 것.
  영어 병기(글로벌 도달): 한국어 본문 뒤에 빈 줄 두 개(\\n\\n) → 영어 2~3줄 핵심 요약 → 빈 줄 → 해시태그 순으로. 영어는 번역투 없이 자연스럽게.

[Facebook] 포지션: {roles['facebook']['position']} — "{roles['facebook']['question']}"
  스타일: {roles['facebook']['style']}
  분량: {roles['facebook']['length']}

[LinkedIn] 포지션: {roles['linkedin']['position']} — "{roles['linkedin']['question']}"
  스타일: {roles['linkedin']['style']}
  분량: {roles['linkedin']['length']}

그리고 Instagram **캐러셀(여러 장 스와이프)** 슬라이드 텍스트도 만들어줘.
구조: 표지 1장 + 포인트 5장 + 아웃트로(코드가 자동 생성). 저장·체류율을 높이는 교육형 캐러셀.
  - badge: 알약형 카테고리 배지. 영문 대문자 1~2단어 (예: "SPACE NOTE", "MEDIA ART", "AI CREATIVE")
  - cover_bold: 표지 헤드라인(볼드) 한 줄. 한국어 12자 이내. 그 자체로 뜻이 통하는 도입 또는 질문.
  - cover_rest: 표지 보조 설명 1줄 배열(원소 1개). 16자 이내. cover_bold를 자연스럽게 잇는 짧은 보충.
  - cover_keyword: 표지에서 가장 크게 박히는 핵심 키워드. 한국어 7자 이내. 명사구나 짧은 단언으로, 그 줄만 봐도 무슨 주제인지 즉시 알 수 있게.
  ※ 표지 카피 규칙(중요): 세 줄을 억지로 한 문장으로 이어붙이지 말 것. 각 줄이 독립적으로 읽혀도 자연스럽고 문법이 맞아야 한다.
    표지만 보고도 '무엇에 관한 글'인지 바로 이해돼야 한다. 도치·생략·말장난으로 호기심만 부풀리는 난해한 카피 금지(예: 금지 "공간 디자이너처럼 AI를 / 다루는 사람은 왜 결과물이 다를까 / 동선이 답이다" — 뜻이 모호함). 쉽고 또렷하게.
  - caption: 푸터 캡션 "{series} · parkjunhyuk.xyz"
  - points: 정확히 5개. 각 {{title: 12자 이내, body: 45자 이내}}.
    · title: 그 장의 핵심을 쉬운 우리말로. "A: B" 같은 라벨식·비유식 제목 금지(예: 금지 "동선: 체이닝 설계", "출구: 포맷 선정"). 무슨 말인지 바로 와닿는 평이한 표현으로.
    · body: 1~2개의 짧고 완결된 문장. 전문용어·영어 약어·번역투 금지. 누구나 한 번에 이해되게.
  - outro_line: 마무리 한 줄. 쉬운 우리말 1~2문장. 두 문장이면 사이에 \\n 1회로 줄을 나눈다(한 문장이 어중간하게 잘리지 않게).
  - image_query: 표지 배경 사진 검색용 **영어** 키워드 2~4단어. 주제를 시각적으로 대표하되 사람 얼굴·글자가 없는 공간/건축/전시/도시/조명/추상 위주. (예: "media art installation", "modern museum interior", "city lights at night", "abstract blue light")
  - facts: 링크드인 표지 우측 요약 패널용 3개. 각 18자 이내. **숫자·핵심 사실 위주**(수치가 있으면 우선 강조, 없으면 가장 또렷한 한 줄). 본문 포인트의 핵심을 압축.
  - cover_accent: cover_bold 안에서 가장 강조할 짧은 어절(cover_bold에 **그대로 들어있는 부분 문자열**). 표지에서 그 어절만 컬러로 강조됨.

JSON 안전 규칙(중요): 모든 문자열 값 안에서 곧은 따옴표(")를 절대 쓰지 말 것 — 인용·강조는 한국어 따옴표 “ ” 또는 ‘ ’ 로 한다. 줄바꿈은 반드시 \\n 으로 쓰고, 다른 제어문자나 실제 줄바꿈을 넣지 말 것. 백슬래시도 넣지 말 것. (이 규칙을 어기면 JSON 파싱이 깨진다.)

반드시 아래 JSON 형식으로만 답해. 다른 말 금지:
{{
  "topic": "오늘 소재 한 줄",
  "image_query": "english keywords for cover photo",
  "instagram": {{"caption": "...", "series": "{series}"}},
  "facebook": {{"text": "..."}},
  "linkedin": {{"text": "..."}},
  "carousel": {{"badge": "...", "cover_bold": "...", "cover_accent": "...", "cover_rest": ["..."], "cover_keyword": "...", "facts": ["...", "...", "..."], "caption": "...", "points": [{{"title": "...", "body": "..."}}, {{"title": "...", "body": "..."}}, {{"title": "...", "body": "..."}}, {{"title": "...", "body": "..."}}, {{"title": "...", "body": "..."}}], "outro_line": "..."}}
}}"""

    # tool-use(구조화 출력)로 받으면 모델이 스키마를 채우므로 JSON 파싱이 깨질 일이 없다.
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    last_err = None
    for attempt in range(3):
        try:
            resp = client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=6000,
                system=system,
                tools=[_CONTENT_TOOL],
                tool_choice={"type": "tool", "name": "post_content"},
                messages=[{"role": "user", "content": user}],
            )
            data = next(b.input for b in resp.content if b.type == "tool_use")
            # 모델이 가끔 객체 대신 문자열로 주는 필드를 정규화(스키마는 강제가 아닌 가이드)
            for k, field in (("instagram", "caption"), ("facebook", "text"), ("linkedin", "text")):
                if isinstance(data.get(k), str):
                    data[k] = {field: data[k]}
            data["carousel"]["cover_keyword"]   # 필수 키 검증
            data["instagram"]["caption"]
            data["topic_meta"] = {"theme": theme, "pillar": pillar, "date": today.strftime("%Y-%m-%d")}
            return data
        except (StopIteration, KeyError, TypeError) as e:
            last_err = e
            print(f"⚠️ 생성 결과 검증 실패 (시도 {attempt + 1}/3): {e}")
    raise RuntimeError(f"콘텐츠 생성 3회 모두 실패: {last_err}")


if __name__ == "__main__":
    print(json.dumps(generate_posts(), ensure_ascii=False, indent=2))
