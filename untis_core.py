import os
import json
import re
import datetime
import webuntis
from google.oauth2 import service_account
from googleapiclient.discovery import build

TEST_KEYWORD_REGEX = re.compile(
    r'\b(test|schularbeit|sa|klausur|prüfung|pruefung|smk|wiederholungsprüfung|nachtest)\b',
    re.IGNORECASE
)

def init_google_calendar():
    creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=["https://www.googleapis.com/auth/calendar"]
    )
    cal_service = build("calendar", "v3", credentials=creds)
    calendar_id = os.environ["CALENDAR_ID"]
    return cal_service, calendar_id

def init_untis_session(useragent="UntisSync"):
    server = os.environ["UNTIS_SERVER"]
    username = os.environ["UNTIS_USER"]
    password = os.environ["UNTIS_PASSWORD"]
    school = os.environ["UNTIS_SCHOOL"]

    s = webuntis.Session(
        server=server,
        username=username,
        password=password,
        school=school,
        useragent=useragent
    )
    s.login()
    return s

def get_base_url(session):
    raw_server = session.config["server"]
    return raw_server.split("/jsonrpc.do")[0]

def fetch_teachers_map(session, date_list):
    """
    Ruft Lehrerkürzel über den internen WebUntis-Web-Endpunkt ab,
    da der Standard-RPC getTeachers() für Schüler gesperrt ist.
    """
    teachers_map = {}
    base_url = get_base_url(session)
    jsessionid = session.config.get("jsessionid")
    http = session.config.get("_http_session")

    if not jsessionid or not http:
        return teachers_map

    person_id = session.login_result.get("personId")
    person_type = session.login_result.get("personType")

    headers = {"Cookie": f"JSESSIONID={jsessionid}"}

    # Wir gruppieren die Termine nach Wochen, um Redundanz zu minimieren
    checked_weeks = set()
    for d in date_list:
        week_key = (d.year, d.isocalendar()[1])
        if week_key in checked_weeks:
            continue
        checked_weeks.add(week_key)

        date_str = d.strftime("%Y-%m-%d")
        url = (
            f"{base_url}/api/public/timetable/weekly/data"
            f"?elementType={person_type}&elementId={person_id}&date={date_str}&formatId=1"
        )
        try:
            resp = http.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                elements = (
                    data.get("data", {})
                    .get("result", {})
                    .get("data", {})
                    .get("elements", [])
                )
                for el in elements:
                    # Type 2 = Teacher
                    if el.get("type") == 2 and "id" in el and "name" in el:
                        t_name = el["name"].strip()
                        if t_name and t_name != "---":
                            teachers_map[el["id"]] = t_name
        except Exception as e:
            print(f"Warnung beim Abruf der Lehrerkürzel für {date_str}: {e}")

    return teachers_map

def fetch_exams_list(session, start_date, end_date):
    """
    Ruft Prüfungen/Tests über den internen WebUntis api/exams Endpunkt ab.
    """
    exams = []
    base_url = get_base_url(session)
    jsessionid = session.config.get("jsessionid")
    http = session.config.get("_http_session")

    if not jsessionid or not http:
        return exams

    start_compact = start_date.strftime("%Y%m%d")
    end_compact = end_date.strftime("%Y%m%d")
    url = f"{base_url}/api/exams?startDate={start_compact}&endDate={end_compact}"
    headers = {"Cookie": f"JSESSIONID={jsessionid}"}

    try:
        resp = http.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            exams = data.get("data", {}).get("exams", [])
    except Exception as e:
        print(f"Warnung beim Abruf der Prüfungen: {e}")

    return exams

def fetch_klassen_map(session):
    klassen_map = {}
    try:
        for kl in session.klassen():
            klassen_map[kl.id] = kl.name
    except Exception as e:
        print(f"Warnung beim Abruf der Klassen: {e}")
    return klassen_map

def is_exam_period(elem, exams_list):
    """
    Prüft, ob eine Stunde ein Test / eine Schularbeit ist.
    """
    raw = getattr(elem, "_data", {})
    if raw.get("lstype") == "ex":
        return True

    lstext = raw.get("lstext", "").strip()
    subst_text = raw.get("substText", "").strip()

    if TEST_KEYWORD_REGEX.search(lstext) or TEST_KEYWORD_REGEX.search(subst_text):
        return True

    # Abgleich mit api/exams
    elem_date = elem.start.year * 10000 + elem.start.month * 100 + elem.start.day
    elem_start_time = elem.start.hour * 100 + elem.start.minute
    elem_end_time = elem.end.hour * 100 + elem.end.minute

    subject_name = elem.subjects[0].name if elem.subjects else ""

    for ex in exams_list:
        ex_date = ex.get("examDate")
        if ex_date != elem_date:
            continue

        ex_start = ex.get("startTime", 0)
        ex_end = ex.get("endTime", 2400)
        ex_sub = ex.get("subject", "")

        # Zeitliche Überlappung
        if elem_start_time < ex_end and elem_end_time > ex_start:
            if not ex_sub or ex_sub == subject_name or not subject_name:
                return True

    return False

