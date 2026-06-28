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


def _clean_field(val, field):
    """채널 필드에서 실제 텍스트만 추출한다.
    val 이 dict({field:...}) / 평문 / '{"text":"..."}' 같은 JSON문자열 어느 쪽이든 처리하고,
    리터럴 \\n(역슬래시+n)을 실제 줄바꿈으로 복원한다."""
    text = ""
    if isinstance(val, dict):
        text = val.get(field, "")
    elif isinstance(val, str):
        text = val
        s = val.strip()
        if s.startswith("{") and (f'"{field}"' in s):
            extracted = None
            try:
                obj = json.loads(s)
                if isinstance(obj, dict) and field in obj:
                    extracted = obj[field]
            except Exception:
                # 실제 줄바꿈이 든 JSON유사 문자열은 json.loads 가 실패 → 정규식으로 내부만 추출
                m = re.search(r'"' + re.escape(field) + r'"\s*:\s*"(.*)"\s*\}?\s*$', s, re.S)
                if m:
                    extracted = m.group(1).replace('\\"', '"')
            if isinstance(extracted, str):
                text = extracted
    if not isinstance(text, str):
        text = str(text)
    if "\\n" in text:
        text = text.replace("\\r\\n", "\n").replace("\\n", "\n")
    # 모델이 '해시태그#키워드'처럼 '해시태그' 단어를 붙이는 경우 제거
    text = re.sub(r"해시\s*태그\s*(?=#)", "", text)
    return text.strip()


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
                    "reel_hook": _S,
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


