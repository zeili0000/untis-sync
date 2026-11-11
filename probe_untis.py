import os
import json
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
        useragent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    s.login()

    http = s.config["_http_session"]
    raw_server = s.config["server"]
    base_url = raw_server.split("/jsonrpc.do")[0]
    jsessionid = s.config["jsessionid"]

    today_compact = datetime.date.today().strftime("%Y%m%d")
    end_compact = (datetime.date.today() + datetime.timedelta(days=90)).strftime("%Y%m%d")

    # 1. Exams
    exams_url = f"{base_url}/api/exams?startDate={today_compact}&endDate={end_compact}"
    resp_exams = http.get(exams_url, headers={"Cookie": f"JSESSIONID={jsessionid}"})
    print("=== EXAMS RESPONSE ===")
    print(resp_exams.text)

    # 2. Check elements in weekly data
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    person_id = s.login_result.get("personId")
    person_type = s.login_result.get("personType")
    weekly_url = f"{base_url}/api/public/timetable/weekly/data?elementType={person_type}&elementId={person_id}&date={today_str}&formatId=1"
    resp_weekly = http.get(weekly_url, headers={"Cookie": f"JSESSIONID={jsessionid}"})
    weekly_json = resp_weekly.json()
    elements = weekly_json.get("data", {}).get("result", {}).get("data", {}).get("elements", [])
    print("\n=== WEEKLY DATA ELEMENTS TYPES ===")
    for el in elements:
        print(f"  Type: {el.get('type')}, ID: {el.get('id')}, Name: {el.get('name')}, Display: {el.get('displayStyle')}")

    s.logout()

if __name__ == "__main__":
    probe()
