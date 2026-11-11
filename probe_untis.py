import os
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
    try:
        sy = s.schoolyears()
        print("Schuljahre:")
        for y in sy:
            print(f"  {y.name}: {y.start} bis {y.end} (id: {y.id})")
    except Exception as e:
        print(f"Fehler bei schoolyears: {e}")

    # Aktuelles Schuljahr abfragen
    try:
        current_sy = s.schoolyear()
        print(f"Aktuelles Schuljahr: {current_sy.name} ({current_sy.start} bis {current_sy.end})")
    except Exception as e:
        print(f"Fehler bei s.schoolyear(): {e}")

    s.logout()

if __name__ == "__main__":
    probe()
