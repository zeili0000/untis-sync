# untis-sync

Synchronisiert WebUntis zuverlässig mit Google Calendar über GitHub Actions – mit automatischer Löschung von Entfällen, Farbcodierung für Tests und Supplierungen sowie Push-Benachrichtigungen via ntfy.

---

## Warum das existiert

Ich tracke mein gesamtes Leben im Google Kalender – Schlaf mit *Sleep as Android*, Termine, Sport und Arbeit –, um eine zentrale Quelle für Zeitplanung und Zeitanalyse zu haben.

WebUntis ist ein geschlossenes Silo: Die offizielle App ist hakelig, iCal-Exporte sind träge, und bestehende Sync-Lösungen haben nervige Schwächen:
- **Entfallene Stunden bleiben im Kalender:** Man sieht Termine, obwohl kein Unterricht stattfindet.
- **Keine Unterscheidung:** Supplierungen, Tests und Raumänderungen sehen im Kalender exakt gleich aus wie regulärer Unterricht.
- **Gesperrte Schnittstellen:** Schüler-Accounts dürfen Lehrernamen über die offizielle WebUntis-API nicht abfragen (`-8509: no right for getTeachers()`).

Dieses Tool löst genau diese Probleme. Es wurde mit Gemini vibe-coded – hier ist es, have fun.

---

## Was das Tool macht

- **Kein Unterricht = Kein Eintrag:** Ausfallende Stunden (`code == "cancelled"`) werden via Google Calendar API restlos aus dem Kalender gelöscht.
- **Farbcodierung (`colorId`):**
  - 🔴 **Rot (`colorId: "11"` - Tomato) + `[TEST]`:** Schularbeiten, Tests und Prüfungen.
  - 🟠 **Orange (`colorId: "6"` - Tangerine) + `[SUPPL.]`:** Supplierungen und Vertretungsstunden.
  - 🟡 **Gelb (`colorId: "5"` - Banana) + `[RAUM]`:** Raumänderungen gegenüber dem Originalraum.
  - Reguläre Stunden behalten die Standardfarbe deines Kalenders.
- **Lehrerkürzel-Bypass:** Da die JSON-RPC-Methode `getTeachers()` für Schüler gesperrt ist, parsed das Skript die internen WebUntis-Webdaten (`/api/public/timetable/weekly/data`) und mappt Lehrer-IDs zu ihren Kürzeln.
- **Prüfungs-Erkennung:** Fragt `/api/exams` ab und gleicht zusätzlich Lehrstoff-Felder auf Test-Keywords ab.
- **Minimalistische Metadaten:** Keine Platzhalter wie *"Keine Daten"*, *"k.A."* oder redundante *"Status: Regulär"*-Zeilen. Es steht nur im Termin, was tatsächlich vorhanden ist (Fach, Lehrer, Raum, Klasse/Gruppe, Notiz/Lehrstoff).
- **Push-Benachrichtigungen via [ntfy.sh](https://ntfy.sh):** Ändert sich heute oder morgen kurzfristig eine Stunde (Entfall, Vertretung, Raum), erhältst du sofort einen Push-Alert auf dein Smartphone. State-Tracking im Kalendereintrag sorgt dafür, dass jede Änderung exakt einmal gemeldet wird.

---

## Setup & Konfiguration

### 1. Repository forken & klonen
```bash
git clone https://github.com/DEIN_USERNAME/untis-sync.git
cd untis-sync
pip install -r requirements.txt
```

### 2. Google Calendar Vorbereitung
1. In der [Google Cloud Console](https://console.cloud.google.com/) ein Projekt anlegen und die **Google Calendar API** aktivieren.
2. Einen **Service Account** anlegen, einen neuen JSON-Schlüssel generieren und lokal speichern (z. B. als `service_account.json`).
3. Google Kalender öffnen, Ziel-Kalender auswählen und diesen für die E-Mail-Adresse des Service Accounts freigeben (Berechtigung: *Termine ändern*).
4. Kalender-ID aus den Kalender-Einstellungen kopieren.

### 3. Konfiguration durchführen

#### Option A: Interaktiver Setup-Wizard (Empfohlen)
Starte einfach den Assistenten im Terminal:
```bash
python setup.py
```
Der Assistent:
- Fragt Untis- und Google-Daten ab und testet auf Wunsch sofort den Login.
- Lässt dich das gewünschte Sync-Intervall für GitHub Actions auswählen.
- Erkennt eine installierte GitHub CLI (`gh`) und lädt alle Secrets **mit einer Bestätigung verschlüsselt in dein GitHub-Repo hoch** – ohne Klick-Orgie im Browser.

#### Option B: Schnell via `.env` und GitHub CLI
```bash
cp .env.example .env
# Werte in .env eintragen
gh secret set -f .env
```

#### Option C: Manuell in den GitHub Repository Settings
Unter **Settings ➔ Secrets and variables ➔ Actions** folgende Secrets anlegen:

| Secret | Beschreibung |
|---|---|
| `UNTIS_SERVER` | Serveradresse (z. B. `tipo.webuntis.com`) |
| `UNTIS_SCHOOL` | Schulname in WebUntis |
| `UNTIS_USER` | WebUntis Benutzername |
| `UNTIS_PASSWORD` | WebUntis Passwort |
| `CALENDAR_ID` | Ziel Google Kalender ID |
| `GOOGLE_CREDENTIALS` | Vollständiger JSON-Inhalt des Service-Account-Keys |
| `NTFY_TOPIC` *(optional)* | Topic-Name für ntfy.sh Push-Alerts |

---

## Synchronisations-Taktung

Der Zeitplan wird in [`.github/workflows/sync.yml`](.github/workflows/sync.yml) gesteuert:
- **Schulzeit (Mo–Fr 06:00 – 17:00 CET):** Alle 5 Minuten
- **Außerhalb & Wochenende:** Alle 30 Minuten

In öffentlichen GitHub-Repositories sind GitHub Actions Runner-Minuten **vollständig unbegrenzt und kostenlos**. Über `setup.py` kann der Takt jederzeit angepasst werden.

Für einen einmaligen Komplettabruf des ganzen Schuljahres existiert der manuelle Workflow **WebUntis School Year Sync** (`sync_year.py`).
