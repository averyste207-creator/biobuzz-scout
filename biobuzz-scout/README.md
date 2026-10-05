# BIOBUZZ Scout 🐝

**FTC 2026–2027 BIOBUZZ Scouting Web App**

A clean, modern web application for collecting and analyzing FIRST Tech Challenge match data during the BIOBUZZ season.

## Features

- **Dashboard** – Quick overview of entries, teams, and matches
- **Event & Match Management** – Create events and schedule matches (Red/Blue alliances)
- **BIOBUZZ-specific Scout Form**
  - Autonomous: Leave, Park, Hive Tips, Pollen/Nectar
  - Teleop: Hive Tips, Flowers Owned, Bottom Nectar Bonus, Garden, Park
  - Reliability: Robot Deaths / Disables, reasons, disabled time
  - Qualitative ratings (Driver, Consistency, Intake) 1–5
- **Team Profiles** – Per-team averages, death rate, park/leave rates
- **Rankings** – Sorted by estimated contribution & reliability
- **CSV Export** – Download all scout data
- **Mobile-friendly** Tailwind UI with nature/bee theme

## Local Development

```bash
# Create virtualenv (optional)
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000

SQLite database (`biobuzz.db`) is created automatically.

## Deploy to Render

1. Push this folder to a GitHub repository.
2. Go to [render.com](https://render.com) → **New** → **Web Service**.
3. Connect the repo.
4. Settings:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. (Optional but recommended) Add a **PostgreSQL** database on Render, then set environment variable:
   ```
   DATABASE_URL = <Internal Database URL from Render>
   ```
   The app automatically converts `postgres://` → `postgresql://`.

6. Deploy. Your app will be live at `https://your-service.onrender.com`.

### Free-tier notes
- Free web services spin down after ~15 min of inactivity (cold start ~30–60 s).
- Free Postgres is deleted after 90 days of inactivity — use a paid plan or external DB for long-term storage.
- SQLite works out of the box but is ephemeral on Render’s free disk (data lost on redeploy). Prefer Postgres for production.

## Project Structure

```
biobuzz-scout/
├── main.py              # FastAPI app & routes
├── models.py            # SQLAlchemy models
├── database.py          # DB connection
├── requirements.txt
├── templates/           # Jinja2 HTML
│   ├── base.html
│   ├── index.html
│   ├── scout.html
│   ├── teams.html
│   ├── team_detail.html
│   ├── events.html
│   ├── event_detail.html
│   ├── rankings.html
│   └── entry_detail.html
└── static/              # (optional extra CSS/JS)
```

## Scoring Reference (BIOBUZZ)

| Achievement              | Points |
|--------------------------|--------|
| Auto Leave               | 3      |
| Auto / Teleop Park       | 5      |
| Hive Tip                 | 20     |
| Pollen/Nectar in Cell    | 2 each |
| Bottom Nectar in Flower  | 5      |
| Element in owned Flower  | 2      |
| Garden element           | 1      |

Estimated points in the app are a simplified approximation for ranking purposes.

---

Built for the FTC community. Happy scouting! 🐝
