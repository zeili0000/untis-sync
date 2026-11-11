import datetime
from untis_core import (
    init_google_calendar,
    init_untis_session,
    fetch_klassen_map,
    fetch_exams_list,
    fetch_teachers_map,
    sync_single_period,
)

def get_schoolyear_end(session, default_date=datetime.date(2027, 7, 11)):
    today = datetime.date.today()
    try:
        for sy in session.schoolyears():
            sy_start = sy.start.date() if hasattr(sy.start, "date") else sy.start
            sy_end = sy.end.date() if hasattr(sy.end, "date") else sy.end
            if sy_start <= today <= sy_end:
                return sy_end
    except Exception as e:
        print(f"Hinweis: Schuljahr konnte nicht dynamisch bestimmt werden ({e}). Nutze Fallback.")
    return default_date

def main():
    print("=== Starte Gesamtschuljahr WebUntis ➔ Google Calendar Sync ===")
    cal_service, calendar_id = init_google_calendar()
    s = init_untis_session(useragent="UntisSyncYear")

    today = datetime.date.today()
    final_date = get_schoolyear_end(s)
    print(f"Synchronisationszeitraum: {today} bis {final_date}")

    # 1. Globale Master Data laden
    klassen_map = fetch_klassen_map(s)
    print(f"Geladene Klassen: {len(klassen_map)}")

    # Prüfungen für das gesamte restliche Schuljahr laden
    exams_list = fetch_exams_list(s, today, final_date)
    print(f"Gefundene Prüfungen im Schuljahr: {len(exams_list)}")

    current_start = today
    chunk_days = 14
    global_teachers_map = {}

    total_stats = {
        "imported": 0,
        "updated": 0,
        "deleted": 0,
        "skipped_cancelled": 0,
        "errors": 0,
    }

    while current_start <= final_date:
        current_end = min(current_start + datetime.timedelta(days=chunk_days), final_date)
        print(f"\nVerarbeite Block: {current_start} bis {current_end}")

        # Lehrerkürzel für diesen Block aktualisieren
        num_weeks = max(1, (current_end - current_start).days // 7 + 2)
        block_dates = [current_start + datetime.timedelta(days=i * 7) for i in range(num_weeks)]
        new_teachers = fetch_teachers_map(s, block_dates)
        global_teachers_map.update(new_teachers)

        try:
            timetable = s.my_timetable(start=current_start, end=current_end)
            print(f"  Stunden in diesem Block: {len(timetable)}")

            for elem in timetable:
                res = sync_single_period(
                    cal_service,
                    calendar_id,
                    elem,
                    global_teachers_map,
                    klassen_map,
                    exams_list,
                )
                if res in total_stats:
                    total_stats[res] += 1
                elif "error" in res:
                    total_stats["errors"] += 1

        except Exception as e:
            print(f"  Fehler im Block {current_start} bis {current_end}: {e}")

        current_start = current_end + datetime.timedelta(days=1)

    s.logout()

    print("\n==========================================")
    print(" Schuljahr-Sync erfolgreich abgeschlossen!")
    print("==========================================")
    print(f"  ✨ Neu importiert: {total_stats['imported']}")
    print(f"  🔄 Aktualisiert:   {total_stats['updated']}")
    print(f"  🗑️  Entfall gelöscht: {total_stats['deleted']}")
    print(f"  ⏭️  Entfall ignoriert: {total_stats['skipped_cancelled']}")
    if total_stats["errors"] > 0:
        print(f"  ⚠️ Fehler:        {total_stats['errors']}")

if __name__ == "__main__":
    main()
