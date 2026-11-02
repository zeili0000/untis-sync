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
        useragent="GitHubActionUntisSync"
    )
    s.login()

    today = datetime.date.today()
    end_date = today + datetime.timedelta(days=14)

    timetable = s.my_timetable(start=today, end=end_date)

    for elem in timetable:
        subject = elem.subjects[0].longname if elem.subjects else "Unterricht"
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

    s.logout()
    print("Sync erfolgreich abgeschlossen.")

if __name__ == "__main__":
    main()
