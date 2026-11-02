import os
import json
import datetime
import webuntis
from google.oauth2 import service_account
from googleapiclient.discovery import build

def main():
    creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=["https://www.googleapis.com/auth/calendar"]
    )
    cal_service = build("calendar", "v3", credentials=creds)
    calendar_id = os.environ["CALENDAR_ID"]

    s = webuntis.Session(
        server=os.environ["UNTIS_SERVER"],
        username=os.environ["UNTIS_USER"],
        password=os.environ["UNTIS_PASSWORD"],
        school=os.environ["UNTIS_SCHOOL"],
        useragent="GitHubActionUntisSyncYear"
    )
    s.login()

    start_date = datetime.date.today()
    # Enddatum auf Schuljahresende (Juli 2027)
    final_date = datetime.date(2027, 7, 10)

    print(f"Starte Basis-Sync von {start_date} bis {final_date}...")

    current_start = start_date
    chunk_days = 14

    while current_start < final_date:
        current_end = min(current_start + datetime.timedelta(days=chunk_days), final_date)
        print(f"Lade Block: {current_start} bis {current_end}")

        try:
            timetable = s.my_timetable(start=current_start, end=current_end)

            for elem in timetable:
                subject = elem.subjects[0].long_name if elem.subjects else "Unterricht"
                room = elem.rooms[0].name if elem.rooms else "–"
                teacher = elem.teachers[0].name if elem.teachers else ""
                
                title = f"{subject} ({room})"
                if elem.code == "cancelled":
                    title = f"[ENTFALL] {title}"

                start_dt = elem.start
                end_dt = elem.end
                event_uid = f"untis_{elem.id}@htlsteyr"

                event_body = {
                    "summary": title,
                    "location": room,
                    "description": f"Lehrer: {teacher}\nStatus: {elem.code if elem.code else 'Regulär'}",
                    "start": {"dateTime": start_dt.isoformat(), "timeZone": "Europe/Vienna"},
                    "end": {"dateTime": end_dt.isoformat(), "timeZone": "Europe/Vienna"},
                    "iCalUID": event_uid,
                }

                try:
                    cal_service.events().import_(calendarId=calendar_id, body=event_body).execute()
                except Exception:
                    events_result = cal_service.events().list(
                        calendarId=calendar_id, iCalUID=event_uid
                    ).execute()
                    items = events_result.get("items", [])
                    if items:
                        cal_service.events().update(
                            calendarId=calendar_id, eventId=items[0]["id"], body=event_body
                        ).execute()
        except Exception as e:
            print(f"Fehler im Block {current_start}: {e}")

        current_start = current_end + datetime.timedelta(days=1)

    s.logout()
    print("Gesamtes Schuljahr erfolgreich synchronisiert!")

if __name__ == "__main__":
    main()
