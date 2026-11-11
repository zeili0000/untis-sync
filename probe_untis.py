import os
import json
import re
import datetime
import webuntis

def probe():
    server = os.environ["UNTIS_SERVER"]
    school = os.environ["UNTIS_SCHOOL"]
    user = os.environ["UNTIS_USER"]
    password = os.environ["UNTIS_PASSWORD"]

    s = webuntis.Session(
        server=server,
        username=user,
        password=password,
        school=school,
        useragent="GitHubActionUntisProbe"
    )
    s.login()

    # 1. Test additional session methods
    print("--- Test zusätzlicher Session-Endpunkte ---")
    extra_calls = [
        ("class_reg_events", lambda: s.class_reg_events(start=datetime.date.today(), end=datetime.date.today() + datetime.timedelta(days=28))),
        ("class_reg_categories", lambda: s.class_reg_categories()),
        ("timetable_with_absences", lambda: s.timetable_with_absences(start=datetime.date.today(), end=datetime.date.today() + datetime.timedelta(days=7))),
    ]
    for name, call in extra_calls:
        try:
            res = call()
            print(f"  [ERLAUBT] {name}: {len(res) if hasattr(res, '__len__') else 'OK'}")
        except Exception as e:
            print(f"  [BLOCKIERT] {name}: {e}")

    # 2. Search whole year (Sept 2026 - July 2027) for exams, test keywords, and period types
    print("\n--- Ganzjahres-Scan nach Prüfungen & Tests (Sep 2026 - Jul 2027) ---")
    start = datetime.date(2026, 9, 1)
    end = datetime.date(2027, 7, 10)
    
    test_keywords = re.compile(r'\b(test|schularbeit|sa|klausur|prüfung|pruefung|smk|wh|wiederholung)\b', re.IGNORECASE)
    
    current_start = start
    chunk = 30
    found_tests = []
    found_types = set()
    found_activity_types = set()

    while current_start < end:
        current_end = min(current_start + datetime.timedelta(days=chunk), end)
        try:
            tt = s.my_timetable(start=current_start, end=current_end)
            for elem in tt:
                raw = elem._data
                lstype = raw.get("lstype", "")
                if lstype:
                    found_types.add(lstype)
                act = raw.get("activityType", "")
                if act:
                    found_activity_types.add(act)

                lstext = raw.get("lstext", "").strip()
                subst = raw.get("substText", "").strip()
                subject = elem.subjects[0].name if elem.subjects else "?"

                if lstype == "ex" or test_keywords.search(lstext) or test_keywords.search(subst):
                    found_tests.append({
                        "date": raw.get("date"),
                        "subject": subject,
                        "lstype": lstype,
                        "activityType": act,
                        "lstext": lstext,
                        "substText": subst,
                    })
        except Exception as e:
            print(f"Fehler bei {current_start}: {e}")
        current_start = current_end + datetime.timedelta(days=1)

    print(f"Gefundene lstype-Werte über das ganze Jahr: {found_types}")
    print(f"Gefundene activityType-Werte: {found_activity_types}")
    print(f"Gefundene Tests/Schularbeiten im gesamten Schuljahr: {len(found_tests)}")
    for t in found_tests[:15]:
        print("  *", t)

    s.logout()

if __name__ == "__main__":
    probe()
