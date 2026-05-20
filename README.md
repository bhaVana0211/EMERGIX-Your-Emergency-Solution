# EMERGIX - Hospital Live Bed Availability & Booking Platform

Real-time hospital bed tracking and pre-arrival alerting system for citizens across India. Find available beds instantly, send alerts to hospitals before you arrive, and navigate directly via Google Maps.

---

## Features

- **Geolocation Discovery** - Instantly find hospitals near you using your browser's location.
- **Live Bed Tracking** - See real-time availability of ICU, Oxygen, General, Ventilator, and Emergency beds.
- **Real-time Updates** - Hospital bed changes push to all clients instantly via WebSockets (Socket.IO).
- **Pre-Arrival Alerts** - Patients send a heads-up to the hospital ER while en route.
- **Hospital Admin Dashboard** - Staff portal to manage beds, acknowledge alerts, and update profiles.
- **Google OAuth Login** - Patients can sign in with their Google account for quick access.
- **Pan-India Coverage** - Hospitals across Delhi, Mumbai, Bengaluru, Chennai, Kolkata, Bhubaneswar, and more.

---

## Tech Stack

| Layer        | Technology                                      |
|--------------|--------------------------------------------------|
| Backend      | Python 3.10+, Flask 3.x, Flask-SocketIO          |
| Database     | PostgreSQL + PostGIS (SQLite fallback for dev)    |
| Frontend     | Jinja2 templates, Alpine.js, Tailwind CSS (CDN)  |
| Real-time    | Socket.IO (eventlet), Redis message queue         |
| Auth         | Session-based + Google OAuth (Authlib)            |
| Deployment   | Docker, Docker Compose, Nginx, Gunicorn           |

---

## Project Structure

```
EMERGIX-Your-Emergency-Solution/
├── Emergix/                      # Flask application package
│   ├── __init__.py               # Application factory
│   ├── app.py                    # Entry point (dev server)
│   ├── models.py                 # SQLAlchemy models (User, Hospital, BedInventory, etc.)
│   ├── oauth.py                  # Authlib OAuth registry
│   ├── sockets.py                # Socket.IO event handlers
│   ├── blueprints/
│   │   ├── admin.py              # Hospital admin routes
│   │   ├── api.py                # JSON API endpoints
│   │   ├── auth.py               # Login, Register, Google OAuth, Logout
│   │   ├── hospitals.py          # Discovery & detail pages
│   │   └── main.py               # Landing page & health check
│   ├── utils/
│   │   ├── alerts.py             # Bed type constants & booking ref generator
│   │   ├── decorators.py         # Route protection decorators
│   │   └── geo.py                # Haversine distance & coordinate helpers
│   ├── static/
│   │   ├── css/
│   │   │   ├── main.css          # Core design system (glassmorphism)
│   │   │   └── admin.css         # Admin dashboard styles
│   │   └── js/
│   │       ├── app.js            # Geolocation, hospital fetching, Alpine stores
│   │       ├── admin-realtime.js # Admin Socket.IO client
│   │       ├── alert-modal.js    # Pre-arrival alert form
│   │       └── hospitals-realtime.js  # Patient Socket.IO client
│   └── templates/
│       ├── base.html             # Master layout
│       ├── main/landing.html     # Landing page
│       ├── auth/                 # Login, Register, Hospital Login
│       ├── hospitals/            # Discovery, Detail
│       ├── admin/                # Dashboard, Beds, Alerts, Profile
│       ├── user/                 # Patient dashboard
│       ├── errors/               # 404, 500
│       └── partials/             # Navbar, Footer, Flash messages, Alert modal
├── nginx/
│   └── nginx.conf                # Nginx reverse proxy config
├── docker-compose.yml            # Full-stack orchestration
├── Dockerfile                    # Web service container
├── requirements.txt              # Python dependencies
├── seed_data.py                  # Database seeder
├── seed_hospitals.json           # Hospital dataset (pan-India)
├── mock_bed_simulator.py         # Live bed update simulator (dev/demo)
├── .env.example                  # Environment variable template
├── .gitignore
├── DEPLOYMENT.md                 # Production deployment guide
└── README.md                     # This file
```

---

## Quick Start (Local Development)

### 1. Clone the repository
```bash
git clone https://github.com/bhaVana0211/EMERGIX-Your-Emergency-Solution.git
cd EMERGIX-Your-Emergency-Solution
```

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
cp .env.example .env
```
Edit `.env` and set your values. For local dev, the defaults use SQLite so no Postgres is needed.

### 5. Seed the database
```bash
python seed_data.py
```
This loads 12 hospitals across major Indian cities with demo users.

### 6. Run the application
```bash
python Emergix/app.py
```
Open http://localhost:5000 in your browser.

### 7. (Optional) Run the bed simulator
In a separate terminal:
```bash
python mock_bed_simulator.py
```

---

## Default Credentials

| Role             | Username                       | Password        |
|------------------|--------------------------------|-----------------|
| Hospital Admin   | `admin_aiims_new_delhi`        | `Admin@123`     |
| Legacy Admin     | `management`                   | `management123` |
| Demo Patient     | `priya`                        | `patient123`    |

---

## Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project > **APIs & Services** > **Credentials**
3. Create an **OAuth 2.0 Client ID** (Web application)
4. Add authorized redirect URI: `http://localhost:5000/auth/google/callback`
5. Copy Client ID and Secret into your `.env`:
   ```
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-secret
   ```

---

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for full production deployment instructions using Docker, Nginx, and SSL.

---

## License

MIT License
