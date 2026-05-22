# EMERGIX — Hospital Live Bed Availability & Booking Platform

> Real-time hospital bed discovery, pre-arrival alerts, and live admin dashboards for Bhubaneswar, Odisha.

---

## Quick Start

```bash
# 1. Clone and enter
git clone <your-repo-url>
cd EMERGIX

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy environment config
cp .env.example .env

# 4. Seed the database (20 Bhubaneswar hospitals + admin accounts)
python seed_data.py

# 5. Run the app
python run.py
```

Open **http://localhost:5000**

---

## Default Credentials

| Role | Username / Email | Password |
|---|---|---|
| Demo Patient | demo@emergix.health | Demo@1234 |
| Hospital Admin (AIIMS) | admin_1 | Admin@123 |
| Hospital Admin (Capital) | admin_2 | Admin@123 |
| … (all 20 hospitals) | admin_1 … admin_20 | Admin@123 |
| Legacy admin | management | management123 |

---

## Project Structure

```
EMERGIX/
├── app/
│   ├── __init__.py          # App factory
│   ├── config.py            # Environment config
│   ├── extensions.py        # Flask extensions
│   ├── models.py            # SQLAlchemy models
│   ├── sockets.py           # WebSocket event handlers
│   ├── blueprints/
│   │   ├── auth.py          # Login, register, logout
│   │   ├── main.py          # Landing, health check
│   │   ├── hospitals.py     # Patient discovery + detail
│   │   ├── admin.py         # Admin dashboard routes
│   │   ├── api.py           # JSON API endpoints
│   │   └── user.py          # Patient dashboard
│   ├── utils/
│   │   ├── geo.py           # Haversine distance calc
│   │   └── decorators.py    # Auth decorators
│   ├── templates/           # Jinja2 templates
│   └── static/
│       ├── css/main.css     # Glassmorphism design system
│       ├── css/admin.css    # Admin dashboard styles
│       └── js/              # Geolocation, alerts, WebSockets
├── seed_data.py             # Database seeder
├── seed_hospitals.json      # 20 Bhubaneswar hospitals (real data)
├── mock_bed_simulator.py    # Background bed count simulator
├── run.py                   # Entry point
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## Architecture

- **Backend:** Python 3.11 + Flask 3.x + Flask-SocketIO (threading mode)
- **Database:** SQLite (dev) / PostgreSQL (prod) via SQLAlchemy 2.x
- **Real-time:** WebSockets via Socket.IO — bed updates broadcast live
- **Geolocation:** Browser GPS + Haversine formula for distance calculation
- **Frontend:** Server-rendered Jinja2 + Alpine.js + vanilla JS (no SPA framework)
- **Design:** Glassmorphism with DM Sans + Outfit fonts, teal/white hospital palette
- **Auth:** Two separate login flows (patient vs hospital admin) with Flask sessions

---

## Key Features

| Feature | Details |
|---|---|
| Auto-location | Browser geolocation → hospitals within 10 km radius |
| Live bed counts | 8 bed types per hospital with real-time WebSocket updates |
| Google Maps navigation | One-tap directions from current location to hospital |
| Pre-arrival alert | Patient sends alert → hospital admin notified instantly via WebSocket |
| Admin bed management | +/− buttons with auto-save and live broadcast to all users |
| Two-role auth | Separate patient and hospital admin login pages and dashboards |
| 20 seed hospitals | Real Bhubaneswar hospitals with accurate GPS coordinates |
| Bed simulator | `mock_bed_simulator.py` randomises counts to simulate live data |

---

## API Endpoints

| Method | Route | Auth | Description |
|---|---|---|---|
| GET | `/api/hospitals/nearby` | Patient | Nearby hospitals with bed data |
| GET | `/api/hospitals/<id>` | Any | Single hospital detail |
| POST | `/api/alerts/create` | Patient | Send pre-arrival alert |
| POST | `/api/alerts/<id>/cancel` | Patient | Cancel own alert |
| PUT | `/api/admin/beds/update` | Admin | Update bed counts |
| PUT | `/api/admin/alerts/<id>/status` | Admin | Acknowledge/admit/cancel alert |
| GET | `/health` | Public | System health check |

---

## Running the Bed Simulator

In a separate terminal while the app is running:

```bash
python mock_bed_simulator.py
```

This randomly adjusts bed counts every 15–45 seconds to simulate live hospital data. Updates are broadcast via WebSocket to all connected patients.

---

## Docker Deployment

```bash
cp .env.example .env
# Edit .env with production SECRET_KEY
docker-compose up --build
```

App runs on port 80 via Nginx reverse proxy.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | (hardcoded dev key) | Flask session secret — **change in production** |
| `DATABASE_URL` | `sqlite:///instance/emergix.db` | Database connection string |
| `FLASK_ENV` | `development` | `development` or `production` |

---

## Acknowledgements

Built for Smart India Hackathon / college project — EMERGIX addresses the real-world problem of bed availability information failures during the COVID-19 pandemic in India, backed by research showing 50–80% reduction in admission delays via digital bed tracking platforms.