def generate_posts(target=None, variant=0, idea=None, ideas_list=None) -> dict:
    today = target or _today_kst()
    weekday = today.weekday()
    theme = config.WEEKLY_THEMES[weekday]
    corner = theme.split("—")[0].strip()   # 「현장 노트」 같은 코너명
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
        "각 문장은 짧고 또렷하게. 한 문장에 한 가지 생각만 담는다. "
        "★AI 티 제거 규칙(한국어 자연성, 매우 중요): 다음 'AI 어투'를 쓰지 마라. "
        "① 번역투 — '~를 통해/~에 대해/~에 있어(서)' 남발 금지(목적격·'~로'·'~에서'로 직결), "
        "'가지고 있다'→형용사·동사로(경쟁력을 가지고 있다→경쟁력이 강하다), 이중피동 '~되어진다'→'~된다', "
        "'~에 의해'→행위자를 주어로, 영어식 대명사 '그/그녀' 반복 금지(생략하거나 이름 반복), 관형절을 길게 좌향 중첩하지 말고 문장을 끊어라. "
        "② 삭제 1순위 관용구 — '결론적으로/따라서/요약하면/이를 통해/본질적으로/주목할 만하다/시사하는 바가 크다', "
        "과장어 '혁신적·압도적·파격적·획기적'. "
        "③ 헤징 금지 — '~할 수 있을 것으로 보인다' 같은 다중 완충은 단언으로. "
        "④ 접속사 — 문두 '또한·따라서·즉·게다가' 남발 금지, 연결어미(-지만·-며·-고·-어서) 바로 뒤에 쉼표를 찍지 마라. "
        "⑤ 형식명사 — '~는다는 것이다/~인 것이다/~할 것이다'로 문장을 맺지 말고 '~다'로 단언하라(★'것이다' 0회 목표), '~하는 것이'→'~하기가'. "
        "⑥ 접미사 '-적/-성/-화' 연쇄 자제(기술적 토대→기술이 안정적이다). "
        "⑦ 리듬 — 같은 종결('~다') 4문장 연속 금지, 문장 길이를 일부러 들쭉날쭉 섞고(짧은 문장+긴 문장), '~고 있다'는 가급적 단순시제로. "
        "⑧ 장식 — 본문 볼드·대시(—) 남용 금지(대시는 글 전체에서 1~2회). "
        "단, 의미·수치·고유명사·인용은 100% 보존하고, 원문에 없던 비유·수사를 억지로 지어내지 마라(자연스러움이 완벽함보다 우선). "
        "★사실성 규칙(매우 중요): 너는 외부 데이터·통계에 접근할 수 없다. 그러므로 통계·퍼센트·"
        "인원수·배수·금액·연도 같은 구체 수치를 지어내 사실처럼 단정하면 그것은 거짓이다. "
        "검증 가능한 수치가 없으면 숫자를 쓰지 말고, 본인의 1인칭 경험·관찰을 정성적으로 서술하라. "
        "예시가 꼭 필요하면 '가령', '예를 들어'로 가정임을 분명히 밝혀라. "
        "'평균 N명', 'N% 증가' 같은 구체 통계를 근거 없이 만들어내는 것을 절대 금지한다. "
        "해시태그는 '#키워드' 형식으로만 쓰고, '해시태그'라는 단어 자체를 본문에 넣지 마라. "
        "과거 경력을 글에 쓸 때 여러 회사명을 나열하지 마라. 공간·경험 프로젝트를 운영해온 "
        "하나의 경험으로만 언급하고, 특정 회사명은 굳이 쓰지 않아도 된다(쓸 경우에도 한 곳만)."
    )

    import ideas as _ideas
    idea_block = ""
    if ideas_list:
        items = "\n".join(
            f"- {it['idea']}" + (f" ({', '.join(it.get('format', []))})" if it.get("format") else "")
            for it in ideas_list
        )
        idea_block = (
            f"\n[이번 주 위클리 큐레이션 — 아래 {len(ideas_list)}개 실제 아이디어를 '한 편의 다이제스트'로 묶어라]\n"
            f"{items}\n"
            "각 항목을 한 줄 코멘트와 함께 소개하는 큐레이션으로 작성한다. "
            "carousel.points 를 이 항목들로 채워라(각 point.title=항목명 축약, body=한 줄 통찰). "
            "본문(IG·FB·LinkedIn)도 이 항목들을 묶어 '이번 주 주목할 것'으로 정리한다. 지어내지 말 것.\n"
        )
    elif idea:
        idea_block = (
            "\n[오늘의 실제 소재 — 반드시 이 실제 프로젝트/아이디어를 바탕으로 쓸 것]\n"
            f"{_ideas.as_brief(idea)}\n"
            "이건 박준혁 본인이 실제로 다룬/구상한 작업이다. 지어내지 말고 이 내용에 근거해, "
            "요일 포맷의 시선으로 풀어라. (이 소재가 곧 '오늘의 소재'다.)\n"
            "소재에 '후킹메시지'가 있으면 그 메시지를 cover_bold와 reel_hook의 출발점으로 삼아라 — "
            "그대로 복붙하지 말고 표지(12자 이내)·릴스 후크(18자 이내) 규칙에 맞게 다듬되, 핵심 후킹 각도는 살려라.\n"
        )

    user = f"""오늘 날짜: {today.strftime('%Y-%m-%d (%A)')}
요일 포맷: {theme}
오늘의 콘텐츠 기둥: {pillar}
{idea_block}
이 하나의 소재를 세 플랫폼의 역할에 맞게 변주해서 작성해줘. 같은 핵심 메시지, 다른 형식.

★코너명 고정 노출: 모든 채널(IG·FB·LinkedIn) 글의 **맨 첫 줄**에 코너명 "{corner}" 만 단독으로 쓰고, 줄바꿈한 뒤 본문을 시작한다. (다른 시리즈/라벨을 본문 위에 겹쳐 쓰지 말 것.)

[Instagram] 포지션: {roles['instagram']['position']} — "{roles['instagram']['question']}"
  스타일: {roles['instagram']['style']}
  분량: {roles['instagram']['length']}
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
  - cover_bold: 표지 헤드라인(볼드) 한 줄. 한국어 12자 이내. **스크롤을 멈추는 후킹**이어야 한다 — 다음 중 하나:
    ① 통념을 뒤집는 단언/역설("...해야 한다는 건 틀렸다", "...하지 않기로 했다")
    ② 구체적 호기심 갭(스와이프해야 풀리는 질문 — 단 반드시 구체적 대상/상황에 앵커, 막연 금지)
    ③ 또렷한 약속/반전.
    ★미완결 레버(저장·스와이프 유발): 표지가 스스로 답을 다 주지 말 것 — 잘린 목록("망하는 N가지 이유"), before-after, "N가지 중 하나" 처럼 다음 장을 봐야 풀리게 남겨라.
    밋밋한 중립 서술·설명문 금지. (단 뜻은 명확해야 — 난해·말장난은 여전히 금지.)
  - reel_hook: 릴스 0초 후크 한 줄(18자 이내). 0~2초에 스크롤을 멈추는 강한 한 방. **효과 높은 순서**로 골라라 — ① 구체적 결과·숫자("18m 벽이 살아 움직이는 순간", "3초 만에 건물이 사라졌다") ② 통념 반전("AI가 그렸다고 무시했죠, 끝까지 보세요") ③ POV("당신이 전시장 문을 연 순간") ④ 질문("왜 ~할까?"). 소재와 직결, 막연·일반론 금지. (수치는 지어내지 말 것 — 단정 어려우면 ①말고 ②③④로.)
  - cover_rest: 표지 보조 설명 1줄 배열(원소 1개). 16자 이내. cover_bold를 자연스럽게 잇는 짧은 보충.
  - cover_keyword: 표지에서 가장 크게 박히는 한 방. 한국어 7자 이내. **결정적 단언이나 반전**을 담을 것.
    밋밋한 분류 라벨(예: 금지 "키네틱 화면", "빛의 설계", "생성형 파사드" 같은 카테고리명) 금지 — 그 한 줄이 약속·통찰·반전이 되게.
  ※ 표지 카피 규칙(중요): 세 줄을 억지로 한 문장으로 이어붙이지 말 것. 각 줄이 독립적으로 읽혀도 자연스럽고 문법이 맞아야 한다.
    표지만 보고도 '무엇에 관한 글'인지 바로 이해돼야 한다. 도치·생략·말장난으로 호기심만 부풀리는 난해한 카피 금지(예: 금지 "공간 디자이너처럼 AI를 / 다루는 사람은 왜 결과물이 다를까 / 동선이 답이다" — 뜻이 모호함). 쉽고 또렷하게.
  - caption: 푸터 캡션 "{series} · parkjunhyuk.xyz"
  - points: 정확히 5개. 각 {{title: 12자 이내, body: 45자 이내}}.
    · title: 그 장의 핵심을 쉬운 우리말로. "A: B" 같은 라벨식·비유식 제목 금지(예: 금지 "동선: 체이닝 설계", "출구: 포맷 선정"). 무슨 말인지 바로 와닿는 평이한 표현으로.
    · body: 1~2개의 짧고 완결된 문장. 전문용어·영어 약어·번역투 금지. 누구나 한 번에 이해되게.
  - outro_line: 마무리 한 줄. 쉬운 우리말 1~2문장. 두 문장이면 사이에 \\n 1회로 줄을 나눈다(한 문장이 어중간하게 잘리지 않게).
  - image_query: 표지 배경 사진 검색용 **영어** 키워드 2~4단어. 주제를 시각적으로 대표하되 사람 얼굴·글자가 없는 공간/건축/전시/도시/조명/추상 위주. (예: "media art installation", "modern museum interior", "city lights at night", "abstract blue light")
  - facts: 링크드인 표지 우측 요약 패널용 3개. 각 18자 이내. 본문 포인트의 핵심 통찰을 압축한 짧은 단언. **지어낸 통계·수치(퍼센트·인원수·배수 등)를 쓰지 말 것** — 검증 가능한 사실이 아니면 정성적 한 줄로.
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
            # 채널 필드 정규화: 모델이 객체 / 평문 / '{"text":"..."}' 형태의 JSON문자열 중
            # 무엇을 주든 실제 텍스트만 뽑고, 리터럴 \n 을 실제 줄바꿈으로 복원한다.
            for k, field in (("instagram", "caption"), ("facebook", "text"), ("linkedin", "text")):
                v = data.get(k)
                text = _clean_field(v, field)
                if isinstance(v, dict):
                    v[field] = text          # series 등 부가 키 보존
                    data[k] = v
                else:
                    data[k] = {field: text}
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
