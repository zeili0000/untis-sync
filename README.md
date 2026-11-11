# untis-sync

Automated synchronization between WebUntis and Google Calendar via GitHub Actions, featuring cancellation pruning, event color-coding, student API workarounds, and push notifications.

---

## Why this exists

This tool integrates WebUntis schedules into Google Calendar for unified personal time tracking and scheduling (alongside sleep tracking via *Sleep as Android* and other daily logs). It replaces stale iCal exports with an automated sync pipeline that removes cancelled classes, color-codes substitutions and tests, and delivers instant push notifications when schedules change.

---

## What it does

- **No class = no event:** Cancelled lessons (`elem.code == "cancelled"`) are permanently deleted from Google Calendar via the Calendar API rather than lingering as misleading blocks.
- **Visual Color-Coding:**
  - 🔴 **Tomato (`colorId: "11"`) + `[TEST]`:** Exams, tests, and assessments (identified via the WebUntis exams API and keyword regex in lesson topics).
  - 🟠 **Tangerine (`colorId: "6"`) + `[SUPPL.]`:** Substitutions and irregular periods.
  - 🟡 **Banana (`colorId: "5"`) + `[RAUM]`:** Room changes relative to the original scheduled room.
  - Regular periods keep your calendar's default accent color.
- **Teacher Resolution Workaround:** Student accounts are typically blocked from invoking `getTeachers()` via the standard JSON-RPC interface (`error -8509`). The engine bypasses this limitation by querying the internal weekly web endpoint (`/api/public/timetable/weekly/data`) using an authenticated web session to map teacher IDs to their abbreviations.
- **Minimalist Event Descriptions:** Displays only data that actually exists. Eliminates redundant placeholders such as *"None"*, *"N/A"*, or unnecessary *"Status: Regular"* tags.
- **Instant Push Alerts via [ntfy.sh](https://ntfy.sh):** Sends an immediate notification to your smartphone if a class for today or tomorrow is cancelled, substituted, or moved. Event-level change tracking ensures each modification is only alerted once.

---

## Repository Structure

- **`untis_core.py`**: Core engine handling authenticated WebUntis sessions, teacher/exam extraction, Google Calendar API CRUD operations, and ntfy webhooks.
- **`sync.py`**: Periodic synchronization script targeting a rolling 28-day schedule window via GitHub Actions.
- **`sync_year.py`**: Batch-import script to sync the full academic year in 14-day chunks.
- **`setup.py`**: Interactive terminal wizard that validates credentials, tests API connections, configures sync intervals, and securely uploads repository secrets.
- **`.github/workflows/sync.yml`**: Scheduled workflow executing the recurring sync.
- **`.github/workflows/sync_year.yml`**: Manual workflow for full-year calendar initialization.

---

## Setup & Configuration

### 1. Fork & Clone
```bash
git clone https://github.com/YOUR_USERNAME/untis-sync.git
cd untis-sync
pip install -r requirements.txt
```

### 2. Google Calendar Preparation
1. Open the [Google Cloud Console](https://console.cloud.google.com/), create a project, and enable the **Google Calendar API**.
2. Create a **Service Account**, generate a JSON key, and download it.
3. Open Google Calendar, create or select your target calendar, and share it with the service account email address (Permission: *Make changes to events*).
4. Copy the **Calendar ID** from your calendar settings.

### 3. Run Configuration

#### Option A: Interactive Setup Wizard (Recommended)
```bash
python setup.py
```
The wizard will:
- Prompt for your WebUntis credentials and test login connectivity.
- Read your Google service account JSON key file and calendar ID.
- Prompt for an optional `ntfy` notification topic.
- Let you choose your preferred GitHub Actions sync interval.
- Automatically encrypt and upload all secrets to your GitHub repository using the GitHub CLI (`gh`).

#### Option B: Using `.env` and GitHub CLI
```bash
cp .env.example .env
# Edit credentials in .env
gh secret set -f .env
```

#### Option C: Manual Entry in GitHub Settings
Add the following secrets under **Settings ➔ Secrets and variables ➔ Actions**:

| Secret | Description |
|---|---|
| `UNTIS_SERVER` | WebUntis server domain (e.g. `tipo.webuntis.com`) |
| `UNTIS_SCHOOL` | School identifier in WebUntis |
| `UNTIS_USER` | Your WebUntis username |
| `UNTIS_PASSWORD` | Your WebUntis password |
| `CALENDAR_ID` | Target Google Calendar ID |
| `GOOGLE_CREDENTIALS` | Complete JSON content of the service account key |
| `NTFY_TOPIC` *(optional)* | Topic name for push notifications via ntfy.sh |

---

## Synchronization Schedule

Configured in [`.github/workflows/sync.yml`](.github/workflows/sync.yml):
- **School Hours (Mon–Fri 06:00 – 17:00 CET):** Every 5 minutes
- **Evenings & Weekends:** Every 30 minutes

On public GitHub repositories, GitHub Actions minutes are **unlimited and free**. You can adjust the cron schedule at any time via `setup.py` or by editing `sync.yml` directly.
