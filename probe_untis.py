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

    today = datetime.date.today()
    end_date = today + datetime.timedelta(days=28)
    timetable = s.my_timetable(start=today, end=end_date)

    print("=== Analyse von Lehrstoff (lstext) und Vertretungstext (substText) ===")
    
    test_keywords = re.compile(r'\b(test|schularbeit|sa|klausur|prüfung|pruefung|smk|wh|wiederholung)\b', re.IGNORECASE)

    subst_samples = []
    test_samples = []
    lstext_samples = []

    for elem in timetable:
        raw = getattr(elem, "_data", {})
        lstext = raw.get("lstext", "").strip()
        subst = raw.get("substText", "").strip()
        code = raw.get("code")

        # Subject name
        subject = elem.subjects[0].name if elem.subjects else "?"
        
        if subst:
            subst_samples.append(f"[{code}] Fach: {subject} | substText: '{subst}' | Lehrstoff: '{lstext}'")

        if test_keywords.search(lstext) or test_keywords.search(subst):
            test_samples.append(f"Fach: {subject} | Datum: {raw.get('date')} | Lehrstoff: '{lstext}' | substText: '{subst}'")

        if lstext and len(lstext_samples) < 10:
            lstext_samples.append(f"Fach: {subject} | lstext: '{lstext}'")

    print(f"\n--- Gefundene Test/Schularbeit-Einträge ({len(test_samples)}) ---")
    for t in test_samples:
        print("  *", t)

    print(f"\n--- Gefundene Vertretungstexte ({len(subst_samples)}) ---")
    for s_item in subst_samples:
        print("  *", s_item)

    print(f"\n--- Stichprobe Lehrstoff-Texte ({len(lstext_samples)}) ---")
    for l_item in lstext_samples:
        print("  *", l_item)

    # Check if there is any teacher info inside te or session
    sample_period = timetable[0]._data if timetable else {}
    print(f"\n--- Teacher Rohdaten Struktur in Period: {sample_period.get('te')} ---")

    s.logout()

if __name__ == "__main__":
    probe()
