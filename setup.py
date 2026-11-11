#!/usr/bin/env python3
"""
Untis-Sync Setup & Configuration Wizard
Konfiguriert Zugangsdaten, Google-Kalender, ntfy und Sync-Intervalle
und lädt Secrets bei Bedarf direkt verschlüsselt via GitHub CLI hoch.
"""

import os
import sys
import json
import shutil
import getpass
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
ENV_FILE = REPO_ROOT / ".env"
WORKFLOW_FILE = REPO_ROOT / ".github" / "workflows" / "sync.yml"

def colored(text, color_code):
    if sys.stdout.isatty():
        return f"\033[{color_code}m{text}\033[0m"
    return text

def header(title):
    print("\n" + colored(f"=== {title} ===", "1;34"))

def ask(prompt_text, default=None, is_secret=False):
    suffix = f" [{default}]" if default else ""
    full_prompt = f"{prompt_text}{suffix}: "
    if is_secret:
        val = getpass.getpass(full_prompt).strip()
    else:
        val = input(full_prompt).strip()
    return val if val else (default or "")

def ask_choice(prompt_text, options, default_index=0):
    print(f"\n{prompt_text}")
    for i, opt in enumerate(options):
        marker = "*" if i == default_index else " "
        print(f"  [{i + 1}] {opt['label']}")
    while True:
        choice = input(f"Auswahl (1-{len(options)}) [{default_index + 1}]: ").strip()
        if not choice:
            return options[default_index]
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        print(colored("Ungültige Eingabe. Bitte Nummer wählen.", "31"))

def check_gh_cli():
    gh_path = shutil.which("gh")
    if not gh_path:
        local_gh = Path.home() / ".local" / "bin" / "gh"
        if local_gh.exists():
            gh_path = str(local_gh)
    if not gh_path:
        return None
    try:
        res = subprocess.run([gh_path, "auth", "status"], capture_output=True, text=True)
        if res.returncode == 0:
            return gh_path
    except Exception:
        pass
    return None

def update_workflow_schedule(cron_list):
    if not WORKFLOW_FILE.exists():
        return False
    content = WORKFLOW_FILE.read_text(encoding="utf-8")
    
    # schedule Block ersetzen
    schedule_lines = ["  schedule:"]
    for c in cron_list:
        schedule_lines.append(f"    - cron: '{c}'")
    schedule_str = "\n".join(schedule_lines)
    
    pattern = re.compile(r"  schedule:\n(    - cron: [^\n]+\n)+", re.MULTILINE)
    if pattern.search(content):
        new_content = pattern.sub(schedule_str + "\n", content, count=1)
        WORKFLOW_FILE.write_text(new_content, encoding="utf-8")
        return True
    return False

