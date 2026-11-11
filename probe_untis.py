import os
import re
import datetime
import webuntis

def probe():
    s = webuntis.Session(
        server=os.environ["UNTIS_SERVER"],
        username=os.environ["UNTIS_USER"],
        password=os.environ["UNTIS_PASSWORD"],
        school=os.environ["UNTIS_SCHOOL"],
        useragent="GitHubActionUntisProbe"
    )
    s.login()

    start = datetime.date(2026, 9, 14)
    end = datetime.date(2027, 7, 10)
    
    test_keywords = re.compile(r'\b(test|schularbeit|sa|klausur|prüfung|pruefung|smk|wh|wiederholung)\b', re.IGNORECASE)
    
    current_start = start
    chunk = 14
    found_tests = []
    found_types = set()
    total_periods = 0
    cancelled_total = 0
    irregular_total = 0

    while current_start < end:
        current_end = min(current_start + datetime.timedelta(days=chunk), end)
        try:
            tt = s.my_timetable(start=current_start, end=current_end)
            total_periods += len(tt)
            for elem in tt:
                raw = elem._data
                lstype = raw.get("lstype", "")
                code = raw.get("code")
                if code == "cancelled":
                    cancelled_total += 1
                elif code == "irregular":
                    irregular_total += 1

                if lstype:
                    found_types.add(lstype)

                lstext = raw.get("lstext", "").strip()
                subst = raw.get("substText", "").strip()
                subject = elem.subjects[0].name if elem.subjects else "?"

                if lstype == "ex" or test_keywords.search(lstext) or test_keywords.search(subst):
                    found_tests.append({
                        "date": raw.get("date"),
                        "subject": subject,
                        "lstype": lstype,
                        "code": code,
                        "lstext": lstext,
                        "substText": subst,
                    })
        except Exception as e:
            print(f"Fehler bei {current_start}: {e}")
        current_start = current_end + datetime.timedelta(days=1)

    print(f"Schuljahr 2026/2027 Gesamtübersicht:")
    print(f"  - Gesamt-Stunden: {total_periods}")
    print(f"  - Entfallene Stunden (cancelled): {cancelled_total}")
    print(f"  - Irreguläre Stunden / Supplierungen (irregular): {irregular_total}")
    print(f"  - Gefundene lstype-Werte: {found_types}")
    print(f"  - Gefundene Tests/Schularbeiten: {len(found_tests)}")
    for t in found_tests[:15]:
        print("    *", t)

    s.logout()

if __name__ == "__main__":
    probe()
