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
import json
import datetime
import anthropic

import config


def _today_kst():
    # GitHub Actions는 UTC이므로 KST(+9)로 보정해 요일을 맞춘다.
    return datetime.datetime.utcnow() + datetime.timedelta(hours=9)


def generate_posts() -> dict:
    today = _today_kst()
    weekday = today.weekday()
    theme = config.WEEKLY_THEMES[weekday]
    # 날짜 기반으로 기둥을 순환 선택 (요일마다 다른 기둥)
    pillar = config.CONTENT_PILLARS[today.timetuple().tm_yday % len(config.CONTENT_PILLARS)]
    series = config.IG_SERIES[today.timetuple().tm_yday % len(config.IG_SERIES)]

    roles = config.PLATFORM_ROLES
    system = (
        f"너는 '{config.BRAND_TAGLINE}'인 {config.BRAND_HANDLE}의 소셜 콘텐츠 작가다. "
        f"경력: {config.CAREER}. 미디어아트·전시·공간·AI 크리에이티브 전문가의 1인칭 목소리로 쓴다. "
        "과장된 마케팅 어투, 이모지 남발, 클리셰를 피하고 통찰이 또렷한 문장을 쓴다. 한국어로 쓴다."
    )

    user = f"""오늘 날짜: {today.strftime('%Y-%m-%d (%A)')}
요일 테마: {theme}
오늘의 콘텐츠 기둥: {pillar}

이 하나의 소재를 세 플랫폼의 역할에 맞게 변주해서 작성해줘. 같은 핵심 메시지, 다른 형식.

[Instagram] 포지션: {roles['instagram']['position']} — "{roles['instagram']['question']}"
  스타일: {roles['instagram']['style']}
  분량: {roles['instagram']['length']}
  IG 시리즈 라벨: "{series}" 를 본문 끝부분에 넣을 것.

[Facebook] 포지션: {roles['facebook']['position']} — "{roles['facebook']['question']}"
  스타일: {roles['facebook']['style']}
  분량: {roles['facebook']['length']}

[LinkedIn] 포지션: {roles['linkedin']['position']} — "{roles['linkedin']['question']}"
  스타일: {roles['linkedin']['style']}
  분량: {roles['linkedin']['length']}

그리고 Instagram **캐러셀(여러 장 스와이프)** 슬라이드 텍스트도 만들어줘.
구조: 표지 1장 + 포인트 4장 + 아웃트로(코드가 자동 생성). 저장·체류율을 높이는 교육형 캐러셀.
  - badge: 알약형 카테고리 배지. 영문 대문자 1~2단어 (예: "SPACE NOTE", "MEDIA ART", "AI CREATIVE")
  - cover_bold: 표지 강조 헤드라인(볼드) 한 줄, 한국어 14자 내외, 문장 도입부
  - cover_rest: 표지 보조 라이트 1줄 배열
  - cover_keyword: 표지에서 가장 크게 박히는 결론/주제 한 줄, 한국어 8자 내외
  → cover_bold + cover_rest + cover_keyword 를 위→아래로 읽으면 하나의 훅 문장이 되게.
  - caption: 푸터 캡션 "{series} · parkjunhyuk.xyz"
  - points: 정확히 4개. 각 {{title: 10자 내외 핵심, body: 40자 내외 1~2문장 설명}}. 실용적·구체적으로.
  - outro_line: 마무리 통찰 한 줄(\\n 1회 허용)

반드시 아래 JSON 형식으로만 답해. 다른 말 금지:
{{
  "topic": "오늘 소재 한 줄",
  "instagram": {{"caption": "...", "series": "{series}"}},
  "facebook": {{"text": "..."}},
  "linkedin": {{"text": "..."}},
  "carousel": {{"badge": "...", "cover_bold": "...", "cover_rest": ["..."], "cover_keyword": "...", "caption": "...", "points": [{{"title": "...", "body": "..."}}, {{"title": "...", "body": "..."}}, {{"title": "...", "body": "..."}}, {{"title": "...", "body": "..."}}], "outro_line": "..."}}
}}"""

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=2000,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = resp.content[0].text.strip()
    # 혹시 코드펜스로 감싸 오면 제거
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    data = json.loads(text)
    data["topic_meta"] = {"theme": theme, "pillar": pillar, "date": today.strftime("%Y-%m-%d")}
    return data


if __name__ == "__main__":
    print(json.dumps(generate_posts(), ensure_ascii=False, indent=2))
