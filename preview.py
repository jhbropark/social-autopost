"""
7일치(요일 포맷별) 콘텐츠를 실제 Ideas Pipeline 소재로 생성해 출력한다(게시 없음).
  python preview.py
"""
import datetime
import ideas
import generate

WD = ["월", "화", "수", "목", "금", "토", "일"]


def main():
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    monday = now - datetime.timedelta(days=now.weekday())
    for wd in range(7):
        target = monday + datetime.timedelta(days=wd)
        idea = ideas.pick_idea(target.timetuple().tm_yday)
        d = generate.generate_posts(target=target, idea=idea)
        cz = d.get("carousel", {})
        print("\n========== [" + WD[wd] + "요일] ==========")
        print("소재(Idea):", idea["idea"] if idea else "(없음)")
        print("TOPIC:", d.get("topic"))
        print("표지:", cz.get("cover_bold"), "/", cz.get("cover_keyword"))
        print("FACTS:", " · ".join(cz.get("facts", [])))
        print("--- IG ---\n" + d.get("instagram", {}).get("caption", ""))
        print("--- LinkedIn ---\n" + d.get("linkedin", {}).get("text", ""))
        print("--- Facebook ---\n" + d.get("facebook", {}).get("text", ""))


if __name__ == "__main__":
    main()