def build_event_payload(elem, teachers_map, klassen_map, exams_list):
    raw = getattr(elem, "_data", {})
    code = raw.get("code")

    # 1. Fach
    if elem.subjects and elem.subjects[0].long_name:
        subject = elem.subjects[0].long_name.strip()
    elif elem.subjects and elem.subjects[0].name:
        subject = elem.subjects[0].name.strip()
    else:
        subject = "Unterricht"

    # 2. Raum
    room = None
    if elem.rooms and elem.rooms[0].name:
        r_name = elem.rooms[0].name.strip()
        if r_name and r_name not in ("-", "–", "---"):
            room = r_name

    # 3. Status- & Farberkennung
    is_test = is_exam_period(elem, exams_list)
    is_subst = (code == "irregular") or bool(raw.get("substText", "").strip())
    
    # Raumänderung (original_rooms weicht ab)
    is_room_change = False
    orig_room = None
    if raw.get("ro") and any("orgid" in r for r in raw["ro"]):
        is_room_change = True
        try:
            if elem.original_rooms and elem.original_rooms[0].name:
                orig_room = elem.original_rooms[0].name.strip()
        except Exception:
            pass

    color_id = None
    prefix = ""

    if is_test:
        color_id = "11"  # Tomato (Rot)
        prefix = "[TEST] "
    elif is_subst:
        color_id = "6"   # Tangerine (Orange)
        prefix = "[SUPPL.] "
    elif is_room_change:
        color_id = "5"   # Banana (Gelb)
        prefix = "[RAUM] "

    # 4. Titel
    if room:
        title = f"{prefix}{subject} ({room})"
    else:
        title = f"{prefix}{subject}"

    # 5. Minimale Beschreibung (nur anzeigen was wirklich da ist, NIE "Keine Daten")
    desc_lines = []
    desc_lines.append(f"📚 Fach: {subject}")

    # Lehrer (über ID-Cache aufgelöst)
    teacher_ids = [t["id"] for t in raw.get("te", []) if "id" in t]
    teacher_names = [teachers_map[tid] for tid in teacher_ids if tid in teachers_map and teachers_map[tid]]
    if teacher_names:
        desc_lines.append(f"👨‍🏫 Lehrer: {', '.join(teacher_names)}")

    # Raum
    if room:
        if is_room_change and orig_room and orig_room != room:
            desc_lines.append(f"🏫 Raum: {room} (statt {orig_room})")
        else:
            desc_lines.append(f"🏫 Raum: {room}")

    # Klassen & Gruppe
    kl_ids = [k["id"] for k in raw.get("kl", []) if "id" in k]
    kl_names = [klassen_map[kid] for kid in kl_ids if kid in klassen_map]
    sg = raw.get("sg", "").strip()

    group_parts = []
    if kl_names:
        group_parts.append(f"Klasse: {', '.join(kl_names)}")
    if sg:
        group_parts.append(f"Gruppe: {sg}")
    if group_parts:
        desc_lines.append(f"👥 {' | '.join(group_parts)}")

    # Status-Hinweis (nur wenn nicht regulär!)
    if is_test:
        desc_lines.append("📝 Status: Test / Schularbeit")
    elif is_subst:
        desc_lines.append("⚠️ Status: Supplierung / Vertretung")

    # Lehrstoff (nur wenn sinnvoll vorhanden, d.h. nicht nur 1 Zeichen Platzhalter)
    lstext = raw.get("lstext", "").strip()
    if lstext and len(lstext) > 1:
        desc_lines.append(f"\n📖 Lehrstoff:\n{lstext}")

    # Notiz / Vertretungstext
    subst_text = raw.get("substText", "").strip()
    if subst_text:
        desc_lines.append(f"\n📢 Notiz:\n{subst_text}")

    description = "\n".join(desc_lines)
    event_uid = f"untis_{elem.id}@htlsteyr"

    event_body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": elem.start.isoformat(), "timeZone": "Europe/Vienna"},
        "end": {"dateTime": elem.end.isoformat(), "timeZone": "Europe/Vienna"},
        "iCalUID": event_uid,
    }
    if room:
        event_body["location"] = room
    if color_id:
        event_body["colorId"] = color_id

    return event_body, is_test, is_subst

def sync_single_period(cal_service, calendar_id, elem, teachers_map, klassen_map, exams_list):
    """
    Synchronisiert eine einzelne Untis-Stunde:
    - Wenn entfallen: Löscht existierende Kalendereinträge und importiert nichts.
    - Wenn aktiv: Erstellt oder aktualisiert den Google-Kalender-Termin mit Farben & Metadaten.
    """
    event_uid = f"untis_{elem.id}@htlsteyr"
    code = getattr(elem, "_data", {}).get("code")

    # ENTALLENES LÖSCHEN
    if code == "cancelled":
        try:
            res = cal_service.events().list(
                calendarId=calendar_id, iCalUID=event_uid
            ).execute()
            items = res.get("items", [])
            if items:
                for item in items:
                    cal_service.events().delete(
                        calendarId=calendar_id, eventId=item["id"]
                    ).execute()
                    print(f"  [ENTFALL GELÖSCHT] {event_uid} ({elem.start})")
                return "deleted"
            else:
                return "skipped_cancelled"
        except Exception as e:
            print(f"  Fehler beim Löschen des Entfalls {event_uid}: {e}")
            return "error_cancelled"

    # AKTIVE STUNDE SYNCHRONISIEREN
    event_body, is_test, is_subst = build_event_payload(
        elem, teachers_map, klassen_map, exams_list
    )

    try:
        cal_service.events().import_(calendarId=calendar_id, body=event_body).execute()
        return "imported"
    except Exception:
        # Event existiert bereits -> Update
        try:
            res = cal_service.events().list(
                calendarId=calendar_id, iCalUID=event_uid
            ).execute()
            items = res.get("items", [])
            if items:
                cal_service.events().update(
                    calendarId=calendar_id, eventId=items[0]["id"], body=event_body
                ).execute()
                return "updated"
            else:
                return "error_not_found"
        except Exception as e:
            print(f"  Fehler beim Aktualisieren von {event_uid}: {e}")
            return "error_update"
