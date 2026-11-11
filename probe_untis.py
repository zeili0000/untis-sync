import os
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
    # server is like: https://kepler.webuntis.com/WebUntis/jsonrpc.do
    base_url = raw_server.split("/jsonrpc.do")[0]
    jsessionid = s.config["jsessionid"] if "jsessionid" in s.config else None
    print(f"Base URL: {base_url}")
    print(f"JSESSIONID: {bool(jsessionid)}")
    person_id = s.login_result.get("personId")
    person_type = s.login_result.get("personType")
    print(f"Login Result: personId={person_id}, personType={person_type}")

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    today_compact = datetime.date.today().strftime("%Y%m%d")
    next_month_compact = (datetime.date.today() + datetime.timedelta(days=28)).strftime("%Y%m%d")

    endpoints_to_try = [
        (f"{base_url}/api/exams?startDate={today_compact}&endDate={next_month_compact}", "api/exams"),
        (f"{base_url}/api/rest/view/v1/exams?startDate={today_compact}&endDate={next_month_compact}", "rest/view/v1/exams"),
        (f"{base_url}/api/public/timetable/weekly/data?elementType={person_type}&elementId={person_id}&date={today_str}&formatId=1", "weekly data"),
    ]

    for url, desc in endpoints_to_try:
        try:
            resp = http.get(url, headers={"Cookie": f"JSESSIONID={jsessionid}"})
            print(f"[{resp.status_code}] {desc}: {resp.text[:300]}")
        except Exception as e:
            print(f"[ERR] {desc}: {e}")

    s.logout()

if __name__ == "__main__":
    probe()
