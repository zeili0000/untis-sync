# Untis-Sync 📅 ➔ 📲

Automatische Synchronisation zwischen **WebUntis** und **Google Calendar** via **GitHub Actions** – inklusive ntfy Push-Benachrichtigungen bei spontanen Änderungen.

---

## ✨ Features

- 🧹 **Kein Unterricht = Kein Eintrag:** Ausfallende Stunden (`cancelled`) werden automatisch und restlos aus dem Google Kalender gelöscht.
- 🎨 **Farbcodierung für den schnellen Überblick:**
  - 🔴 **Rot (Tomato):** Schularbeiten, Tests & Prüfungen (`[TEST]`)
  - 🟠 **Orange (Tangerine):** Vertretungen & Supplierungen (`[SUPPL.]`)
  - 🟡 **Gelb (Banana):** Raumänderungen (`[RAUM]`)
- 👨‍🏫 **Lehrerkürzel ohne Admin-Rechte:** Funktioniert auch an Schulen, an denen die Standard-API `getTeachers()` für Schüler gesperrt ist (Lösung über interne WebUntis Web-Session).
- 📝 **Minimalistische Metadaten:** Keine Platzhalter wie *"Keine Daten"*, *"k.A."* oder unnötige Status-Zeilen – nur vorhandene Raumnummern, Lehrer und Notizen werden angezeigt.
- 📲 **Instant Push-Benachrichtigungen via [ntfy.sh](https://ntfy.sh):**
  - Erhalte sofort eine Push-Benachrichtigung auf dein Handy, wenn für heute oder morgen eine Stunde entfällt oder eine Supplierung eingetragen wird.
  - Kein Account nötig, 100% Open Source & kostenlos (iOS & Android).
- ⏰ **Schultag-optimierter Zeitplan:**
  - Mo–Fr alle 10 Minuten während der Unterrichtszeit (06:00 – 17:00 CET).
  - Abends & sonntags zur Vorbereitung auf den nächsten Schultag.
  - **100% kostenlos** dank unbegrenzter GitHub Actions Minuten für öffentliche Repositories.

---

## 🚀 Schnellstart & Einrichtung

### 1. Repository forken
Forke dieses Repository in deinen eigenen GitHub-Account.

### 2. Google Calendar vorbereiten
1. Erstelle ein Projekt in der [Google Cloud Console](https://console.cloud.google.com/).
2. Aktiviere die **Google Calendar API**.
3. Erstelle ein **Service Account**, generiere einen neuen JSON-Schlüssel und lade ihn herunter.
4. Öffne deinen Google Kalender (oder erstelle einen neuen eigenen Stundenplan-Kalender) und teile ihn mit der E-Mail-Adresse des Service Accounts (Berechtigung: *Termine ändern*).
5. Kopiere die **Kalender-ID** aus den Kalender-Einstellungen.

### 3. Push-Benachrichtigungen mit ntfy einrichten (optional)
1. Installiere die kostenlose App **ntfy** ([Google Play](https://play.google.com/store/apps/details?id=io.heckel.ntfy) / [App Store](https://apps.apple.com/app/ntfy/id1625396347)) oder öffne [ntfy.sh](https://ntfy.sh) im Browser.
2. Wähle ein beliebiges, geheimes Topic (z. B. `mein-stundenplan-alert-893f`) und abonniere es in der App.

### 4. GitHub Secrets anlegen
Gehe in deinem Repository auf **Settings ➔ Secrets and variables ➔ Actions ➔ New repository secret** und erstelle folgende Secrets:

| Secret | Beschreibung | Beispiel |
|---|---|---|
| `UNTIS_SERVER` | WebUntis Serveradresse | `tipo.webuntis.com` |
| `UNTIS_SCHOOL` | Schulname in WebUntis | `htl-steyr` |
| `UNTIS_USER` | Dein WebUntis Benutzername | `max.mustermann` |
| `UNTIS_PASSWORD` | Dein WebUntis Passwort | `••••••••` |
| `CALENDAR_ID` | Ziel Google Kalender ID | `xyz@group.calendar.google.com` |
| `GOOGLE_CREDENTIALS` | Inhalt der Service-Account JSON-Datei | `{ "type": "service_account", ... }` |
| `NTFY_TOPIC` *(optional)* | Topic-Name für Push-Benachrichtigungen | `mein-stundenplan-alert-893f` |

### 5. Ersten Sync starten
- Gehe auf **Actions ➔ WebUntis Sync ➔ Run workflow**.
- Um das gesamte Schuljahr auf einmal vorab in den Kalender zu laden, führe den Workflow **WebUntis School Year Sync** aus.

---

## 🔒 Privatsphäre & Sicherheit
- Deine Zugangsdaten liegen verschlüsselt in den **GitHub Secrets** und sind auch in einem öffentlichen Repository für niemanden sichtbar.
- GitHub Actions maskiert Secrets automatisch in allen Konsolen-Logs.

---

## 🛠️ Technologien
- Python 3.11+
- [python-webuntis](https://github.com/python-webuntis/python-webuntis)
- [google-api-python-client](https://github.com/googleapis/google-api-python-client)
- [ntfy.sh](https://ntfy.sh)
