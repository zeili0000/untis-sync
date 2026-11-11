import datetime
from untis_core import (
    init_google_calendar,
    init_untis_session,
    fetch_klassen_map,
    fetch_exams_list,
    fetch_teachers_map,
    sync_single_period,
)

def main():
    print("=== Starte WebUntis ➔ Google Calendar Sync (28 Tage) ===")
    cal_service, calendar_id = init_google_calendar()
    s = init_untis_session(useragent="UntisSyncDaily")

    today = datetime.date.today()
    end_date = today + datetime.timedelta(days=28)
    print(f"Zeitraum: {today} bis {end_date}")

    # 1. Master Data & Metadaten vorbereiten
    klassen_map = fetch_klassen_map(s)
    exams_list = fetch_exams_list(s, today, end_date)
    print(f"Gefundene Prüfungen im Zeitraum: {len(exams_list)}")

    # Wöchentliche Datumsliste für Lehrerkürzel-Abruf
    week_dates = [today + datetime.timedelta(days=i * 7) for i in range(5)]
    teachers_map = fetch_teachers_map(s, week_dates)
    print(f"Geladene Lehrerkürzel: {len(teachers_map)}")

    # 2. Stundenplan abrufen
    timetable = s.my_timetable(start=today, end=end_date)
    print(f"Zu verarbeitende Stunden: {len(timetable)}")

    stats = {
        "imported": 0,
        "updated": 0,
        "deleted": 0,
        "skipped_cancelled": 0,
        "errors": 0,
    }

    for elem in timetable:
        res = sync_single_period(
            cal_service, calendar_id, elem, teachers_map, klassen_map, exams_list
        )
        if res in stats:
            stats[res] += 1
        elif "error" in res:
            stats["errors"] += 1

    s.logout()

    print("\n=== Synchronisation abgeschlossen ===")
    print(f"  ✨ Neu importiert: {stats['imported']}")
    print(f"  🔄 Aktualisiert:   {stats['updated']}")
    print(f"  🗑️  Entfall gelöscht: {stats['deleted']}")
    print(f"  ⏭️  Entfall ignoriert: {stats['skipped_cancelled']}")
    if stats["errors"] > 0:
        print(f"  ⚠️ Fehler:        {stats['errors']}")

if __name__ == "__main__":
    main()