def main():
    print(colored("\n📅 WebUntis ➔ Google Calendar Sync — Setup Wizard", "1;32"))
    print("Dieses Skript hilft dir, alle Einstellungen für GitHub Actions vorzubereiten.\n")

    # 1. Bestehende .env laden falls vorhanden
    existing = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()

    # --- SCHRITT 1: WebUntis Zugangsdaten ---
    header("1. WebUntis Zugangsdaten")
    server = ask("Untis Server (ohne https://)", existing.get("UNTIS_SERVER", "tipo.webuntis.com"))
    school = ask("Untis Schulname (z. B. htl-steyr)", existing.get("UNTIS_SCHOOL", ""))
    user = ask("Untis Benutzername", existing.get("UNTIS_USER", ""))
    
    has_existing_pw = bool(existing.get("UNTIS_PASSWORD"))
    pw_prompt = "Untis Passwort" + (" (Enter übernimmt bestehendes)" if has_existing_pw else "")
    password = ask(pw_prompt, existing.get("UNTIS_PASSWORD", ""), is_secret=True)

    # Optionaler Login-Test
    test_untis = ask("Möchtest du den Untis-Login jetzt kurz testen? (j/n)", "j").lower() in ("j", "ja", "y", "yes")
    if test_untis and school and user and password:
        try:
            import webuntis
            print("  Teste Verbindung zu Untis...", end="", flush=True)
            s = webuntis.Session(
                server=server,
                school=school,
                username=user,
                password=password,
                useragent="UntisSetupTest"
            )
            s.login()
            s.logout()
            print(colored(" OK! Login erfolgreich.", "32"))
        except Exception as e:
            print(colored(f" FEHLER: {e}", "31"))
            print(colored("  Hinweis: Bitte prüfe Server, Schulname, User und Passwort.", "33"))

    # --- SCHRITT 2: Google Kalender ---
    header("2. Google Kalender & Service Account")
    print("Du benötigst einen Google Cloud Service Account und die Ziel-Kalender-ID.")
    
    calendar_id = ask("Google Kalender ID", existing.get("CALENDAR_ID", ""))
    
    # Service Account JSON einlesen
    google_creds_json = existing.get("GOOGLE_CREDENTIALS", "")
    creds_path_default = "service_account.json" if Path("service_account.json").exists() else ""
    
    while True:
        prompt_text = "Pfad zur Service-Account JSON-Datei"
        if google_creds_json:
            prompt_text += " (Enter behält bestehende Credentials)"
        path_input = ask(prompt_text, creds_path_default)
        
        if not path_input and google_creds_json:
            break
        
        p = Path(path_input).expanduser()
        if p.exists() and p.is_file():
            try:
                content = p.read_text(encoding="utf-8")
                parsed = json.loads(content)
                if "client_email" in parsed:
                    google_creds_json = json.dumps(parsed)
                    client_email = parsed.get("client_email")
                    print(colored(f"  ✓ Service Account erkannt: {client_email}", "32"))
                    print(colored(f"  👉 WICHTIG: Teile deinen Google Kalender mit '{client_email}' (Berechtigung: 'Termine ändern')!", "33"))
                    break
                else:
                    print(colored("  Datei ist kein gültiger Google Service-Account Key (client_email fehlt).", "31"))
            except Exception as e:
                print(colored(f"  Ungültige JSON-Datei: {e}", "31"))
        else:
            print(colored(f"  Datei nicht gefunden: {p}", "31"))

    # --- SCHRITT 3: ntfy Push-Benachrichtigungen ---
    header("3. Push-Benachrichtigungen via ntfy.sh (optional)")
    print("Erhalte sofort eine Push-Meldung auf dein Handy bei Entfall oder Vertretung heute/morgen.")
    print("Kostenlos, ohne Account: https://ntfy.sh")
    ntfy_topic = ask("ntfy Topic (Name ohne Domain, leer lassen zum Deaktivieren)", existing.get("NTFY_TOPIC", ""))

    # --- SCHRITT 4: Sync-Intervall konfigurieren ---
    header("4. Synchronisations-Taktung (GitHub Actions)")
    schedule_options = [
        {
            "label": "5 Min während der Schulzeit (Mo-Fr 06-17 Uhr) + 30 Min sonst (Empfohlen)",
            "crons": ["*/5 5-16 * * 1-5", "*/30 * * * *"]
        },
        {
            "label": "Alle 15 Minuten durchgehend",
            "crons": ["*/15 * * * *"]
        },
        {
            "label": "Alle 30 Minuten durchgehend (Sehr sparsam, gut für private Repos)",
            "crons": ["*/30 * * * *"]
        },
        {
            "label": "Bestehenden Zeitplan in sync.yml unverändert lassen",
            "crons": None
        }
    ]
    chosen_schedule = ask_choice("Welches Intervall soll GitHub Actions verwenden?", schedule_options, default_index=0)
    if chosen_schedule["crons"]:
        updated = update_workflow_schedule(chosen_schedule["crons"])
        if updated:
            print(colored("  ✓ .github/workflows/sync.yml erfolgreich aktualisiert.", "32"))

    # --- SCHRITT 5: Konfiguration speichern ---
    header("5. Konfiguration speichern")
    
    # .env schreiben
    env_lines = [
        f"UNTIS_SERVER={server}",
        f"UNTIS_SCHOOL={school}",
        f"UNTIS_USER={user}",
        f"UNTIS_PASSWORD={password}",
        f"CALENDAR_ID={calendar_id}",
        f"GOOGLE_CREDENTIALS={google_creds_json}",
    ]
    if ntfy_topic:
        env_lines.append(f"NTFY_TOPIC={ntfy_topic}")

    ENV_FILE.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    print(colored("  ✓ Lokale .env Datei gespeichert (ist durch .gitignore geschützt).", "32"))

    # --- SCHRITT 6: GitHub Secrets hochladen ---
    header("6. GitHub Secrets hochladen")
    gh_bin = check_gh_cli()
    
    if gh_bin:
        upload_now = ask("GitHub CLI (gh) gefunden! Möchtest du alle Secrets jetzt direkt in dein GitHub-Repo laden? (j/n)", "j").lower() in ("j", "ja", "y", "yes")
        if upload_now:
            print("  Lade Secrets verschlüsselt hoch...")
            cmd = [gh_bin, "secret", "set", "-f", str(ENV_FILE)]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                print(colored("  🎉 Alle GitHub Secrets erfolgreich gesetzt!", "1;32"))
            else:
                print(colored(f"  Fehler beim Upload via gh: {res.stderr.strip()}", "31"))
                print("  Du kannst die Secrets manuell mit folgendem Befehl hochladen:")
                print(f"    gh secret set -f {ENV_FILE.name}")
    else:
        print("GitHub CLI (`gh`) nicht gefunden oder nicht eingeloggt.")
        print("Du hast zwei Möglichkeiten, die Secrets hochzuladen:\n")
        print("Option A (Empfohlen mit gh CLI):")
        print(colored(f"  gh secret set -f {ENV_FILE.name}\n", "1;36"))
        print("Option B (Im Browser unter Repository Settings ➔ Secrets and variables ➔ Actions):")
        print("  - UNTIS_SERVER, UNTIS_SCHOOL, UNTIS_USER, UNTIS_PASSWORD")
        print("  - CALENDAR_ID, GOOGLE_CREDENTIALS")
        if ntfy_topic:
            print("  - NTFY_TOPIC")

    print(colored("\n✅ Setup abgeschlossen! Have fun.", "1;32"))

if __name__ == "__main__":
    main()
