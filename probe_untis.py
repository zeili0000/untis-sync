import os
import json
import datetime
import webuntis

def probe():
    server = os.environ["UNTIS_SERVER"]
    school = os.environ["UNTIS_SCHOOL"]
    user = os.environ["UNTIS_USER"]
    password = os.environ["UNTIS_PASSWORD"]

    print(f"=== WebUntis API Probe für Server: {server}, Schule: {school} ===")
    
    s = webuntis.Session(
        server=server,
        username=user,
        password=password,
        school=school,
        useragent="GitHubActionUntisProbe"
    )
    s.login()
    print("Login erfolgreich!")

    # 1. Master Data Tests
    print("\n--- 1. Master Data Rechte-Test ---")
    endpoints = [
        ("subjects (Fächer)", lambda: s.subjects()),
        ("rooms (Räume)", lambda: s.rooms()),
        ("klassen (Klassen)", lambda: s.klassen()),
        ("teachers (Lehrer)", lambda: s.teachers()),
        ("holidays (Ferien)", lambda: s.holidays()),
        ("statusdata (Statusdaten)", lambda: s.statusdata()),
        ("exam_types (Prüfungsarten)", lambda: s.exam_types()),
        ("exams (Prüfungen)", lambda: s.exams(start=datetime.date.today(), end=datetime.date.today() + datetime.timedelta(days=28))),
    ]

    for name, call in endpoints:
        try:
            res = call()
            count = len(res) if hasattr(res, "__len__") else "OK"
            print(f"  [ERLAUBT] {name}: {count} Einträge")
        except Exception as e:
            print(f"  [BLOCKIERT] {name}: Fehler -> {e}")

    # 2. Timetable & Field Probe
    print("\n--- 2. Stundenplan- & Feld-Analyse (nächste 28 Tage) ---")
    today = datetime.date.today()
    end_date = today + datetime.timedelta(days=28)
    
    try:
        timetable = s.my_timetable(start=today, end=end_date)
        print(f"Stundenplan geladen: {len(timetable)} Einheiten gefunden.")

        all_keys = set()
        codes_found = set()
        types_found = set()
        has_subst_text = 0
        has_lstext = 0
        has_info = 0
        has_bk_text = 0
        cancelled_count = 0
        irregular_count = 0
        exam_type_count = 0

        sample_cancelled = None
        sample_irregular = None
        sample_regular = None

        for elem in timetable:
            raw = getattr(elem, "_data", {})
            all_keys.update(raw.keys())
            
            code = raw.get("code")
            if code:
                codes_found.add(code)
            if code == "cancelled":
                cancelled_count += 1
                if not sample_cancelled:
                    sample_cancelled = raw
            elif code == "irregular":
                irregular_count += 1
                if not sample_irregular:
                    sample_irregular = raw
            elif not sample_regular:
                sample_regular = raw

            lstype = raw.get("lstype")
            if lstype:
                types_found.add(lstype)
            if lstype == "ex":
                exam_type_count += 1

            if raw.get("substText"):
                has_subst_text += 1
            if raw.get("lstext"):
                has_lstext += 1
            if raw.get("info"):
                has_info += 1
            if raw.get("bkText") or raw.get("bkRemark"):
                has_bk_text += 1

        print(f"\nGefundene Rohdaten-Schlüssel in Period-Objekten:\n  {sorted(list(all_keys))}")
        print(f"\nGefundene 'code'-Werte: {codes_found}")
        print(f"Gefundene 'lstype'-Werte: {types_found}")
        print(f"Statistik:")
        print(f"  - Entfallene Stunden (code='cancelled'): {cancelled_count}")
        print(f"  - Irreguläre Stunden / Supplierungen (code='irregular'): {irregular_count}")
        print(f"  - Prüfungs-Stunden (lstype='ex'): {exam_type_count}")
        print(f"  - Stunden mit substText (Vertretungstext): {has_subst_text}")
        print(f"  - Stunden mit lstext (Lehrstoff): {has_lstext}")
        print(f"  - Stunden mit info: {has_info}")
        print(f"  - Stunden mit Klassenbuch-Bemerkungen: {has_bk_text}")

        # Anonymisiertes Schema von Samples
        def sanitize_sample(raw):
            if not raw:
                return None
            return {k: (type(v).__name__ if not isinstance(v, (int, str, bool)) or k in ("id", "date") else v) for k, v in raw.items()}

        print("\nBeispiel-Struktur Regulär:")
        print(" ", json.dumps(sanitize_sample(sample_regular), indent=2))
        if sample_cancelled:
            print("\nBeispiel-Struktur Entfall:")
            print(" ", json.dumps(sanitize_sample(sample_cancelled), indent=2))
        if sample_irregular:
            print("\nBeispiel-Struktur Supplierung:")
            print(" ", json.dumps(sanitize_sample(sample_irregular), indent=2))

    except Exception as e:
        print(f"Fehler bei Stundenplan-Abfrage: {e}")

    s.logout()
    print("\n=== Probe abgeschlossen ===")

if __name__ == "__main__":
    probe()
